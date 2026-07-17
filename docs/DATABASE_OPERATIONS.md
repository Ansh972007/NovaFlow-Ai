# Database Operations

## Environment

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | SQLAlchemy URL (`postgresql+psycopg://…`) |
| `DB_PGBOUNCER_MODE` | `1` → NullPool (PgBouncer owns pooling) |
| `DB_POOL_SIZE` / `DB_MAX_OVERFLOW` | Direct pool (no PgBouncer) |
| `DB_STATEMENT_TIMEOUT_MS` | PostgreSQL statement_timeout |
| `DB_PARTITION_MONTHS_AHEAD` | Auto partition horizon |
| `VECTOR_PROVIDER` | `auto\|milvus\|pgvector\|qdrant\|sqlite` |
| `STORAGE_PROVIDER` | `local\|s3\|r2\|minio\|gcs\|azure` |
| `STORAGE_*` | Bucket / endpoint / keys |
| `REDIS_URL` | Cache + future rate limits |
| `AUDIT_RETENTION_DAYS` | Audit retention policy |
| `SOFT_DELETE_PURGE_DAYS` | Hard-delete eligibility |

## Compose

```bash
# Legacy MySQL stack (unchanged)
docker compose -f deploy/docker-compose.yml up -d

# PostgreSQL 17 + PgBouncer overlay
docker compose -f deploy/docker-compose.yml -f deploy/docker-compose.postgres.yml up -d
```

## Health

`GET /health` includes `database`, `vector_backend`, `storage_backend`, `cache_backend`, `db_metrics`, `data_platform`.

## Security

- TLS to Postgres in production
- Encryption at rest via cloud volume / TDE
- Secrets via env / secret manager (never in git)
- Parameterized SQL only (SQLAlchemy)
- Schema changes audited via Alembic + security audit log
