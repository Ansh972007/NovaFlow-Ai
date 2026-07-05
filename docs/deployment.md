# Production deployment

This guide covers running NovaFlow AI in production with Docker. For local development, see [deploy/README.md](../deploy/README.md).

## Architecture

```
Browser ──► Web (Next.js :3000)
              │ rewrites /api/*
              ▼
           API (FastAPI :3001) ──► MySQL, Redis, Milvus
              │
              └── WebSocket (chat, workflow run progress)
```

| Service | Purpose |
|---------|---------|
| **web** | Next.js UI (standalone build) |
| **api** | FastAPI backend, file uploads, embeddings |
| **mysql** | Primary database |
| **redis** | Session/cache (reserved for future use) |
| **milvus** | Optional vector search at scale (SQLite fallback if unavailable) |

## Quick production start (Docker)

From the `novaflow-ai` root:

```powershell
# 1. Configure secrets
copy deploy\.env.production.example deploy\.env.production
# Edit JWT_SECRET, NOVAFLOW_ADMIN_PASSWORD, OPENAI_API_KEY

# 2. Start full stack
.\deploy\start-prod.ps1
```

Open **http://localhost:3000** and sign in with the admin credentials from `.env.production`.

### Demo environment

One command to start production stack **with sample data** (handbook, assistants, workflow):

```powershell
.\deploy\start-demo.ps1
```

| Account | Password | Role |
|---------|----------|------|
| `admin` | value of `NOVAFLOW_ADMIN_PASSWORD` | Admin |
| `demo` | `demo123` | Viewer (read-only) |

Sample content includes **Support Assistant**, **Document Q&A**, a **NovaFlow Handbook** knowledge base, and a published **Handbook Q&A pipeline** workflow.

To re-seed, remove the API data volume and marker:

```powershell
docker compose -f deploy/docker-compose.prod.yml down -v
.\deploy\start-demo.ps1
```

## Environment variables

### Required (production)

| Variable | Description |
|----------|-------------|
| `JWT_SECRET` | Long random string for JWT signing |
| `NOVAFLOW_ADMIN_PASSWORD` | Initial admin password |

### Web

| Variable | Default | Description |
|----------|---------|-------------|
| `NEXT_PUBLIC_API_URL` | `http://localhost:3001` | URL the **browser** uses for API + WebSocket |
| `API_INTERNAL_URL` | `http://api:3001` | Server-side proxy target inside Docker |
| `WEB_PORT` | `3000` | Host port for the web container |

### API

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | MySQL in compose | SQLAlchemy connection string |
| `OPENAI_API_KEY` | empty | Enables real LLM + embeddings (demo mode without) |
| `MILVUS_URI` | `http://milvus:19530` | Vector store; omit for SQLite-only embeddings |
| `NOVAFLOW_DEMO_SEED` | `0` | Set `1` to seed demo assistants on first boot |

See [deploy/.env.production.example](../deploy/.env.production.example) for the full list.

## Behind a reverse proxy (HTTPS)

1. Terminate TLS at nginx, Caddy, or a cloud load balancer.
2. Set `NEXT_PUBLIC_API_URL` to your public API origin, e.g. `https://api.yourdomain.com`.
3. Proxy WebSocket paths:
   - `/api/v1/assistant/chat/*`
   - `/api/v1/workflow/chat/*`
   - `/api/v1/workflow/run/ws/*`
4. Increase body size limits for knowledge file uploads (recommend **50 MB+**).

Example nginx snippet:

```nginx
location / {
  proxy_pass http://127.0.0.1:3000;
  proxy_http_version 1.1;
  proxy_set_header Upgrade $http_upgrade;
  proxy_set_header Connection "upgrade";
  proxy_set_header Host $host;
}

location /api/ {
  proxy_pass http://127.0.0.1:3001;
  proxy_http_version 1.1;
  proxy_set_header Upgrade $http_upgrade;
  proxy_set_header Connection "upgrade";
  client_max_body_size 50m;
}
```

When using split domains, point the Next.js rewrite `API_INTERNAL_URL` at the internal API service.

## Manual deployment (no Docker)

### Backend

```bash
cd backend
pip install -r requirements.txt
export DATABASE_URL=mysql+pymysql://user:pass@host:3306/novaflow
export JWT_SECRET=your-secret
python -m uvicorn app.main:app --host 0.0.0.0 --port 3001
```

Use a process manager (systemd, supervisord) and place uploads on persistent storage (`DATA_DIR`).

### Frontend

```bash
npm ci
export NEXT_PUBLIC_API_URL=https://api.yourdomain.com
npm run build
npm start
```

## Health checks

| Endpoint | Expected |
|----------|----------|
| `GET /health` (API) | `{ "status_code": 200, "data": { "version": "1.0.0", ... } }` |
| `GET /api/health` (Web) | `{ "ok": true }` when API is reachable |

## Upgrades

1. Pull latest code and checkout tag `v1.0`.
2. Rebuild containers: `docker compose -f deploy/docker-compose.prod.yml up -d --build`.
3. Database schema migrations run automatically on API startup (`migrate_schema()`).

## Security checklist

- [ ] Change `JWT_SECRET` and admin password before going live
- [ ] Do not expose MySQL/Redis/Milvus ports publicly
- [ ] Set `OPENAI_API_KEY` via secrets manager, not in git
- [ ] Use HTTPS and secure cookies in production
- [ ] Assign **viewer** role to read-only users (Settings → Team)

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Login page shows “API offline” | Ensure API is on port 3001; check `NEXT_PUBLIC_API_URL` |
| WebSocket chat fails | Confirm proxy passes `Upgrade` headers; token in `?t=` query |
| Milvus slow to start | Wait ~90s on first boot; API falls back to SQLite vectors |
| Empty demo data | Set `NOVAFLOW_DEMO_SEED=1` and reset volumes |

Logs: `docker logs novaflow-api --tail 50` · `docker logs novaflow-web --tail 50`
