"""Qdrant vector provider — optional HTTP client via qdrant-client when installed."""

from __future__ import annotations

import logging
from typing import Sequence

from app.config import EMBEDDING_DIM
from app.data.vectors.base import VectorStoreProvider

logger = logging.getLogger(__name__)
COLLECTION = "novaflow_chunks"


class QdrantVectorStore(VectorStoreProvider):
    name = "qdrant"

    def __init__(self, url: str, api_key: str = ""):
        self.url = url
        self.api_key = api_key
        self._client = None
        self._ready = False

    def init(self) -> bool:
        if self._ready:
            return True
        if not self.url:
            return False
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.http import models as qm

            self._client = QdrantClient(url=self.url, api_key=self.api_key or None)
            names = [c.name for c in self._client.get_collections().collections]
            if COLLECTION not in names:
                self._client.create_collection(
                    collection_name=COLLECTION,
                    vectors_config=qm.VectorParams(size=EMBEDDING_DIM, distance=qm.Distance.COSINE),
                )
            self._ready = True
            return True
        except Exception as exc:
            logger.warning("Qdrant unavailable: %s", exc)
            self._ready = False
            self._client = None
            return False

    def upsert(self, rows: Sequence[tuple[int, int, int, list[float]]]) -> None:
        if not self.init() or not rows:
            return
        from qdrant_client.http import models as qm

        points = [
            qm.PointStruct(
                id=int(cid),
                vector=list(emb),
                payload={"knowledge_id": int(kid), "file_id": int(fid)},
            )
            for cid, kid, fid, emb in rows
        ]
        self._client.upsert(collection_name=COLLECTION, points=points)

    def delete_by_file(self, file_id: int) -> None:
        if not self.init():
            return
        from qdrant_client.http import models as qm

        self._client.delete(
            collection_name=COLLECTION,
            points_selector=qm.FilterSelector(
                filter=qm.Filter(
                    must=[qm.FieldCondition(key="file_id", match=qm.MatchValue(value=int(file_id)))]
                )
            ),
        )

    def search(
        self,
        knowledge_id: int,
        query_vec: list[float],
        limit: int,
        *,
        workspace_id: int | None = None,
    ) -> list[tuple[int, float]]:
        if not self.init() or not query_vec:
            return []
        from qdrant_client.http import models as qm

        hits = self._client.search(
            collection_name=COLLECTION,
            query_vector=query_vec,
            query_filter=qm.Filter(
                must=[qm.FieldCondition(key="knowledge_id", match=qm.MatchValue(value=int(knowledge_id)))]
            ),
            limit=limit,
        )
        return [(int(h.id), float(h.score)) for h in hits]
