"""AgentOS agent communication — events and status."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session


def emit_agent_event(
    db: Session,
    event_type: str,
    *,
    workspace_id: int,
    run_id: str = "",
    agent_id: str = "",
    organization_id: int | None = None,
    actor_user_id: int | None = None,
    payload: dict | None = None,
) -> None:
    try:
        from app.platform_intelligence.events.emitter import emit_platform_event

        emit_platform_event(
            db,
            event_type,
            workspace_id=workspace_id,
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            resource_type="agent_run",
            resource_id=run_id or agent_id,
            payload={"agent_id": agent_id, **(payload or {})},
        )
    except Exception:
        pass


def status_update(status: str, *, detail: str = "", progress: float = 0.0) -> dict[str, Any]:
    return {"status": status, "detail": detail, "progress": progress}
