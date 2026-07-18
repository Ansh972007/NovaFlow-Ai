"""ECP connector plugins."""

from __future__ import annotations

from typing import Any

from app.connectivity.plugins.base import BaseConnectorPlugin, PluginResult
from app.connectivity.plugins.builtin import (
    DiscordPlugin,
    GithubPlugin,
    JiraPlugin,
    LinearPlugin,
    SlackPlugin,
    TelegramPlugin,
    StubCloudPlugin,
)
from app.connectivity.plugins.cloud_storage import (
    DropboxPlugin,
    GoogleDrivePlugin,
    OneDrivePlugin,
    S3Plugin,
    SharePointPlugin,
)
from app.connectivity.plugins.git import GitPlugin

_REGISTRY: dict[str, type[BaseConnectorPlugin]] = {
    "slack": SlackPlugin,
    "discord": DiscordPlugin,
    "telegram": TelegramPlugin,
    "github": GithubPlugin,
    "jira": JiraPlugin,
    "linear": LinearPlugin,
    # Cloud storage — production implementations
    "s3": S3Plugin,
    "gcs": S3Plugin,  # GCS via S3 interoperability endpoint
    "dropbox": DropboxPlugin,
    "gdrive": GoogleDrivePlugin,
    "onedrive": OneDrivePlugin,
    "sharepoint": SharePointPlugin,
    "git": GitPlugin,
}


def register_connector_plugin(name: str, plugin_cls: type[BaseConnectorPlugin]) -> None:
    _REGISTRY[name.lower()] = plugin_cls


def get_connector_plugin(connector_type: str) -> BaseConnectorPlugin:
    cls = _REGISTRY.get((connector_type or "").lower())
    if not cls:
        return StubCloudPlugin()
    return cls()


def list_connector_plugins() -> list[dict[str, Any]]:
    return [{"type": k, "description": v.description} for k, v in _REGISTRY.items()]
