# Event Platform

Location: `backend/app/platform_intelligence/events/emitter.py`

## Event types (examples)

- `WorkflowStarted`, `WorkflowCompleted`, `WorkflowFailed`
- `AgentFinished`
- `TestEvent` (testing)

## Features

| Feature | Support |
|---------|---------|
| Filtering | By workspace, event_type, trace_id |
| Subscriptions | In-memory handlers (`subscribe()`) |
| Retention | Configurable purge via automation |
| Correlation | `trace_id` on every event |
| Audit | Governance events → `SecurityAuditLog` |

## API

`GET /platform/intelligence/events?event_type=&trace_id=&limit=`

## Storage

`platform_events` table with JSON payload.

## Emission

```python
from app.platform_intelligence.events.emitter import emit_platform_event

emit_platform_event(db, "WorkflowStarted", workspace_id=1, resource_id=wf_id)
```
