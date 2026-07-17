# Agent Runtime

Location: `backend/app/runtime/agents.py`

## Agent loop (deterministic)

1. Select relevant tools (max 3)
2. Execute tools in dependency order
3. Compile synthesis prompt with tool results
4. Generate final answer via execution engine
5. Validate output

No hidden autonomous loops — each step is observable in `tool_results` and audit logs.

## Limits (`AgentLimits`)

| Field | Default |
|-------|---------|
| `max_tools` | 3 |
| `max_steps` | 1 |
| `timeout_seconds` | 120 |

## Multi-agent roles

| Role | Purpose |
|------|---------|
| `planner` | Decompose request into steps |
| `research` | Extract evidence from tools |
| `developer` | Implementation guidance |
| `reviewer` | Accuracy review |
| `writer` | User-facing draft |
| `coordinator` | Merge specialist outputs |

Specialists run sequentially; coordinator produces final answer. Use `run_multi_agent()` for orchestrated flows.

## Permissions

Requires `Permission.AGENT_RUN` (editor+ by default).

## API

```python
result = await runtime.run_agent(AgentRequest(
    user_input="Summarize our warranty policy",
    tool_ids=["kb_search", "summarize"],
    knowledge_id=42,
    agent_id="abc123",
))
# result.output, result.tool_results, result.selected_tools, result.metrics
```

## Retry / cancellation

- Cancellation: set `cancel_event` on `RuntimeContext`
- Retries: recorded in `RuntimeMetrics.retries` (execution layer)
