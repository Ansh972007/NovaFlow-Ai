# NovaFlow AI

**Enterprise AI workspace** — unified interface for chat, knowledge bases, and AI applications.

> v0.1 — Initial scaffold: landing, auth UI, dashboard shell, API client.

## What's included (checkpoint v0.1)

- Next.js 16 app (JavaScript, App Router, Tailwind CSS)
- Branded landing page with features & roadmap
- Login / register pages (Bisheng-compatible API)
- Dashboard shell with user info
- API client with dev proxy to backend
- Project docs & deploy notes

## Quick start

### 1. Backend

NovaFlow AI uses a compatible backend API. For local dev, run Bisheng:

```bash
cd path/to/bisheng/docker
docker compose -f docker-compose.yml -p bisheng up -d
```

Backend + default API: `http://localhost:3001`

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
├── src/
│   ├── app/              # Pages (landing, login, dashboard, docs)
│   ├── components/       # UI components (Logo, Navbar)
│   └── lib/api/          # API client & auth helpers
├── docs/                 # Architecture & roadmap
├── deploy/               # Docker / deployment configs
└── public/               # Static assets
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
| v0.4 | Setup wizard + templates |
| v1.0 | Production deploy |

## Tech stack

- **Frontend:** Next.js, React, Tailwind CSS, Axios
- **Backend (current):** Bisheng-compatible API (FastAPI)
- **Infra:** Docker, MySQL, Redis, Milvus, Elasticsearch

## License

Proprietary — NovaFlow AI. Backend architecture references open-source Bisheng patterns.
