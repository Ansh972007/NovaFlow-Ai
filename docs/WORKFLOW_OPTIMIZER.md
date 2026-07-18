# Workflow Optimizer

Location: `backend/app/workflow_intelligence/optimizer.py`

## Suggestion categories

- **latency** — merge consecutive LLM nodes
- **knowledge** — batch retrieval, add RAG
- **parallel** — parallelizable root branches, loop concurrency
- **cost** — reduce parallel branch count
- **cache** — enable prompt/knowledge cache

## API

`POST /api/v1/workflow/intelligence/optimize`

Also included in publish-check response.

## Metrics

- `estimated_llm_calls`
- `parallelizable_groups`

## Copilot

`POST /workflow/intelligence/copilot/suggest` returns optimizer output via AI Runtime context.
