# Memory Engine (Agent OS)

Location: `backend/app/agent_os/memory.py`

## Memory types

| Scope | Source |
|-------|--------|
| Agent memory | `AIMemoryEntry` scope=`agent` |
| Conversation | `load_history_for_runtime()` |
| Execution | Saved post-run via learning records |

## Integration

Memory context injected into agent system prompt during `execute_agent()`.

## API

Future: `GET /agent-os/agents/{id}/memory`

Uses existing `runtime/memory.py` for AI Runtime chat paths.
