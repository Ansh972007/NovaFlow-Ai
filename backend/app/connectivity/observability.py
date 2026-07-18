"""ECP observability."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.database import ConnectorConnection, ConnectorEvent, ConnectorSyncJob


def connection_health(db: Session, conn: ConnectorConnection) -> dict[str, Any]:
    recent = (
        db.query(ConnectorEvent)
        .filter(ConnectorEvent.connection_id == conn.id)
        .order_by(ConnectorEvent.create_time.desc())
        .limit(20)
        .all()
    )
    failures = sum(1 for e in recent if e.status == "failed")
    avg_latency = int(sum(e.latency_ms or 0 for e in recent) / max(len(recent), 1))
    status = "healthy" if failures <= 1 else ("degraded" if failures <= 5 else "unhealthy")
    return {
        "connection_id": conn.id,
        "connector_type": conn.connector_type,
        "status": status,
        "recent_events": len(recent),
        "failures": failures,
        "avg_latency_ms": avg_latency,
    }


def workspace_connectivity_metrics(db: Session, *, workspace_id: int) -> dict[str, Any]:
    connections = db.query(ConnectorConnection).filter(ConnectorConnection.workspace_id == workspace_id).count()
    sync_jobs = db.query(ConnectorSyncJob).filter(ConnectorSyncJob.workspace_id == workspace_id).count()
    events = db.query(ConnectorEvent).filter(ConnectorEvent.workspace_id == workspace_id).count()
    failed_syncs = (
        db.query(ConnectorSyncJob)
        .filter(ConnectorSyncJob.workspace_id == workspace_id, ConnectorSyncJob.status == "failed")
        .count()
    )
    return {
        "connections": connections,
        "sync_jobs": sync_jobs,
        "events": events,
        "failed_syncs": failed_syncs,
        "sync_success_rate": round(1 - failed_syncs / max(sync_jobs, 1), 2),
    }
