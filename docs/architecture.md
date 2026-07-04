# Architecture

## Overview

NovaFlow AI is a **monorepo-style product** with a custom Next.js frontend and a separate backend API.

```
┌─────────────────┐     /api/v1/*     ┌──────────────────┐
│  NovaFlow Web   │ ────────────────► │  Backend API     │
│  (Next.js)      │                   │  (FastAPI)       │
│  :3000          │                   │  :3001 / :7860   │
└─────────────────┘                   └────────┬─────────┘
                                               │
                    ┌──────────────────────────┼──────────────────────────┐
                    ▼                          ▼                          ▼
                 MySQL                      Redis                    Milvus + ES
```

## Design principles

1. **One UI** — single Next.js app (no split platform/client)
2. **API-first** — all features via REST + WebSocket
3. **Lite deploy** — optional reduced service profile for dev
4. **Progressive build** — ship MVP fast, add workflow editor later

## Current phase

- Frontend: NovaFlow-owned (this repo)
- Backend: Bisheng-compatible engine during v0.x
- Future: extract/rename backend modules into `services/api`
