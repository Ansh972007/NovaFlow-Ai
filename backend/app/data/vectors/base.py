"""Vector store provider interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Sequence


class VectorStoreProvider(ABC):
    name: str = "base"

    @abstractmethod
    def init(self) -> bool:
        ...

    @abstractmethod
    def upsert(self, rows: Sequence[tuple[int, int, int, list[float]]]) -> None:
        """rows: (chunk_id, knowledge_id, file_id, embedding)"""

    @abstractmethod
    def delete_by_file(self, file_id: int) -> None:
        ...

    @abstractmethod
    def search(
        self,
        knowledge_id: int,
        query_vec: list[float],
        limit: int,
        *,
        workspace_id: int | None = None,
    ) -> list[tuple[int, float]]:
        """Return (chunk_id, score). Must never cross knowledge_id / workspace boundaries."""

    def health(self) -> dict:
        return {"provider": self.name, "ok": True}
