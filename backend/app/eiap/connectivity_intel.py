"""EIAP connectivity intelligence — connector health, fallback recommendations.

Reuses connectivity.analytics and connectivity.observability.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.connectivity.analytics import connector_usage_report, workspace_analytics
from app.connectivity.observability import connection_health, workspace_connectivity_metrics
from app.eiap.recommendations import create_recommendation


def analyze_connectivity(db: Session, *, workspace_id: int) -> dict[str, Any]:
    from app.database import ConnectorConnection

    metrics = workspace_connectivity_metrics(db, workspace_id=workspace_id)
    usage = connector_usage_report(db, workspace_id=workspace_id)
    connections = db.query(ConnectorConnection).filter(
        ConnectorConnection.workspace_id == workspace_id,
        ConnectorConnection.status != "deleted",
    ).all()
    health = [connection_health(db, c) for c in connections]
    return {
        "workspace_id": workspace_id,
        "metrics": metrics,
        "usage": usage,
        "connection_health": health,
    }


def recommend(db: Session, *, workspace_id: int, organization_id: int | None = None) -> list[dict[str, Any]]:
    from app.database import ConnectorConnection

    created: list[dict[str, Any]] = []
    connections = db.query(ConnectorConnection).filter(
        ConnectorConnection.workspace_id == workspace_id,
        ConnectorConnection.status != "deleted",
    ).all()
    for conn in connections:
        health = connection_health(db, conn)
        if health.get("status") == "unhealthy":
            rec = create_recommendation(
                db,
                workspace_id=workspace_id,
                organization_id=organization_id,
                domain="connectivity",
                category="reliability",
                severity="high",
                title=f"Unhealthy connector '{conn.name}'",
                detail=f"{health.get('failures')} recent failures on {conn.connector_type}. Consider a fallback connector, alternative provider, or stricter retry policy.",
                resource_type="connector",
                resource_id=conn.id,
                evidence=health,
                estimated_impact="Reduced integration failures and sync delays",
            )
            created.append({"id": rec.id, "title": rec.title})
        elif health.get("status") == "degraded":
            rec = create_recommendation(
                db,
                workspace_id=workspace_id,
                organization_id=organization_id,
                domain="connectivity",
                category="reliability",
                severity="medium",
                title=f"Degraded connector '{conn.name}'",
                detail=f"Elevated failures/latency on {conn.connector_type}. Review credentials, rate limits, and webhook delivery.",
                resource_type="connector",
                resource_id=conn.id,
                evidence=health,
                estimated_impact="More stable connector performance",
            )
            created.append({"id": rec.id, "title": rec.title})
    return created
