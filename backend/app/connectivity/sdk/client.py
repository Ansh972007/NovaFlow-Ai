"""Enterprise Connectivity Platform SDK."""

from __future__ import annotations

from typing import Any


class ConnectivityClient:
    """Python SDK client for ECP REST API."""

    def __init__(self, base_url: str, token: str, workspace_id: int):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.workspace_id = workspace_id

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "X-Workspace-Id": str(self.workspace_id),
            "Content-Type": "application/json",
        }

    async def list_connectors(self) -> list[dict[str, Any]]:
        import httpx

        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.base_url}/api/v1/connectivity/connectors", headers=self._headers())
            resp.raise_for_status()
            return resp.json().get("data") or []

    async def invoke_action(self, connection_id: str, action: str, params: dict | None = None) -> dict[str, Any]:
        import httpx

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/api/v1/connectivity/connections/{connection_id}/invoke",
                headers=self._headers(),
                json={"action": action, "params": params or {}},
            )
            resp.raise_for_status()
            return resp.json().get("data") or {}
