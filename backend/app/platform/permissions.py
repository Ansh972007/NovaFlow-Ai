"""Workspace permission engine — every request validates role → permission.

Platform super_admin does NOT inherit customer-workspace permissions.
Emergency access is read-biased (read permissions only).
"""

from __future__ import annotations

from fastapi import HTTPException

from app.platform.roles import has_workspace_min_role, normalize_workspace_role
from app.security.rbac import Permission

# Minimum workspace role required for each permission (customer tenant ladder).
_WORKSPACE_PERMISSION_MIN: dict[Permission, str] = {
    Permission.WORKSPACE_READ: "guest",
    Permission.WORKSPACE_WRITE: "editor",
    Permission.WORKSPACE_ADMIN: "admin",
    Permission.WORKSPACE_BILLING: "owner",
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
    Permission.SECURITY_AUDIT: "admin",
}

# Permissions allowed during emergency (break-glass) access.
_EMERGENCY_ALLOWED = frozenset(
    {
        Permission.WORKSPACE_READ,
        Permission.ASSISTANT_READ,
        Permission.KNOWLEDGE_READ,
        Permission.WORKFLOW_READ,
        Permission.AGENT_READ,
        Permission.EVAL_READ,
        Permission.MODEL_LAB_READ,
        Permission.INTEGRATION_READ,
        Permission.ANALYTICS_READ,
        Permission.SECURITY_AUDIT,
    }
)

VISIBILITY_LEVELS = (
    "private",
    "team",
    "workspace",
    "organization",
    "marketplace",
    "public",
    "custom",
)


def workspace_has_permission(
    role: str | None,
    permission: Permission | str,
    *,
    via_emergency_access: bool = False,
) -> bool:
    perm = Permission(permission) if isinstance(permission, str) else permission
    if via_emergency_access and perm not in _EMERGENCY_ALLOWED:
        return False
    min_role = _WORKSPACE_PERMISSION_MIN.get(perm, "admin")
    return has_workspace_min_role(role, min_role)


def require_workspace_permission(
    role: str | None,
    permission: Permission | str,
    *,
    via_emergency_access: bool = False,
) -> None:
    if not workspace_has_permission(
        role, permission, via_emergency_access=via_emergency_access
    ):
        perm = Permission(permission) if isinstance(permission, str) else permission
        raise HTTPException(
            status_code=403,
            detail=f"Permission denied: {perm.value}",
        )


def permission_matrix() -> dict[str, list[str]]:
    """Role → granted permission values (for docs / admin UI)."""
    roles = ("guest", "viewer", "analyst", "editor", "developer", "manager", "admin", "owner")
    out: dict[str, list[str]] = {}
    for role in roles:
        out[role] = sorted(
            p.value
            for p in Permission
            if workspace_has_permission(role, p)
        )
    return out


def normalize_visibility(value: str | None, default: str = "workspace") -> str:
    v = (value or default).strip().lower()
    return v if v in VISIBILITY_LEVELS else default


def can_view_resource(
    *,
    viewer_role: str,
    visibility: str | None,
    owner_id: int | None,
    viewer_user_id: int,
    same_team: bool = False,
    same_org: bool = False,
    is_marketplace: bool = False,
) -> bool:
    """Evaluate resource visibility for a member of the same workspace."""
    vis = normalize_visibility(visibility, "workspace")
    if vis in ("workspace", "public"):
        return True
    if vis == "marketplace" or is_marketplace:
        return True
    if vis == "organization" and same_org:
        return True
    if vis == "team" and same_team:
        return True
    if vis == "private":
        return owner_id is not None and int(owner_id) == int(viewer_user_id)
    if vis == "custom":
        # Custom ACL rows are enforced by callers; default deny unless owner/admin
        return owner_id == viewer_user_id or has_workspace_min_role(viewer_role, "admin")
    return has_workspace_min_role(viewer_role, "viewer")
