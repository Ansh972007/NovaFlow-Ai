"""Built-in ECP connector plugins.

Each plugin reuses an existing NovaFlow service (no duplicated API clients).
Credentials resolve from the workspace integration store; connection `config`
supplies per-action defaults (repo, project_key, team_id, channel).
"""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.connectivity.plugins.base import BaseConnectorPlugin, PluginResult
from app.database import ConnectorConnection, ConnectorSyncJob


def _config(conn: ConnectorConnection) -> dict[str, Any]:
    try:
        return json.loads(conn.config_json or "{}")
    except (json.JSONDecodeError, TypeError):
        return {}


class SlackPlugin(BaseConnectorPlugin):
    connector_type = "slack"
    description = "Slack notifications and events"

    def test(self, db: Session, conn: ConnectorConnection, secret: str = "") -> PluginResult:
        cfg = _config(conn)
        ok = bool(secret or cfg.get("webhook_url"))
        return PluginResult(success=ok, message="Slack configured" if ok else "Missing Slack webhook/token")

    async def invoke_action(self, db: Session, conn: ConnectorConnection, action: str, params: dict | None = None, secret: str = "") -> PluginResult:
        if action != "notify":
            return PluginResult(success=False, message=f"Unsupported action: {action}")
        from app.services.integrations import send_notification

        params = params or {}
        cfg = _config(conn)
        result = await send_notification(
            "slack",
            secret or cfg.get("webhook_url") or "",
            params.get("subject") or "NovaFlow",
            params.get("message") or params.get("body") or "",
            db=db,
            workspace_id=conn.workspace_id,
        )
        ok = bool(result.get("ok") or result.get("success"))
        return PluginResult(success=ok, message="Slack notification sent" if ok else "Slack send failed", data=result)


class DiscordPlugin(BaseConnectorPlugin):
    connector_type = "discord"
    description = "Discord webhook notifications"

    def test(self, db: Session, conn: ConnectorConnection, secret: str = "") -> PluginResult:
        cfg = _config(conn)
        ok = bool(secret or cfg.get("webhook_url"))
        return PluginResult(success=ok, message="Discord configured" if ok else "Missing Discord webhook")

    async def invoke_action(self, db: Session, conn: ConnectorConnection, action: str, params: dict | None = None, secret: str = "") -> PluginResult:
        if action != "notify":
            return PluginResult(success=False, message=f"Unsupported action: {action}")
        from app.services.integrations import send_notification

        params = params or {}
        cfg = _config(conn)
        result = await send_notification(
            "discord",
            secret or cfg.get("webhook_url") or "",
            params.get("subject") or "NovaFlow",
            params.get("message") or params.get("body") or "",
            db=db,
            workspace_id=conn.workspace_id,
        )
        ok = bool(result.get("ok") or result.get("success"))
        return PluginResult(success=ok, message="Discord notification sent" if ok else "Discord send failed", data=result)


class TelegramPlugin(BaseConnectorPlugin):
    connector_type = "telegram"
    description = "Telegram bot notifications"

    def test(self, db: Session, conn: ConnectorConnection, secret: str = "") -> PluginResult:
        return PluginResult(success=bool(secret), message="Telegram bot configured" if secret else "Missing bot token")

    async def invoke_action(self, db: Session, conn: ConnectorConnection, action: str, params: dict | None = None, secret: str = "") -> PluginResult:
        if action != "notify":
            return PluginResult(success=False, message=f"Unsupported action: {action}")
        from app.services.integrations import send_notification

        params = params or {}
        cfg = _config(conn)
        result = await send_notification(
            "telegram",
            params.get("chat_id") or cfg.get("chat_id") or "",
            params.get("subject") or "NovaFlow",
            params.get("message") or params.get("body") or "",
            bot_token=secret,
            db=db,
            workspace_id=conn.workspace_id,
        )
        ok = bool(result.get("ok") or result.get("success"))
        return PluginResult(success=ok, message="Telegram message sent" if ok else "Telegram send failed", data=result)


