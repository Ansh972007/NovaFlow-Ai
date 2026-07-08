import json
from typing import Any, AsyncIterator

import httpx

from app.services.workspace_settings import get_chat_config


def _provider_headers(cfg: dict) -> dict[str, str]:
    from app.services.llm_providers import openai_compat_headers

    return openai_compat_headers(cfg["api_key"], cfg.get("base_url") or "")


async def stream_chat(
    system_prompt: str,
    user_message: str,
    *,
    db=None,
    workspace_id: int | None = None,
    cancel_event=None,
    usage_out: dict | None = None,
) -> AsyncIterator[str]:
    cfg = get_chat_config(db)
    if db is not None and workspace_id:
        from app.services.ab_routing import pick_ab_model

        routed = pick_ab_model(db, workspace_id, cfg.get("model") or "")
        if routed:
            cfg = {**cfg, "model": routed["model"]}

    if usage_out is not None:
        usage_out.setdefault("model", cfg.get("model") or "")

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
            if cancel_event is not None and cancel_event.is_set():
                break
            yield (" " if i else "") + w
        return

    if cfg.get("provider_type") == "anthropic":
        async for token in _stream_anthropic(cfg, system_prompt, user_message, cancel_event=cancel_event):
            yield token
        return

    url = f"{cfg['base_url']}/chat/completions"
    headers = _provider_headers(cfg)
    payload: dict[str, Any] = {
        "model": cfg["model"],
        "stream": True,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
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
                    if cancel_event is not None and cancel_event.is_set():
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


async def _stream_anthropic(
    cfg: dict,
    system_prompt: str,
    user_message: str,
    *,
    cancel_event=None,
) -> AsyncIterator[str]:
    base = cfg["base_url"].rstrip("/")
    url = f"{base}/v1/messages" if not base.endswith("/v1/messages") else base
    headers = {
        "x-api-key": cfg["api_key"],
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }
    payload = {
        "model": cfg["model"],
        "max_tokens": 4096,
        "stream": True,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_message}],
    }
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream("POST", url, headers=headers, json=payload) as resp:
                if resp.status_code >= 400:
                    body = (await resp.aread()).decode("utf-8", errors="ignore")
                    yield _friendly_llm_error(resp.status_code, body, provider_name=cfg.get("provider_name"))
                    return
                async for line in resp.aiter_lines():
                    if cancel_event is not None and cancel_event.is_set():
                        break
                    if not line.startswith("data: "):
                        continue
                    data = line[6:].strip()
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        if chunk.get("type") == "content_block_delta":
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
) -> str:
    parts = []
    async for token in stream_chat(system_prompt, user_message, db=db, workspace_id=workspace_id):
        parts.append(token)
    return "".join(parts)
