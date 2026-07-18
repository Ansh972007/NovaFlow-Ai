# Memory Integration

Location: `backend/app/conversation/memory.py`

## Automatic integration

| Memory type | Source |
|-------------|--------|
| Conversation | Stored messages → runtime history |
| Workspace | `AIMemoryEntry` via runtime memory |
| Agent | Agent-scoped memory entries |
| Pinned | Pinned memory entries |
| Semantic | Knowledge + conversation summaries |

## Summarization

`POST /conversations/{id}/summarize` — AI-generated summary stored on conversation + memory entry.

## Runtime hook

When `conversation_id` provided to WebSocket, server loads history from DB instead of client-only `chatHistory`.

## Context compression

Summaries used in `load_conversation_memory()` for long threads.
