import json
from typing import AsyncIterator

import httpx

from app.services.workspace_settings import get_chat_config


async def stream_chat(system_prompt: str, user_message: str) -> AsyncIterator[str]:
    cfg = get_chat_config()
    if not cfg["api_key"]:
        reply = (
            f"I'm {system_prompt[:40]}… (NovaFlow demo mode — add a model provider in Settings.)\n\n"
            f"You asked: {user_message}"
        )
        words = reply.split(" ")
        for i, w in enumerate(words):
            yield (" " if i else "") + w
        return

    if cfg.get("provider_type") == "anthropic":
        async for token in _stream_anthropic(cfg, system_prompt, user_message):
            yield token
        return

    url = f"{cfg['base_url']}/chat/completions"
    headers = {"Authorization": f"Bearer {cfg['api_key']}", "Content-Type": "application/json"}
    payload = {
        "model": cfg["model"],
        "stream": True,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
    }
    async with httpx.AsyncClient(timeout=120) as client:
        async with client.stream("POST", url, headers=headers, json=payload) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data = line[6:].strip()
                if data == "[DONE]":
                    break
                try:
                    chunk = json.loads(data)
                    delta = chunk["choices"][0]["delta"].get("content") or ""
                    if delta:
                        yield delta
                except (json.JSONDecodeError, KeyError, IndexError):
                    continue


async def _stream_anthropic(cfg: dict, system_prompt: str, user_message: str) -> AsyncIterator[str]:
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
    async with httpx.AsyncClient(timeout=120) as client:
        async with client.stream("POST", url, headers=headers, json=payload) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
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


async def stream_chat_sync(system_prompt: str, user_message: str) -> str:
    parts = []
    async for token in stream_chat(system_prompt, user_message):
        parts.append(token)
    return "".join(parts)
