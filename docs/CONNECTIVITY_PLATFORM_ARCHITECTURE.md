# Connectivity Platform Architecture

NovaFlow Enterprise Connectivity Platform (`backend/app/connectivity/`) is the **permanent integration backbone** for all external system interactions.

## Position in stack

```
Security → Platform → Data → AI Runtime → Workflow Intelligence → Platform Intelligence
→ Conversation → Knowledge OS → Agent OS → Connectivity Platform
```

## Data model

| Table | Purpose |
|-------|---------|
| `connector_connections` | Named connector instances per workspace |
| `connector_credentials` | Encrypted secrets with versioning |
| `connector_sync_jobs` | Incremental/scheduled sync |
| `connector_webhooks` | Inbound/outbound webhook subscriptions |
| `connector_events` | Event log for replay and observability |
| `mcp_registrations` | MCP server/client registrations |

## Single integration path

All external operations use `invoke_connector_action()` or `send_notification()` — never call third-party APIs directly from feature code.

## API

Prefix: `/api/v1/connectivity/*`

Legacy `/api/v1/integrations/*` remains for UI backward compatibility.

## Health

`"connectivity_platform": "enterprise-v1"` on `/health`

See: `CONNECTOR_FRAMEWORK.md`, `MCP_ARCHITECTURE.md`, `AUTHENTICATION_FRAMEWORK.md`, `SYNC_ENGINE.md`, `EVENT_ENGINE.md`, `SECRET_MANAGEMENT.md`, `CONNECTOR_SDK.md`, `PLUGIN_GUIDE.md`, `MARKETPLACE_CONNECTORS.md`.
