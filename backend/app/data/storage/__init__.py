"""Object storage registry."""

from __future__ import annotations

from app.data.config import load_data_config
from app.data.storage.base import ObjectStorageProvider
from app.data.storage.local import LocalObjectStorage
from app.data.storage.s3 import S3CompatibleStorage

_storage: ObjectStorageProvider | None = None


def resolve_storage(cfg=None) -> ObjectStorageProvider:
    cfg = cfg or load_data_config()
    p = (cfg.storage_provider or "local").lower()
    if p in ("s3", "r2", "minio", "gcs", "azure"):
        label = p if p != "gcs" else "s3"  # GCS via S3 interop endpoint
        return S3CompatibleStorage(
            bucket=cfg.storage_bucket,
            endpoint=cfg.storage_endpoint,
            access_key=cfg.storage_access_key,
            secret_key=cfg.storage_secret_key,
            region=cfg.storage_region,
            provider_label=label,
        )
    return LocalObjectStorage()


def get_object_storage(*, reset: bool = False) -> ObjectStorageProvider:
    global _storage
    if reset or _storage is None:
        _storage = resolve_storage()
    return _storage
