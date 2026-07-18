"""Shared async HTTP helper for connector plugins.

Handles rate limits (429 + Retry-After), transient 5xx retries with exponential
backoff, and SSRF-safe outbound calls. Reused by all remote connector plugins so
no plugin reimplements retry/pagination logic.
"""

from __future__ import annotations

import asyncio
from typing import Any

import httpx

DEFAULT_TIMEOUT = 30
MAX_RETRIES = 3


async def request_with_retry(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
    json_body: dict | None = None,
    data: Any = None,
    content: bytes | None = None,
    timeout: int = DEFAULT_TIMEOUT,
    max_retries: int = MAX_RETRIES,
    allow_http: bool = False,
) -> httpx.Response:
    """Perform an outbound HTTP call with SSRF checks, 429 and 5xx retries."""
    from app.security.ssrf import SafeUrlError, assert_safe_url

    try:
        safe_url = assert_safe_url(url, allow_http=allow_http)
    except SafeUrlError as exc:
        raise ValueError(f"URL blocked by security policy: {exc}") from exc

    last_exc: Exception | None = None
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
        for attempt in range(max_retries + 1):
            try:
                resp = await client.request(
                    method.upper(),
                    safe_url,
                    headers=headers,
                    params=params,
                    json=json_body,
                    data=data,
                    content=content,
                )
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                last_exc = exc
                if attempt >= max_retries:
                    raise
                await asyncio.sleep(0.4 * (2**attempt))
                continue

            if resp.status_code == 429 and attempt < max_retries:
                retry_after = resp.headers.get("Retry-After")
                delay = float(retry_after) if (retry_after or "").isdigit() else 0.5 * (2**attempt)
                await asyncio.sleep(min(delay, 30))
                continue
            if resp.status_code >= 500 and attempt < max_retries:
                await asyncio.sleep(0.4 * (2**attempt))
                continue
            return resp

    if last_exc:
        raise last_exc
    raise RuntimeError("request_with_retry exhausted without response")


async def paginate(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
    items_key: str,
    next_from,
    max_pages: int = 20,
    max_items: int = 500,
) -> list[dict]:
    """Follow pagination via a caller-supplied `next_from(response_json) -> (url, params) | None`."""
    items: list[dict] = []
    cur_url, cur_params = url, dict(params or {})
    for _ in range(max_pages):
        resp = await request_with_retry(method, cur_url, headers=headers, params=cur_params)
        if resp.status_code >= 400:
            raise ValueError(resp.text[:400])
        data = resp.json()
        page_items = data.get(items_key) or []
        items.extend(page_items)
        if len(items) >= max_items:
            return items[:max_items]
        nxt = next_from(data)
        if not nxt:
            break
        cur_url, cur_params = nxt
    return items
