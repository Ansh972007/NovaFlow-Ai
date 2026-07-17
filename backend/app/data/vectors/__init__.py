"""Vector store registry — runtime provider switching."""

from __future__ import annotations

from app.data.config import load_data_config
from app.data.dialect import DialectKind, detect_dialect
from app.data.vectors.base import VectorStoreProvider
from app.data.vectors.milvus_provider import MilvusVectorStore
from app.data.vectors.pgvector_provider import PgVectorStore
from app.data.vectors.qdrant_provider import QdrantVectorStore
from app.data.vectors.sqlite_provider import SqliteVectorStore

_provider: VectorStoreProvider | None = None


def resolve_vector_provider(cfg=None) -> VectorStoreProvider:
    cfg = cfg or load_data_config()
    choice = (cfg.vector_provider or "auto").lower()
    if choice == "milvus":
        return MilvusVectorStore(cfg.milvus_uri)
    if choice == "pgvector":
        return PgVectorStore(cfg.database_url)
    if choice == "qdrant":
        return QdrantVectorStore(cfg.qdrant_url, cfg.qdrant_api_key)
    if choice == "sqlite":
        return SqliteVectorStore()
    # auto
    if cfg.milvus_uri:
        p = MilvusVectorStore(cfg.milvus_uri)
        if p.init():
            return p
    if cfg.qdrant_url:
        p = QdrantVectorStore(cfg.qdrant_url, cfg.qdrant_api_key)
        if p.init():
            return p
    if detect_dialect(cfg.database_url) == DialectKind.POSTGRESQL:
        p = PgVectorStore(cfg.database_url)
        if p.init():
            return p
    return SqliteVectorStore()


def get_vector_store(*, reset: bool = False) -> VectorStoreProvider:
    global _provider
    if reset or _provider is None:
        _provider = resolve_vector_provider()
        _provider.init()
    return _provider
