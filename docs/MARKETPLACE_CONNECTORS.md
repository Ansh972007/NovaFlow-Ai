# Marketplace Connectors

Location: `backend/app/connectivity/registry.py`

## Connector marketplace model

Connectors are registered in `CONNECTOR_CATALOG` with category, auth types, and capabilities. Custom connectors register via plugin SDK.

## Categories

| Category | Examples |
|----------|----------|
| cloud_storage | s3, azure_blob, gcs, dropbox, sharepoint |
| communication | slack, discord, telegram, email_smtp |
| development | github, gitlab, jira, linear |
| crm | salesforce, hubspot |
| database | postgresql, mongodb, redis, snowflake |
| ai_provider | openai, anthropic, openrouter, ollama |
| mcp | mcp_server, mcp_client |

## Discovery

- `GET /connectivity/connectors` — full catalog
- `GET /connectivity/connectors/matrix` — category matrix

## UI integration

Connectors auto-discover in Workflow Builder, Knowledge OS sync, AgentOS tools, and Conversation attachments via unified registry — no UI redesign required.
