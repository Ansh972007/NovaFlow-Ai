"""ECP integration facade — single path for external operations."""

from __future__ import annotations

import time
from typing import Any

from sqlalchemy.orm import Session

from app.connectivity.events import log_event
from app.connectivity.observability import connection_health
from app.connectivity.policy import evaluate_connector_policy, evaluate_domain_policy, requires_approval
from app.connectivity.plugins import get_connector_plugin
from app.connectivity.secrets import decrypt_credential
from app.connectivity.service import get_connection, get_latest_credential


async def invoke_connector_action(
    db: Session,
    *,
    workspace_id: int,
    connection_id: str,
    action: str,
    params: dict | None = None,
    trace_id: str = "",
    policies: dict | None = None,
    actor_user_id: int | None = None,
    organization_id: int | None = None,
) -> dict[str, Any]:
    """Single entry point for all external connector operations."""
    conn = get_connection(db, connection_id, workspace_id=workspace_id)
    if not conn:
        raise ValueError("Connection not found")

    policy = evaluate_connector_policy(
        connector_type=conn.connector_type,
        workspace_policies=policies,
    )
    if not policy.get("allowed"):
        raise ValueError(policy.get("reason") or "Policy denied")

    if requires_approval(conn.connector_type, action, policies=policies):
        raise ValueError("Action requires human approval")

    cred = get_latest_credential(db, connection_id, workspace_id=workspace_id)
    secret = decrypt_credential(cred.secret_enc) if cred else ""

    start = time.perf_counter()
    plugin = get_connector_plugin(conn.connector_type)
    result = await plugin.invoke_action(db, conn, action, params=params, secret=secret)
    latency = int((time.perf_counter() - start) * 1000)

    log_event(
        db,
        workspace_id=workspace_id,
        connection_id=connection_id,
        event_type=f"connector.{action}",
        payload={"success": result.success, "message": result.message},
        trace_id=trace_id,
        latency_ms=latency,
        status="completed" if result.success else "failed",
    )

    try:
        from app.platform_intelligence.events.emitter import emit_platform_event

        emit_platform_event(
            db,
            "ConnectorActionInvoked",
            workspace_id=workspace_id,
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            resource_type="connector",
            resource_id=connection_id,
            payload={"action": action, "connector_type": conn.connector_type, "trace_id": trace_id},
        )
    except Exception:
        pass

    return result.to_dict()


async def send_notification(
    db: Session,
    *,
    workspace_id: int,
    channel: str,
    message: str,
    trace_id: str = "",
) -> dict[str, Any]:
    """Route notifications through ECP — wraps legacy integrations service."""
    from app.services.integrations import send_notification as legacy_send

    start = time.perf_counter()
    result = await legacy_send(channel, "", "NovaFlow", message, db=db, workspace_id=workspace_id)
    ok = bool(result.get("ok") or result.get("success"))
    latency = int((time.perf_counter() - start) * 1000)
    log_event(
        db,
        workspace_id=workspace_id,
        event_type=f"notify.{channel}",
        payload={"message_preview": message[:200]},
        trace_id=trace_id,
        latency_ms=latency,
        status="completed" if ok else "failed",
    )
    return {"success": ok, "channel": channel, "latency_ms": latency}


def test_connection(db: Session, *, workspace_id: int, connection_id: str) -> dict[str, Any]:
    conn = get_connection(db, connection_id, workspace_id=workspace_id)
    if not conn:
        raise ValueError("Connection not found")
    cred = get_latest_credential(db, connection_id, workspace_id=workspace_id)
    secret = decrypt_credential(cred.secret_enc) if cred else ""
    plugin = get_connector_plugin(conn.connector_type)
    result = plugin.test(db, conn, secret=secret)
    health = connection_health(db, conn)
    return {"test": result.to_dict(), "health": health}
