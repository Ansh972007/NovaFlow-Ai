from fastapi import APIRouter, Depends, Query, Request
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
            "jira_ready": data.get("jira", {}).get("configured", False),
            "slack_ready": data.get("slack", {}).get("configured", False),
            "github_ready": data.get("github", {}).get("configured", False),
            "discord_ready": data.get("discord", {}).get("configured", False),
            "linear_ready": data.get("linear", {}).get("configured", False),
            "slack_bot_ready": data.get("slack", {}).get("bot_configured", False),
            "telegram_source": data["telegram"]["source"],
            "email_source": data["email"]["source"],
            "jira_source": data.get("jira", {}).get("source", "none"),
            "slack_source": data.get("slack", {}).get("source", "none"),
            "github_source": data.get("github", {}).get("source", "none"),
            "discord_source": data.get("discord", {}).get("source", "none"),
            "linear_source": data.get("linear", {}).get("source", "none"),
            "gmail_oauth_connected": data["email"].get("oauth_connected", False),
        }
    )


@router.get("/integrations/gmail/oauth/start")
def gmail_oauth_start(
    json_mode: bool | None = Query(None, alias="json"),
    db: Session = Depends(get_db),
    ctx=Depends(require_workspace_admin),
):
    from app.services.gmail_jira import build_gmail_authorize_url, gmail_oauth_enabled_for_workspace
    from fastapi.responses import RedirectResponse

    if not gmail_oauth_enabled_for_workspace(db, ctx.workspace_id):
        return fail(
            400,
            "Add Google Client ID and Client secret under Credentials → Email & Gmail, then click Save credential before connecting.",
        )
    url = build_gmail_authorize_url(db, ctx.workspace_id, ctx.user.user_id)
    if not url:
        return fail(400, "Could not build Google authorize URL. Verify Google Client ID & Secret.")
    if json_mode:
        return ok({"url": url})
    return RedirectResponse(url)


@router.get("/integrations/gmail/oauth/callback")
async def gmail_oauth_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
):
    from fastapi.responses import RedirectResponse
    from app.services.gmail_jira import (
        exchange_gmail_code,
        fetch_gmail_profile,
        frontend_settings_redirect,
        store_gmail_oauth_tokens,
        verify_gmail_oauth_state,
    )

    if error:
        return RedirectResponse(frontend_settings_redirect(f"tab=integrations&gmail=error&msg={error}"))
    payload = verify_gmail_oauth_state(state or "")
    if not payload or not code:
        return RedirectResponse(frontend_settings_redirect("tab=integrations&gmail=error&msg=invalid_state"))
    try:
        wid = int(payload["workspace_id"])
        token_data = await exchange_gmail_code(db, wid, code)
        access = token_data.get("access_token") or ""
        profile = await fetch_gmail_profile(access) if access else {}
        email = profile.get("email") or ""
        store_gmail_oauth_tokens(
            db,
            wid,
            token_data,
            email,
            user_id=int(payload.get("user_id") or 0),
        )
        return RedirectResponse(frontend_settings_redirect("tab=integrations&gmail=connected"))
    except Exception as exc:
        return RedirectResponse(
            frontend_settings_redirect(f"tab=integrations&gmail=error&msg={str(exc)[:120]}")
        )


@router.post("/integrations/gmail/oauth/disconnect")
def gmail_oauth_disconnect(db: Session = Depends(get_db), ctx=Depends(require_workspace_admin)):
    from app.services.gmail_jira import disconnect_gmail_oauth

    disconnect_gmail_oauth(db, ctx.workspace_id)
    return ok(integrations_dict(db, ctx.workspace_id))


@router.post("/integrations/jira/verify")
async def verify_jira(db: Session = Depends(get_db), ctx=Depends(require_workspace_admin)):
    from app.services.gmail_jira import jira_verify

    result = await jira_verify(db, ctx.workspace_id)
    if not result.get("ok"):
        return fail(400, result.get("detail") or "Jira verification failed")
    return ok(result)


@router.post("/integrations/slack/test")
async def test_slack_integration(
    body: dict | None = None,
    db: Session = Depends(get_db),
    ctx=Depends(require_workspace_admin),
):
    body = body or {}
    result = await send_notification(
        "slack",
        (body.get("webhook_url") or "").strip(),
        (body.get("subject") or "NovaFlow Slack test").strip(),
        (body.get("message") or "Slack integration test OK ✅").strip(),
        db=db,
        workspace_id=ctx.workspace_id,
    )
    if not result.get("ok"):
        return fail(400, result.get("detail") or "Slack test failed")
    return ok(result)


@router.post("/integrations/github/verify")
async def verify_github(db: Session = Depends(get_db), ctx=Depends(require_workspace_admin)):
    from app.services.github_issues import github_verify

    result = await github_verify(db, ctx.workspace_id)
    if not result.get("ok"):
        return fail(400, result.get("detail") or "GitHub verification failed")
    return ok(result)


@router.post("/integrations/discord/test")
async def test_discord_integration(
    body: dict | None = None,
    db: Session = Depends(get_db),
    ctx=Depends(require_workspace_admin),
):
    body = body or {}
    result = await send_notification(
        "discord",
        (body.get("webhook_url") or "").strip(),
        (body.get("subject") or "NovaFlow Discord test").strip(),
        (body.get("message") or "Discord integration test OK ✅").strip(),
        db=db,
        workspace_id=ctx.workspace_id,
    )
    if not result.get("ok"):
        return fail(400, result.get("detail") or "Discord test failed")
    return ok(result)


