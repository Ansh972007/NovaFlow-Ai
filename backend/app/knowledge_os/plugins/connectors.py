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


class S3Connector(BaseConnector):
    connector_type = "s3"
    description = "S3 bucket sync (requires object storage config)"

    def sync(self, db: Session, job: KnowledgeSyncJob) -> dict[str, Any]:
        config = json.loads(job.config_json or "{}")
        prefix = config.get("prefix") or ""
        result = ConnectorResult(skipped=1)
        result.errors.append(
            f"S3 sync stub — configure bucket={config.get('bucket', '')} prefix={prefix}; use manual upload until credentials wired"
        )
        return result.to_dict()


class GitConnector(BaseConnector):
    connector_type = "git"
    description = "Git repository sync"

    def sync(self, db: Session, job: KnowledgeSyncJob) -> dict[str, Any]:
        config = json.loads(job.config_json or "{}")
        repo_url = config.get("repo_url") or ""
        result = ConnectorResult(skipped=1)
        result.errors.append(f"Git sync stub — repo={repo_url}; schedule via webhook or manual ingest")
        return result.to_dict()


class WebhookConnector(BaseConnector):
    connector_type = "webhook"
    description = "Webhook-triggered incremental sync"

    def sync(self, db: Session, job: KnowledgeSyncJob) -> dict[str, Any]:
        kb = db.get(KnowledgeBase, job.knowledge_id)
        if not kb:
            return ConnectorResult(errors=["Collection not found"]).to_dict()
        return ManualConnector().sync(db, job)
