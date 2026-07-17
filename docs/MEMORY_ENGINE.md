# Memory Engine

Location: `backend/app/runtime/memory.py`  
Storage: `ai_memory_entries` table (`AIMemoryEntry`)

## Scopes

| Scope | Description |
|-------|-------------|
| `conversation` | Prior user/assistant turns (from client history) |
| `workspace` | Shared workspace facts |
| `project` | Project-scoped notes (`scope_ref` = project id) |
| `agent` | Agent-specific memory (`scope_ref` = agent id) |
| `pinned` | Always-included pinned snippets |
| `semantic` | Reserved for vector-backed long-term memory (via knowledge layer) |

## Tenant isolation

All queries filter by `workspace_id`. Cross-tenant reads are impossible at the resolver layer.

## API

```python
from app.runtime.memory import resolve_memory, store_memory, MemoryRequest

bundle = resolve_memory(ctx, MemoryRequest(
    history=history,
    assistant_id=assistant_id,
    agent_id=agent_id,
    query=user_message,
))
# bundle.combined() → injected into prompt compiler

store_memory(db, workspace_id=1, scope="workspace", content="...", pinned=True)
```

## Limits

- Last 12 conversation turns
- 4000 chars per history message
- 8 memory snippets per scope

## Integration

Memory is resolved automatically in `AIRuntime._build_chat_prompt()` before prompt compilation.
