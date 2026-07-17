# NovaFlow Database Architecture (Constitution)

**Primary target:** PostgreSQL 17+  
**Compatible:** SQLite (local), MySQL 8 (legacy Docker), PostgreSQL 17+ (production)

This is the permanent data platform. Application modules depend on `app.data.*` — never on a vendor SDK directly.

## Goals

| Scale | Target |
|-------|--------|
| Users | 10M+ |
| Workflows | 100M+ |
| Executions / audit / chat / vectors | Billions |
| Object storage | Petabytes (outside the RDBMS) |

## Package map

```
app/data/
  engine.py          Engine + PgBouncer-aware pools
  dialect.py         Capability matrix
  mixins.py          Tenant / soft-delete / optimistic lock
  soft_delete.py     Soft delete / restore / purge + legal hold
  transactions.py    Deadlock retry + optimistic lock
  partitioning.py    Monthly RANGE partitions (PostgreSQL)
  observability.py   Slow-query metrics
  migration_health.py Impact + post-verify reports
  vectors/           milvus | pgvector | qdrant | sqlite
  storage/           local | s3 | r2 | minio
  cache/             redis | memory (tenant keys)
```

## Multi-tenancy

Every workspace resource supports (via migration + mixins):

`workspace_id`, `organization_id`, `team_id`, `owner_id`, `created_by`, `updated_by`, `deleted_at`, `visibility`, `tenant_version`, `row_version`, `legal_hold`

Indexes: `(workspace_id, deleted_at)`, `(workspace_id, create_time)`.

PlatformContext / `scoped_query` remain the query boundary — unchanged.

## Domains

Identity · Platform · Workspace · Knowledge · Workflow · Agent · Execution · Analytics · Marketplace · Evaluation · Storage · Notification · Security · Audit · System

## Zero-downtime migration

1. Stand up PostgreSQL + PgBouncer (`deploy/docker-compose.postgres.yml`)
2. `alembic upgrade head` on the new cluster
3. Expand-only schema (nullable columns) — no API break
4. Dual-write / backfill high-volume tables into `*_p` partitions
5. Switch `DATABASE_URL`; enable `DB_PGBOUNCER_MODE=1`
6. Contract obsolete columns only after soak

See `MIGRATION_GUIDE.md`.

## What stays out of PostgreSQL

- File bytes → object storage (`ObjectFile` metadata only)
- Vector ANN → Milvus / pgvector / Qdrant (provider registry)
- Hot cache / locks → Redis

## Related docs

`SCHEMA_GUIDE.md` · `MIGRATION_GUIDE.md` · `INDEXING_GUIDE.md` · `PARTITIONING_GUIDE.md` · `BACKUP_STRATEGY.md` · `DISASTER_RECOVERY.md` · `PERFORMANCE_GUIDE.md` · `DATABASE_OPERATIONS.md`
