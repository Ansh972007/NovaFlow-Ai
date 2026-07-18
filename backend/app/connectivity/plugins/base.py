"""Base connector plugin."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from app.database import ConnectorConnection, ConnectorSyncJob


@dataclass
class PluginResult:
    success: bool = True
    message: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    checkpoint: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "message": self.message,
            "data": self.data,
            "checkpoint": self.checkpoint,
        }


class BaseConnectorPlugin:
    connector_type: str = "generic"
    description: str = "Generic connector plugin"

    def test(self, db: Session, conn: ConnectorConnection, secret: str = "") -> PluginResult:
        return PluginResult(success=True, message="Test stub OK")

    async def invoke_action(
        self,
        db: Session,
        conn: ConnectorConnection,
        action: str,
        params: dict | None = None,
        secret: str = "",
    ) -> PluginResult:
        return PluginResult(success=False, message=f"Connector '{self.connector_type}' does not support action '{action}'")

    def sync(self, db: Session, conn: ConnectorConnection, job: ConnectorSyncJob) -> dict[str, Any]:
        return PluginResult(message="Sync stub", checkpoint={"cursor": 0}).to_dict()
