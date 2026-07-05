# Architecture

## Overview

NovaFlow AI is a product monorepo: a **Next.js** frontend and a **FastAPI** backend designed to deploy together or independently.

```
┌─────────────────────┐     REST + WS      ┌─────────────────────┐
│  NovaFlow Web       │ ─────────────────► │  NovaFlow API       │
│  Next.js  :3000     │   /api/v1/*        │  FastAPI  :3001     │
└─────────────────────┘                    └──────────┬──────────┘
                                                      │
                         ┌────────────────────────────┼────────────────────────────┐
                         ▼                            ▼                            ▼
                      MySQL                        Redis                         Milvus
                   (primary DB)                  (cache)                  (vectors, optional)
```

## Frontend (`src/`)

| Area | Route | Purpose |
|------|-------|---------|
| Landing | `/` | Marketing page |
| Auth | `/login` | RSA-encrypted login/register |
| Dashboard | `/dashboard` | Analytics + workspace overview |
| Chat | `/chat` | WebSocket streaming chat |
| Apps | `/apps`, `/apps/[id]` | Assistant list + studio |
| Knowledge | `/knowledge` | Libraries, upload, chunk preview |
| Workflows | `/workflows`, `/workflows/[id]` | List + visual builder |
| Settings | `/settings` | Profile, team roles |

API calls go through `src/lib/api/*`. Chat uses `AssistantChatSocket` for WebSocket streaming.

## Backend (`backend/app/`)

| Module | Responsibility |
|--------|----------------|
| `routers/user.py` | Auth, JWT, public key |
| `routers/assistant.py` | Assistant CRUD, publish |
| `routers/knowledge.py` | Upload, chunk, search |
| `routers/workflow.py` | Workflow CRUD, REST run |
| `routers/chat_ws.py` | Assistant + workflow chat WS, run progress WS |
| `routers/analytics.py` | Usage stats, team roles |
| `services/knowledge.py` | Chunking, embeddings, RAG |
| `services/workflow.py` | Graph execution engine |
| `services/vector_store.py` | Milvus with SQLite fallback |
| `services/demo_seed.py` | Demo environment seed data |

## Data model (core)

- **User** — `role`: admin | editor | viewer
- **Assistant** — prompt, status (draft/published), linked knowledge
- **KnowledgeBase** → **KnowledgeFile** → **KnowledgeChunk** (+ `embedding_json`)
- **Workflow** — JSON graph (nodes + edges), **WorkflowRun** history
- **UsageEvent** — chat, workflow_run, workflow_chat analytics

## RAG pipeline

1. Upload file → chunk text → OpenAI embeddings
2. Store vectors in `embedding_json` and optionally **Milvus**
3. On chat/workflow retrieve step: cosine search → top chunks → LLM context

## Workflow engine

Topological execution of graph nodes:

```
trigger → retrieve (optional) → llm → output
```

Test runs can stream step events and LLM tokens over `/workflow/run/ws/{id}`.

## Deployment profiles

| Profile | Command | Use case |
|---------|---------|----------|
| Dev | `npm run dev` + uvicorn | Local development |
| Backend only | `deploy/start-backend.ps1` | Frontend dev against Docker API |
| Production | `deploy/start-prod.ps1` | Web + API + data services |
| Demo | `deploy/start-demo.ps1` | Production + seeded sample data |

## Design principles

1. **Single UI** — one Next.js app, no split admin/client
2. **API-first** — REST for CRUD, WebSocket for streaming
3. **Progressive complexity** — SQLite locally, MySQL + Milvus in production
4. **Role-aware** — viewer enforcement on mutating APIs and UI

## Reference

The sibling `bisheng-main/` folder in this repository is an **architecture reference only**. NovaFlow does not depend on Bisheng at runtime.
