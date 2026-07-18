# Reasoning Engine

Location: `backend/app/agent_os/reasoning.py`

## Trace components

- Task reasoning
- Tool reasoning
- Knowledge reasoning
- Reflection steps
- Self-critique

## Confidence

`score_confidence()` combines tool evidence, verification verdict, output quality.

## Storage

Reasoning stored on `agent_runs.reasoning_json`.