@router.post("/integrations/linear/verify")
async def verify_linear(db: Session = Depends(get_db), ctx=Depends(require_workspace_admin)):
    from app.services.linear_issues import linear_verify

    result = await linear_verify(db, ctx.workspace_id)
    if not result.get("ok"):
        return fail(400, result.get("detail") or "Linear verification failed")
    return ok(result)


@router.post("/integrations/slack/events/bind")
def bind_slack_events(
    body: dict,
    db: Session = Depends(get_db),
    ctx=Depends(require_workspace_admin),
):
    from app.services.workspace_integrations import record_slack_events

    workflow_id = (body.get("workflow_id") or "").strip()
    if not workflow_id:
        return fail(400, "workflow_id required")
    wf = ctx.fetch(Workflow, workflow_id)
    if not wf:
        return fail(404, "Workflow not found")
    if wf.status != 1:
        return fail(400, "Publish the workflow before binding Slack events")
    settings = integrations_dict(db, ctx.workspace_id)
    if not settings.get("slack", {}).get("bot_configured"):
        return fail(400, "Add Slack bot token + signing secret in Settings first")
    public_base = resolve_public_base_url(db, ctx.workspace_id, (body.get("public_base_url") or "").strip())
    events_url = f"{public_base}/api/v1/integrations/slack/events/{workflow_id}"
    record_slack_events(db, ctx.workspace_id, workflow_id, events_url)
    return ok(
        {
            "ok": True,
            "events_url": events_url,
            "detail": "Point Slack Event Subscriptions Request URL to this URL (app_mention, message.im).",
        }
    )


@router.post("/integrations/slack/events/{workflow_id}")
async def slack_events_webhook(workflow_id: str, request: Request, db: Session = Depends(get_db)):
    import json as _json

    from fastapi.responses import PlainTextResponse

    from app.crypto import decrypt_secret
    from app.database import WorkspaceIntegration
    from app.services.integrations import parse_slack_event, send_slack_bot_message, verify_slack_signature

    wf = db.get(Workflow, workflow_id)
    if not wf or wf.status != 1:
        return fail(404, "Workflow not found or not published")

    body_bytes = await request.body()
    try:
        payload = _json.loads(body_bytes.decode("utf-8"))
    except Exception:
        return fail(400, "Invalid JSON")

    # URL verification challenge
    if payload.get("type") == "url_verification":
        return PlainTextResponse(payload.get("challenge") or "")

    row = db.get(WorkspaceIntegration, wf.workspace_id)
    signing = decrypt_secret(row.slack_signing_secret_enc or "") if row and row.slack_signing_secret_enc else ""
    timestamp = request.headers.get("X-Slack-Request-Timestamp") or ""
    signature = request.headers.get("X-Slack-Signature") or ""
    if signing and not verify_slack_signature(signing, timestamp, body_bytes, signature):
        return fail(401, "Invalid Slack signature")

    if payload.get("type") != "event_callback":
        return ok({"ignored": True})

    channel, user_id, text = parse_slack_event(payload)
    if not text:
        return ok({"ignored": True})

    result = await run_workflow(
        db,
        wf,
        wf.user_id,
        text,
        wf.workspace_id,
        extra_context={"slack_channel": channel, "slack_user": user_id, "chat_id": channel},
    )
    output = (result.get("output") or "")[:3500]
    if channel and output:
        await send_slack_bot_message(db, wf.workspace_id, channel, output)
    return ok({"channel": channel, "result": result})


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
    wf = ctx.fetch(Workflow, workflow_id)
    if not wf:
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
        credential_id=body.get("credential_id"),
    )
    if not result.get("ok"):
        return fail(400, result.get("detail") or "Send failed")
    return ok(result)


@router.post("/integrations/telegram/webhook/{workflow_id}")
async def telegram_webhook(workflow_id: str, request: Request, db: Session = Depends(get_db)):
    from app.services.integrations import telegram_trigger_chat_filter

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
    chat_filter = telegram_trigger_chat_filter(wf.graph_json or "")
    if chat_filter and chat_id and chat_id != chat_filter:
        return ok({"ignored": True, "reason": "chat_filter"})
    result = await run_workflow(
        db,
        wf,
        wf.user_id,
        text,
        wf.workspace_id,
        extra_context={"chat_id": chat_id, "telegram_chat_id": chat_id},
    )
    return ok({"chat_id": chat_id, "result": result})


@router.get("/integrations/telegram/setup/{workflow_id}")
def telegram_setup(workflow_id: str, db: Session = Depends(get_db), ctx=Depends(get_workspace_ctx)):
    wf = ctx.fetch(Workflow, workflow_id)
    if not wf:
        return fail(404, "Workflow not found")
    settings = integrations_dict(db, ctx.workspace_id)
    public_base = resolve_public_base_url(db, ctx.workspace_id)
    webhook_url = f"{public_base}/api/v1/integrations/telegram/webhook/{workflow_id}"
    tg = settings.get("telegram") or {}
    return ok(
        {
            "workflow": workflow_dict(wf),
            "webhook_url": webhook_url,
            "public_base_url": public_base,
            "telegram_configured": tg.get("configured"),
            "bot_username": tg.get("bot_username") or "",
            "default_chat_id": tg.get("default_chat_id"),
            "webhook_registered": tg.get("webhook_workflow_id") == workflow_id,
            "stored_webhook_url": tg.get("webhook_url") or "",
            "hint": "Add bot token in Credentials → Messaging, publish workflow — webhook registers automatically.",
        }
    )
