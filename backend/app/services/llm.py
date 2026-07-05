import json
from typing import AsyncIterator

import httpx

from app.config import OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL


async def stream_chat(system_prompt: str, user_message: str) -> AsyncIterator[str]:
    if not OPENAI_API_KEY:
        reply = (
            f"I'm {system_prompt[:40]}… (NovaFlow demo mode — set OPENAI_API_KEY for real replies.)\n\n"
            f"You asked: {user_message}"
        )
        words = reply.split(" ")
        for i, w in enumerate(words):
            yield (" " if i else "") + w
        return

    url = f"{OPENAI_BASE_URL.rstrip('/')}/chat/completions"
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": OPENAI_MODEL,
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


async def stream_chat_sync(system_prompt: str, user_message: str) -> str:
    parts = []
    async for token in stream_chat(system_prompt, user_message):
        parts.append(token)
    return "".join(parts)
