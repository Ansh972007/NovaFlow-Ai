"""EIAP unified observability — aggregate telemetry across all layers.

Read-only aggregation. Reuses each layer's own observability service.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session


def unified_health(db: Session, *, workspace_id: int) -> dict[str, Any]:
    from app.agent_os.analytics import workspace_agent_analytics
    from app.connectivity.observability import workspace_connectivity_metrics
    from app.knowledge_os.curator import workspace_analytics as kos_analytics
    from app.platform_intelligence.finops.ledger import workspace_cost_summary
    from app.platform_intelligence.observability.metrics import aggregate_subsystems
    from app.workflow_intelligence.observability import workspace_run_stats

    layers: dict[str, Any] = {}
    scores: list[float] = []

    def safe(fn, default):
        try:
            return fn()
        except Exception as exc:
            return {"error": str(exc)[:200], **default}

    workflow = safe(lambda: workspace_run_stats(db, workspace_id, limit=100), {"success_rate": 1.0})
    layers["workflow"] = workflow
    scores.append(float(workflow.get("success_rate", 1.0)))

    agents = safe(lambda: workspace_agent_analytics(db, workspace_id=workspace_id), {"success_rate": 1.0})
    layers["agent_os"] = agents
    scores.append(float(agents.get("success_rate", 1.0)))

    knowledge = safe(lambda: kos_analytics(db, workspace_id=workspace_id), {})
    layers["knowledge_os"] = knowledge

    connectivity = safe(lambda: workspace_connectivity_metrics(db, workspace_id=workspace_id), {"sync_success_rate": 1.0})
    layers["connectivity"] = connectivity
    scores.append(float(connectivity.get("sync_success_rate", 1.0)))

    layers["cost"] = safe(lambda: workspace_cost_summary(db, workspace_id, days=30), {})
    layers["subsystems"] = safe(lambda: aggregate_subsystems(), {})

    overall = round(sum(scores) / len(scores), 3) if scores else 1.0
    status = "healthy" if overall >= 0.9 else ("degraded" if overall >= 0.7 else "unhealthy")

    return {
        "workspace_id": workspace_id,
        "overall_health_score": overall,
        "status": status,
        "layers": layers,
    }
