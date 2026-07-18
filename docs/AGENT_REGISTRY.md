# Agent Registry

Location: `backend/app/agent_os/service.py`, `registry.py`

## Agent types

`research`, `knowledge`, `coding`, `workflow`, `evaluation`, `monitoring`, `supervisor`, `custom`

## Lifecycle

`draft` → `testing` → `published` → `archived` / `deprecated` / `deleted`

## Templates

Built-in: `research_pipeline`, `code_review`, `knowledge_qa`

## API

- `GET /agent-os/types`
- `GET /agent-os/templates`
- `POST /agent-os/agents`
- `POST /agent-os/agents/{id}/publish`
- `POST /agent-os/agents/{id}/clone`
- `GET /agent-os/agents/{id}/export`

## Metadata

Each agent stores: `capabilities_json`, `policies_json`, `template_id`, `version_no`, `agent_type`.
