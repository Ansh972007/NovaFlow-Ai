# Platform Intelligence Architecture

NovaFlow's **Enterprise Platform Intelligence Layer** (`backend/app/platform_intelligence/`) sits above the locked foundations and provides unified observability, tracing, FinOps, policy, events, self-healing, and admin intelligence.

## Stack position

```
Enterprise Security Foundation
Enterprise Multi-Tenant Platform (app/platform/)
Enterprise Data Platform (app/data/)
Enterprise AI Runtime (app/runtime/)
Enterprise Workflow Intelligence (app/workflow_intelligence/)
Enterprise Platform Intelligence (app/platform_intelligence/)  ← this layer
```

## Package layout

| Module | Role |
|--------|------|
| `tracing/` | Distributed trace ID via `X-Trace-Id`, contextvars |
| `observability/` | Metrics ring buffer, DB persistence, health |
| `finops/` | Cost ledger, budgets, forecasts, anomalies |
| `policy/` | Centralized policy evaluation |
| `events/` | Domain event stream |
| `healing/` | Circuit breakers, anomaly detection |
| `reliability/` | Retry with backoff + breaker integration |
| `capacity/` | Growth forecasting |
| `automation/` | Maintenance (purge, integrity checks) |
| `admin/` | Enterprise dashboards |
| `sdk/` | Python REST client |
| `integration/` | Hooks into runtime/workflow |

## API prefix

`/api/v1/platform/intelligence/*`

## Middleware

`TraceMiddleware` — every HTTP request gets/propagates `X-Trace-Id`.

## Scheduler

Platform maintenance runs every ~30 min via `background_scheduler_loop`.

## Health

`/health` reports `"platform_intelligence": "enterprise-v1"`.

## Related docs

- `OBSERVABILITY_PLATFORM.md`
- `POLICY_ENGINE.md`
- `EVENT_PLATFORM.md`
- `SELF_HEALING.md`
- `FINOPS.md`
- `CAPACITY_PLANNING.md`
- `RELIABILITY_ENGINE.md`
- `DEVELOPER_PLATFORM.md`
- `PLATFORM_ARCHITECTURE.md` (multi-tenant kernel)
