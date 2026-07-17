# Performance Guide

## Built-in signals

`/health` → `db_metrics`: query_count, slow_count, avg_ms, recent slow statements.

`app.data.observability.optimization_report()` for recommendations.

## PostgreSQL

Enable `pg_stat_statements` (compose overlay sets `shared_preload_libraries`).

Watch:

- Sequential scans on large tenant tables
- Lock waits / deadlocks (`with_deadlock_retry`)
- Pool saturation (PgBouncer `SHOW POOLS`)
- Partition pruning on `*_p` tables

## Application rules

- Always `ctx.query` / tenant indexes
- No N+1: join or eager-load where measured
- Keep transactions short
- Optimistic lock (`row_version`) for concurrent edits
- Cache hot reads via `get_cache()` with tenant keys
