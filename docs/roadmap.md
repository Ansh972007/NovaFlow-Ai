# Roadmap

## v9.2 — Integration wiring & project depth (current)

- [x] Telegram webhook panel in Workflow Builder — register, copy URL, public base URL
- [x] Webhook persistence in DB + live status from Telegram API
- [x] Projects detail page — run workflows, test integrations, linked workflow list
- [x] Dashboard workspace pulse — integrations, projects, Model Lab jobs, drift warnings
- [x] Model Lab — system prompt, webhook URL, auto-poll active jobs
- [x] Settings — public API URL, clear credentials, integration status cards
- [x] Developer playground — v9 API presets

## v9.1 — Integration credentials in Settings (done)

- [x] Workspace DB storage for Telegram bot token and Gmail/SMTP (encrypted)
- [x] Settings → Integrations UI — configure, verify, and test Telegram & email
- [x] Workflows, eval alerts, and projects use workspace credentials from DB

## v9.0 — Integrations, Model Lab & quality radar (done)

- [x] Notify workflow node — Telegram, email, webhook channels
- [x] Dev workflow templates — Telegram Q&A, daily digest, eval alert
- [x] Telegram webhook trigger — inbound messages run published workflows
- [x] Model Lab — knowledge → dataset → train → auto-eval pipeline
- [x] Dev Projects hub — map integrations and workflows per project
- [x] AI Receipt — per-response audit (model, RAG sources/chunks) in chat
- [x] Prompt drift radar — eval regression detection in Evaluation UI

## v8.0 — Unified workspace UI & diff export (done)

- [x] Shared workspace design system — `WorkspacePageShell`, tabs, stat cards, alerts, loading
- [x] Enhanced chat UI — `AppHeader`, new chat fix, sidebar cleanup
- [x] Tabbed settings — Overview, Security, Models, Integrations, Team
- [x] Polished all workspace pages — Apps, Knowledge, Workflows, Agents, Evaluation, Developer, Marketplace, Setup, Docs
- [x] Performance runtime — shared pointer/scroll buses, rAF loop, canvas optimizations
- [x] Workflow diff export — download JSON or Markdown report from version compare

## v7.0 — Collaboration & security (done)

- [x] SAML signature verification — IdP cert validation, audience & timestamp checks
- [x] Side-by-side workflow diff — dual canvas compare (before / after)
- [x] Co-editing presence — multi-viewer list with live cursor positions on canvas

## v6.0 — Developer & diff canvas (done)

- [x] Visual workflow diff canvas — overlay added/changed/removed nodes on the builder
- [x] Knowledge URL ingest — fetch web pages into a knowledge base
- [x] A/B model routing UI — manage traffic split in Settings
- [x] API playground — test endpoints with session or API key

## Future enhancements

| Feature | Notes |
|---------|--------|
| Real-time graph merge | Operational transform for simultaneous edits |
| SAML SLO | Single logout with IdP |
| Diff PDF export | Printable comparison reports |

**NovaFlow v9.2** wires Telegram webhooks end-to-end and deepens Projects, dashboard, and Model Lab.
