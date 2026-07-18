# Multi-Agent Engine

Location: `backend/app/agent_os/orchestration.py`

## Modes

| Mode | Function |
|------|----------|
| `sequential` | `run_team()` default |
| `parallel` | Tool phase + role fan-out |
| `consensus` | Multiple reviewers + coordinator |

## Pipeline example

Research → Knowledge → Reasoning → Coding → Testing → Verification → Final Response

## Execution

Built on `runtime/agents.run_multi_agent()` — never bypass AI Runtime.

## API

`POST /agent-os/execute` with `mode: "multi"` or `"consensus"`
