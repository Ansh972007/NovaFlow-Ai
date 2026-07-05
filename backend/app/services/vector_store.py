import logging
from typing import Optional

from app.config import EMBEDDING_DIM, MILVUS_URI

logger = logging.getLogger(__name__)

COLLECTION = "novaflow_chunks"
_collection = None
_milvus_ready = False


def milvus_enabled() -> bool:
    return bool(MILVUS_URI)


def _ensure_collection():
    global _collection, _milvus_ready
    if _milvus_ready and _collection is not None:
        return _collection
    if not MILVUS_URI:
        return None
    try:
        from pymilvus import Collection, CollectionSchema, DataType, FieldSchema, connections, utility

        connections.connect(alias="default", uri=MILVUS_URI)
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
        _collection = col
        _milvus_ready = True
        logger.info("Milvus vector store ready at %s", MILVUS_URI)
        return col
    except Exception as exc:
        logger.warning("Milvus unavailable, using SQLite embeddings: %s", exc)
        _milvus_ready = False
        _collection = None
        return None


def init_vector_store() -> bool:
    return _ensure_collection() is not None


def upsert_vectors(rows: list[tuple[int, int, int, list[float]]]) -> None:
    col = _ensure_collection()
    if not col or not rows:
        return
    chunk_ids, knowledge_ids, file_ids, embeddings = zip(*rows)
    col.upsert([list(chunk_ids), list(knowledge_ids), list(file_ids), list(embeddings)])
    col.flush()


def delete_by_file(file_id: int) -> None:
    col = _ensure_collection()
    if not col:
        return
    col.delete(f"file_id == {int(file_id)}")
    col.flush()


def search_vectors(knowledge_id: int, query_vec: list[float], limit: int) -> list[tuple[int, float]]:
    col = _ensure_collection()
    if not col or not query_vec:
        return []
    try:
        results = col.search(
            data=[query_vec],
            anns_field="embedding",
            param={"metric_type": "IP", "params": {"nprobe": 16}},
            limit=limit,
            expr=f"knowledge_id == {int(knowledge_id)}",
            output_fields=["chunk_id"],
        )
        hits: list[tuple[int, float]] = []
        for group in results:
            for hit in group:
                hits.append((int(hit.id), float(hit.distance)))
        return hits
    except Exception as exc:
        logger.warning("Milvus search failed: %s", exc)
        return []


def vector_backend() -> str:
    return "milvus" if _ensure_collection() else "sqlite"
