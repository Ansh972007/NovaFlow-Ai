# Reliability Engine

Location: `backend/app/platform_intelligence/reliability/engine.py`

## Features

| Feature | Implementation |
|---------|----------------|
| Retry policies | Exponential backoff, max attempts |
| Circuit breakers | Integrated via `healing/circuit_breaker.py` |
| Checkpoint resume | Workflow Intelligence `WorkflowPendingRun` |
| Dead letter | Workflow run status=error + events |
| Health checks | `observability/health.py` |

## Usage

```python
from app.platform_intelligence.reliability.engine import execute_with_reliability, ReliabilityPolicy

result, meta = await execute_with_reliability(
    my_async_fn,
    policy=ReliabilityPolicy(max_attempts=3),
    breaker_name="llm_provider",
)
```

## Workflow integration

Existing HITL pause/resume + Workflow Intelligence checkpoint module.

## Provider failover

Circuit breaker open → recommendation in incidents dashboard; runtime can route to fallback model (via `runtime/router.py` policies).
