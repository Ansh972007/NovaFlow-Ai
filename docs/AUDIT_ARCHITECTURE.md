# Audit Architecture

## Security audit (authoritative)

Table: `security_audit_logs` via `audit_log()` / `PlatformContext.audit()`.

Captured fields: action, actor, workspace_id, resource_type/id, IP, UA, success, detail JSON, timestamp.

Tenant read API: `GET /analytics/audit` (requires `security:audit` in workspace).  
Export: `GET /analytics/export` (`analytics:export`).

## Usage events (product analytics)

Table: `usage_events` — chat / workflow run volume metrics. Not a substitute for security audit.

## Emergency access trail

Actions: `emergency_access.requested|approved|denied|revoked|expired`, `tenant.emergency_access.used`.

## Worker trail

`worker.job.start` / `worker.job.end` with workspace binding.
