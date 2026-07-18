# Verification Engine

Location: `backend/app/agent_os/verification.py`

## Sources

- Tool outputs
- Knowledge OS (kb_search evidence)
- Citation checks
- Policy rules
- Math claim detection

## Verdicts

`pass`, `review`, `fail`

## API

- `GET /agent-os/runs/{id}/verification`
- Automatic on every `execute_agent()` when `verify=true`

## Storage

`agent_verification_reports` table.
