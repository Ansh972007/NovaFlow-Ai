"""Domain event platform — everything becomes an event."""

from __future__ import annotations

import json
import time
from typing import Any

from sqlalchemy.orm import Session

from app.platform_intelligence.tracing.context import get_trace_id

# In-memory subscription registry (extensible to webhooks)
_subscribers: dict[str, list] = {}


def subscribe(event_type: str, handler) -> None:
    _subscribers.setdefault(event_type, []).append(handler)


def emit_platform_event(
    db: Session | None,
    event_type: str,
    *,
    workspace_id: int | None = None,
    organization_id: int | None = None,
    actor_user_id: int | None = None,
    resource_type: str = "",
    resource_id: str = "",
    payload: dict | None = None,
    correlation_id: str = "",
) -> int | None:
    """Emit a platform event — persisted + audit correlation."""
    trace_id = correlation_id or get_trace_id()
    data = payload or {}
    event_data = dict(data)
    event_data["_workspace_id"] = workspace_id
    event_data["_organization_id"] = organization_id
    event_data["_actor_user_id"] = actor_user_id
    event_data["_resource_type"] = resource_type
    event_data["_resource_id"] = resource_id

    for handler in _subscribers.get(event_type, []):
        try:
            handler(event_type, event_data)
        except Exception:
            pass
    for handler in _subscribers.get("*", []):
        try:
            handler(event_type, event_data)
        except Exception:
            pass

    row_id = None
    if db is not None:
        try:
            from app.database import PlatformEvent

            row = PlatformEvent(
                event_type=event_type,
                trace_id=trace_id,
                workspace_id=workspace_id,
                organization_id=organization_id,
                actor_user_id=actor_user_id,
                resource_type=resource_type,
                resource_id=str(resource_id or ""),
                payload_json=json.dumps(data),
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            row_id = int(row.id)
        except Exception:
            try:
                db.rollback()
            except Exception:
                pass

    # Correlate with security audit for governance events
    if db is not None and event_type.startswith(("Workflow", "Policy", "Provider", "Budget")):
        try:
            from app.security.audit import audit_log

            audit_log(
                db,
                action=f"platform.event.{event_type}",
                actor_user_id=actor_user_id,
                workspace_id=workspace_id,
                resource_type=resource_type,
                resource_id=str(resource_id or ""),
                detail={"trace_id": trace_id, **data},
            )
        except Exception:
            pass

    return row_id


def list_events(
    db: Session,
    *,
    workspace_id: int | None = None,
    event_type: str | None = None,
    trace_id: str | None = None,
    limit: int = 50,
) -> list[dict]:
    from app.database import PlatformEvent

    q = db.query(PlatformEvent).order_by(PlatformEvent.create_time.desc())
    if workspace_id is not None:
        q = q.filter(PlatformEvent.workspace_id == workspace_id)
    if event_type:
        q = q.filter(PlatformEvent.event_type == event_type)
    if trace_id:
        q = q.filter(PlatformEvent.trace_id == trace_id)
    rows = q.limit(limit).all()
    out = []
    for r in rows:
        try:
            payload = json.loads(r.payload_json or "{}")
        except json.JSONDecodeError:
            payload = {}
        out.append(
            {
                "id": r.id,
                "event_type": r.event_type,
                "trace_id": r.trace_id,
                "workspace_id": r.workspace_id,
                "resource_type": r.resource_type,
                "resource_id": r.resource_id,
                "payload": payload,
                "create_time": r.create_time.isoformat() if r.create_time else None,
            }
        )
    return out
