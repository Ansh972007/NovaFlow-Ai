"""Enterprise admin dashboards — aggregated intelligence."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.platform_intelligence.capacity.planner import capacity_forecast
from app.platform_intelligence.finops.ledger import (
    check_budget,
    detect_cost_anomalies,
    forecast_monthly,
    workspace_cost_summary,
)
from app.platform_intelligence.healing.detectors import detect_anomalies, recovery_recommendations
from app.platform_intelligence.observability.health import platform_health_snapshot
from app.platform_intelligence.observability.metrics import aggregate_subsystems, get_recent_metrics


def organization_dashboard(db: Session, organization_id: int) -> dict[str, Any]:
    from app.database import Workspace

    workspaces = db.query(Workspace).filter(Workspace.organization_id == organization_id).limit(50).all()
    return {
        "organization_id": organization_id,
        "workspace_count": len(workspaces),
        "workspaces": [{"id": w.id, "name": w.name} for w in workspaces],
        "platform_health": platform_health_snapshot(),
    }


def workspace_dashboard(db: Session, workspace_id: int) -> dict[str, Any]:
    return {
        "workspace_id": workspace_id,
        "cost": workspace_cost_summary(db, workspace_id),
        "budget": check_budget(db, workspace_id),
        "forecast": forecast_monthly(db, workspace_id),
        "capacity": capacity_forecast(db, workspace_id),
        "anomalies": detect_cost_anomalies(db, workspace_id),
        "subsystems": aggregate_subsystems(),
    }


def system_dashboard() -> dict[str, Any]:
    return {
        "health": platform_health_snapshot(),
        "subsystems": aggregate_subsystems(),
        "recent_metrics": get_recent_metrics(limit=20),
        "anomalies": detect_anomalies(),
        "recovery": recovery_recommendations(),
    }


def security_dashboard(db: Session, workspace_id: int, *, limit: int = 20) -> dict[str, Any]:
    from app.database import SecurityAuditLog

    rows = (
        db.query(SecurityAuditLog)
        .filter(SecurityAuditLog.workspace_id == workspace_id)
        .order_by(SecurityAuditLog.created_at.desc())
        .limit(limit)
        .all()
    )
    return {
        "workspace_id": workspace_id,
        "recent_audit": [
            {"action": r.action, "actor_user_id": r.actor_user_id, "created_at": r.created_at.isoformat() if r.created_at else None}
            for r in rows
        ],
        "anomalies": detect_anomalies(),
    }
