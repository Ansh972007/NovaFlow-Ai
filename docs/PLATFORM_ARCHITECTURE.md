# NovaFlow Platform Architecture — Multi-Tenant Workspace Kernel

This document defines the permanent tenancy model for NovaFlow AI. Future modules must extend this kernel; they must not invent parallel org/workspace systems.

## Hierarchy

```
Platform
  └── Organizations
        └── Workspaces
              └── Teams (optional sub-teams / departments)
                    └── Projects → Resources
```

Every product resource belongs to a **workspace** (`workspace_id`). Optional `team_id`, `owner_id` / `created_by`, soft-delete (`deleted_at`), and audit fields attach to that boundary.

### Workspace types

| Type | Intent |
|------|--------|
| `personal` | Single-user default |
| `team` | Collaborating group |
| `organization` | Company / campus unit (may sit under `Organization`) |
| `enterprise` | Large tenant with stricter quotas / governance |

## Dependency graph (Phase 2)

```
database.py (resources + EmergencyAccessGrant + SecurityAuditLog)
        │
        ▼
platform/
  roles.py / permissions.py / scoping.py
  access.py          → PlatformContext (tenant+perm+audit+ownership)
  context.py         → resolve_tenant
  emergency.py       → break-glass lifecycle
  worker.py          → WorkerTenantContext + cache keys
  invites.py / teams.py
        │
        ▼
deps.get_platform_ctx / require_permission
        │
        ├── routers/* (assistants, knowledge, workflow, agents, eval, …)
        ├── routers/emergency.py
        ├── routers/chat_ws.py  (resolve_tenant)
        └── services/*_scheduler.py (worker_tenant)
```

Related docs: `TENANT_ARCHITECTURE.md`, `PERMISSION_MATRIX.md`, `WORKSPACE_LIFECYCLE.md`, `TEAM_ARCHITECTURE.md`, `AUDIT_ARCHITECTURE.md`, `DEVELOPER_GUIDE.md`.

## Tenant isolation rules

1. Queries use `PlatformContext.query` / `scoped_query` — never hand-filter `workspace_id` in feature routers.
2. Cross-tenant existence must never leak (`ctx.fetch` / `require_same_workspace`).
3. Platform admins do **not** see customer resources without Emergency Access.
4. Background jobs and WebSockets inherit the same tenant rules.

## Implementation phases

| Phase | Scope | Status |
|-------|--------|--------|
| **1** | Org/Workspace/Team models, TenantContext, invites/teams APIs, Settings members UI | **Complete** |
| **2** | PlatformContext migration, permission engine, emergency APIs, WS/worker binding, tenant audit | **Complete** |
| **3** | Enterprise Data Platform — PG-first, soft-delete, partitions, vector/storage/cache abstractions | **Complete** |
| **4** | Redis-backed tenant rate limits / queues / sessions (deep); chat history scale-out | Planned |
| **5** | Billing seats; org admin surfaces; dual-write cutover automation | Planned |
| **6** | Full create wizard, presence, activity feed UX | Planned |

## Developer contract

See `DEVELOPER_GUIDE.md`. This kernel is the last tenancy redesign.
