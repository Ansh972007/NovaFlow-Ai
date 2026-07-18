"""AgentOS long-running task management."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.database import AgentCheckpoint, AgentRun


def create_run(
    db: Session,
    *,
    workspace_id: int,
    user_id: int,
    input_text: str,
    agent_id: str | None = None,
    mode: str = "single",
    organization_id: int | None = None,
    trace_id: str = "",
) -> AgentRun:
    run = AgentRun(
        id=uuid.uuid4().hex,
        agent_id=agent_id,
        workspace_id=workspace_id,
        organization_id=organization_id,
        user_id=user_id,
        mode=mode,
        status="running",
        input_text=input_text[:8000],
        trace_id=trace_id,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def complete_run(
    db: Session,
    run: AgentRun,
    *,
    output: str,
    plan: dict | None = None,
    reasoning: dict | None = None,
    verification: dict | None = None,
    metrics: dict | None = None,
    confidence: float = 0.0,
    cost_usd: float = 0.0,
    conversation_id: str | None = None,
) -> AgentRun:
    run.status = "completed"
    run.output_text = output[:16000]
    run.plan_json = json.dumps(plan or {})
    run.reasoning_json = json.dumps(reasoning or {})
    run.verification_json = json.dumps(verification or {})
    run.metrics_json = json.dumps(metrics or {})
    run.confidence = confidence
    run.cost_usd = cost_usd
    run.conversation_id = conversation_id
    run.completed_at = datetime.utcnow()
    run.update_time = datetime.utcnow()
    db.commit()
    db.refresh(run)
    return run


def fail_run(db: Session, run: AgentRun, error: str) -> AgentRun:
    run.status = "failed"
    run.error_message = (error or "")[:2000]
    run.completed_at = datetime.utcnow()
    run.update_time = datetime.utcnow()
    db.commit()
    db.refresh(run)
    return run


def pause_run(db: Session, run: AgentRun, *, state: dict | None = None, step_no: int = 0) -> AgentCheckpoint:
    run.status = "paused"
    run.update_time = datetime.utcnow()
    cp = AgentCheckpoint(
        id=uuid.uuid4().hex,
        run_id=run.id,
        workspace_id=run.workspace_id,
        step_no=step_no,
        state_json=json.dumps(state or {}),
        status="saved",
    )
    db.add(cp)
    db.commit()
    db.refresh(cp)
    return cp


def resume_run(db: Session, run: AgentRun) -> AgentRun:
    if run.status != "paused":
        raise ValueError("Run is not paused")
    run.status = "running"
    run.update_time = datetime.utcnow()
    db.commit()
    db.refresh(run)
    return run


def cancel_run(db: Session, run: AgentRun) -> AgentRun:
    run.status = "cancelled"
    run.completed_at = datetime.utcnow()
    run.update_time = datetime.utcnow()
    db.commit()
    db.refresh(run)
    return run


def get_run(db: Session, run_id: str, *, workspace_id: int) -> AgentRun | None:
    run = db.get(AgentRun, run_id)
    if not run or run.workspace_id != workspace_id:
        return None
    return run


def run_dict(run: AgentRun) -> dict[str, Any]:
    return {
        "id": run.id,
        "agent_id": run.agent_id,
        "mode": run.mode,
        "status": run.status,
        "input": run.input_text,
        "output": run.output_text,
        "confidence": run.confidence,
        "cost_usd": run.cost_usd,
        "trace_id": run.trace_id,
        "conversation_id": run.conversation_id,
        "error_message": run.error_message,
        "create_time": run.create_time.isoformat() if run.create_time else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
    }
