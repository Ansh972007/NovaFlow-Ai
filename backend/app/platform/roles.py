"""Workspace / platform role vocabulary for the multi-tenant kernel."""

from __future__ import annotations

WORKSPACE_ROLES = (
    "owner",
    "admin",
    "manager",
    "developer",
    "editor",
    "analyst",
    "viewer",
    "guest",
)

# Map legacy names
_ALIASES = {
    "workspace_owner": "owner",
    "ws_owner": "owner",
}

_RANK = {
    "guest": 0,
    "viewer": 10,
    "analyst": 20,
    "editor": 30,
    "developer": 40,
    "manager": 50,
    "admin": 60,
    "owner": 70,
}


def normalize_workspace_role(role: str | None) -> str:
    if not role:
        return "editor"
    r = role.strip().lower()
    r = _ALIASES.get(r, r)
    # Legacy "admin" who is workspace owner remains admin-capable
    if r not in _RANK:
        return "viewer"
    return r


def workspace_role_rank(role: str | None) -> int:
    return _RANK.get(normalize_workspace_role(role), 0)


def has_workspace_min_role(role: str | None, min_role: str) -> bool:
    return workspace_role_rank(role) >= workspace_role_rank(min_role)
