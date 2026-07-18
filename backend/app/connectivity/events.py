"""ECP event engine — webhooks, delivery, replay."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.database import ConnectorEvent, ConnectorWebhook


def create_webhook(
    db: Session,
    *,
    workspace_id: int,
    direction: str,
    url: str = "",
    connection_id: str | None = None,
    events: list | None = None,
    secret: str = "",
) -> ConnectorWebhook:
    from app.connectivity.secrets import encrypt_credential

    wh = ConnectorWebhook(
        id=uuid.uuid4().hex,
        connection_id=connection_id,
        workspace_id=workspace_id,
        direction=direction,
        url=url[:500],
        secret_enc=encrypt_credential(secret) if secret else "",
        events_json=json.dumps(events or ["*"]),
        status="active",
    )
    db.add(wh)
    db.commit()
    db.refresh(wh)
    return wh


def log_event(
    db: Session,
    *,
    workspace_id: int,
    event_type: str,
    connection_id: str | None = None,
    direction: str = "outbound",
    payload: dict | None = None,
    trace_id: str = "",
    status: str = "completed",
    latency_ms: int = 0,
    error: str = "",
) -> ConnectorEvent:
    ev = ConnectorEvent(
        id=uuid.uuid4().hex,
        workspace_id=workspace_id,
        connection_id=connection_id,
        event_type=event_type,
        direction=direction,
        status=status,
        payload_json=json.dumps(payload or {}),
        trace_id=trace_id,
        latency_ms=latency_ms,
        error_message=error[:1000],
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)
    return ev


async def deliver_outbound_webhook(
    db: Session,
    webhook: ConnectorWebhook,
    payload: dict,
    *,
    trace_id: str = "",
) -> dict[str, Any]:
    import time

    from app.services.webhooks import post_webhook

    start = time.perf_counter()
    try:
        ok = await post_webhook(webhook.url, payload, event="connectivity.event")
        latency = int((time.perf_counter() - start) * 1000)
        webhook.last_delivery_at = datetime.utcnow()
        db.commit()
        log_event(
            db,
            workspace_id=webhook.workspace_id,
            connection_id=webhook.connection_id,
            event_type="webhook.delivered",
            payload={"success": ok},
            trace_id=trace_id,
            latency_ms=latency,
            status="completed" if ok else "failed",
        )
        return {"success": ok, "latency_ms": latency}
    except Exception as exc:
        latency = int((time.perf_counter() - start) * 1000)
        log_event(
            db,
            workspace_id=webhook.workspace_id,
            connection_id=webhook.connection_id,
            event_type="webhook.failed",
            trace_id=trace_id,
            latency_ms=latency,
            status="failed",
            error=str(exc),
        )
        raise


def list_events(
    db: Session,
    *,
    workspace_id: int,
    connection_id: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    q = db.query(ConnectorEvent).filter(ConnectorEvent.workspace_id == workspace_id)
    if connection_id:
        q = q.filter(ConnectorEvent.connection_id == connection_id)
    rows = q.order_by(ConnectorEvent.create_time.desc()).limit(limit).all()
    return [
        {
            "id": r.id,
            "event_type": r.event_type,
            "status": r.status,
            "trace_id": r.trace_id,
            "latency_ms": r.latency_ms,
            "create_time": r.create_time.isoformat() if r.create_time else None,
        }
        for r in rows
    ]
