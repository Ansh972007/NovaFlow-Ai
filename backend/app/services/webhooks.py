import logging
from typing import Any

import httpx

logger = logging.getLogger("novaflow.webhooks")


async def post_webhook(url: str, payload: dict[str, Any], *, event: str) -> bool:
    if not (url or "").strip():
        return False
    from app.security.ssrf import SafeUrlError, assert_safe_url

    try:
        target = assert_safe_url(url.strip(), allow_http=True)
    except SafeUrlError as exc:
        logger.warning("Webhook %s blocked by SSRF policy: %s", event, exc)
        return False
    body = {"event": event, **payload}
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=False) as client:
            resp = await client.post(target, json=body)
            resp.raise_for_status()
        return True
    except Exception as exc:
        logger.warning("Webhook %s failed: %s", event, exc)
        return False


async def post_alert_notification(
    url: str,
    message: str,
    payload: dict[str, Any],
    *,
    event: str,
) -> bool:
    if not (url or "").strip():
        return False
    target = url.strip()
    if "hooks.slack.com" in target or "hook.slack.com" in target:
        body: dict[str, Any] = {"text": message}
    else:
        body = {"event": event, "message": message, **payload}
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(target, json=body)
            resp.raise_for_status()
        return True
    except Exception as exc:
        logger.warning("Alert notification %s failed: %s", event, exc)
        return False


async def post_pagerduty_alert(routing_key: str, summary: str, payload: dict[str, Any]) -> bool:
    if not (routing_key or "").strip():
        return False
    body = {
        "routing_key": routing_key.strip(),
        "event_action": "trigger",
        "payload": {
            "summary": summary[:1024],
            "severity": "warning",
            "source": "novaflow-eval",
            "custom_details": payload,
        },
    }
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post("https://events.pagerduty.com/v2/enqueue", json=body)
            resp.raise_for_status()
        return True
    except Exception as exc:
        logger.warning("PagerDuty alert failed: %s", exc)
        return False


async def post_opsgenie_alert(api_key: str, message: str, description: str, payload: dict[str, Any]) -> bool:
    if not (api_key or "").strip():
        return False
    body = {
        "message": message[:130],
        "description": description[:15000],
        "priority": "P3",
        "details": payload,
    }
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                "https://api.opsgenie.com/v2/alerts",
                headers={"Authorization": f"GenieKey {api_key.strip()}", "Content-Type": "application/json"},
                json=body,
            )
            resp.raise_for_status()
        return True
    except Exception as exc:
        logger.warning("Opsgenie alert failed: %s", exc)
        return False
