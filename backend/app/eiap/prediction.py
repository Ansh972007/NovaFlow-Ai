"""EIAP prediction engine — forecast growth across resources.

Reuses platform_intelligence.capacity and finops. Trend-based, not model retraining.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.platform_intelligence.capacity.planner import capacity_forecast
from app.platform_intelligence.finops.ledger import forecast_monthly


def _count_since(db, model, workspace_id: int, days: int) -> int:
    since = datetime.utcnow() - timedelta(days=days)
    try:
        return (
            db.query(model)
            .filter(model.workspace_id == workspace_id, model.create_time >= since)
            .count()
        )
    except Exception:
        return 0


def forecast(db: Session, *, workspace_id: int) -> dict[str, Any]:
    from app.database import (
        AgentRun,
        ConnectorEvent,
        KnowledgeChunk,
        KnowledgeBase,
        WorkflowRun,
    )

    capacity = capacity_forecast(db, workspace_id)
    cost = forecast_monthly(db, workspace_id)

    agent_7d = _count_since(db, AgentRun, workspace_id, 7)
    conn_7d = _count_since(db, ConnectorEvent, workspace_id, 7)
    runs_7d = _count_since(db, WorkflowRun, workspace_id, 7)

    kb_count = db.query(KnowledgeBase).filter(KnowledgeBase.workspace_id == workspace_id).count()
    chunk_count = db.query(KnowledgeChunk).join(
        KnowledgeBase, KnowledgeChunk.knowledge_id == KnowledgeBase.id
    ).filter(KnowledgeBase.workspace_id == workspace_id).count()

    def project(weekly: int) -> dict[str, int]:
        daily = weekly / 7
        return {"next_7d": int(daily * 7), "next_30d": int(daily * 30), "next_90d": int(daily * 90)}

    return {
        "workspace_id": workspace_id,
        "cost": cost,
        "capacity": capacity,
        "growth": {
            "agent_runs": project(agent_7d),
            "connector_events": project(conn_7d),
            "workflow_runs": project(runs_7d),
            "vector_chunks_current": chunk_count,
            "knowledge_bases_current": kb_count,
        },
    }
