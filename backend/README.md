# NovaFlow API

FastAPI backend for NovaFlow AI v1.0.

## Quick start (SQLite, no Docker)

```bash
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 3001
```

Default user: **admin** / **admin123**

## Docker (MySQL + Redis + Milvus)

From `novaflow-ai` root:

```powershell
.\deploy\start-backend.ps1
```

## Demo seed

Set `NOVAFLOW_DEMO_SEED=1` to populate sample assistants, knowledge, and a workflow on first boot:

```bash
export NOVAFLOW_DEMO_SEED=1
python -m uvicorn app.main:app --port 3001
```

Or use `.\deploy\start-demo.ps1` for the full stack.

## Implemented (v1.0)

- Auth (RSA login, JWT, register)
- Assistants (CRUD, publish, RAG, WebSocket chat, analytics)
- Knowledge (upload, chunk, embed, Milvus/SQLite search)
- Workflows (visual graph, REST + WebSocket run progress, chat)
- Analytics (dashboard, per-assistant, team roles)
- Demo seed service
- Health check with version + vector backend

## Environment

See `.env.example` and [docs/deployment.md](../docs/deployment.md).

## API prefix

All routes under `/api/v1/` except `/health` and `/`.
