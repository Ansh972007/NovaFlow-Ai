# Workflow Planner

Location: `backend/app/workflow_intelligence/planner.py`

## Purpose

Convert natural language automation descriptions into execution graphs.

## Example

> "When a customer uploads an invoice, extract information, store it, notify finance, update CRM."

## Output (`WorkflowPlan`)

- `summary` — one-line description
- `graph` — `{ nodes, edges }` ready for builder
- `documentation` — markdown summary
- `security_notes` — SSRF, credential, scope reminders
- `permissions` — required platform permissions
- `retry_policy` — default exponential backoff

## API

`POST /api/v1/workflow/intelligence/plan`

```json
{ "description": "When invoice uploaded..." }
```

Uses **AI Runtime** when provider configured; falls back to deterministic heuristic planner.

## Audit

`workflow.intelligence.plan` logged via PlatformContext.
