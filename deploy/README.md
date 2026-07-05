# NovaFlow deployment

NovaFlow ships its **own backend** (FastAPI + MySQL + Redis). Bisheng in this repo is reference-only — not required to run NovaFlow.

## Local development

### 1. Start NovaFlow API

```powershell
cd novaflow-ai
.\deploy\start-backend.ps1
```

This starts:
| Service | Port |
|---------|------|
| NovaFlow API | **3001** |
| MySQL | 3307 |
| Redis | 6381 |

Default admin: **admin** / **admin123**

### 2. Start the web app

```powershell
cd novaflow-ai
cp .env.example .env.local
npm install
npm run dev
```

Open **http://localhost:3000**

### 3. Verify

- **http://localhost:3000/api/health** → `{"ok":true,...}`
- Login page has no “API offline” banner

## Run API without Docker (dev)

```powershell
cd novaflow-ai/backend
pip install -r requirements.txt
copy .env.example .env
python -m uvicorn app.main:app --reload --port 3001
```

Uses SQLite at `backend/data/novaflow.db` when `DATABASE_URL` is unset.

## Optional: real LLM chat

Set in `deploy/docker-compose.yml` or `backend/.env`:

```
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```

Without a key, chat runs in demo mode with placeholder replies.

## Architecture

```
novaflow-ai/
  src/          # Next.js frontend
  backend/      # NovaFlow FastAPI API
  deploy/       # docker-compose + scripts
```

## Bisheng (blueprint only)

The `bisheng-main/` folder is kept as a design reference. Do **not** point NovaFlow at Bisheng Docker unless you are comparing behavior.
