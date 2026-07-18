# Agent OS Plugin SDK

Location: `backend/app/agent_os/plugins/`

## Register custom extensions

```python
from app.agent_os.plugins import register_custom_agent, register_custom_planner, register_custom_verifier

def my_planner(goal: str) -> dict:
    return {"tasks": [{"id": "t1", "title": goal}]}

register_custom_planner("acme", my_planner)
```

## Extensibility surface

| Hook | Purpose |
|------|---------|
| Custom agents | Alternative execution handlers |
| Custom planners | Goal decomposition |
| Custom verifiers | Domain-specific verification |

## Requirements

Plugins must:
- Respect tenant scope (`workspace_id`)
- Not bypass PlatformContext
- Route LLM calls through AI Runtime
- Route knowledge through Knowledge OS
- Persist runs via AgentOS task layer

## API

`GET /agent-os/plugins`
