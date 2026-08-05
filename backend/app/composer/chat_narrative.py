"""Plain-English narratives for Peak Chat AIOS events (no jargon / UUIDs by default)."""

from __future__ import annotations

import re
from typing import Any

_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
_UUIDISH = re.compile(r"\b[0-9a-f]{8}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{12}\b", re.I)
_HEX32 = re.compile(r"\b[0-9a-f]{32}\b", re.I)

_CRED_FRIENDLY = {
    "smtp_password": "email password (SMTP app password)",
    "smtp_user": "email username",
    "smtp_host": "email server host",
    "telegram_bot_token": "Telegram bot token",
    "slack_webhook_url": "Slack webhook URL",
    "slack_bot_token": "Slack bot token",
    "discord_webhook_url": "Discord webhook URL",
    "openai_api_key": "LLM API key",
    "github_token": "GitHub token",
    "jira_api_token": "Jira API token",
    "linear_api_key": "Linear API key",
    "webhook_url": "webhook URL",
    "whatsapp_access_token": "WhatsApp access token",
    "whatsapp_phone_number_id": "WhatsApp phone number ID",
    "youtube_api_key": "YouTube API key",
    "shopify_shop": "Shopify shop domain",
    "shopify_access_token": "Shopify Admin API token",
    "google_client_id": "Google OAuth client ID",
    "google_client_secret": "Google OAuth client secret",
    "google_refresh_token": "Google OAuth refresh token",
    "outlook_client_id": "Outlook / Microsoft client ID",
    "outlook_client_secret": "Outlook / Microsoft client secret",
    "outlook_refresh_token": "Outlook refresh token",
    "custom_api_key": "API key for this integration",
}


def extract_email(text: str) -> str | None:
    m = _EMAIL_RE.search(text or "")
    return m.group(0) if m else None


def wants_schedule(text: str) -> bool:
    t = (text or "").lower()
    return bool(re.search(r"\b(daily|every day|weekly|every monday|schedule|cron)\b", t))


def wants_email(text: str) -> bool:
    t = (text or "").lower()
    return bool(re.search(r"\b(email|e-mail|mail|smtp|gmail)\b", t) or extract_email(text))


def friendly_credential_name(key: str) -> str:
    k = (key or "").strip()
    if k in _CRED_FRIENDLY:
        return _CRED_FRIENDLY[k]
    try:
        from app.composer.chat_channels import friendly_missing_name

        return friendly_missing_name(k)
    except Exception:  # noqa: BLE001
        return k.replace("_", " ")


def strip_tech_ids(text: str) -> str:
    out = _UUIDISH.sub("", text or "")
    out = _HEX32.sub("", out)
    out = re.sub(r"\s{2,}", " ", out).strip()
    return out


def _goal_from_events(events: list[dict[str, Any]], goal: str = "") -> str:
    if goal:
        return goal
    for ev in events:
        data = ev.get("data") or {}
        if data.get("goal"):
            return str(data["goal"])
    return ""


def _solution_blurb(data: dict[str, Any], goal: str) -> str:
    try:
        from app.composer.chat_channels import solution_blurb_for_goal

        return solution_blurb_for_goal(
            goal or str(data.get("goal") or ""),
            missing=list(data.get("missing_credentials") or []),
        )
    except Exception:  # noqa: BLE001
        pass
    email = extract_email(goal) or extract_email(str(data.get("goal") or ""))
    schedule = wants_schedule(goal) or wants_schedule(str(data.get("goal") or ""))
    recipe = data.get("recipe_name") or (data.get("recipe") or {}).get("name") or ""
    if recipe and "generic" in str(recipe).lower():
        recipe = ""

    if email and schedule:
        head = f"I drafted a plan to email **{email}** on a schedule."
    elif email:
        head = f"I drafted a plan to send email to **{email}**."
    elif wants_email(goal):
        head = "I drafted a plan to send emails for you."
    elif recipe:
        head = f"I drafted a plan for **{recipe}**."
    else:
        head = "I drafted an automation plan for you."

    missing = data.get("missing_credentials") or []
    bits = [head]
    if missing:
        names = ", ".join(friendly_credential_name(m) for m in missing[:4])
        bits.append(f"To go live I need: {names}. Paste them here or open **Credentials**.")
        bits.append("Then tap **Approve** when you’re ready.")
    else:
        bits.append("Tap **Approve** when this looks right — I’ll test it next.")
    return " ".join(bits)


