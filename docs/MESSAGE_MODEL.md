# Message Model

Location: `backend/app/database.py` + `conversation/service.py`

## Message types

`user`, `assistant`, `system`, `tool`, `workflow`, `knowledge`, `agent`, `notification`, `approval`, `comment`

## Core fields

| Field | Description |
|-------|-------------|
| `id` | UUID hex |
| `conversation_id` | Parent conversation |
| `thread_id` | Thread container |
| `parent_message_id` | Nested reply |
| `message_type` / `role` | Type and display role |
| `content` | Message body (32k max) |
| `model`, `provider` | AI provider metadata |
| `prompt_tokens`, `completion_tokens` | Token usage |
| `latency_ms`, `cost_usd` | Performance + FinOps |
| `trace_id` | Distributed tracing |
| `knowledge_refs_json` | RAG chunks used |
| `citations_json` | Citation IDs |
| `tool_calls_json` | Agent tool invocations |
| `workflow_ref`, `agent_ref` | Linked resources |

## Conversation types

`assistant`, `knowledge`, `workflow`, `agent`, `evaluation`, `marketplace`, `api`, `voice`, `desktop`, `browser`, `mobile`

## Visibility

`private`, `shared`, `workspace`, `organization`, `public`
