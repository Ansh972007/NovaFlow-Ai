# Governance Engine

Location: `backend/app/eiap/governance.py`

## Reports

| Function | Purpose |
|----------|---------|
| `workspace_health_report()` | Unified health + open/critical recommendations |
| `compliance_report()` | Audit events, failed ops, isolation/encryption status |
| `security_posture()` | Active security controls + posture score |

## Data sources

- `eiap.observability.unified_health`
- `SecurityAuditLog` (audit events)
- Existing security controls (RBAC, PII scan, SSRF, connector policy)

## API

- `GET /eiap/governance/health`
- `GET /eiap/governance/compliance`
- `GET /eiap/governance/security`

## Reporting

`reporting.generate_report()` produces daily/weekly/monthly/executive snapshots persisted in `eiap_reports`.
