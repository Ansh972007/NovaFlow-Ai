"""
NovaFlow Multi-Tenant Platform Kernel.

Hierarchy: Organization → Workspace → Team → Resources

Import submodules directly to avoid circular imports with app.deps:
  from app.platform.context import TenantContext, get_tenant_context
  from app.platform.scoping import scoped_query
  from app.platform.roles import normalize_workspace_role
"""

from app.platform.roles import WORKSPACE_ROLES, normalize_workspace_role, workspace_role_rank
from app.platform.scoping import scoped_query, require_same_workspace, not_deleted

__all__ = [
    "scoped_query",
    "require_same_workspace",
    "not_deleted",
    "WORKSPACE_ROLES",
    "normalize_workspace_role",
    "workspace_role_rank",
]
