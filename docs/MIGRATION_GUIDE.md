# Migration Guide

## Tooling

**Alembic only** for production schema evolution.

```bash
cd backend
alembic upgrade head
alembic downgrade -1
python scripts/migration_report.py --phase pre
python scripts/migration_report.py --phase post
python scripts/migration_report.py --phase partitions
```

Revisions:

| ID | Purpose |
|----|---------|
| `0001_security_foundation` | Auth sessions / refresh tokens |
| `0002_enterprise_data_platform` | Soft-delete columns, `object_files`, tenant indexes, PG partition parents |

`create_all` + `migrate_schema()` remain for **dev bootstrap** and additive backfill — production forward path is Alembic.

## Quality gates (before)

1. Generate impact report (`migration_report.py --phase pre`)
2. Confirm API / PlatformContext / Security unchanged
3. Estimate downtime (additive = online)
4. Prepare rollback (`alembic downgrade -1`)

## Quality gates (after)

1. `migration_report.py --phase post`
2. Full pytest suite
3. `/health` shows `data_platform: enterprise-v1`
4. Workers, WebSockets, tenant isolation smoke checks

## MySQL → PostgreSQL (zero downtime)

1. Deploy `docker-compose.postgres.yml` alongside existing MySQL stack
2. Alembic upgrade on Postgres
3. Logical replication / ETL backfill
4. Dual-write window
5. Cut `DATABASE_URL` to `postgresql+psycopg://…@pgbouncer:5432/novaflow` with `DB_PGBOUNCER_MODE=1`
6. Decommission MySQL after soak

SQLite local development continues to work without Postgres.
