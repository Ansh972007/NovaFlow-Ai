# Policy Engine

Location: `backend/app/platform_intelligence/policy/engine.py`

## Policy types

| Type | Examples |
|------|----------|
| `quota` | Monthly cost budget |
| `provider` | Model allowlist |
| `workflow` | Require publish validation |
| `execution` | Max concurrent runs |
| `prompt` | Block prompt injection |
| `retention` | Audit log retention days |
| `rate_limit` | AI requests per minute |

## Scopes

Organization → Workspace → User (inheritance via DB query)

## API

- `GET /platform/intelligence/policies`
- `POST /platform/intelligence/policies/seed`
- `POST /platform/intelligence/policies/evaluate`

## Storage

`platform_policies` table; defaults in `DEFAULT_POLICIES` when no rows exist.

## Integration

Publish gate, runtime budget checks, workflow execution limits.
