# NovaFlow AI

**Enterprise AI workspace** — unified interface for chat, knowledge bases, and AI applications.

> v0.1 — Initial scaffold: landing, auth UI, dashboard shell, API client.

## What's included (checkpoint v0.1)

- Next.js 16 app (JavaScript, App Router, Tailwind CSS)
- Branded landing page with features & roadmap
- Login / register pages (NovaFlow API)
- Dashboard shell with user info
- API client with dev proxy to backend
- Project docs & deploy notes

## Quick start

### 1. Backend (NovaFlow API)

Start NovaFlow's **own** API (not Bisheng):

```powershell
.\deploy\start-backend.ps1
```

Default API URL: `http://localhost:3001` · login **admin** / **admin123**

> If port 3001 is in use by old Bisheng containers, stop them first:  
> `docker stop bisheng-frontend`

### 2. Frontend

```bash
cd novaflow-ai
cp .env.example .env.local
npm install
npm run dev
```

Open **http://localhost:3000**

### 3. Sign in

Use your backend account or register a new user at `/login?mode=register`.

## Project structure

```
novaflow-ai/
├── src/              # Next.js frontend
├── backend/          # NovaFlow FastAPI API
├── deploy/           # docker-compose + start scripts
└── docs/             # Architecture & roadmap
```

## Environment

| Variable | Default | Description |
|----------|---------|-------------|
| `NEXT_PUBLIC_API_URL` | `http://localhost:3001` | Backend API base URL |
| `NEXT_PUBLIC_APP_NAME` | `NovaFlow AI` | Display name |

## Roadmap

| Version | Goal |
|---------|------|
| **v0.1** | Landing, auth UI, dashboard shell ✅ |
| v0.2 | Streaming chat |
| v0.3 | Knowledge upload & list |
| **v0.4** | NovaFlow API + Docker stack ✅ |
| v1.0 | Production deploy |

## Tech stack

- **Frontend:** Next.js, React, Tailwind CSS
- **Backend:** NovaFlow API (FastAPI, MySQL/SQLite, Redis)
- **Reference:** Bisheng architecture (not a runtime dependency)

## License

Proprietary — NovaFlow AI.
