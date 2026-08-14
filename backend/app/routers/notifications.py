import asyncio
import datetime
import json
import re
from typing import Optional

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.orm import Session

from app.database import get_db, Notification, UserNotificationPreference, WorkspaceMember, User
from app.deps import get_current_user, require_admin
from app.schemas import fail, ok
from app.crypto import decode_token

router = APIRouter(tags=["Notifications"])


# --- Connection Manager for WebSockets ---
class ConnectionManager:
    def __init__(self):
        # Maps (user_id, workspace_id) -> list[WebSocket]
        self.active_connections: dict[tuple[int, int], list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: int, workspace_id: int):
        await websocket.accept()
        self.active_connections.setdefault((user_id, workspace_id), []).append(websocket)

    def disconnect(self, websocket: WebSocket, user_id: int, workspace_id: int):
        if (user_id, workspace_id) in self.active_connections:
            self.active_connections[(user_id, workspace_id)].remove(websocket)
            if not self.active_connections[(user_id, workspace_id)]:
                del self.active_connections[(user_id, workspace_id)]

    async def send_personal_message(self, message: dict, user_id: int, workspace_id: int):
        sockets = self.active_connections.get((user_id, workspace_id), [])
        for socket in sockets:
            try:
                await socket.send_json(message)
            except Exception:
                pass


manager = ConnectionManager()


# --- Notification Templates ---
TEMPLATES = {
    "WorkflowStarted": {
        "title": "Workflow Started",
        "message": "Workflow '{workflow_name}' (ID: {resource_id}) has started execution.",
        "category": "WORKFLOW",
        "level": "INFO",
    },
    "WorkflowCompleted": {
        "title": "Workflow Completed",
        "message": "Workflow '{workflow_name}' (ID: {resource_id}) completed successfully.",
        "category": "WORKFLOW",
        "level": "SUCCESS",
    },
    "WorkflowFailed": {
        "title": "Workflow Failed",
        "message": "Workflow '{workflow_name}' (ID: {resource_id}) failed: {error}.",
        "category": "WORKFLOW",
        "level": "ERROR",
    },
    "ConnectorActionInvoked": {
        "title": "Connector Action Invoked",
        "message": "Connector action '{action}' was executed on connection '{resource_id}' ({connector_type}).",
        "category": "CONNECTOR",
        "level": "INFO",
    },
    "ConnectorSyncFailed": {
        "title": "Connector Sync Failed",
        "message": "Synchronization failed for connection '{resource_id}': {error_message}.",
        "category": "CONNECTOR",
        "level": "ERROR",
    },
    "EvalFinished": {
        "title": "Evaluation Finished",
        "message": "Evaluation run for suite '{suite_name}' completed with status: {status}.",
        "category": "ADMIN",
        "level": "SUCCESS",
    },
    "SecurityAlert": {
        "title": "Security Alert",
        "message": "Security event triggered: {event_detail}.",
        "category": "SECURITY",
        "level": "CRITICAL",
    },
    "WorkspaceInvite": {
        "title": "Workspace Invitation",
        "message": "You have been invited to join workspace '{workspace_name}' as {role}.",
        "category": "TEAM",
        "level": "INFO",
    },
    "MemberJoined": {
        "title": "Member Joined",
        "message": "User {user_name} has joined the workspace.",
        "category": "TEAM",
        "level": "INFO",
    },
    "RoleChanged": {
        "title": "Role Changed",
        "message": "Your workspace role has been updated to {role}.",
        "category": "TEAM",
        "level": "WARNING",
    },
    "VoiceSessionStarted": {
        "title": "Voice Session Started",
        "message": "A new real-time voice streaming session has been initiated.",
        "category": "VOICE",
        "level": "INFO",
    },
    "VoiceSessionFailed": {
        "title": "Voice Session Failed",
        "message": "Voice session failed: {error}.",
        "category": "VOICE",
        "level": "ERROR",
    },
}


def is_in_quiet_hours(pref: UserNotificationPreference) -> bool:
    if not pref or not pref.quiet_hours_start or not pref.quiet_hours_end:
        return False
    try:
        now_time = datetime.datetime.utcnow().time()
        start_h, start_m = map(int, pref.quiet_hours_start.split(":"))
        end_h, end_m = map(int, pref.quiet_hours_end.split(":"))
        start_time = datetime.time(start_h, start_m)
        end_time = datetime.time(end_h, end_m)
        if start_time < end_time:
            return start_time <= now_time <= end_time
        else:
            return now_time >= start_time or now_time <= end_time
    except Exception:
        return False


def resolve_template(template_str: str, data: dict, resource_id: str) -> str:
    try:
        merged = {**data, "resource_id": resource_id}
        def repl(match):
            key = match.group(1)
            return str(merged.get(key, f"{{{key}}}"))
        return re.sub(r"\{([^{}]+)\}", repl, template_str)
    except Exception:
        return template_str


