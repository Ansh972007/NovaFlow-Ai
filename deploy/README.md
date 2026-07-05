# NovaFlow deployment

NovaFlow ships its **own backend** (FastAPI + MySQL + Redis + optional Milvus). The `bisheng-main/` folder in this repo is reference-only.

## Profiles

| Script | Stack | Use case |
|--------|-------|----------|
| `start-backend.ps1` | API + MySQL + Redis + Milvus | Local frontend dev |
| `start-prod.ps1` | Web + API + all data services | Production |
| `start-demo.ps1` | Same as prod + seeded demo data | Try NovaFlow quickly |

## Local development

### Backend only (Docker)

```powershell
cd novaflow-ai
.\deploy\start-backend.ps1
```

| Service | Port |
|---------|------|
| NovaFlow API | **3001** |
| MySQL | 3307 |
| Redis | 6381 |
| Milvus | 19530 |

Default admin: **admin** / **admin123**

### Frontend

```powershell
cd novaflow-ai
copy .env.example .env.local
npm install
npm run dev
```

Open **http://localhost:3000**

### API without Docker

```powershell
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 3001
```

Uses SQLite at `backend/data/novaflow.db` when `DATABASE_URL` is unset.

## Production

```powershell
copy deploy\.env.production.example deploy\.env.production
# Edit secrets
.\deploy\start-prod.ps1
```

Web: **http://localhost:3000** · API: **http://localhost:3001**

Full guide: [docs/deployment.md](../docs/deployment.md)

## Demo

```powershell
.\deploy\start-demo.ps1
```

Seeds **Support Assistant**, **Document Q&A**, **NovaFlow Handbook** knowledge base, and a **Handbook Q&A** workflow. Also creates viewer user **demo** / **demo123**.

## Optional: real LLM

Set in `deploy/.env.production` or `backend/.env`:

```
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```

Without a key, chat runs in demo mode with placeholder replies.

## Verify

- **http://localhost:3000/api/health** → `{ "ok": true }`
- **http://localhost:3001/health** → API version `1.0.0`

## Files

| File | Purpose |
|------|---------|
| `docker-compose.yml` | Dev backend stack |
| `docker-compose.prod.yml` | Production (web + api + data) |
| `.env.production.example` | Production env template |
