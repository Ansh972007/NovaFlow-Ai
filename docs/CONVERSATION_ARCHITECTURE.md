# Conversation Architecture

NovaFlow Enterprise Conversation Platform (`backend/app/conversation/`) is the **permanent conversation system** for all AI interactions.

## Position in stack

```
Security → Platform → Data → AI Runtime → Workflow Intelligence → Platform Intelligence → Conversation Platform
```

## Data model

| Table | Purpose |
|-------|---------|
| `conversations` | Top-level conversation record |
| `conversation_threads` | Thread within conversation |
| `conversation_messages` | Messages with full metadata |
| `conversation_branches` | Fork/merge tracking |
| `conversation_attachments` | File attachments (object storage) |
| `conversation_shares` | Share links with expiry |
| `conversation_snapshots` | Version history |

## Message metadata

Every message stores: workspace_id, organization_id, trace_id, model, provider, tokens, latency, cost, knowledge refs, citations, tool calls, workflow/agent refs.

## Integration points

| Entry | Integration |
|-------|-------------|
| WebSocket assistant chat | `integration/persist_chat_turn()` |
| AI Runtime memory | `conversation/memory.py` |
| Platform events | `ConversationMessageCreated` |
| FinOps | cost_usd on messages |

## API

Prefix: `/api/v1/conversations/*`

## UI compatibility

Existing WebSocket protocol unchanged. Optional `conversation_id` query param + server-side history load. Server emits `{"type":"conversation","conversation_id":"..."}` after each turn.

See: `MESSAGE_MODEL.md`, `THREADING_ENGINE.md`, `SEARCH_ENGINE.md`, `MEMORY_INTEGRATION.md`, `EXPORT_ENGINE.md`, `COLLABORATION.md`.
