# Roadmap

## v8.0 — Unified workspace UI & diff export (current)

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

**NovaFlow v8.0** unifies the workspace UI and adds workflow diff export.
