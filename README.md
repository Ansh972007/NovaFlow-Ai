# NovaFlow AI

**Enterprise AI workspace** — chat, knowledge bases (RAG), visual workflows, and team analytics in one frosted-glass UI.

**Version 1.0** — production-ready Docker stack, English docs, and one-command demo environment.

## Features

- **Assistant Studio** — prompts, publish/unpublish, per-assistant analytics
- **Knowledge (RAG)** — upload, chunk, embed, semantic search
- **Workflow builder** — circular canvas, live test runs with WebSocket progress
- **Streaming chat** — assistants and published workflows
- **Team roles** — admin, editor, viewer with API + UI enforcement
- **Analytics** — dashboard charts, usage tracking
- **Milvus** — optional vector store (SQLite fallback for dev)

## Quick start (development)

### 1. Backend

```powershell
cd novaflow-ai
.\deploy\start-backend.ps1
```

API: **http://localhost:3001** · default login **admin** / **admin123**

### 2. Frontend

```powershell
cd novaflow-ai
copy .env.example .env.local
npm install
npm run dev
```

Open **http://localhost:3000**

## Demo environment (one command)

Full stack with sample handbook, assistants, and workflow:

```powershell
.\deploy\start-demo.ps1
```

| Account | Password | Role |
|---------|----------|------|
| admin | see `deploy/.env.production` | Admin |
| demo | demo123 | Viewer |

## Production deployment

```powershell
copy deploy\.env.production.example deploy\.env.production
# Edit JWT_SECRET, NOVAFLOW_ADMIN_PASSWORD, OPENAI_API_KEY
.\deploy\start-prod.ps1
```

See **[docs/deployment.md](docs/deployment.md)** for HTTPS, reverse proxy, and security checklist.

## Documentation

| Doc | Description |
|-----|-------------|
| [User guide](docs/user-guide.md) | Chat, apps, knowledge, workflows, roles |
| [Deployment](docs/deployment.md) | Production Docker, env vars, troubleshooting |
| [Architecture](docs/architecture.md) | System design and data model |
| [Roadmap](docs/roadmap.md) | Version history |

## Project structure

```
novaflow-ai/
├── src/              # Next.js frontend
├── backend/          # FastAPI API
├── deploy/           # Docker Compose + start scripts
├── docs/             # Guides and architecture
└── Dockerfile        # Production web image
```

## Environment

| Variable | Default | Description |
|----------|---------|-------------|
| `NEXT_PUBLIC_API_URL` | `http://localhost:3001` | Backend URL (browser) |
| `OPENAI_API_KEY` | — | Real LLM + embeddings (demo mode without) |
| `NOVAFLOW_DEMO_SEED` | `0` | Seed sample data on first boot |

## Tech stack

- **Frontend:** Next.js 16, React, Tailwind CSS, Recharts, Framer Motion
- **Backend:** FastAPI, SQLAlchemy, MySQL/SQLite, Redis, Milvus (optional)
- **AI:** OpenAI-compatible chat + embeddings

## License

Proprietary — NovaFlow AI.
