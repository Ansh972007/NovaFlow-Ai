import json
import math
from typing import Any

import httpx

from app.config import OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_EMBEDDING_MODEL


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
    if not OPENAI_API_KEY or not texts:
        return []
    model = model or OPENAI_EMBEDDING_MODEL
    url = f"{OPENAI_BASE_URL.rstrip('/')}/embeddings"
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
    payload = {"model": model, "input": texts}
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()
        items = sorted(data.get("data", []), key=lambda x: x.get("index", 0))
        return [item["embedding"] for item in items if "embedding" in item]


def embed_texts_sync(texts: list[str], model: str | None = None) -> list[list[float]]:
    import asyncio

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(embed_texts(texts, model))
    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(lambda: asyncio.run(embed_texts(texts, model))).result()


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
