"""Capacity planning — growth predictions and recommendations."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session


def capacity_forecast(db: Session, workspace_id: int) -> dict[str, Any]:
    from app.database import KnowledgeBase, UsageEvent, Workflow, WorkflowRun

    since = datetime.utcnow() - timedelta(days=30)
    chat_30d = (
        db.query(UsageEvent)
        .filter(UsageEvent.workspace_id == workspace_id, UsageEvent.create_time >= since)
        .count()
    )
    runs_30d = (
        db.query(WorkflowRun)
        .filter(WorkflowRun.workspace_id == workspace_id, WorkflowRun.create_time >= since)
        .count()
    )
    wf_count = db.query(Workflow).filter(Workflow.workspace_id == workspace_id).count()
    kb_count = db.query(KnowledgeBase).filter(KnowledgeBase.workspace_id == workspace_id).count()

    daily_chat = chat_30d / 30
    daily_runs = runs_30d / 30

    recommendations = []
    if daily_chat > 500:
        recommendations.append("Consider dedicated AI runtime pool for high chat volume")
    if daily_runs > 200:
        recommendations.append("Enable workflow queue workers for burst execution")
    if kb_count > 20:
        recommendations.append("Review vector index partitioning for knowledge growth")
    if not recommendations:
        recommendations.append("Current capacity within normal bounds")

    return {
        "workspace_id": workspace_id,
        "forecast_30d": {
            "chat_events": int(daily_chat * 30),
            "workflow_runs": int(daily_runs * 30),
        },
        "current": {
            "workflows": wf_count,
            "knowledge_bases": kb_count,
            "daily_chat_avg": round(daily_chat, 1),
            "daily_runs_avg": round(daily_runs, 1),
        },
        "recommendations": recommendations,
    }
