"""Backward-compatible vector store facade — delegates to app.data.vectors registry."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def milvus_enabled() -> bool:
    from app.data.config import load_data_config

    return bool(load_data_config().milvus_uri)


def init_vector_store() -> bool:
    from app.data.vectors import get_vector_store

    store = get_vector_store(reset=True)
    return store.init()


def upsert_vectors(rows: list[tuple[int, int, int, list[float]]]) -> None:
    from app.data.vectors import get_vector_store

    get_vector_store().upsert(rows)


def delete_by_file(file_id: int) -> None:
    from app.data.vectors import get_vector_store

    get_vector_store().delete_by_file(file_id)


def search_vectors(knowledge_id: int, query_vec: list[float], limit: int) -> list[tuple[int, float]]:
    from app.data.vectors import get_vector_store

    return get_vector_store().search(knowledge_id, query_vec, limit)


def vector_backend() -> str:
    from app.data.vectors import get_vector_store

    store = get_vector_store()
    store.init()
    return store.name