# --- Global Notification Publisher (Async & Queue Safe) ---
async def push_notification(
    db: Session,
    *,
    user_id: int,
    workspace_id: int,
    title: str,
    message: str,
    category: str = "INFO",
    level: str = "INFO",
    action_url: str = "",
) -> None:
    pref = db.query(UserNotificationPreference).filter(UserNotificationPreference.user_id == user_id).first()
    
    enabled_chans = ["database", "websocket"]
    dnd = False
    quiet = False

    if pref:
        try:
            enabled_cats = json.loads(pref.enabled_categories or "[]")
            muted_cats = json.loads(pref.muted_categories or "[]")
            chans = json.loads(pref.enabled_channels or "[]")
            if chans:
                enabled_chans = chans
            if category in muted_cats:
                return
            if enabled_cats and category not in enabled_cats:
                return
        except Exception:
            pass
        dnd = bool(pref.do_not_disturb)
        quiet = is_in_quiet_hours(pref)

    # Database persistence
    if "database" in enabled_chans:
        row = Notification(
            workspace_id=workspace_id,
            user_id=user_id,
            title=title,
            message=message,
            category=category,
            level=level,
            action_url=action_url,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        notif_dict = {
            "id": row.id,
            "workspace_id": row.workspace_id,
            "user_id": row.user_id,
            "title": row.title,
            "message": row.message,
            "category": row.category,
            "level": row.level,
            "is_read": row.is_read,
            "action_url": row.action_url,
            "create_time": row.create_time.isoformat(),
        }
    else:
        notif_dict = {
            "id": 99999,
            "workspace_id": workspace_id,
            "user_id": user_id,
            "title": title,
            "message": message,
            "category": category,
            "level": level,
            "is_read": 0,
            "action_url": action_url,
            "create_time": datetime.datetime.utcnow().isoformat(),
        }

    # WebSocket real-time delivery
    if not dnd and not quiet and "websocket" in enabled_chans:
        await manager.send_personal_message(
            {"type": "notification", "notification": notif_dict},
            user_id=user_id,
            workspace_id=workspace_id,
        )

    # Deliver via external channels if enabled
    if not dnd and not quiet:
        for chan in enabled_chans:
            if chan in ("slack", "discord", "telegram", "email"):
                from app.services.integrations import send_notification as legacy_send
                # Dispatch async tasks in loop to avoid blocking
                asyncio.create_task(
                    legacy_send(chan, "", title, message, db=db, workspace_id=workspace_id)
                )


# --- Global Event Bus Hook ---
def handle_platform_event(event_type: str, data: dict):
    """Listens to all emitted domain events, applies templates, and pushes to relevant users."""
    if event_type not in TEMPLATES:
        return

    from app.database import SessionLocal
    db = SessionLocal()
    try:
        workspace_id = data.get("_workspace_id")
        actor_user_id = data.get("_actor_user_id")
        resource_id = data.get("_resource_id") or ""
        
        if not workspace_id:
            return

        tmpl = TEMPLATES[event_type]
        title = tmpl["title"]
        message = resolve_template(tmpl["message"], data, resource_id)
        category = tmpl["category"]
        level = tmpl["level"]
        action_url = ""
        if event_type.startswith("Workflow"):
            action_url = f"/workflows/{resource_id}"
        elif event_type.startswith("Connector"):
            action_url = "/settings?tab=integrations"

        # Determine target user(s)
        recipients = []
        if actor_user_id:
            recipients = [actor_user_id]
        else:
            # Query workspace members
            members = db.query(WorkspaceMember).filter(WorkspaceMember.workspace_id == workspace_id).all()
            recipients = [m.user_id for m in members]

        for uid in recipients:
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(
                    push_notification(
                        db,
                        user_id=uid,
                        workspace_id=workspace_id,
                        title=title,
                        message=message,
                        category=category,
                        level=level,
                        action_url=action_url,
                    )
                )
            except RuntimeError:
                asyncio.run(
                    push_notification(
                        db,
                        user_id=uid,
                        workspace_id=workspace_id,
                        title=title,
                        message=message,
                        category=category,
                        level=level,
                        action_url=action_url,
                    )
                )
    except Exception:
        pass
    finally:
        db.close()


# Subscribe handle_platform_event to all events emitted on the Event Bus
from app.platform_intelligence.events.emitter import subscribe
subscribe("*", handle_platform_event)


# --- REST API Endpoints ---
@router.get("/notifications")
def get_notifications(
    workspace_id: int,
    category: Optional[str] = None,
    is_read: Optional[int] = None,
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    # Verify membership
    member = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == workspace_id, WorkspaceMember.user_id == user.user_id
    ).first()
    if not member:
        return fail(403, "Workspace access denied")

    q = db.query(Notification).filter(
        Notification.workspace_id == workspace_id, Notification.user_id == user.user_id
    )
    if category:
        q = q.filter(Notification.category == category)
    if is_read is not None:
        q = q.filter(Notification.is_read == is_read)
    
    total = q.count()
    rows = q.order_by(Notification.create_time.desc()).offset(offset).limit(limit).all()

    return ok({
        "total": total,
        "rows": [
            {
                "id": r.id,
                "workspace_id": r.workspace_id,
                "title": r.title,
                "message": r.message,
                "category": r.category,
                "level": r.level,
                "is_read": r.is_read,
                "action_url": r.action_url,
                "create_time": r.create_time.isoformat() if r.create_time else None,
            }
            for r in rows
        ]
    })


@router.get("/notifications/unread-count")
def get_unread_count(
    workspace_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    member = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == workspace_id, WorkspaceMember.user_id == user.user_id
    ).first()
    if not member:
        return fail(403, "Workspace access denied")

    count = db.query(Notification).filter(
        Notification.workspace_id == workspace_id,
        Notification.user_id == user.user_id,
        Notification.is_read == 0,
    ).count()
    return ok({"unread_count": count})


@router.post("/notifications/{id}/read")
def mark_read(
    id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    row = db.get(Notification, id)
    if not row or row.user_id != user.user_id:
        return fail(404, "Notification not found")
    row.is_read = 1
    db.commit()
    return ok({"id": id, "is_read": 1})


@router.post("/notifications/read-all")
def mark_all_read(
    workspace_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    db.query(Notification).filter(
        Notification.workspace_id == workspace_id,
        Notification.user_id == user.user_id,
        Notification.is_read == 0,
    ).update({Notification.is_read: 1})
    db.commit()
    return ok({"marked_all_read": True})


@router.delete("/notifications/{id}")
def delete_notif(
    id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    row = db.get(Notification, id)
    if not row or row.user_id != user.user_id:
        return fail(404, "Notification not found")
    db.delete(row)
    db.commit()
    return ok({"deleted": id})


@router.delete("/notifications/clear-all")
def clear_all_notifications(
    workspace_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    db.query(Notification).filter(
        Notification.workspace_id == workspace_id,
        Notification.user_id == user.user_id,
    ).delete()
    db.commit()
    return ok({"cleared": True})


# --- Preferences Endpoints ---
@router.get("/notifications/preferences")
def get_preferences(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    row = db.query(UserNotificationPreference).filter(UserNotificationPreference.user_id == user.user_id).first()
    if not row:
        row = UserNotificationPreference(user_id=user.user_id)
        db.add(row)
        db.commit()
        db.refresh(row)
    
    return ok({
        "enabled_categories": json.loads(row.enabled_categories or "[]"),
        "enabled_channels": json.loads(row.enabled_channels or "[]"),
        "muted_categories": json.loads(row.muted_categories or "[]"),
        "do_not_disturb": row.do_not_disturb,
        "quiet_hours_start": row.quiet_hours_start,
        "quiet_hours_end": row.quiet_hours_end,
    })


@router.patch("/notifications/preferences")
def patch_preferences(
    body: dict,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    row = db.query(UserNotificationPreference).filter(UserNotificationPreference.user_id == user.user_id).first()
    if not row:
        row = UserNotificationPreference(user_id=user.user_id)
        db.add(row)
        db.commit()
        db.refresh(row)

    if "enabled_categories" in body:
        row.enabled_categories = json.dumps(body["enabled_categories"])
    if "enabled_channels" in body:
        row.enabled_channels = json.dumps(body["enabled_channels"])
    if "muted_categories" in body:
        row.muted_categories = json.dumps(body["muted_categories"])
    if "do_not_disturb" in body:
        row.do_not_disturb = int(body["do_not_disturb"])
    if "quiet_hours_start" in body:
        row.quiet_hours_start = str(body["quiet_hours_start"])
    if "quiet_hours_end" in body:
        row.quiet_hours_end = str(body["quiet_hours_end"])

    db.commit()
    db.refresh(row)
    
    return ok({
        "enabled_categories": json.loads(row.enabled_categories or "[]"),
        "enabled_channels": json.loads(row.enabled_channels or "[]"),
        "muted_categories": json.loads(row.muted_categories or "[]"),
        "do_not_disturb": row.do_not_disturb,
        "quiet_hours_start": row.quiet_hours_start,
        "quiet_hours_end": row.quiet_hours_end,
    })


# --- WebSocket Endpoint ---
@router.websocket("/notifications/ws")
async def notifications_ws(websocket: WebSocket, db: Session = Depends(get_db)):
    token = (
        websocket.query_params.get("token")
        or websocket.query_params.get("t")
        or websocket.query_params.get("access_token")
    )
    if not token:
        auth = websocket.headers.get("authorization")
        if auth and auth.lower().startswith("bearer "):
            token = auth.split(" ", 1)[1].strip()
    workspace_id_str = websocket.query_params.get("workspace_id") or websocket.query_params.get("wid")
    if not token or not workspace_id_str:
        await websocket.close(code=4003)
        return

    try:
        workspace_id = int(workspace_id_str)
    except ValueError:
        await websocket.close(code=4003)
        return

    # Verify token
    payload = decode_token(token)
    if not payload:
        await websocket.close(code=4003)
        return

    user_id = int(payload["sub"])
    user = db.get(User, user_id)
    if not user or user.delete:
        await websocket.close(code=4003)
        return

    # Verify workspace membership
    member = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == workspace_id, WorkspaceMember.user_id == user_id
    ).first()
    if not member:
        await websocket.close(code=4003)
        return

    # Accept connection
    await manager.connect(websocket, user_id, workspace_id)
    try:
        while True:
            # Maintain connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id, workspace_id)
