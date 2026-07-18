"""Base classes for KOS ingestion connectors."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from app.database import KnowledgeSyncJob


@dataclass
class ConnectorResult:
    imported: int = 0
    updated: int = 0
    skipped: int = 0
    errors: list[str] = field(default_factory=list)
    files: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "imported": self.imported,
            "updated": self.updated,
            "skipped": self.skipped,
            "errors": self.errors,
            "files": self.files,
        }


class BaseConnector:
    """Source-specific sync connector — extend for Drive, SharePoint, etc."""

    connector_type: str = "manual"
    description: str = "Manual connector"

    def sync(self, db: Session, job: KnowledgeSyncJob) -> dict[str, Any]:
        raise NotImplementedError
