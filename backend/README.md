# NovaFlow API

FastAPI backend for NovaFlow AI — **not** Bisheng. Implements the endpoints used by the NovaFlow frontend.

## Quick start (local, SQLite)

```bash
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 3001
```

Default user: **admin** / **admin123**

## Docker (MySQL + Redis)

From `novaflow-ai` root:

```powershell
.\deploy\start-backend.ps1
```

## Implemented

- Auth (RSA login, JWT, register)
- Assistants (CRUD, publish, WebSocket chat)
- Knowledge (upload, chunk, search preview)
- LLM config stubs
- Health check

## Roadmap (Bisheng parity)

- Milvus / vector RAG
- Workflows & skills
- Multi-tenant groups & roles
- Model provider admin UI
- Finetune & evaluation
