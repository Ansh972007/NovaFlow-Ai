import json
import math
from typing import Any

import httpx

from app.services.workspace_settings import get_chat_config, get_embedding_model


def _emb_headers(cfg: dict) -> dict[str, str]:
    from app.services.llm_providers import openai_compat_headers

    return openai_compat_headers(cfg["api_key"], cfg.get("base_url") or "")


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


async def embed_texts(texts: list[str], model: str | None = None) -> list[list[float]]:
    cfg = get_chat_config()
    if not cfg["api_key"] or not texts:
        return []
    if cfg.get("provider_type") == "anthropic":
        return []
    model = model or get_embedding_model()
    url = f"{cfg['base_url']}/embeddings"
    headers = _emb_headers(cfg)
    payload = {"model": model, "input": texts}
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code >= 400:
                # Quota/key errors: fall back to keyword search rather than crashing ingest
                return []
            data = resp.json()
            items = sorted(data.get("data", []), key=lambda x: x.get("index", 0))
            return [item["embedding"] for item in items if "embedding" in item]
    except httpx.HTTPError:
        return []


def embed_texts_sync(texts: list[str], model: str | None = None) -> list[list[float]]:
    from app.runtime.async_bridge import run_coro_sync

    return run_coro_sync(embed_texts(texts, model))


def parse_embedding(raw: str | None) -> list[float] | None:
    if not raw:
        return None
    try:
        vec = json.loads(raw)
        if isinstance(vec, list) and vec:
            return [float(x) for x in vec]
    except (json.JSONDecodeError, TypeError, ValueError):
        return None
    return None


def rank_by_embedding(
    rows: list[tuple[Any, Any, list[float] | None]],
    query_vec: list[float],
    limit: int,
) -> list[tuple[float, Any, Any]]:
    scored: list[tuple[float, Any, Any]] = []
    for chunk, file, vec in rows:
        if not vec:
            continue
        score = _cosine(query_vec, vec)
        if score > 0.05:
            scored.append((score, chunk, file))
    scored.sort(key=lambda x: -x[0])
    return scored[:limit]
