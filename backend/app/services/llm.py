import json
from typing import Any, AsyncIterator

import httpx

from app.services.workspace_settings import get_chat_config

MAX_HISTORY_MESSAGES = 12
MAX_HISTORY_CHARS = 4000


def _provider_headers(cfg: dict) -> dict[str, str]:
    from app.services.llm_providers import openai_compat_headers

    return openai_compat_headers(cfg["api_key"], cfg.get("base_url") or "")


def _normalize_history(history: list[dict] | None) -> list[dict[str, str]]:
    """Keep last N prior user/assistant turns for multi-turn chat."""
    if not history:
        return []
    cleaned: list[dict[str, str]] = []
    for row in history:
        role = (row.get("role") or "").strip().lower()
        if role not in ("user", "assistant"):
            continue
        content = (row.get("content") or "").strip()
        if not content:
            continue
        cleaned.append({"role": role, "content": content[:MAX_HISTORY_CHARS]})
    return cleaned[-MAX_HISTORY_MESSAGES:]


def _cancelled(cancel_event) -> bool:
    return cancel_event is not None and cancel_event.is_set()


async def stream_chat(
    system_prompt: str,
    user_message: str,
    *,
    db=None,
    workspace_id: int | None = None,
    cancel_event=None,
    usage_out: dict | None = None,
    history: list[dict] | None = None,
) -> AsyncIterator[str]:
    cfg = get_chat_config(db)
    if db is not None and workspace_id:
        from app.services.ab_routing import pick_ab_model

        routed = pick_ab_model(db, workspace_id, cfg.get("model") or "")
        if routed:
            cfg = {**cfg, "model": routed["model"]}

    if usage_out is not None:
        usage_out.setdefault("model", cfg.get("model") or "")

    prior = _normalize_history(history)

    if not cfg["api_key"]:
        context_bits = ""
        if "--- Retrieved context ---" in system_prompt or "--- Context ---" in system_prompt:
            context_bits = (
                "\n\n[Grounded from your knowledge library — add an API key in Settings for full model answers.]\n"
            )
            for marker in ("--- Retrieved context ---", "--- Context ---"):
                if marker in system_prompt:
                    excerpt = system_prompt.split(marker, 1)[-1]
                    excerpt = excerpt.split("--- End", 1)[0].strip()[:800]
                    if excerpt:
                        context_bits += f"Retrieved evidence:\n{excerpt}\n"
                    break
        reply = (
            f"(NovaFlow demo mode — add a model provider in Settings → Model providers.)\n\n"
            f"You asked: {user_message}"
            f"{context_bits}"
        )
        words = reply.split(" ")
        for i, w in enumerate(words):
            if _cancelled(cancel_event):
                break
            yield (" " if i else "") + w
        return

    if cfg.get("provider_type") == "anthropic":
        async for token in _stream_anthropic(
            cfg,
            system_prompt,
            user_message,
            cancel_event=cancel_event,
            usage_out=usage_out,
            history=prior,
        ):
            yield token
        return

    url = f"{cfg['base_url']}/chat/completions"
    headers = _provider_headers(cfg)
    messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
    messages.extend(prior)
    messages.append({"role": "user", "content": user_message})
    payload: dict[str, Any] = {
        "model": cfg["model"],
        "stream": True,
        "messages": messages,
        "stream_options": {"include_usage": True},
    }
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream("POST", url, headers=headers, json=payload) as resp:
                if resp.status_code >= 400:
                    body = (await resp.aread()).decode("utf-8", errors="ignore")
                    yield _friendly_llm_error(resp.status_code, body, provider_name=cfg.get("provider_name"))
                    return
                async for line in resp.aiter_lines():
                    if _cancelled(cancel_event):
                        await resp.aclose()
                        break
                    if not line.startswith("data: "):
                        continue
                    data = line[6:].strip()
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        if usage_out is not None and chunk.get("usage"):
                            u = chunk["usage"]
                            usage_out["prompt_tokens"] = u.get("prompt_tokens") or usage_out.get("prompt_tokens")
                            usage_out["completion_tokens"] = u.get("completion_tokens") or usage_out.get(
                                "completion_tokens"
                            )
                            usage_out["total_tokens"] = u.get("total_tokens") or usage_out.get("total_tokens")
                        choices = chunk.get("choices") or []
                        if not choices:
                            continue
                        delta = (choices[0].get("delta") or {}).get("content") or ""
                        if delta:
                            yield delta
                    except (json.JSONDecodeError, KeyError, IndexError, TypeError):
                        continue
    except httpx.HTTPError as exc:
        yield f"NovaFlow could not reach the model provider ({exc}). Check Settings → Model providers."


