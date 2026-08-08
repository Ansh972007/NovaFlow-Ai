"""Enterprise RBAC — roles, ranks, and fine-grained permissions.

Legacy roles (admin/editor/viewer) continue to work. Expanded enterprise
roles map onto the same rank ladder so existing checks keep functioning.
"""

from __future__ import annotations

from enum import Enum
from typing import Iterable

ROLE_RANK: dict[str, int] = {
    "guest": 0,
    "viewer": 10,
    "analyst": 20,
    "editor": 30,
    "developer": 40,
    "manager": 50,
    "admin": 60,
    "workspace_owner": 70,
    "owner": 70,
    "super_admin": 100,
}

_ROLE_ALIASES = {
    "superadmin": "super_admin",
    "workspace-owner": "workspace_owner",
    "ws_owner": "workspace_owner",
}


class Permission(str, Enum):
    WORKSPACE_READ = "workspace:read"
    WORKSPACE_WRITE = "workspace:write"
    WORKSPACE_ADMIN = "workspace:admin"
    WORKSPACE_BILLING = "workspace:billing"
    ASSISTANT_READ = "assistant:read"
    ASSISTANT_WRITE = "assistant:write"
    ASSISTANT_PUBLISH = "assistant:publish"
    KNOWLEDGE_READ = "knowledge:read"
    KNOWLEDGE_WRITE = "knowledge:write"
    KNOWLEDGE_DELETE = "knowledge:delete"
    WORKFLOW_READ = "workflow:read"
    WORKFLOW_WRITE = "workflow:write"
    WORKFLOW_RUN = "workflow:run"
    WORKFLOW_PUBLISH = "workflow:publish"
    AGENT_READ = "agent:read"
    AGENT_RUN = "agent:run"
    AGENT_WRITE = "agent:write"
    EVAL_READ = "eval:read"
    EVAL_WRITE = "eval:write"
    EVAL_RUN = "eval:run"
    MODEL_LAB_READ = "modellab:read"
    MODEL_LAB_WRITE = "modellab:write"
    INTEGRATION_READ = "integration:read"
    INTEGRATION_WRITE = "integration:write"
    ANALYTICS_READ = "analytics:read"
    ANALYTICS_EXPORT = "analytics:export"
    API_KEY_MANAGE = "apikey:manage"
    MARKETPLACE_PUBLISH = "marketplace:publish"
    TEAM_MANAGE = "team:manage"
    SECURITY_AUDIT = "security:audit"


_PERMISSION_MIN_ROLE: dict[Permission, str] = {
    Permission.WORKSPACE_READ: "guest",
    Permission.WORKSPACE_WRITE: "editor",
    Permission.WORKSPACE_ADMIN: "admin",
    Permission.WORKSPACE_BILLING: "workspace_owner",
    Permission.ASSISTANT_READ: "viewer",
    Permission.ASSISTANT_WRITE: "editor",
    Permission.ASSISTANT_PUBLISH: "editor",
    Permission.KNOWLEDGE_READ: "viewer",
    Permission.KNOWLEDGE_WRITE: "editor",
    Permission.KNOWLEDGE_DELETE: "admin",
    Permission.WORKFLOW_READ: "viewer",
    Permission.WORKFLOW_WRITE: "editor",
    Permission.WORKFLOW_RUN: "editor",
    Permission.WORKFLOW_PUBLISH: "editor",
    Permission.AGENT_READ: "viewer",
    Permission.AGENT_RUN: "editor",
    Permission.AGENT_WRITE: "editor",
    Permission.EVAL_READ: "analyst",
    Permission.EVAL_WRITE: "developer",
    Permission.EVAL_RUN: "analyst",
    Permission.MODEL_LAB_READ: "developer",
    Permission.MODEL_LAB_WRITE: "developer",
    Permission.INTEGRATION_READ: "editor",
    Permission.INTEGRATION_WRITE: "editor",
    Permission.ANALYTICS_READ: "analyst",
    Permission.ANALYTICS_EXPORT: "admin",
    Permission.API_KEY_MANAGE: "developer",
    Permission.MARKETPLACE_PUBLISH: "editor",
    Permission.TEAM_MANAGE: "admin",
    Permission.SECURITY_AUDIT: "super_admin",
}


def normalize_role(role: str | None, *, user_id: int | None = None) -> str:
    if not role:
        if user_id == 1:
            return "super_admin"
        return "editor"
    r = role.strip().lower()
    r = _ROLE_ALIASES.get(r, r)
    if r == "admin" and user_id == 1:
        return "super_admin"
    if r not in ROLE_RANK:
        return "viewer"
    return r


def has_min_role(role: str | None, min_role: str, *, user_id: int | None = None) -> bool:
    current = normalize_role(role, user_id=user_id)
    required = normalize_role(min_role)
    return ROLE_RANK.get(current, 0) >= ROLE_RANK.get(required, 999)


def role_has_permission(
    role: str | None,
    permission: Permission | str,
    *,
    user_id: int | None = None,
) -> bool:
    current = normalize_role(role, user_id=user_id)
    if current == "super_admin":
        return True
    perm = Permission(permission) if isinstance(permission, str) else permission
    min_role = _PERMISSION_MIN_ROLE.get(perm, "admin")
    return has_min_role(current, min_role, user_id=user_id)


def require_permissions(
    role: str | None,
    permissions: Iterable[Permission | str],
    *,
    user_id: int | None = None,
) -> bool:
    return all(role_has_permission(role, p, user_id=user_id) for p in permissions)
