"""Execution checkpointing, retry, and idempotency."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable

from sqlalchemy.orm import Session


@dataclass
class RetryPolicy:
    max_attempts: int = 3
    base_delay_ms: int = 500
    max_delay_ms: int = 8000
    backoff_factor: float = 2.0


@dataclass
class ExecutionContext:
    trace_id: str = ""
    idempotency_key: str = ""
    checkpoint_node: str = ""
    retries: dict[str, int] = field(default_factory=dict)
    metrics: dict[str, Any] = field(default_factory=dict)


async def with_retry(
    fn: Callable[[], Awaitable[Any]],
    *,
    policy: RetryPolicy | None = None,
    label: str = "step",
) -> tuple[Any, int]:
    policy = policy or RetryPolicy()
    last_exc: Exception | None = None
    attempts = 0
    delay = policy.base_delay_ms / 1000.0

    for attempt in range(1, policy.max_attempts + 1):
        attempts = attempt
        try:
            return await fn(), attempts - 1
        except Exception as exc:
            last_exc = exc
            if attempt >= policy.max_attempts:
                break
            await _sleep(delay)
            delay = min(delay * policy.backoff_factor, policy.max_delay_ms / 1000.0)

    raise last_exc or RuntimeError(f"{label} failed")


async def _sleep(seconds: float) -> None:
    import asyncio

    await asyncio.sleep(seconds)


def save_checkpoint(
    db: Session,
    *,
    workflow_id: str,
    run_id: int | None,
    workspace_id: int,
    user_id: int,
    node_id: str,
    context: dict,
    steps: list,
    status: str = "paused",
) -> int:
    from app.database import WorkflowExecutionCheckpoint

    row = WorkflowExecutionCheckpoint(
        workflow_id=workflow_id,
        run_id=run_id,
        workspace_id=workspace_id,
        user_id=user_id,
        node_id=node_id,
        context_json=json.dumps(context),
        steps_json=json.dumps(steps),
        status=status,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return int(row.id)


def load_checkpoint(db: Session, checkpoint_id: int) -> dict | None:
    from app.database import WorkflowExecutionCheckpoint

    row = db.get(WorkflowExecutionCheckpoint, checkpoint_id)
    if not row:
        return None
    return {
        "id": row.id,
        "workflow_id": row.workflow_id,
        "run_id": row.run_id,
        "node_id": row.node_id,
        "context": json.loads(row.context_json or "{}"),
        "steps": json.loads(row.steps_json or "[]"),
        "status": row.status,
    }
