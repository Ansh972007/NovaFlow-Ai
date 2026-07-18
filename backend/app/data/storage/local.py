"""Local filesystem object storage — default for development."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import BinaryIO

from app.config import UPLOAD_DIR
from app.data.storage.base import ObjectStorageProvider, StoredObject


class LocalObjectStorage(ObjectStorageProvider):
    name = "local"

    def __init__(self, root: Path | None = None):
        self.root = Path(root or UPLOAD_DIR)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        key = key.replace("\\", "/").lstrip("/")
        if ".." in key.split("/"):
            raise ValueError("Invalid key")
        path = self.root / key
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def put(
        self,
        key: str,
        data: bytes | BinaryIO,
        *,
        content_type: str = "application/octet-stream",
        workspace_id: int | None = None,
    ) -> StoredObject:
        if workspace_id is not None and not key.startswith("ws/"):
            key = self.tenant_key(workspace_id, key)
        raw = data.read() if hasattr(data, "read") else data
        assert isinstance(raw, (bytes, bytearray))
        path = self._path(key)
        path.write_bytes(raw)
        checksum = hashlib.sha256(raw).hexdigest()
        return StoredObject(
            key=key,
            bucket=str(self.root),
            size=len(raw),
            checksum=checksum,
            content_type=content_type,
            provider=self.name,
        )

    def get(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def delete(self, key: str) -> None:
        path = self._path(key)
        if path.exists():
            path.unlink()

    def exists(self, key: str) -> bool:
        return self._path(key).exists()

    def signed_url(self, key: str, *, expires_seconds: int = 3600, method: str = "GET") -> str:
        # Local: return file URI for operators (not for public browsers)
        return self._path(key).as_uri()

    def list_objects(self, *, prefix: str = "", limit: int = 1000) -> list[StoredObject]:
        base = self.root
        safe_prefix = prefix.replace("\\", "/").lstrip("/")
        out: list[StoredObject] = []
        for path in sorted(base.rglob("*")):
            if not path.is_file():
                continue
            key = path.relative_to(base).as_posix()
            if safe_prefix and not key.startswith(safe_prefix):
                continue
            raw = path.read_bytes()
            out.append(
                StoredObject(
                    key=key,
                    bucket=str(base),
                    size=len(raw),
                    checksum=hashlib.sha256(raw).hexdigest(),
                    content_type="",
                    provider=self.name,
                )
            )
            if len(out) >= limit:
                break
        return out
