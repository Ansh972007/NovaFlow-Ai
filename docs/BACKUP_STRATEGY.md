# Backup Strategy

## PostgreSQL (production)

| Type | Tooling | Cadence |
|------|---------|---------|
| Full | `pg_basebackup` / managed snapshot | Daily |
| Incremental / WAL | continuous archiving | Continuous |
| Logical | `pg_dump` (schema+data) | Weekly + pre-migration |
| Object storage | Provider versioning + cross-region | Continuous |
| Redis | RDB/AOF per provider policy | Daily |

## Verification

- Monthly restore to isolated cluster
- Checksum validation on dump artifacts
- Application smoke: login, workspace switch, knowledge search, workflow run

## Retention

| Class | Retention |
|-------|-----------|
| WAL / PITR | ≥ 7 days (prod ≥ 30) |
| Daily full | 14–30 days |
| Weekly | 90 days |
| Audit legal hold | Per policy; `legal_hold` blocks purge |

Env: `AUDIT_RETENTION_DAYS`, `SOFT_DELETE_PURGE_DAYS`.
