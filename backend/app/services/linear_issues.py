"""Linear Issues helpers for workspace integrations + workflow node."""

from __future__ import annotations

from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.crypto import decrypt_secret
from app.database import WorkspaceIntegration

LINEAR_GQL = "https://api.linear.app/graphql"


def resolve_linear_config(
    db: Session,
    workspace_id: int | None,
    credential_id: str | None = None,
) -> dict[str, Any]:
    if not workspace_id:
        return {"api_key": "", "team_id": "", "configured": False}
    try:
        from app.services import credential_vault as vault

        fields = vault.resolve_fields(
            db,
            workspace_id,
            category="linear",
            kind="linear_api",
            credential_id=credential_id,
        )
        key = (fields.get("api_key") or "").strip()
        team_id = (fields.get("team_id") or "").strip()
        if key:
            return {"api_key": key, "team_id": team_id, "configured": True}
    except Exception:
        pass
    row = db.get(WorkspaceIntegration, workspace_id)
    if not row:
        return {"api_key": "", "team_id": "", "configured": False}
    key = decrypt_secret(row.linear_api_key_enc or "") if getattr(row, "linear_api_key_enc", None) else ""
    team_id = (getattr(row, "linear_team_id", None) or "").strip()
    return {"api_key": key, "team_id": team_id, "configured": bool(key)}


async def _gql(api_key: str, query: str, variables: dict | None = None) -> dict:
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            LINEAR_GQL,
            headers={"Authorization": api_key, "Content-Type": "application/json"},
            json={"query": query, "variables": variables or {}},
        )
        if resp.status_code >= 400:
            raise ValueError(resp.text[:500])
        data = resp.json()
        if data.get("errors"):
            raise ValueError(str(data["errors"])[:500])
        return data.get("data") or {}


async def linear_verify(
    db: Session,
    workspace_id: int,
    credential_id: str | None = None,
) -> dict:
    cfg = resolve_linear_config(db, workspace_id, credential_id=credential_id)
    if not cfg["configured"]:
        return {"ok": False, "detail": "Linear API key not configured — add it in Settings → Integrations"}
    try:
        data = await _gql(cfg["api_key"], "{ viewer { id name email } }")
        viewer = data.get("viewer") or {}
        detail = f"Connected as {viewer.get('name') or viewer.get('email') or 'Linear user'}"
        if cfg["team_id"]:
            detail += f" · team {cfg['team_id']}"
        return {"ok": True, "detail": detail, "viewer": viewer}
    except Exception as exc:
        return {"ok": False, "detail": str(exc)[:500]}


async def linear_create_issue(
    db: Session,
    workspace_id: int,
    *,
    title: str,
    description: str = "",
    team_id: str = "",
    credential_id: str | None = None,
) -> dict:
    cfg = resolve_linear_config(db, workspace_id, credential_id=credential_id)
    if not cfg["configured"]:
        raise ValueError("Linear not configured in Settings → Integrations")
    tid = (team_id or cfg["team_id"] or "").strip()
    if not tid:
        raise ValueError("Linear team_id required (node or Settings default)")
    data = await _gql(
        cfg["api_key"],
        """
        mutation IssueCreate($input: IssueCreateInput!) {
          issueCreate(input: $input) {
            success
            issue { id identifier title url }
          }
        }
        """,
        {
            "input": {
                "teamId": tid,
                "title": (title or "NovaFlow issue")[:255],
                "description": (description or "")[:50000],
            }
        },
    )
    payload = (data.get("issueCreate") or {})
    if not payload.get("success"):
        raise ValueError("Linear issueCreate failed")
    return payload.get("issue") or {}


async def linear_update_issue(
    db: Session,
    workspace_id: int,
    *,
    issue_id: str,
    title: str = "",
    description: str = "",
    credential_id: str | None = None,
) -> dict:
    cfg = resolve_linear_config(db, workspace_id, credential_id=credential_id)
    if not cfg["configured"]:
        raise ValueError("Linear not configured in Settings → Integrations")
    iid = (issue_id or "").strip()
    if not iid:
        raise ValueError("issue_id required for Linear update")
    inp: dict[str, Any] = {}
    if title:
        inp["title"] = title[:255]
    if description:
        inp["description"] = description[:50000]
    if not inp:
        raise ValueError("Nothing to update")
    data = await _gql(
        cfg["api_key"],
        """
        mutation IssueUpdate($id: String!, $input: IssueUpdateInput!) {
          issueUpdate(id: $id, input: $input) {
            success
            issue { id identifier title url }
          }
        }
        """,
        {"id": iid, "input": inp},
    )
    payload = data.get("issueUpdate") or {}
    if not payload.get("success"):
        raise ValueError("Linear issueUpdate failed")
    return payload.get("issue") or {}
