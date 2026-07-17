"""Milvus provider — wraps existing pymilvus collection logic."""

from __future__ import annotations

import logging
from typing import Sequence

from app.config import EMBEDDING_DIM
from app.data.vectors.base import VectorStoreProvider

logger = logging.getLogger(__name__)
COLLECTION = "novaflow_chunks"


class MilvusVectorStore(VectorStoreProvider):
    name = "milvus"

    def __init__(self, uri: str):
        self.uri = uri
        self._collection = None
        self._ready = False

    def init(self) -> bool:
        if self._ready and self._collection is not None:
            return True
        if not self.uri:
            return False
        try:
            from pymilvus import Collection, CollectionSchema, DataType, FieldSchema, connections, utility

            connections.connect(alias="default", uri=self.uri)
            if not utility.has_collection(COLLECTION):
                fields = [
                    FieldSchema(name="chunk_id", dtype=DataType.INT64, is_primary=True, auto_id=False),
                    FieldSchema(name="knowledge_id", dtype=DataType.INT64),
                    FieldSchema(name="file_id", dtype=DataType.INT64),
                    FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=EMBEDDING_DIM),
                ]
                schema = CollectionSchema(fields, description="NovaFlow knowledge chunk vectors")
                col = Collection(COLLECTION, schema)
                col.create_index(
                    "embedding",
                    {"index_type": "IVF_FLAT", "metric_type": "IP", "params": {"nlist": 128}},
                )
            else:
                col = Collection(COLLECTION)
            col.load()
            self._collection = col
            self._ready = True
            return True
        except Exception as exc:
            logger.warning("Milvus unavailable: %s", exc)
            self._ready = False
            self._collection = None
            return False

    def upsert(self, rows: Sequence[tuple[int, int, int, list[float]]]) -> None:
        if not self.init() or not rows:
            return
        chunk_ids, knowledge_ids, file_ids, embeddings = zip(*rows)
        self._collection.upsert([list(chunk_ids), list(knowledge_ids), list(file_ids), list(embeddings)])
        self._collection.flush()

    def delete_by_file(self, file_id: int) -> None:
        if not self.init():
            return
        self._collection.delete(f"file_id == {int(file_id)}")
        self._collection.flush()

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
        results = self._collection.search(
            data=[query_vec],
            anns_field="embedding",
            param={"metric_type": "IP", "params": {"nprobe": 16}},
            limit=limit,
            expr=f"knowledge_id == {int(knowledge_id)}",
            output_fields=["chunk_id"],
        )
        out: list[tuple[int, float]] = []
        for hits in results:
            for hit in hits:
                cid = hit.entity.get("chunk_id") if hasattr(hit, "entity") else hit.id
                out.append((int(cid), float(hit.score)))
        return out

    def health(self) -> dict:
        ok = self.init()
        return {"provider": self.name, "ok": ok, "uri": bool(self.uri)}
