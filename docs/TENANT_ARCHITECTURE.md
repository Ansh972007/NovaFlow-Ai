# Tenant Architecture (Phase 2)

## Isolation model

Every customer resource is bound to a **workspace**. Organization and team are optional layers above/within that boundary.

```
Request
  → Auth (JWT / API key)
  → PlatformContext (Tenant + Permission + Ownership + Audit)
  → ctx.query(Model) / ctx.fetch(Model, id)
  → Response
```

Developers **must not** hand-filter `workspace_id`. Use:

| Helper | Purpose |
|--------|---------|
| `get_platform_ctx` / `get_workspace_ctx` | Resolve tenant for HTTP |
| `ctx.query(Model)` | Tenant-scoped SQLAlchemy query |
| `ctx.fetch(Model, id)` | Opaque cross-tenant 404 |
| `ctx.attach(obj)` | Stamp workspace / owner fields |
| `ctx.require(Permission.X)` | Permission gate |
| `ctx.audit(...)` | Immutable security audit |
| `worker_tenant(workspace_id)` | Background job binding |
| `tenant_cache_key(workspace_id, …)` | Cache / Redis key prefix |

## WebSocket

`chat_ws.get_ws_workspace` uses `resolve_tenant` (membership **or** active emergency grant, soft-delete aware). Unauthorized subscriptions are rejected.

## Background jobs

Eval and workflow schedulers wrap each due job in `worker_tenant(...)`. Jobs without `workspace_id` are refused/disabled.

## Emergency access

Platform staff never auto-access tenant data. See emergency APIs under `/api/v1/emergency-access/*`.

## Search

Knowledge, workflow, agent, project, and analytics list/search endpoints run through `ctx.query` / `ctx.fetch` so results cannot cross workspaces. Marketplace public listing is the only intentional cross-tenant read (public flag only).

## Phase boundary

Phase 2 does **not** include PostgreSQL migration, object storage providers, or distributed Redis queues (Phase 3+).
