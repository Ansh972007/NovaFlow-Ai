# Planning Engine

Location: `backend/app/agent_os/planning.py`

## Capabilities

| Function | Purpose |
|----------|---------|
| `decompose_goal()` | Hierarchical task breakdown |
| `create_plan_session()` | Persist plan with dependencies |
| `replan()` | Dynamic replanning |

## Output

Plan includes `tasks`, `dependencies`, `execution_order`.

## API

- `POST /agent-os/plan`
- `POST /agent-os/plan/{id}/replan`
