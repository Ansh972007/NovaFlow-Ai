# Workflow Debugger

Location: `backend/app/workflow_intelligence/debugger.py`

## Features

- **Execution timeline** — ordered step events from `steps_json`
- **Live variables** — input, output, retrieved hits, agent tools
- **Dependency graph** — from workflow edges
- **Replay** — steps up to first error

## API

| Endpoint | Purpose |
|----------|---------|
| `GET /workflow/intelligence/runs/{id}/debug` | Full debug session + metrics |
| `GET /workflow/intelligence/runs/{id}/replay` | Replay steps |

## WebSocket

Live run progress via existing `/workflow/run/ws/{id}` — step events unchanged.

## Trace correlation

Each step includes `trace_id` linking to AI Runtime observability.
