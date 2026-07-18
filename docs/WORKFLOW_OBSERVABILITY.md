# Workflow Observability

Location: `backend/app/workflow_intelligence/observability.py`

## Per-run metrics

- Duration, step count, error count
- LLM steps, retrieve steps
- Per-node latency (when recorded)
- Trace ID (AI Runtime correlation)

## Workspace stats

`GET /api/v1/workflow/intelligence/observability`

- Total runs (sample window)
- Error rate, success rate
- Average duration

## Stored artifacts

- `WorkflowRun.steps_json` — per-node status/output
- `UsageEvent` — `workflow_run` with `trace_id`, `duration_ms`

## AI Runtime metrics

LLM/agent nodes inherit runtime metrics (tokens, model, knowledge hits) via bridge.

## Analytics

Existing `/analytics` endpoints complement workspace-level workflow stats.
