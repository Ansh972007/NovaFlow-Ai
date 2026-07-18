"""Object storage provider interface — DB stores metadata only."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import BinaryIO, Optional


@dataclass
class StoredObject:
    key: str
    bucket: str
    size: int
    checksum: str
    content_type: str
    version_id: str = ""
    provider: str = ""


class ObjectStorageProvider(ABC):
    name: str = "base"

    @abstractmethod
    def put(
        self,
        key: str,
        data: bytes | BinaryIO,
        *,
        content_type: str = "application/octet-stream",
        workspace_id: int | None = None,
    ) -> StoredObject:
        ...

    @abstractmethod
    def get(self, key: str) -> bytes:
        ...

    @abstractmethod
    def delete(self, key: str) -> None:
        ...

    @abstractmethod
    def exists(self, key: str) -> bool:
        ...

    def signed_url(self, key: str, *, expires_seconds: int = 3600, method: str = "GET") -> str:
        """Default: not supported — local/dev returns path reference."""
        raise NotImplementedError(f"{self.name} does not support signed URLs")

    def list_objects(self, *, prefix: str = "", limit: int = 1000) -> list[StoredObject]:
        """List stored objects under a key prefix. Default: empty (override per provider)."""
        return []

    def tenant_key(self, workspace_id: int, *parts: str) -> str:
        safe = [str(workspace_id)] + [p.strip("/").replace("..", "") for p in parts]
        return "ws/" + "/".join(safe)