class GithubPlugin(BaseConnectorPlugin):
    connector_type = "github"
    description = "GitHub Issues integration"

    async def invoke_action(self, db: Session, conn: ConnectorConnection, action: str, params: dict | None = None, secret: str = "") -> PluginResult:
        from app.services.github_issues import github_create_issue, github_update_issue

        params = params or {}
        cfg = _config(conn)
        repo = params.get("repo") or cfg.get("repo") or ""
        try:
            if action == "create_issue":
                issue = await github_create_issue(
                    db,
                    conn.workspace_id,
                    repo=repo,
                    title=params.get("title") or "NovaFlow issue",
                    body=params.get("body") or "",
                    labels=params.get("labels"),
                )
                return PluginResult(success=True, message="GitHub issue created", data={"number": issue.get("number"), "url": issue.get("html_url")})
            if action == "update_issue":
                issue = await github_update_issue(
                    db,
                    conn.workspace_id,
                    repo=repo,
                    issue_number=params.get("issue_number"),
                    body=params.get("body"),
                    state=params.get("state"),
                )
                return PluginResult(success=True, message="GitHub issue updated", data={"number": issue.get("number")})
            return PluginResult(success=False, message=f"Unsupported action: {action}")
        except Exception as exc:
            return PluginResult(success=False, message=f"GitHub error: {exc}")


class JiraPlugin(BaseConnectorPlugin):
    connector_type = "jira"
    description = "Jira Cloud integration"

    async def invoke_action(self, db: Session, conn: ConnectorConnection, action: str, params: dict | None = None, secret: str = "") -> PluginResult:
        from app.services.gmail_jira import jira_create_issue

        params = params or {}
        cfg = _config(conn)
        try:
            if action == "create_issue":
                issue = await jira_create_issue(
                    db,
                    conn.workspace_id,
                    project_key=params.get("project_key") or cfg.get("project_key") or "",
                    summary=params.get("summary") or params.get("title") or "NovaFlow issue",
                    description=params.get("description") or params.get("body") or "",
                    issue_type=params.get("issue_type") or "Task",
                )
                return PluginResult(success=True, message="Jira issue created", data={"key": issue.get("key"), "id": issue.get("id")})
            return PluginResult(success=False, message=f"Unsupported action: {action}")
        except Exception as exc:
            return PluginResult(success=False, message=f"Jira error: {exc}")


class LinearPlugin(BaseConnectorPlugin):
    connector_type = "linear"
    description = "Linear Issues integration"

    async def invoke_action(self, db: Session, conn: ConnectorConnection, action: str, params: dict | None = None, secret: str = "") -> PluginResult:
        from app.services.linear_issues import linear_create_issue

        params = params or {}
        cfg = _config(conn)
        try:
            if action == "create_issue":
                issue = await linear_create_issue(
                    db,
                    conn.workspace_id,
                    title=params.get("title") or "NovaFlow issue",
                    description=params.get("description") or params.get("body") or "",
                    team_id=params.get("team_id") or cfg.get("team_id") or "",
                )
                return PluginResult(success=True, message="Linear issue created", data={"identifier": issue.get("identifier"), "url": issue.get("url")})
            return PluginResult(success=False, message=f"Unsupported action: {action}")
        except Exception as exc:
            return PluginResult(success=False, message=f"Linear error: {exc}")


class StubCloudPlugin(BaseConnectorPlugin):
    connector_type = "cloud"
    description = "Cloud storage connector (object-storage backed)"

    async def invoke_action(self, db: Session, conn: ConnectorConnection, action: str, params: dict | None = None, secret: str = "") -> PluginResult:
        return PluginResult(success=False, message=f"Action '{action}' not supported for {conn.connector_type}; use sync")

    def sync(self, db: Session, conn: ConnectorConnection, job: ConnectorSyncJob) -> dict[str, Any]:
        """Sync via the configured object-storage backend when available."""
        try:
            from app.data import get_object_storage

            storage = get_object_storage()
            cfg = _config(conn)
            prefix = cfg.get("prefix") or ""
            listed = []
            if hasattr(storage, "list_objects"):
                listed = storage.list_objects(prefix=prefix)[:100]
            return PluginResult(
                success=True,
                message=f"Listed {len(listed)} objects via {getattr(storage, 'name', 'storage')}",
                data={"objects": len(listed)},
                checkpoint={"prefix": prefix, "count": len(listed)},
            ).to_dict()
        except Exception as exc:
            return PluginResult(success=False, message=f"Cloud sync unavailable: {exc}").to_dict()
