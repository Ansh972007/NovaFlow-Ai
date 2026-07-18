# Search Engine

Location: `backend/app/conversation/search.py`

## Modes

- **Full-text** — token match on title, summary, message content
- **Filters** — conversation_type, assistant_id, model, message_type, pinned, starred, date

## API

`POST /api/v1/conversations/search`

```json
{
  "q": "invoice processing",
  "assistant_id": "abc123",
  "conversation_type": "assistant",
  "pinned": false,
  "limit": 30
}
```

## Future

Semantic/hybrid search via vector index on message embeddings (extends Data Platform vector abstraction).

## Tenant isolation

All queries filter by `workspace_id` from PlatformContext.
