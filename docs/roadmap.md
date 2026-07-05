# Roadmap

## v0.7 — Embeddings, workflow chat, analytics charts, team roles (current)

- [x] OpenAI vector embeddings on knowledge ingest (cosine search + keyword fallback)
- [x] Workflow WebSocket chat for published workflows (`/workflow/chat/{id}`)
- [x] Analytics timeseries + top apps charts on dashboard
- [x] Team roles (admin / editor / viewer) + settings UI for admins
- [x] DB migrations for `embedding_json` and `user.role`

## v0.6 — Workflow builder + analytics (done)

- [x] Workflow CRUD API + DB models
- [x] Visual workflow builder (`/workflows/[id]`)
- [x] Workflow runtime (trigger → retrieve → LLM → output)
- [x] Semantic chunk retrieval (token overlap scoring)
- [x] Usage analytics API + dashboard widgets
- [x] Chat usage logging

## v0.5 — Assistant Studio + RAG (done)

- [x] Assistant detail / studio page (`/apps/[id]`)
- [x] Link knowledge bases to assistants (RAG in chat)
- [x] Settings page — workspace UI
- [x] Workflows preview page (`/workflows`)
- [x] Unified frosted workspace UI across chat, dashboard, apps, knowledge

## v0.4 — Onboarding (done)

- [x] First-run setup wizard (`/setup`)
- [x] 3 starter assistant templates
- [x] Health & settings page (`/settings`)
- [x] Apps page — create, publish, delete assistants
- [x] NovaFlow FastAPI backend + Docker stack

## v0.3 — Knowledge (done)

- [x] Knowledge base list (`/knowledge`)
- [x] Create knowledge base
- [x] File upload with progress
- [x] Processing status (auto-refresh)
- [x] Q&A preview (chunk search)

## v0.2 — Chat (done)

- [x] Chat page with sidebar
- [x] List online assistants / apps
- [x] WebSocket streaming chat
- [x] Session history (localStorage)
- [x] Stop generation button

## v0.1 — Foundation (done)

- [x] Project scaffold & git init
- [x] Landing page + branding
- [x] Login / register UI
- [x] API client + auth encryption
- [x] Dashboard shell

## v0.8 — Next

- [ ] Milvus vector store (production scale)
- [ ] Viewer role enforcement on mutating APIs
- [ ] Per-assistant analytics detail page
- [ ] Workflow run WebSocket progress events

## v1.0 — Launch

- [ ] Production deploy guide
- [ ] English docs
- [ ] Demo environment
- [ ] v1.0 tag
