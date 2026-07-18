"""AgentOS human-in-the-loop."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.database import AgentRun


def request_approval(
    db: Session,
    run: AgentRun,
    *,
    reason: str,
    action: str = "continue",
) -> dict[str, Any]:
    meta = {}
    try:
        meta = json.loads(run.metrics_json or "{}")
    except json.JSONDecodeError:
        pass
    meta["hitl"] = {
        "status": "pending",
        "reason": reason,
        "action": action,
        "requested_at": datetime.utcnow().isoformat(),
    }
    run.status = "paused"
    run.metrics_json = json.dumps(meta)
    run.update_time = datetime.utcnow()
    db.commit()
    return meta["hitl"]


def submit_feedback(
    db: Session,
    run: AgentRun,
    *,
    approved: bool,
    feedback: str = "",
) -> dict[str, Any]:
    meta = {}
    try:
        meta = json.loads(run.metrics_json or "{}")
    except json.JSONDecodeError:
        pass
    meta["hitl"] = {
        "status": "approved" if approved else "rejected",
        "feedback": feedback,
        "resolved_at": datetime.utcnow().isoformat(),
    }
    run.metrics_json = json.dumps(meta)
    if approved:
        run.status = "running"
    else:
        run.status = "cancelled"
        run.completed_at = datetime.utcnow()
    run.update_time = datetime.utcnow()
    db.commit()
    return meta["hitl"]
