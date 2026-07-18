# Observability Platform

## Telemetry sources

| Subsystem | Collection |
|-----------|------------|
| HTTP APIs | `TraceMiddleware` → `record_http_metric()` |
| AI Runtime | `integration/runtime_hook.py` → `PlatformMetric` |
| Workflow Engine | Events + step `trace_id` |
| Database | `data/observability.py` slow-query hooks |
| Workers | `platform/worker.py` audit |

## Per-request fields

Trace ID, latency, status, workspace, provider, model, tokens, cost, knowledge hits, retries.

## Storage

- **Hot:** in-memory ring buffer (500 samples) for dashboards
- **Cold:** `platform_metrics` table

## Dashboards

- `GET /platform/intelligence/metrics`
- `GET /platform/intelligence/dashboard/system`
- `GET /platform/intelligence/dashboard/workspace`

## Correlation

All layers share `trace_id` from `platform_intelligence.tracing.context`.
