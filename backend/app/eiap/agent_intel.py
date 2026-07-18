"""EIAP agent intelligence — scorecards, rankings, recommendations.

Reuses agent_os.analytics and agent_os.learning. Never re-implements agent execution.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.agent_os.analytics import failure_analysis, workspace_agent_analytics
from app.agent_os.learning import agent_leaderboard
from app.eiap.recommendations import create_recommendation


def agent_scorecards(db: Session, *, workspace_id: int) -> dict[str, Any]:
    analytics = workspace_agent_analytics(db, workspace_id=workspace_id)
    leaderboard = agent_leaderboard(db, workspace_id=workspace_id, limit=25)
    failures = failure_analysis(db, workspace_id=workspace_id, limit=10)
    return {
        "workspace_id": workspace_id,
        "analytics": analytics,
        "leaderboard": leaderboard,
        "recent_failures": failures,
    }


def recommend(db: Session, *, workspace_id: int, organization_id: int | None = None) -> list[dict[str, Any]]:
    board = agent_leaderboard(db, workspace_id=workspace_id, limit=50)
    created: list[dict[str, Any]] = []
    for agent in board:
        if agent.get("runs", 0) < 5:
            continue
        if agent.get("success_rate", 1.0) < 0.6:
            rec = create_recommendation(
                db,
                workspace_id=workspace_id,
                organization_id=organization_id,
                domain="agent",
                category="quality",
                severity="high" if agent["success_rate"] < 0.4 else "medium",
                title=f"Low-performing agent {agent['agent_id']}",
                detail=f"Success rate {int(agent['success_rate'] * 100)}% across {agent['runs']} runs. Review system prompt, tool selection, and verification policies.",
                resource_type="agent",
                resource_id=agent["agent_id"],
                evidence=agent,
                estimated_impact="Higher answer quality and confidence",
            )
            created.append({"id": rec.id, "title": rec.title})
        elif agent.get("avg_confidence", 1.0) < 0.5:
            rec = create_recommendation(
                db,
                workspace_id=workspace_id,
                organization_id=organization_id,
                domain="agent",
                category="confidence",
                severity="low",
                title=f"Low confidence agent {agent['agent_id']}",
                detail="Average confidence is below 0.5. Consider adding knowledge grounding or stronger verification.",
                resource_type="agent",
                resource_id=agent["agent_id"],
                evidence=agent,
                estimated_impact="More trustworthy agent outputs",
            )
            created.append({"id": rec.id, "title": rec.title})
    return created