def _friendly_llm_error(status: int, body: str, provider_name: str | None = None) -> str:
    low = (body or "").lower()
    label = provider_name or "Model provider"
    if status == 401:
        return (
            f"{label} rejected this API key (unauthorized). "
            "Update the key in Settings → Model providers, then try again."
        )
    if status == 429 or "quota" in low or "billing" in low or "rate limit" in low:
        return (
            f"{label} quota/billing or rate limit reached. "
            "Add credits or wait and retry. "
            "Document upload and keyword search still work without embeddings."
        )
    if status == 404:
        return f"Model not found for this provider. Check chat model in Settings. Details: {body[:180]}"
    return f"{label} error HTTP {status}. {body[:240]}"


def _merge_anthropic_usage(usage_out: dict | None, usage: dict | None) -> None:
    if usage_out is None or not usage:
        return
    if usage.get("input_tokens") is not None:
        usage_out["prompt_tokens"] = usage["input_tokens"]
    if usage.get("output_tokens") is not None:
        usage_out["completion_tokens"] = usage["output_tokens"]
    pt = usage_out.get("prompt_tokens")
    ct = usage_out.get("completion_tokens")
    if pt is not None or ct is not None:
        usage_out["total_tokens"] = int(pt or 0) + int(ct or 0)


async def _stream_anthropic(
    cfg: dict,
    system_prompt: str,
    user_message: str,
    *,
    cancel_event=None,
    usage_out: dict | None = None,
    history: list[dict] | None = None,
) -> AsyncIterator[str]:
    base = cfg["base_url"].rstrip("/")
    url = f"{base}/v1/messages" if not base.endswith("/v1/messages") else base
    headers = {
        "x-api-key": cfg["api_key"],
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }
    messages: list[dict[str, str]] = []
    for row in history or []:
        messages.append({"role": row["role"], "content": row["content"]})
    messages.append({"role": "user", "content": user_message})
    # Anthropic requires alternating roles; merge consecutive same-role turns
    merged: list[dict[str, str]] = []
    for m in messages:
        if merged and merged[-1]["role"] == m["role"]:
            merged[-1]["content"] = f"{merged[-1]['content']}\n\n{m['content']}"
        else:
            merged.append(dict(m))
    if merged and merged[0]["role"] != "user":
        merged.insert(0, {"role": "user", "content": "(continue)"})

    payload = {
        "model": cfg["model"],
        "max_tokens": 4096,
        "stream": True,
        "system": system_prompt,
        "messages": merged,
    }
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream("POST", url, headers=headers, json=payload) as resp:
                if resp.status_code >= 400:
                    body = (await resp.aread()).decode("utf-8", errors="ignore")
                    yield _friendly_llm_error(resp.status_code, body, provider_name=cfg.get("provider_name"))
                    return
                async for line in resp.aiter_lines():
                    if _cancelled(cancel_event):
                        await resp.aclose()
                        break
                    if not line.startswith("data: "):
                        continue
                    data = line[6:].strip()
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        ctype = chunk.get("type")
                        if ctype == "message_start":
                            _merge_anthropic_usage(usage_out, (chunk.get("message") or {}).get("usage"))
                        elif ctype == "message_delta":
                            _merge_anthropic_usage(usage_out, chunk.get("usage"))
                        elif ctype == "content_block_delta":
                            delta = chunk.get("delta", {}).get("text") or ""
                            if delta:
                                yield delta
                    except json.JSONDecodeError:
                        continue
    except httpx.HTTPError as exc:
        yield f"NovaFlow could not reach Anthropic ({exc}). Check Settings → Model providers."


async def stream_chat_sync(
    system_prompt: str,
    user_message: str,
    *,
    db=None,
    workspace_id: int | None = None,
    history: list[dict] | None = None,
) -> str:
    parts = []
    async for token in stream_chat(
        system_prompt,
        user_message,
        db=db,
        workspace_id=workspace_id,
        history=history,
    ):
        parts.append(token)
    return "".join(parts)
