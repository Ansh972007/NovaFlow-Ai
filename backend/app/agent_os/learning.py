"""AgentOS learning system — analytics without model retraining."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.database import AgentLearningRecord, AgentRun


def record_learning(
    db: Session,
    *,
    run_id: str,
    agent_id: str | None,
    workspace_id: int,
    success: bool,
    retry_count: int = 0,
    tool_quality: float = 0.0,
    knowledge_quality: float = 0.0,
    latency_ms: int = 0,
    cost_usd: float = 0.0,
    confidence: float = 0.0,
    meta: dict | None = None,
) -> AgentLearningRecord:
    rec = AgentLearningRecord(
        run_id=run_id,
        agent_id=agent_id,
        workspace_id=workspace_id,
        success=1 if success else 0,
        retry_count=retry_count,
        tool_quality=tool_quality,
        knowledge_quality=knowledge_quality,
        latency_ms=latency_ms,
        cost_usd=cost_usd,
        confidence=confidence,
        meta_json=json.dumps(meta or {}),
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return rec


def agent_leaderboard(db: Session, *, workspace_id: int, limit: int = 20) -> list[dict[str, Any]]:
    rows = (
        db.query(AgentLearningRecord)
        .filter(AgentLearningRecord.workspace_id == workspace_id)
        .order_by(AgentLearningRecord.create_time.desc())
        .limit(500)
        .all()
    )
    stats: dict[str, dict] = {}
    for r in rows:
        aid = r.agent_id or "unknown"
        if aid not in stats:
            stats[aid] = {"agent_id": aid, "runs": 0, "successes": 0, "avg_confidence": 0.0, "total_cost": 0.0}
        stats[aid]["runs"] += 1
        stats[aid]["successes"] += r.success
        stats[aid]["avg_confidence"] += r.confidence
        stats[aid]["total_cost"] += r.cost_usd or 0
    leaderboard = []
    for aid, s in stats.items():
        s["success_rate"] = round(s["successes"] / max(s["runs"], 1), 2)
        s["avg_confidence"] = round(s["avg_confidence"] / max(s["runs"], 1), 2)
        s["total_cost"] = round(s["total_cost"], 4)
        leaderboard.append(s)
    leaderboard.sort(key=lambda x: (-x["success_rate"], -x["avg_confidence"]))
    return leaderboard[:limit]
