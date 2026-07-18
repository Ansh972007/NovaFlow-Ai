"""ECP analytics."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.connectivity.observability import workspace_connectivity_metrics
from app.database import ConnectorConnection, ConnectorEvent


def connector_usage_report(db: Session, *, workspace_id: int, limit: int = 20) -> list[dict[str, Any]]:
    rows = (
        db.query(ConnectorEvent)
        .filter(ConnectorEvent.workspace_id == workspace_id)
        .order_by(ConnectorEvent.create_time.desc())
        .limit(500)
        .all()
    )
    stats: dict[str, dict] = {}
    for r in rows:
        cid = r.connection_id or "unknown"
        if cid not in stats:
            stats[cid] = {"connection_id": cid, "events": 0, "failures": 0, "latency_ms": 0}
        stats[cid]["events"] += 1
        stats[cid]["failures"] += 1 if r.status == "failed" else 0
        stats[cid]["latency_ms"] += r.latency_ms or 0
    report = []
    for cid, s in stats.items():
        s["avg_latency_ms"] = int(s["latency_ms"] / max(s["events"], 1))
        s["success_rate"] = round(1 - s["failures"] / max(s["events"], 1), 2)
        report.append(s)
    report.sort(key=lambda x: -x["events"])
    return report[:limit]


def workspace_analytics(db: Session, *, workspace_id: int) -> dict[str, Any]:
    metrics = workspace_connectivity_metrics(db, workspace_id=workspace_id)
    by_type: dict[str, int] = {}
    for conn in db.query(ConnectorConnection).filter(ConnectorConnection.workspace_id == workspace_id).all():
        by_type[conn.connector_type] = by_type.get(conn.connector_type, 0) + 1
    return {
        **metrics,
        "connectors_by_type": by_type,
        "usage": connector_usage_report(db, workspace_id=workspace_id),
    }
