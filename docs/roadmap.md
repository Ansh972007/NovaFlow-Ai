# Roadmap

## v1.0 — Launch (current)

- [x] Production deploy guide ([deployment.md](./deployment.md))
- [x] English docs ([user-guide.md](./user-guide.md), updated README)
- [x] Demo environment (`start-demo.ps1` + demo seed)
- [x] Production Docker stack (web + API + data services)
- [x] v1.0 release

## v0.8 — Milvus, role enforcement, assistant analytics, run progress (done)

- [x] Optional Milvus vector store (Docker + SQLite fallback)
- [x] Viewer role enforcement on mutating APIs
- [x] Per-assistant analytics detail page
- [x] Workflow run WebSocket progress events

## v0.7 — Embeddings, workflow chat, analytics charts, team roles (done)

- [x] OpenAI vector embeddings on knowledge ingest
- [x] Workflow WebSocket chat for published workflows
- [x] Analytics timeseries + top apps charts on dashboard
- [x] Team roles (admin / editor / viewer) + settings UI

## v0.6 — Workflow builder + analytics (done)

- [x] Workflow CRUD API + visual builder
- [x] Workflow runtime + usage analytics

## v0.5 — Assistant Studio + RAG (done)

- [x] Assistant detail / studio page
- [x] Link knowledge bases to assistants
- [x] Unified frosted workspace UI

## Earlier versions

See git history for v0.1–v0.4 (foundation, chat, knowledge, onboarding).

## Future ideas

- SSO / OAuth login
- Model provider admin UI
- Audit logs export
- Multi-tenant workspaces
