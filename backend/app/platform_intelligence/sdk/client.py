"""NovaFlow Platform SDK — Python client helpers."""

from __future__ import annotations

from typing import Any


class NovaFlowPlatformClient:
    """Minimal REST SDK for platform intelligence endpoints."""

    def __init__(self, base_url: str, token: str, workspace_id: int | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.workspace_id = workspace_id

    def _headers(self) -> dict[str, str]:
        h = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
        if self.workspace_id:
            h["X-Workspace-Id"] = str(self.workspace_id)
        return h

    async def health(self) -> dict[str, Any]:
        import httpx

        async with httpx.AsyncClient() as client:
            r = await client.get(f"{self.base_url}/health")
            return r.json()

    async def workspace_dashboard(self) -> dict[str, Any]:
        import httpx

        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{self.base_url}/api/v1/platform/intelligence/dashboard/workspace",
                headers=self._headers(),
            )
            return r.json()

    async def list_events(self, *, event_type: str | None = None, limit: int = 50) -> dict[str, Any]:
        import httpx

        params = {"limit": limit}
        if event_type:
            params["event_type"] = event_type
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{self.base_url}/api/v1/platform/intelligence/events",
                headers=self._headers(),
                params=params,
            )
            return r.json()
