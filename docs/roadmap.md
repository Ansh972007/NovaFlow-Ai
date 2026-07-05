# Roadmap

## v1.1 — Admin operations (current)

- [x] Model provider admin UI (chat model, embedding model, base URL in Settings)
- [x] Audit log CSV export (`/analytics/export`)
- [x] Password change in Settings
- [x] Login fix — username field for admin sign-in

## v1.0 — Launch (done)

- [x] Production deploy guide, English docs, demo environment, Docker stack, v1.0 tag

## v0.8 — Milvus, roles, analytics, run progress (done)

- [x] Milvus vector store, viewer enforcement, per-assistant analytics, workflow run WS

## Earlier versions

v0.1–v0.7: foundation, chat, knowledge, onboarding, workflow builder, embeddings, team roles.

## Remaining for full enterprise product

| Feature | Est. effort at current pace |
|---------|----------------------------|
| SSO / OAuth (Google, Azure AD) | 2–4 days |
| Multi-tenant workspaces | 1–2 weeks |
| Advanced workflow nodes (API, code, branch) | 1 week |
| Model provider UI (multiple providers, keys in vault) | 3–5 days |
| Fine-tune & evaluation module | 2–3 weeks |
| Mobile-responsive polish + i18n | 3–5 days |

**Total to “full” Bisheng-class parity:** ~4–6 weeks part-time (with AI-assisted dev), or ~2–3 weeks full-time.
