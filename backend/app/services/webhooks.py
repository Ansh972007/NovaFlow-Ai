import logging
from typing import Any

import httpx

logger = logging.getLogger("novaflow.webhooks")


async def post_webhook(url: str, payload: dict[str, Any], *, event: str) -> bool:
    if not (url or "").strip():
        return False
    body = {"event": event, **payload}
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(url.strip(), json=body)
            resp.raise_for_status()
        return True
    except Exception as exc:
        logger.warning("Webhook %s failed: %s", event, exc)
        return False
