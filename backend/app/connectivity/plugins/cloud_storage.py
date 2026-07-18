"""Production cloud-storage connector plugins.

S3 reuses the Data Platform object-storage provider. Dropbox, Google Drive,
OneDrive and SharePoint call their real REST APIs through the shared
rate-limit/retry HTTP helper. Credentials come from the ECP credential store
(bearer/access token) and per-connection `config` supplies bucket/site/prefix.
"""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.connectivity.plugins.base import BaseConnectorPlugin, PluginResult
from app.connectivity.plugins.http import request_with_retry
from app.database import ConnectorConnection, ConnectorSyncJob


def _config(conn: ConnectorConnection) -> dict[str, Any]:
    try:
        return json.loads(conn.config_json or "{}")
    except (json.JSONDecodeError, TypeError):
        return {}


class S3Plugin(BaseConnectorPlugin):
    connector_type = "s3"
    description = "Amazon S3 / S3-compatible object storage"

    def _storage(self, conn: ConnectorConnection, secret: str):
        from app.data.storage.s3 import S3CompatibleStorage

        cfg = _config(conn)
        return S3CompatibleStorage(
            bucket=cfg.get("bucket") or "",
            endpoint=cfg.get("endpoint") or "",
            access_key=cfg.get("access_key") or "",
            secret_key=secret or cfg.get("secret_key") or "",
            region=cfg.get("region") or "auto",
            provider_label=self.connector_type,
        )

    def test(self, db: Session, conn: ConnectorConnection, secret: str = "") -> PluginResult:
        cfg = _config(conn)
        if not cfg.get("bucket"):
            return PluginResult(success=False, message="S3 bucket not configured")
        try:
            objs = self._storage(conn, secret).list_objects(prefix=cfg.get("prefix") or "", limit=1)
            return PluginResult(success=True, message=f"S3 reachable ({len(objs)} sample object)", data={"bucket": cfg["bucket"]})
        except Exception as exc:
            return PluginResult(success=False, message=f"S3 error: {exc}")

    async def invoke_action(self, db: Session, conn: ConnectorConnection, action: str, params: dict | None = None, secret: str = "") -> PluginResult:
        params = params or {}
        cfg = _config(conn)
        try:
            storage = self._storage(conn, secret)
            if action == "list_files":
                objs = storage.list_objects(prefix=params.get("prefix") or cfg.get("prefix") or "", limit=int(params.get("limit") or 100))
                return PluginResult(success=True, message=f"{len(objs)} objects", data={"files": [{"key": o.key, "size": o.size} for o in objs]})
            if action == "download_file":
                key = params.get("key")
                if not key:
                    return PluginResult(success=False, message="key required")
                raw = storage.get(key)
                return PluginResult(success=True, message="downloaded", data={"key": key, "bytes": len(raw)})
            if action == "signed_url":
                return PluginResult(success=True, message="signed", data={"url": storage.signed_url(params.get("key") or "", method=params.get("method") or "GET")})
            return PluginResult(success=False, message=f"Unsupported action: {action}")
        except Exception as exc:
            return PluginResult(success=False, message=f"S3 error: {exc}")

    def sync(self, db: Session, conn: ConnectorConnection, job: ConnectorSyncJob) -> dict[str, Any]:
        cfg = _config(conn)
        try:
            objs = self._storage(conn, "").list_objects(prefix=cfg.get("prefix") or "", limit=500)
            return PluginResult(success=True, message=f"Listed {len(objs)} objects", data={"count": len(objs)}, checkpoint={"count": len(objs)}).to_dict()
        except Exception as exc:
            return PluginResult(success=False, message=f"S3 sync error: {exc}").to_dict()


