"""KOS ingestion engine — upload, URL, sync connectors."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.config import UPLOAD_DIR
from app.database import KnowledgeBase, KnowledgeFile, KnowledgeSyncJob
from app.knowledge_os.indexing import index_document
from app.knowledge_os.parsing import detect_document_type, parse_document


def _content_hash(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def ingest_uploaded_file(
    db: Session,
    *,
    kb: KnowledgeBase,
    record: KnowledgeFile,
    folder_id: str | None = None,
    chunk_size: int = 1000,
    chunk_overlap: int = 100,
    auto_index: bool = True,
) -> dict[str, Any]:
    """Process an uploaded file through parse → index pipeline."""
    path = UPLOAD_DIR / record.file_path
    if path.exists() and hasattr(record, "content_hash"):
        record.content_hash = _content_hash(path)
    if hasattr(record, "document_type"):
        record.document_type = detect_document_type(path)
    if folder_id and hasattr(record, "folder_id"):
        record.folder_id = folder_id
    if hasattr(record, "lifecycle_status"):
        record.lifecycle_status = "published"
    db.commit()

    if auto_index:
        result = index_document(db, record, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        return {"file_id": record.id, "indexed": True, **result}
    return {"file_id": record.id, "indexed": False, "status": record.status}


def create_sync_job(
    db: Session,
    *,
    knowledge_id: int,
    workspace_id: int,
    connector_type: str,
    config: dict | None = None,
) -> KnowledgeSyncJob:
    job = KnowledgeSyncJob(
        knowledge_id=knowledge_id,
        workspace_id=workspace_id,
        connector_type=connector_type,
        status="pending",
        config_json=json.dumps(config or {}),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def run_sync_job(db: Session, job: KnowledgeSyncJob) -> dict[str, Any]:
    """Execute a sync job — connector plugins handle source-specific logic."""
    from app.knowledge_os.plugins import get_connector

    job.status = "running"
    job.update_time = datetime.utcnow()
    db.commit()
    try:
        connector = get_connector(job.connector_type)
        result = connector.sync(db, job)
        job.status = "completed"
        job.last_sync_at = datetime.utcnow()
        job.error_message = ""
        db.commit()
        return result
    except Exception as exc:
        job.status = "failed"
        job.error_message = str(exc)[:1000]
        db.commit()
        raise


def ingest_url_content(
    db: Session,
    *,
    kb: KnowledgeBase,
    file_name: str,
    text: str,
    source_url: str = "",
) -> KnowledgeFile:
    """Ingest fetched URL/text as a document."""
    from app.knowledge_os.versioning import create_document_version

    kb_dir = UPLOAD_DIR / str(kb.id)
    kb_dir.mkdir(parents=True, exist_ok=True)
    safe_name = file_name.replace("/", "_").replace("\\", "_")[:200] or "web_page.txt"
    if not safe_name.endswith(".txt"):
        safe_name = f"{safe_name}.txt"
    rel = f"{kb.id}/{safe_name}"
    path = UPLOAD_DIR / rel
    path.write_text(text, encoding="utf-8")

    record = KnowledgeFile(
        knowledge_id=kb.id,
        file_name=safe_name,
        file_path=rel,
        status=5,
    )
    if hasattr(record, "document_type"):
        record.document_type = "web"
    if hasattr(record, "metadata_json"):
        record.metadata_json = json.dumps({"source_url": source_url})
    db.add(record)
    db.commit()
    db.refresh(record)

    parsed = parse_document(path)
    if hasattr(record, "metadata_json"):
        meta = json.loads(record.metadata_json or "{}")
        meta.update(parsed.get("metadata") or {})
        record.metadata_json = json.dumps(meta)
    create_document_version(db, record, created_by=kb.user_id, change_summary="URL ingest")
    index_document(db, record)
    return record
