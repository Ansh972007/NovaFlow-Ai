from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.config import PORT
from app.database import Workflow, get_db
from app.deps import get_workspace_ctx, require_workspace_admin, require_workspace_editor
from app.schemas import fail, ok
from app.services.integrations import (
    get_telegram_bot_info,
    get_telegram_webhook_info,
    parse_telegram_input,
    register_telegram_webhook,
    send_notification,
)
from app.services.workflow import run_workflow, workflow_dict
from app.services.workspace_integrations import (
    integrations_dict,
    record_telegram_webhook,
    resolve_public_base_url,
    update_integrations,
)

router = APIRouter(tags=["Integrations"])


@router.get("/integrations/settings")
def get_integration_settings(db: Session = Depends(get_db), ctx=Depends(get_workspace_ctx)):
    return ok(integrations_dict(db, ctx.workspace_id))


@router.patch("/integrations/settings")
def patch_integration_settings(
    body: dict,
    db: Session = Depends(get_db),
    ctx=Depends(require_workspace_admin),
):
    return ok(update_integrations(db, ctx.workspace_id, body))


@router.get("/integrations/health")
def integration_health(db: Session = Depends(get_db), ctx=Depends(get_workspace_ctx)):
    data = integrations_dict(db, ctx.workspace_id)
    return ok(
        {
            "telegram_ready": data["telegram"]["configured"],
            "email_ready": data["email"]["configured"],
            "telegram_source": data["telegram"]["source"],
            "email_source": data["email"]["source"],
        }
    )


@router.get("/integrations/telegram/webhook-status")
async def telegram_webhook_status(db: Session = Depends(get_db), ctx=Depends(get_workspace_ctx)):
    settings = integrations_dict(db, ctx.workspace_id)
    live = await get_telegram_webhook_info(db, ctx.workspace_id)
    return ok(
        {
            "stored": settings.get("telegram") or {},
            "live": live.get("info") if live.get("ok") else None,
            "live_error": live.get("detail") if not live.get("ok") else None,
        }
    )


@router.post("/integrations/telegram/verify")
async def verify_telegram_bot(
    body: dict | None = None,
    db: Session = Depends(get_db),
    ctx=Depends(require_workspace_admin),
):
    body = body or {}
    result = await get_telegram_bot_info(
        db,
        ctx.workspace_id,
        (body.get("bot_token") or "").strip(),
    )
    if not result.get("ok"):
        return fail(400, result.get("detail") or "Verification failed")
    bot = result.get("bot") or {}
    if bot.get("username"):
        from app.services.workspace_integrations import get_or_create

        row = get_or_create(db, ctx.workspace_id)
        row.telegram_bot_username = str(bot["username"])[:64]
        db.commit()
    return ok(result)


@router.post("/integrations/telegram/register-webhook")
async def register_webhook(
    body: dict,
    db: Session = Depends(get_db),
    ctx=Depends(require_workspace_admin),
):
    workflow_id = (body.get("workflow_id") or "").strip()
    if not workflow_id:
        return fail(400, "workflow_id required")
    wf = db.get(Workflow, workflow_id)
    if not wf or wf.workspace_id != ctx.workspace_id:
        return fail(404, "Workflow not found")
    if wf.status != 1:
        return fail(400, "Publish the workflow before registering a Telegram webhook")
    public_base = resolve_public_base_url(db, ctx.workspace_id, (body.get("public_base_url") or "").strip())
    webhook_url = f"{public_base}/api/v1/integrations/telegram/webhook/{workflow_id}"
    result = await register_telegram_webhook(
        db,
        ctx.workspace_id,
        webhook_url,
        (body.get("bot_token") or "").strip(),
    )
    if not result.get("ok"):
        return fail(400, result.get("detail") or "Registration failed")
    record_telegram_webhook(db, ctx.workspace_id, workflow_id, webhook_url)
    return ok({**result, "webhook_url": webhook_url, "public_base_url": public_base})


@router.post("/integrations/email/test")
async def test_email_integration(
    body: dict,
    db: Session = Depends(get_db),
    ctx=Depends(require_workspace_admin),
):
    to_addr = (body.get("to") or "").strip()
    if not to_addr:
        from app.services.workspace_integrations import get_or_create

        row = get_or_create(db, ctx.workspace_id)
        to_addr = (row.smtp_user or "").strip()
    if not to_addr:
        return fail(400, "Recipient email required")
    result = await send_notification(
        "email",
        to_addr,
        (body.get("subject") or "NovaFlow email test").strip(),
        (body.get("message") or "NovaFlow Gmail/SMTP integration test OK").strip(),
        db=db,
        workspace_id=ctx.workspace_id,
    )
    if not result.get("ok"):
        return fail(400, result.get("detail") or "Send failed")
    return ok(result)


@router.post("/integrations/notify/test")
async def test_notify(
    body: dict,
    db: Session = Depends(get_db),
    ctx=Depends(require_workspace_editor),
):
    channel = (body.get("channel") or "telegram").strip().lower()
    to_addr = (body.get("to") or "").strip()
    if not to_addr and channel == "telegram":
        from app.services.workspace_integrations import get_or_create

        row = get_or_create(db, ctx.workspace_id)
        to_addr = (row.telegram_default_chat_id or "").strip()
    if not to_addr:
        return fail(400, "to required (or set default chat ID in Settings)")
    result = await send_notification(
        channel,
        to_addr,
        (body.get("subject") or "NovaFlow test").strip(),
        (body.get("message") or "NovaFlow integration test OK").strip(),
        bot_token=(body.get("bot_token") or "").strip(),
        db=db,
        workspace_id=ctx.workspace_id,
    )
    if not result.get("ok"):
        return fail(400, result.get("detail") or "Send failed")
    return ok(result)


@router.post("/integrations/telegram/webhook/{workflow_id}")
async def telegram_webhook(workflow_id: str, request: Request, db: Session = Depends(get_db)):
    wf = db.get(Workflow, workflow_id)
    if not wf or wf.status != 1:
        return fail(404, "Workflow not found or not published")
    try:
        payload = await request.json()
    except Exception:
        return fail(400, "Invalid JSON")
    chat_id, text = parse_telegram_input(payload)
    if not text:
        return ok({"ignored": True})
    result = await run_workflow(
        db,
        wf,
        wf.user_id,
        text,
        wf.workspace_id,
        extra_context={"chat_id": chat_id},
    )
    return ok({"chat_id": chat_id, "result": result})


@router.get("/integrations/telegram/setup/{workflow_id}")
def telegram_setup(workflow_id: str, db: Session = Depends(get_db), ctx=Depends(get_workspace_ctx)):
    wf = db.get(Workflow, workflow_id)
    if not wf or wf.workspace_id != ctx.workspace_id:
        return fail(404, "Workflow not found")
    settings = integrations_dict(db, ctx.workspace_id)
    public_base = resolve_public_base_url(db, ctx.workspace_id)
    webhook_url = f"{public_base}/api/v1/integrations/telegram/webhook/{workflow_id}"
    return ok(
        {
            "workflow": workflow_dict(wf),
            "webhook_url": webhook_url,
            "public_base_url": public_base,
            "telegram_configured": settings["telegram"]["configured"],
            "default_chat_id": settings["telegram"]["default_chat_id"],
            "webhook_registered": settings["telegram"].get("webhook_workflow_id") == workflow_id,
            "stored_webhook_url": settings["telegram"].get("webhook_url") or "",
            "hint": "Save bot token in Settings → Integrations, then register webhook.",
        }
    )
