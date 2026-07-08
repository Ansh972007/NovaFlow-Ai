"""GitHub Issues helpers for workspace integrations + workflow node."""

from __future__ import annotations

from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.crypto import decrypt_secret
from app.database import WorkspaceIntegration


def resolve_github_config(db: Session, workspace_id: int | None) -> dict[str, Any]:
    if not workspace_id:
        return {"token": "", "owner": "", "repo": "", "default_repo": "", "configured": False}
    row = db.get(WorkspaceIntegration, workspace_id)
    if not row:
        return {"token": "", "owner": "", "repo": "", "default_repo": "", "configured": False}
    token = decrypt_secret(row.github_token_enc or "") if getattr(row, "github_token_enc", None) else ""
    owner = (getattr(row, "github_owner", None) or "").strip()
    repo = (getattr(row, "github_repo", None) or "").strip()
    default_repo = f"{owner}/{repo}" if owner and repo else ""
    return {
        "token": token,
        "owner": owner,
        "repo": repo,
        "default_repo": default_repo,
        "configured": bool(token),
    }


def _parse_repo(repo: str, fallback: str = "") -> tuple[str, str]:
    raw = (repo or fallback or "").strip().strip("/")
    if "/" not in raw:
        raise ValueError("Repository must be owner/repo")
    owner, name = raw.split("/", 1)
    owner, name = owner.strip(), name.strip()
    if not owner or not name:
        raise ValueError("Repository must be owner/repo")
    return owner, name


async def github_verify(db: Session, workspace_id: int) -> dict:
    cfg = resolve_github_config(db, workspace_id)
    if not cfg["configured"]:
        return {"ok": False, "detail": "GitHub PAT not configured — add a token in Settings → Integrations"}
    try:
        async with httpx.AsyncClient(timeout=25) as client:
            resp = await client.get(
                "https://api.github.com/user",
                headers={
                    "Authorization": f"Bearer {cfg['token']}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
            )
            if resp.status_code >= 400:
                return {"ok": False, "detail": resp.text[:400]}
            data = resp.json()
            login = data.get("login") or "user"
            detail = f"Connected as @{login}"
            if cfg["default_repo"]:
                detail += f" · default {cfg['default_repo']}"
            return {"ok": True, "detail": detail, "user": data}
    except Exception as exc:
        return {"ok": False, "detail": str(exc)[:500]}


async def github_create_issue(
    db: Session,
    workspace_id: int,
    *,
    repo: str = "",
    title: str,
    body: str = "",
    labels: list[str] | None = None,
) -> dict:
    cfg = resolve_github_config(db, workspace_id)
    if not cfg["configured"]:
        raise ValueError("GitHub not configured in Settings → Integrations")
    owner, name = _parse_repo(repo, cfg["default_repo"])
    payload: dict[str, Any] = {
        "title": (title or "NovaFlow issue")[:256],
        "body": (body or "")[:65000],
    }
    if labels:
        payload["labels"] = [str(x).strip() for x in labels if str(x).strip()][:20]
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"https://api.github.com/repos/{owner}/{name}/issues",
            headers={
                "Authorization": f"Bearer {cfg['token']}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            json=payload,
        )
        if resp.status_code >= 400:
            raise ValueError(resp.text[:500])
        return resp.json()


async def github_update_issue(
    db: Session,
    workspace_id: int,
    *,
    repo: str = "",
    issue_number: int | str,
    title: str = "",
    body: str = "",
) -> dict:
    cfg = resolve_github_config(db, workspace_id)
    if not cfg["configured"]:
        raise ValueError("GitHub not configured in Settings → Integrations")
    owner, name = _parse_repo(repo, cfg["default_repo"])
    num = int(str(issue_number).lstrip("#").strip())
    payload: dict[str, Any] = {}
    if title:
        payload["title"] = title[:256]
    if body:
        payload["body"] = body[:65000]
    if not payload:
        raise ValueError("Nothing to update")
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.patch(
            f"https://api.github.com/repos/{owner}/{name}/issues/{num}",
            headers={
                "Authorization": f"Bearer {cfg['token']}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            json=payload,
        )
        if resp.status_code >= 400:
            raise ValueError(resp.text[:500])
        return resp.json()
