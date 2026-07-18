# Agent OS Architecture

NovaFlow Enterprise Agent Operating System (`backend/app/agent_os/`) is the **permanent autonomous intelligence layer** for all agent execution.

## Position in stack

```
Security → Platform → Data → AI Runtime → Workflow Intelligence → Platform Intelligence → Conversation → Knowledge OS → Agent OS
```

## Data model

| Table | Purpose |
|-------|---------|
| `saved_agents` | Agent registry with lifecycle, capabilities, policies |
| `agent_runs` | Execution sessions with plan, reasoning, verification |
| `agent_checkpoints` | Pause/resume state |
| `agent_plan_sessions` | Planning with dependency graphs |
| `agent_verification_reports` | Verification outcomes |
| `agent_learning_records` | Analytics without model retraining |

## Single execution path

All agent runs use `execute_agent()` or `execute_agent_from_runtime()`:

| Consumer | Integration |
|----------|-------------|
| REST `/agents/run` | `integration.execute_agent()` |
| REST `/agent-os/execute` | `integration.execute_agent()` |
| Workflow agent node | `integration.execute_agent_from_runtime()` |
| Future background workers | Same integration hook |

## API

Prefix: `/api/v1/agent-os/*`

Legacy `/api/v1/agents/*` remains for UI backward compatibility; `/agents/run` delegates to AgentOS.

## Health

`"agent_os": "enterprise-v1"` on `/health`

See: `AGENT_REGISTRY.md`, `SUPERVISOR_ENGINE.md`, `PLANNING_ENGINE.md`, `MULTI_AGENT_ENGINE.md`, `REASONING_ENGINE.md`, `VERIFICATION_ENGINE.md`, `MEMORY_ENGINE.md`, `TOOL_ORCHESTRATION.md`, `AGENT_ANALYTICS.md`, `PLUGIN_SDK_AGENT.md`.
