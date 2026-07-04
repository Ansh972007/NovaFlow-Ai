# Development deployment

## Option A — Bisheng backend + NovaFlow frontend (recommended for now)

1. Run Bisheng Docker stack (port **3001**)
2. Run NovaFlow frontend:

```bash
npm run dev
```

3. Next.js proxies `/api/*` → `http://localhost:3001/api/*`

## Option B — Production (future)

- Build: `npm run build && npm start`
- Serve behind nginx with API upstream
- See `docker-compose.yml` (coming in v0.4)

## Ports

| Service | Port |
|---------|------|
| NovaFlow Web | 3000 |
| Backend API | 3001 (via nginx) or 7860 (direct) |
