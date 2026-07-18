# Supervisor Engine

Location: `backend/app/agent_os/supervisor.py`

## Responsibilities

- Break goals into subtasks (`supervise_plan`)
- Assign roles to tasks
- Track progress (`evaluate_progress`)
- Merge specialist outputs
- Flag retry/escalation needs

## API

`POST /agent-os/supervisor/plan`

## Roles

Uses runtime `AGENT_ROLES`: planner, research, developer, reviewer, writer, coordinator.
