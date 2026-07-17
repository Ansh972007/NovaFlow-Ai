# Indexing Guide

## Philosophy

Measure first. Prefer composite **tenant-leading** indexes. Avoid unused single-column indexes on low-cardinality flags.

## Standard patterns

| Pattern | Columns | Use |
|---------|---------|-----|
| Tenant active | `(workspace_id, deleted_at)` | List queries via `scoped_query` |
| Tenant time | `(workspace_id, create_time)` | Runs, usage, analytics |
| Ownership | `(workspace_id, owner_id)` | Private visibility |
| Audit | `(workspace_id, created_at)` | Security audit trail |
| Lookup | PK / unique slug | Identity |

## PostgreSQL extras

- **BRIN** on append-only time columns for huge partitions
- **GIN** on JSONB metadata when introduced
- **Partial** indexes `WHERE deleted_at IS NULL` for hot paths
- **Expression** indexes for lower(email) style lookups

## Process

1. Capture slow query from `db_metrics` / `pg_stat_statements`
2. `EXPLAIN (ANALYZE, BUFFERS)`
3. Add minimal index via Alembic
4. Re-measure; drop if unused
