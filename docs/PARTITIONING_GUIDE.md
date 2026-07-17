# Partitioning Guide

## Strategy

Monthly `RANGE` partitions on PostgreSQL for high-volume time-series:

| Parent | Column |
|--------|--------|
| `security_audit_logs_p` | `created_at` |
| `workflow_runs_p` | `create_time` |
| (planned) `usage_events_p`, `notifications_p` | `create_time` |

Created by Alembic `0002` (parents) + `ensure_monthly_partitions()` (children).

## Operations

```bash
python scripts/migration_report.py --phase partitions
```

Env: `DB_PARTITION_MONTHS_AHEAD` (default 3).

## Cutover

1. Dual-write application → live table + partition parent  
2. Backfill historical months  
3. Switch reads to parent  
4. Drop/rename legacy table after soak  

SQLite/MySQL: partitioning helpers no-op (capability gate).