def _next_step_from_progress(data: dict[str, Any]) -> str | None:
    next_action = (data.get("next_action") or "").lower()
    if next_action == "credentials":
        return "Next step: add the missing login details for this automation."
    if next_action == "approve":
        return "Next step: **Approve** when this looks right."
    if next_action == "test":
        return "Next step: run a quick test."
    if next_action == "deploy":
        return "Next step: go live with **Deploy**."
    if next_action == "heal":
        return "Next step: tap **Fix & retest** to repair the plan."
    if data.get("express") and data.get("compose_ms") is not None:
        return "I put this together quickly — review the card, then Approve."
    return None


def friendly_summary(events: list[dict[str, Any]], goal: str = "", *, tech_details: bool = False) -> str:
    """
    Build one short user-facing reply from AIOS events.
    By default omits UUIDs / node lists / recipe jargon.
    """
    if not events:
        return "Done — use the buttons on the card if you see one."

    goal_text = _goal_from_events(events, goal)
    parts: list[str] = []
    seen: set[str] = set()

    def add(line: str) -> None:
        line = (line or "").strip()
        if not line:
            return
        if not tech_details:
            line = strip_tech_ids(line)
        key = line.lower()
        if key in seen:
            return
        seen.add(key)
        parts.append(line)

    for ev in events:
        t = ev.get("type") or ""
        data = ev.get("data") or {}

        if t == "aios_clarify":
            add(data.get("message") or "I need a bit more detail to help.")
        elif t == "aios_solution":
            if data.get("message"):
                add(data["message"])
            else:
                add(_solution_blurb(data, goal_text))
            if tech_details and data.get("solution_id"):
                add(f"Plan id: `{data.get('solution_id')}`")
        elif t == "aios_progress":
            step = _next_step_from_progress(data)
            if step:
                add(step)
        elif t == "aios_approved":
            add("Plan approved. Running a quick test…")
        elif t == "aios_heal":
            add(data.get("message") or "I repaired the plan and retested.")
        elif t == "aios_hitl":
            add(data.get("message") or "I need your OK before continuing.")
        elif t in ("aios_test_report", "aios_sandbox"):
            if data.get("status") == "success":
                add(data.get("message") or "Tests passed. Ready to go live — tap **Deploy** when you want.")
            else:
                add(data.get("message") or "A test didn’t pass. Tap **Fix & retest** or refine the plan.")
        elif t == "aios_deploy":
            if data.get("status") == "error":
                add(data.get("message") or "Deploy didn’t finish — try again or check credentials.")
            else:
                add("You’re live — your automation is running.")
                if data.get("schedule_note"):
                    add(str(data["schedule_note"]))
        elif t == "aios_credentials_saved":
            add(data.get("message") or "Saved your credentials securely. You can Approve or Deploy next.")
        elif t == "aios_credentials_needed":
            if data.get("message"):
                add(data["message"])
            else:
                missing = data.get("missing") or []
                names = ", ".join(friendly_credential_name(m) for m in missing[:5]) if missing else "your login details"
                add(f"To send mail I need {names}. Paste them here or open **Credentials**.")
        elif t == "aios_cancelled":
            add("Cancelled — say what you’d like to build instead.")
        elif t == "aios_capabilities":
            add(data.get("title") or "Here’s what I can help with in NovaFlow.")
        elif t == "aios_workflows":
            n = data.get("count", 0)
            add(f"You have {n} workflow(s). Pick one on the card or say **run my last workflow**.")
        elif t == "aios_run_status":
            add(data.get("message") or f"Run status: {data.get('status') or 'updated'}.")
        elif t == "aios_knowledge":
            add(data.get("message") or "Knowledge updated.")
        elif t == "aios_memory":
            # Skip recipe memory noise in friendly mode
            if tech_details and data.get("last_recipe"):
                add(f"Remembered: {data['last_recipe']}")
        elif t == "aios_agent_progress":
            add(data.get("message") or "Working on that…")
        elif t == "aios_agent_result":
            out = (data.get("output") or "")[:400]
            add(out or "Finished.")
        elif t == "aios_requirements":
            # Silent by default unless it's the only useful line
            msg = data.get("message") or ""
            if msg and "linked" not in msg.lower():
                add(msg)
        elif t == "aios_fulfillment":
            # Prefer solution blurb; skip checklist chatter unless alone
            pass
        elif t == "aios_policy":
            add(data.get("message") or "Policy note.")
        elif t == "aios_denied":
            add(data.get("message") or "You don’t have permission for that action.")
        elif t == "aios_suggest":
            add(data.get("message") or "Here are some next steps.")
        elif t == "aios_powerhouse":
            add(data.get("message") or "Here are the big chat tools you can use.")
        elif t == "aios_diff":
            add(data.get("message") or "Here’s how your plan changed.")
        elif t == "aios_versions":
            add(data.get("message") or "Here are saved versions of this workflow.")
        elif t == "aios_eval":
            add(data.get("message") or "Eval scorecard ready.")
        elif t == "aios_receipt":
            add(data.get("message") or "Here’s your session cost estimate.")
        elif t == "aios_debug":
            add(data.get("message") or "Here’s what happened in the last run.")
        elif t == "aios_kg":
            add(data.get("message") or "Here’s what I found in your knowledge.")
        elif t == "aios_collab":
            add(data.get("message") or "Collaboration share is ready.")
        elif t == "aios_incident":
            add(data.get("message") or "Incident controls ready.")
        elif t == "aios_simulate":
            add(data.get("message") or "Simulation finished — see the results on the card.")
        elif t == "aios_sla":
            add(data.get("message") or "Here’s your reliability brief.")
        elif t == "aios_change_request":
            add(data.get("message") or "Here’s a proposed change to review.")
        elif t == "aios_digest":
            add(data.get("message") or "I pulled action items from your files.")
        elif t == "aios_autopilot":
            add(data.get("message") or "Autopilot is running your playbook steps.")
        elif t == "aios_forge":
            add(data.get("message") or "Here are the Chat Forge tools.")
        elif t == "aios_drift":
            add(data.get("message") or "Here’s your prompt/config drift radar.")
        elif t == "aios_ab":
            add(data.get("message") or "Here are your A/B model routes.")
        elif t == "aios_webhook":
            add(data.get("message") or "Webhook studio ready.")
        elif t == "aios_project":
            add(data.get("message") or "Project packs listed.")
        elif t == "aios_publish_scan":
            add(data.get("message") or "Publish scan complete.")
        elif t == "aios_reuse":
            add(data.get("message") or "Template reuse match ready.")
        elif t == "aios_model_lab":
            add(data.get("message") or "Model lab cost desk ready.")
        elif t == "aios_ocr":
            add(data.get("message") or "Extracted text from your attachments.")
        elif t == "aios_issue":
            add(data.get("message") or "GitHub issue bridge status.")
        elif t == "aios_csv":
            add(data.get("message") or "CSV import preview ready.")
        elif t == "aios_docs":
            add(data.get("message") or "Solution documentation generated.")
        elif t == "aios_assert":
            add(data.get("message") or "Solution assertions finished.")
        elif t in (
            "aios_schedule",
            "aios_compliance",
            "aios_finops",
            "aios_health",
            "aios_recommendation",
            "aios_export",
            "aios_share",
            "aios_meta",
            "aios_audit",
            "aios_vault",
            "aios_integration",
            "aios_playbook",
        ):
            add(
                data.get("message")
                or data.get("title")
                or "Done — see the card for details."
            )

    summary = "\n".join(parts).strip()
    if not summary:
        summary = "Done — use the buttons on the card."
    return summary