class _BearerStoragePlugin(BaseConnectorPlugin):
    """Shared base for token-authenticated cloud drives."""

    test_url = ""
    list_url = ""
    items_key = "value"

    def test(self, db: Session, conn: ConnectorConnection, secret: str = "") -> PluginResult:
        if not secret:
            return PluginResult(success=False, message=f"{self.connector_type} access token required")
        return PluginResult(success=True, message=f"{self.connector_type} token present (verify via list_files)")

    def _headers(self, secret: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {secret}", "Accept": "application/json"}


class DropboxPlugin(_BearerStoragePlugin):
    connector_type = "dropbox"
    description = "Dropbox files (API v2)"

    async def invoke_action(self, db: Session, conn: ConnectorConnection, action: str, params: dict | None = None, secret: str = "") -> PluginResult:
        params = params or {}
        if not secret:
            return PluginResult(success=False, message="Dropbox access token required")
        headers = {"Authorization": f"Bearer {secret}", "Content-Type": "application/json"}
        try:
            if action == "test" or action == "account":
                resp = await request_with_retry("POST", "https://api.dropboxapi.com/2/users/get_current_account", headers=headers, content=b"null")
                return PluginResult(success=resp.status_code < 400, message="account ok" if resp.status_code < 400 else resp.text[:200])
            if action == "list_files":
                path = params.get("path") or _config(conn).get("path") or ""
                files: list[dict] = []
                body: dict[str, Any] = {"path": path, "limit": min(int(params.get("limit") or 100), 2000)}
                url = "https://api.dropboxapi.com/2/files/list_folder"
                for _ in range(20):
                    resp = await request_with_retry("POST", url, headers=headers, json_body=body)
                    if resp.status_code >= 400:
                        return PluginResult(success=False, message=resp.text[:200])
                    data = resp.json()
                    files.extend(data.get("entries") or [])
                    if not data.get("has_more") or len(files) >= 500:
                        break
                    body = {"cursor": data.get("cursor")}
                    url = "https://api.dropboxapi.com/2/files/list_folder/continue"
                return PluginResult(success=True, message=f"{len(files)} entries", data={"files": [{"name": f.get("name"), "path": f.get("path_lower")} for f in files[:500]]})
            return PluginResult(success=False, message=f"Unsupported action: {action}")
        except Exception as exc:
            return PluginResult(success=False, message=f"Dropbox error: {exc}")


class GoogleDrivePlugin(_BearerStoragePlugin):
    connector_type = "gdrive"
    description = "Google Drive (Drive API v3)"

    async def invoke_action(self, db: Session, conn: ConnectorConnection, action: str, params: dict | None = None, secret: str = "") -> PluginResult:
        params = params or {}
        if not secret:
            return PluginResult(success=False, message="Google Drive access token required")
        headers = self._headers(secret)
        try:
            if action in ("test", "about"):
                resp = await request_with_retry("GET", "https://www.googleapis.com/drive/v3/about", headers=headers, params={"fields": "user"})
                return PluginResult(success=resp.status_code < 400, message="drive ok" if resp.status_code < 400 else resp.text[:200])
            if action == "list_files":
                files: list[dict] = []
                page_token = None
                for _ in range(20):
                    qp = {"pageSize": 100, "fields": "nextPageToken,files(id,name,mimeType,size)"}
                    if params.get("query"):
                        qp["q"] = params["query"]
                    if page_token:
                        qp["pageToken"] = page_token
                    resp = await request_with_retry("GET", "https://www.googleapis.com/drive/v3/files", headers=headers, params=qp)
                    if resp.status_code >= 400:
                        return PluginResult(success=False, message=resp.text[:200])
                    data = resp.json()
                    files.extend(data.get("files") or [])
                    page_token = data.get("nextPageToken")
                    if not page_token or len(files) >= 500:
                        break
                return PluginResult(success=True, message=f"{len(files)} files", data={"files": files[:500]})
            return PluginResult(success=False, message=f"Unsupported action: {action}")
        except Exception as exc:
            return PluginResult(success=False, message=f"Google Drive error: {exc}")


class OneDrivePlugin(_BearerStoragePlugin):
    connector_type = "onedrive"
    description = "OneDrive (Microsoft Graph)"

    async def invoke_action(self, db: Session, conn: ConnectorConnection, action: str, params: dict | None = None, secret: str = "") -> PluginResult:
        params = params or {}
        if not secret:
            return PluginResult(success=False, message="OneDrive access token required")
        headers = self._headers(secret)
        try:
            if action in ("test", "drive"):
                resp = await request_with_retry("GET", "https://graph.microsoft.com/v1.0/me/drive", headers=headers)
                return PluginResult(success=resp.status_code < 400, message="onedrive ok" if resp.status_code < 400 else resp.text[:200])
            if action == "list_files":
                folder = params.get("folder") or _config(conn).get("folder") or "root"
                url = f"https://graph.microsoft.com/v1.0/me/drive/{'root' if folder == 'root' else 'items/' + folder}/children"
                files: list[dict] = []
                for _ in range(20):
                    resp = await request_with_retry("GET", url, headers=headers)
                    if resp.status_code >= 400:
                        return PluginResult(success=False, message=resp.text[:200])
                    data = resp.json()
                    files.extend(data.get("value") or [])
                    url = data.get("@odata.nextLink")
                    if not url or len(files) >= 500:
                        break
                return PluginResult(success=True, message=f"{len(files)} items", data={"files": [{"name": f.get("name"), "id": f.get("id"), "size": f.get("size")} for f in files[:500]]})
            return PluginResult(success=False, message=f"Unsupported action: {action}")
        except Exception as exc:
            return PluginResult(success=False, message=f"OneDrive error: {exc}")


class SharePointPlugin(_BearerStoragePlugin):
    connector_type = "sharepoint"
    description = "SharePoint document libraries (Microsoft Graph)"

    async def invoke_action(self, db: Session, conn: ConnectorConnection, action: str, params: dict | None = None, secret: str = "") -> PluginResult:
        params = params or {}
        if not secret:
            return PluginResult(success=False, message="SharePoint access token required")
        headers = self._headers(secret)
        cfg = _config(conn)
        site_id = params.get("site_id") or cfg.get("site_id") or ""
        try:
            if action in ("test", "site"):
                url = f"https://graph.microsoft.com/v1.0/sites/{site_id}" if site_id else "https://graph.microsoft.com/v1.0/sites?search=*"
                resp = await request_with_retry("GET", url, headers=headers)
                return PluginResult(success=resp.status_code < 400, message="sharepoint ok" if resp.status_code < 400 else resp.text[:200])
            if action == "list_files":
                if not site_id:
                    return PluginResult(success=False, message="site_id required (params or config)")
                url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive/root/children"
                files: list[dict] = []
                for _ in range(20):
                    resp = await request_with_retry("GET", url, headers=headers)
                    if resp.status_code >= 400:
                        return PluginResult(success=False, message=resp.text[:200])
                    data = resp.json()
                    files.extend(data.get("value") or [])
                    url = data.get("@odata.nextLink")
                    if not url or len(files) >= 500:
                        break
                return PluginResult(success=True, message=f"{len(files)} items", data={"files": [{"name": f.get("name"), "id": f.get("id")} for f in files[:500]]})
            return PluginResult(success=False, message=f"Unsupported action: {action}")
        except Exception as exc:
            return PluginResult(success=False, message=f"SharePoint error: {exc}")
