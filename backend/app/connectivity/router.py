"""Enterprise Connectivity Platform API."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.connectivity.analytics import workspace_analytics
from app.connectivity.auth import validate_auth_config
from app.connectivity.events import create_webhook, deliver_outbound_webhook, list_events
from app.connectivity.integration import invoke_connector_action, send_notification, test_connection
from app.connectivity.mcp import list_mcp_registrations, mcp_dict, register_mcp
from app.connectivity.observability import connection_health, workspace_connectivity_metrics
from app.connectivity.plugins import list_connector_plugins
from app.connectivity.registry import connector_matrix, get_connector_meta, list_connectors
from app.connectivity.secrets import credential_dict
from app.connectivity.service import (
    connection_dict,
    create_connection,
    delete_connection,
    get_connection,
    list_connections,
    store_credential,
    update_connection,
)
from app.connectivity.sync import create_sync_job, run_sync_job, sync_dict
from app.database import ConnectorWebhook, get_db
from app.deps import get_workspace_ctx, require_permission, require_workspace_editor
from app.schemas import fail, ok
from app.security.rbac import Permission

router = APIRouter(tags=["Connectivity"])


@router.get("/connectivity/connectors")
def api_list_connectors(category: str = Query(""), ctx=Depends(get_workspace_ctx)):
    return ok(list_connectors(category=category))


@router.get("/connectivity/connectors/matrix")
def api_connector_matrix(ctx=Depends(get_workspace_ctx)):
    return ok(connector_matrix())


@router.get("/connectivity/connectors/{connector_type}")
def api_get_connector(connector_type: str, ctx=Depends(get_workspace_ctx)):
    meta = get_connector_meta(connector_type)
    if not meta:
        return fail(404, "Connector type not found")
    return ok(meta)


@router.get("/connectivity/plugins")
def api_plugins(ctx=Depends(get_workspace_ctx)):
    return ok(list_connector_plugins())


@router.post("/connectivity/connections")
def api_create_connection(body: dict, db: Session = Depends(get_db), ctx=Depends(require_workspace_editor)):
    name = (body.get("name") or "").strip()
    ctype = (body.get("connector_type") or body.get("type") or "").strip()
    if not name or not ctype:
        return fail(400, "name and connector_type required")
    auth_check = validate_auth_config(body.get("auth_type") or "api_key", body.get("auth_config"))
    if not auth_check.get("valid") and body.get("auth_config"):
        return fail(400, f"Invalid auth config: {auth_check.get('missing')}")
    conn = create_connection(
        db,
        workspace_id=ctx.workspace_id,
        user_id=ctx.user.user_id,
        organization_id=ctx.organization_id,
        connector_type=ctype,
        name=name,
        auth_type=body.get("auth_type") or "api_key",
        config=body.get("config"),
    )
    if body.get("secret"):
        store_credential(db, connection_id=conn.id, workspace_id=ctx.workspace_id, secret_plain=str(body["secret"]))
    ctx.audit("connectivity.connection.create", resource_type="connector", resource_id=conn.id)
    return ok(connection_dict(conn))


@router.get("/connectivity/connections")
def api_list_connections(
    connector_type: str = Query(""),
    db: Session = Depends(get_db),
    ctx=Depends(require_permission(Permission.ASSISTANT_READ)),
):
    rows = list_connections(db, workspace_id=ctx.workspace_id, connector_type=connector_type)
    return ok([connection_dict(r) for r in rows])


@router.get("/connectivity/connections/{connection_id}")
def api_get_connection(connection_id: str, db: Session = Depends(get_db), ctx=Depends(require_permission(Permission.ASSISTANT_READ))):
    conn = get_connection(db, connection_id, workspace_id=ctx.workspace_id)
    if not conn:
        return fail(404, "Connection not found")
    return ok(connection_dict(conn))


@router.put("/connectivity/connections/{connection_id}")
def api_update_connection(connection_id: str, body: dict, db: Session = Depends(get_db), ctx=Depends(require_workspace_editor)):
    conn = get_connection(db, connection_id, workspace_id=ctx.workspace_id)
    if not conn:
        return fail(404, "Connection not found")
    conn = update_connection(db, conn, body)
    if body.get("secret"):
        store_credential(db, connection_id=conn.id, workspace_id=ctx.workspace_id, secret_plain=str(body["secret"]))
    return ok(connection_dict(conn))


@router.delete("/connectivity/connections/{connection_id}")
def api_delete_connection(connection_id: str, db: Session = Depends(get_db), ctx=Depends(require_workspace_editor)):
    conn = get_connection(db, connection_id, workspace_id=ctx.workspace_id)
    if not conn:
        return fail(404, "Connection not found")
    delete_connection(db, conn)
    return ok({"deleted": connection_id})


@router.post("/connectivity/connections/{connection_id}/test")
def api_test_connection(connection_id: str, db: Session = Depends(get_db), ctx=Depends(require_workspace_editor)):
    try:
        return ok(test_connection(db, workspace_id=ctx.workspace_id, connection_id=connection_id))
    except ValueError as exc:
        return fail(400, str(exc))


@router.post("/connectivity/connections/{connection_id}/invoke")
async def api_invoke(connection_id: str, body: dict, db: Session = Depends(get_db), ctx=Depends(require_workspace_editor)):
    action = (body.get("action") or "").strip()
    if not action:
        return fail(400, "action required")
    try:
        result = await invoke_connector_action(
            db,
            workspace_id=ctx.workspace_id,
            connection_id=connection_id,
            action=action,
            params=body.get("params"),
            trace_id=getattr(ctx, "trace_id", "") or "",
            actor_user_id=ctx.user.user_id,
            organization_id=ctx.organization_id,
        )
        return ok(result)
    except ValueError as exc:
        return fail(400, str(exc))


@router.get("/connectivity/connections/{connection_id}/health")
def api_health(connection_id: str, db: Session = Depends(get_db), ctx=Depends(require_permission(Permission.ASSISTANT_READ))):
    conn = get_connection(db, connection_id, workspace_id=ctx.workspace_id)
    if not conn:
        return fail(404, "Connection not found")
    return ok(connection_health(db, conn))


@router.post("/connectivity/connections/{connection_id}/sync")
def api_sync(connection_id: str, body: dict, db: Session = Depends(get_db), ctx=Depends(require_workspace_editor)):
    conn = get_connection(db, connection_id, workspace_id=ctx.workspace_id)
    if not conn:
        return fail(404, "Connection not found")
    job = create_sync_job(db, connection=conn, direction=body.get("direction") or "inbound", mode=body.get("mode") or "incremental")
    try:
        result = run_sync_job(db, job)
    except Exception as exc:
        return fail(400, str(exc))
    return ok({"job": sync_dict(job), "result": result})


@router.post("/connectivity/webhooks")
def api_create_webhook(body: dict, db: Session = Depends(get_db), ctx=Depends(require_workspace_editor)):
    wh = create_webhook(
        db,
        workspace_id=ctx.workspace_id,
        direction=body.get("direction") or "outbound",
        url=body.get("url") or "",
        connection_id=body.get("connection_id"),
        events=body.get("events"),
        secret=body.get("secret") or "",
    )
    return ok({"id": wh.id, "url": wh.url, "direction": wh.direction})


@router.post("/connectivity/webhooks/{webhook_id}/deliver")
async def api_deliver_webhook(webhook_id: str, body: dict, db: Session = Depends(get_db), ctx=Depends(require_workspace_editor)):
    wh = db.get(ConnectorWebhook, webhook_id)
    if not wh or wh.workspace_id != ctx.workspace_id:
        return fail(404, "Webhook not found")
    try:
        result = await deliver_outbound_webhook(db, wh, body.get("payload") or {})
    except Exception as exc:
        return fail(400, str(exc))
    return ok(result)


@router.get("/connectivity/events")
def api_events(
    connection_id: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    ctx=Depends(require_permission(Permission.ASSISTANT_READ)),
):
    return ok(list_events(db, workspace_id=ctx.workspace_id, connection_id=connection_id, limit=limit))


@router.post("/connectivity/mcp/register")
def api_register_mcp(body: dict, db: Session = Depends(get_db), ctx=Depends(require_workspace_editor)):
    name = (body.get("name") or "").strip()
    if not name:
        return fail(400, "name required")
    reg = register_mcp(
        db,
        workspace_id=ctx.workspace_id,
        organization_id=ctx.organization_id,
        name=name,
        role=body.get("role") or "client",
        transport=body.get("transport") or "stdio",
        endpoint=body.get("endpoint") or "",
        capabilities=body.get("capabilities"),
        tools=body.get("tools"),
        auth_type=body.get("auth_type") or "none",
        config=body.get("config"),
    )
    ctx.audit("connectivity.mcp.register", resource_type="mcp", resource_id=reg.id)
    return ok(mcp_dict(reg))


@router.get("/connectivity/mcp")
def api_list_mcp(role: str = Query(""), db: Session = Depends(get_db), ctx=Depends(require_permission(Permission.ASSISTANT_READ))):
    return ok([mcp_dict(r) for r in list_mcp_registrations(db, workspace_id=ctx.workspace_id, role=role)])


@router.get("/connectivity/analytics")
def api_analytics(db: Session = Depends(get_db), ctx=Depends(require_permission(Permission.ASSISTANT_READ))):
    return ok(workspace_analytics(db, workspace_id=ctx.workspace_id))


@router.get("/connectivity/metrics")
def api_metrics(db: Session = Depends(get_db), ctx=Depends(require_permission(Permission.ASSISTANT_READ))):
    return ok(workspace_connectivity_metrics(db, workspace_id=ctx.workspace_id))


@router.post("/connectivity/notify")
async def api_notify(body: dict, db: Session = Depends(get_db), ctx=Depends(require_workspace_editor)):
    channel = (body.get("channel") or "telegram").strip()
    message = (body.get("message") or body.get("body") or "").strip()
    if not message:
        return fail(400, "message required")
    result = await send_notification(db, workspace_id=ctx.workspace_id, channel=channel, message=message)
    return ok(result)
