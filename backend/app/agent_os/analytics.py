"""AgentOS analytics."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.agent_os.learning import agent_leaderboard
from app.database import AgentLearningRecord, AgentRun, SavedAgent


def workspace_agent_analytics(db: Session, *, workspace_id: int) -> dict[str, Any]:
    agents = db.query(SavedAgent).filter(SavedAgent.workspace_id == workspace_id).count()
    runs = db.query(AgentRun).filter(AgentRun.workspace_id == workspace_id).count()
    completed = db.query(AgentRun).filter(AgentRun.workspace_id == workspace_id, AgentRun.status == "completed").count()
    failed = db.query(AgentRun).filter(AgentRun.workspace_id == workspace_id, AgentRun.status == "failed").count()
    learning = db.query(AgentLearningRecord).filter(AgentLearningRecord.workspace_id == workspace_id).count()
    return {
        "agent_count": agents,
        "run_count": runs,
        "completed_runs": completed,
        "failed_runs": failed,
        "success_rate": round(completed / max(runs, 1), 2),
        "learning_records": learning,
        "leaderboard": agent_leaderboard(db, workspace_id=workspace_id, limit=10),
    }


def failure_analysis(db: Session, *, workspace_id: int, limit: int = 20) -> list[dict[str, Any]]:
    rows = (
        db.query(AgentRun)
        .filter(AgentRun.workspace_id == workspace_id, AgentRun.status == "failed")
        .order_by(AgentRun.update_time.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "run_id": r.id,
            "agent_id": r.agent_id,
            "error": r.error_message,
            "trace_id": r.trace_id,
            "create_time": r.create_time.isoformat() if r.create_time else None,
        }
        for r in rows
    ]
