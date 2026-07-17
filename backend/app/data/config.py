"""Data platform configuration — env-driven, vendor-agnostic."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class DataPlatformConfig:
    database_url: str
    redis_url: str
    vector_provider: str  # auto | milvus | pgvector | qdrant | sqlite
    milvus_uri: str
    qdrant_url: str
    qdrant_api_key: str
    storage_provider: str  # local | s3 | r2 | minio | gcs | azure
    storage_bucket: str
    storage_endpoint: str
    storage_access_key: str
    storage_secret_key: str
    storage_region: str
    pool_size: int
    max_overflow: int
    pool_timeout: int
    pool_recycle: int
    statement_timeout_ms: int
    partition_months_ahead: int
    audit_retention_days: int
    soft_delete_purge_days: int
    enable_pgbouncer_mode: bool  # disables SQLAlchemy pool when behind PgBouncer


def load_data_config() -> DataPlatformConfig:
    from app.config import DATABASE_URL, REDIS_URL, MILVUS_URI

    return DataPlatformConfig(
        database_url=DATABASE_URL,
        redis_url=REDIS_URL or os.getenv("REDIS_URL", ""),
        vector_provider=(os.getenv("VECTOR_PROVIDER") or "auto").strip().lower(),
        milvus_uri=MILVUS_URI or os.getenv("MILVUS_URI", ""),
        qdrant_url=os.getenv("QDRANT_URL", ""),
        qdrant_api_key=os.getenv("QDRANT_API_KEY", ""),
        storage_provider=(os.getenv("STORAGE_PROVIDER") or "local").strip().lower(),
        storage_bucket=os.getenv("STORAGE_BUCKET", "novaflow"),
        storage_endpoint=os.getenv("STORAGE_ENDPOINT", ""),
        storage_access_key=os.getenv("STORAGE_ACCESS_KEY", ""),
        storage_secret_key=os.getenv("STORAGE_SECRET_KEY", ""),
        storage_region=os.getenv("STORAGE_REGION", "auto"),
        pool_size=int(os.getenv("DB_POOL_SIZE", "10")),
        max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "20")),
        pool_timeout=int(os.getenv("DB_POOL_TIMEOUT", "30")),
        pool_recycle=int(os.getenv("DB_POOL_RECYCLE", "1800")),
        statement_timeout_ms=int(os.getenv("DB_STATEMENT_TIMEOUT_MS", "30000")),
        partition_months_ahead=int(os.getenv("DB_PARTITION_MONTHS_AHEAD", "3")),
        audit_retention_days=int(os.getenv("AUDIT_RETENTION_DAYS", "365")),
        soft_delete_purge_days=int(os.getenv("SOFT_DELETE_PURGE_DAYS", "90")),
        enable_pgbouncer_mode=os.getenv("DB_PGBOUNCER_MODE", "").lower() in {"1", "true", "yes"},
    )
