"""In-DB embedding fallback — cosine over KnowledgeChunk.embedding_json."""

from __future__ import annotations

import json
import math
from typing import Sequence

from app.data.vectors.base import VectorStoreProvider


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


class SqliteVectorStore(VectorStoreProvider):
    """No separate vector engine — search delegated to callers via DB rows.

    upsert/delete are no-ops (embeddings already stored on KnowledgeChunk).
    search uses SessionLocal when available.
    """

    name = "sqlite"

    def init(self) -> bool:
        return True

    def upsert(self, rows: Sequence[tuple[int, int, int, list[float]]]) -> None:
        return None

    def delete_by_file(self, file_id: int) -> None:
        return None

    def search(
        self,
        knowledge_id: int,
        query_vec: list[float],
        limit: int,
        *,
        workspace_id: int | None = None,
    ) -> list[tuple[int, float]]:
        from app.database import KnowledgeChunk, SessionLocal

        db = SessionLocal()
        try:
            q = db.query(KnowledgeChunk).filter(KnowledgeChunk.knowledge_id == knowledge_id)
            scored: list[tuple[int, float]] = []
            for row in q.all():
                try:
                    emb = json.loads(row.embedding_json or "[]")
                except json.JSONDecodeError:
                    continue
                if not isinstance(emb, list) or not emb:
                    continue
                scored.append((row.id, _cosine(query_vec, [float(x) for x in emb])))
            scored.sort(key=lambda x: -x[1])
            return scored[:limit]
        finally:
            db.close()
