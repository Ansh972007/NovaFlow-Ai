"""KOS plugin registry — parsers, chunkers, connectors, rerankers."""

from __future__ import annotations

from typing import Any

from app.knowledge_os.plugins.base import BaseConnector, ConnectorResult
from app.knowledge_os.plugins.connectors import (
    GitConnector,
    ManualConnector,
    S3Connector,
    WebhookConnector,
)

_REGISTRY: dict[str, type[BaseConnector]] = {
    "manual": ManualConnector,
    "s3": S3Connector,
    "git": GitConnector,
    "webhook": WebhookConnector,
}


def register_connector(name: str, connector_cls: type[BaseConnector]) -> None:
    _REGISTRY[name.lower()] = connector_cls


def get_connector(connector_type: str) -> BaseConnector:
    key = (connector_type or "manual").lower()
    cls = _REGISTRY.get(key)
    if not cls:
        raise ValueError(f"Unknown connector type: {connector_type}")
    return cls()


def list_connectors() -> list[dict[str, Any]]:
    return [{"type": k, "description": v.description} for k, v in _REGISTRY.items()]


__all__ = [
    "BaseConnector",
    "ConnectorResult",
    "get_connector",
    "list_connectors",
    "register_connector",
]
