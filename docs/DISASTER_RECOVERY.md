# Disaster Recovery

## RTO / RPO targets (enterprise baseline)

| Tier | RPO | RTO |
|------|-----|-----|
| Production primary | ≤ 5 min (WAL) | ≤ 1 hour |
| Object storage | Versioning | ≤ 4 hours |
| Regional failover | Async replica | ≤ 4 hours |

## Runbook (summary)

1. Declare incident; freeze schema migrations
2. Promote read replica / restore from PITR to new primary
3. Point PgBouncer / `DATABASE_URL` at new primary
4. Verify `/health` (`database.dialect=postgresql`, ping OK)
5. Replay object-storage failover if needed
6. Run `migration_report.py --phase post` + pytest smoke
7. Re-enable writers; communicate customer status

## Geo replication

Architecture is replica-ready: PgBouncer → primary; read replicas via future `DATABASE_READ_URL` (not required for Phase 3 kernel).
