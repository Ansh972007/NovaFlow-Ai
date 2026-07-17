"""Dialect detection and capability matrix — no vendor lock-in in app code."""

from __future__ import annotations

from enum import Enum
from functools import lru_cache
from urllib.parse import urlparse


class DialectKind(str, Enum):
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    SQLITE = "sqlite"
    UNKNOWN = "unknown"


@lru_cache(maxsize=8)
def detect_dialect(database_url: str) -> DialectKind:
    url = (database_url or "").lower()
    if url.startswith("postgres") or url.startswith("postgresql") or "+psycopg" in url or "+asyncpg" in url:
        return DialectKind.POSTGRESQL
    if url.startswith("mysql") or "+pymysql" in url or "+mysqldb" in url:
        return DialectKind.MYSQL
    if url.startswith("sqlite"):
        return DialectKind.SQLITE
    # try parse scheme
    try:
        scheme = urlparse(database_url).scheme.split("+")[0]
        if scheme in ("postgres", "postgresql"):
            return DialectKind.POSTGRESQL
        if scheme == "mysql":
            return DialectKind.MYSQL
        if scheme == "sqlite":
            return DialectKind.SQLITE
    except Exception:
        pass
    return DialectKind.UNKNOWN


def dialect_capabilities(kind: DialectKind) -> dict:
    """Feature flags used by migrations / partitioning / FTS."""
    if kind == DialectKind.POSTGRESQL:
        return {
            "jsonb": True,
            "gin": True,
            "gist": True,
            "brin": True,
            "partitioning": True,
            "listen_notify": True,
            "advisory_locks": True,
            "generated_columns": True,
            "native_uuid": True,
            "full_text": True,
            "pgvector": True,
            "materialized_views": True,
            "partial_indexes": True,
            "expression_indexes": True,
        }
    if kind == DialectKind.MYSQL:
        return {
            "jsonb": False,
            "gin": False,
            "gist": False,
            "brin": False,
            "partitioning": True,  # limited
            "listen_notify": False,
            "advisory_locks": False,
            "generated_columns": True,
            "native_uuid": False,
            "full_text": True,
            "pgvector": False,
            "materialized_views": False,
            "partial_indexes": False,
            "expression_indexes": False,
        }
    # sqlite / unknown — dev only
    return {
        "jsonb": False,
        "gin": False,
        "gist": False,
        "brin": False,
        "partitioning": False,
        "listen_notify": False,
        "advisory_locks": False,
        "generated_columns": False,
        "native_uuid": False,
        "full_text": True,
        "pgvector": False,
        "materialized_views": False,
        "partial_indexes": False,
        "expression_indexes": False,
    }
