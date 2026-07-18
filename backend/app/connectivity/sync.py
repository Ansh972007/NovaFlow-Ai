"""ECP sync engine."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.database import ConnectorConnection, ConnectorSyncJob


def create_sync_job(
    db: Session,
    *,
    connection: ConnectorConnection,
    direction: str = "inbound",
    mode: str = "incremental",
    config: dict | None = None,
) -> ConnectorSyncJob:
    job = ConnectorSyncJob(
        id=uuid.uuid4().hex,
        connection_id=connection.id,
        workspace_id=connection.workspace_id,
        direction=direction,
        mode=mode,
        status="pending",
        config_json=json.dumps(config or {}),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def run_sync_job(db: Session, job: ConnectorSyncJob) -> dict[str, Any]:
    from app.connectivity.plugins import get_connector_plugin

    job.status = "running"
    job.update_time = datetime.utcnow()
    db.commit()
    conn = db.get(ConnectorConnection, job.connection_id)
    if not conn:
        job.status = "failed"
        job.error_message = "Connection not found"
        db.commit()
        return {"error": job.error_message}
    try:
        plugin = get_connector_plugin(conn.connector_type)
        result = plugin.sync(db, conn, job)
        job.status = "completed"
        job.last_sync_at = datetime.utcnow()
        job.next_sync_at = datetime.utcnow() + timedelta(hours=1)
        job.checkpoint_json = json.dumps(result.get("checkpoint") or {})
        job.error_message = ""
        db.commit()
        return result
    except Exception as exc:
        job.status = "failed"
        job.error_message = str(exc)[:1000]
        db.commit()
        raise


def sync_dict(job: ConnectorSyncJob) -> dict[str, Any]:
    return {
        "id": job.id,
        "connection_id": job.connection_id,
        "direction": job.direction,
        "mode": job.mode,
        "status": job.status,
        "last_sync_at": job.last_sync_at.isoformat() if job.last_sync_at else None,
        "next_sync_at": job.next_sync_at.isoformat() if job.next_sync_at else None,
        "error_message": job.error_message,
    }
