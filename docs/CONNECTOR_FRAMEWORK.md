# Connector Framework

Location: `backend/app/connectivity/registry.py`, `plugins/`

## Universal connector model

Every connector supports: metadata, authentication, capabilities, validation, versioning, health, retry, rate limits, sync, webhooks.

## Catalog

`list_connectors()` — 40+ connector types across cloud storage, communication, development, CRM, databases, AI providers, identity, observability, MCP.

## Plugins

| Plugin | Delegates to |
|--------|--------------|
| `SlackPlugin` | integrations service |
| `GithubPlugin` | github_issues service |
| `JiraPlugin` | gmail_jira service |
| `LinearPlugin` | linear_issues service |

## API

- `GET /connectivity/connectors`
- `GET /connectivity/connectors/matrix`
- `GET /connectivity/plugins`

## Extension

```python
from app.connectivity.plugins import register_connector_plugin, BaseConnectorPlugin

register_connector_plugin("acme_crm", AcmeCRMPlugin)
```
