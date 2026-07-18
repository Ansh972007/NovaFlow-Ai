"""Built-in KOS sync connectors."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.database import KnowledgeBase, KnowledgeFile, KnowledgeSyncJob
from app.knowledge_os.indexing import index_document
from app.knowledge_os.plugins.base import BaseConnector, ConnectorResult


class ManualConnector(BaseConnector):
    connector_type = "manual"
    description = "Manual upload — no remote sync"

    def sync(self, db: Session, job: KnowledgeSyncJob) -> dict[str, Any]:
        pending = (
            db.query(KnowledgeFile)
            .filter(KnowledgeFile.knowledge_id == job.knowledge_id, KnowledgeFile.status.in_([5, 3]))
            .limit(50)
            .all()
        )
        result = ConnectorResult()
        for record in pending:
            try:
                index_document(db, record)
                result.imported += 1
                result.files.append({"file_id": record.id, "status": record.status})
            except Exception as exc:
                result.errors.append(str(exc)[:200])
        return result.to_dict()


_TEXT_SUFFIXES = {".txt", ".md", ".markdown", ".rst", ".json", ".yaml", ".yml", ".csv", ".html", ".xml", ".py", ".js", ".ts"}


class S3Connector(BaseConnector):
    connector_type = "s3"
    description = "S3 bucket sync into the collection via object storage"

    def sync(self, db: Session, job: KnowledgeSyncJob) -> dict[str, Any]:
        from app.config import UPLOAD_DIR
        from app.data.storage.s3 import S3CompatibleStorage
        from app.knowledge_os.versioning import create_document_version

        config = json.loads(job.config_json or "{}")
        prefix = config.get("prefix") or ""
        result = ConnectorResult()
        kb = db.get(KnowledgeBase, job.knowledge_id)
        if not kb:
            return ConnectorResult(errors=["Collection not found"]).to_dict()
        if not config.get("bucket"):
            return ConnectorResult(errors=["S3 bucket not configured in sync job config"]).to_dict()

        storage = S3CompatibleStorage(
            bucket=config["bucket"],
            endpoint=config.get("endpoint") or "",
            access_key=config.get("access_key") or "",
            secret_key=config.get("secret_key") or "",
            region=config.get("region") or "auto",
        )
        try:
            objects = storage.list_objects(prefix=prefix, limit=int(config.get("limit") or 50))
        except Exception as exc:
            return ConnectorResult(errors=[f"S3 list failed: {exc}"]).to_dict()

        kb_dir = UPLOAD_DIR / str(kb.id)
        kb_dir.mkdir(parents=True, exist_ok=True)
        for obj in objects:
            name = obj.key.rsplit("/", 1)[-1]
            if not name:
                continue
            existing = (
                db.query(KnowledgeFile)
                .filter(KnowledgeFile.knowledge_id == kb.id, KnowledgeFile.file_name == name)
                .first()
            )
            if existing:
                result.skipped += 1
                continue
            try:
                raw = storage.get(obj.key)
                rel = f"{kb.id}/{name}"
                (UPLOAD_DIR / rel).write_bytes(raw)
                record = KnowledgeFile(knowledge_id=kb.id, file_name=name, file_path=rel, status=5)
                db.add(record)
                db.commit()
                db.refresh(record)
                create_document_version(db, record, created_by=kb.user_id, change_summary=f"S3 sync {obj.key}")
                index_document(db, record)
                result.imported += 1
                result.files.append({"file_id": record.id, "key": obj.key})
            except Exception as exc:
                result.errors.append(f"{obj.key}: {str(exc)[:150]}")
        return result.to_dict()


class GitConnector(BaseConnector):
    connector_type = "git"
    description = "Git repository sync into the collection via system git"

    def sync(self, db: Session, job: KnowledgeSyncJob) -> dict[str, Any]:
        import shutil
        import subprocess
        import tempfile
        from pathlib import Path

        from app.config import UPLOAD_DIR
        from app.knowledge_os.versioning import create_document_version

        config = json.loads(job.config_json or "{}")
        repo_url = config.get("repo_url") or ""
        result = ConnectorResult()
        kb = db.get(KnowledgeBase, job.knowledge_id)
        if not kb:
            return ConnectorResult(errors=["Collection not found"]).to_dict()
        if not repo_url:
            return ConnectorResult(errors=["repo_url not configured"]).to_dict()
        if not shutil.which("git"):
            return ConnectorResult(errors=["git binary not available on host"]).to_dict()

        tmp = tempfile.mkdtemp(prefix="nf_kos_git_")
        try:
            clone = ["git", "clone", "--depth", "1", "--quiet"]
            if config.get("branch"):
                clone += ["--branch", str(config["branch"])]
            clone += [repo_url, tmp]
            proc = subprocess.run(clone, capture_output=True, text=True, timeout=120)
            if proc.returncode != 0:
                return ConnectorResult(errors=[f"clone failed: {proc.stderr[:200]}"]).to_dict()
            root = Path(tmp)
            count = 0
            for path in sorted(root.rglob("*")):
                if count >= int(config.get("limit") or 100):
                    break
                if not path.is_file() or "/.git/" in path.as_posix():
                    continue
                if path.suffix.lower() not in _TEXT_SUFFIXES:
                    continue
                name = path.relative_to(root).as_posix().replace("/", "_")
                existing = (
                    db.query(KnowledgeFile)
                    .filter(KnowledgeFile.knowledge_id == kb.id, KnowledgeFile.file_name == name)
                    .first()
                )
                if existing:
                    result.skipped += 1
                    continue
                try:
                    rel = f"{kb.id}/{name}"
                    (UPLOAD_DIR / str(kb.id)).mkdir(parents=True, exist_ok=True)
                    (UPLOAD_DIR / rel).write_bytes(path.read_bytes())
                    record = KnowledgeFile(knowledge_id=kb.id, file_name=name, file_path=rel, status=5)
                    db.add(record)
                    db.commit()
                    db.refresh(record)
                    create_document_version(db, record, created_by=kb.user_id, change_summary="Git sync")
                    index_document(db, record)
                    result.imported += 1
                    count += 1
                except Exception as exc:
                    result.errors.append(f"{name}: {str(exc)[:150]}")
            return result.to_dict()
        except subprocess.TimeoutExpired:
            return ConnectorResult(errors=["git clone timed out"]).to_dict()
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class WebhookConnector(BaseConnector):
    connector_type = "webhook"
    description = "Webhook-triggered incremental sync"

    def sync(self, db: Session, job: KnowledgeSyncJob) -> dict[str, Any]:
        kb = db.get(KnowledgeBase, job.knowledge_id)
        if not kb:
            return ConnectorResult(errors=["Collection not found"]).to_dict()
        return ManualConnector().sync(db, job)
