# Roadmap

## v1.3 — Multi-tenant workspaces (current)

- [x] Workspace model with members (admin / editor / viewer)
- [x] Resources scoped by `workspace_id` (assistants, knowledge, workflows, analytics)
- [x] Workspace API: list, create, invite members, role management
- [x] `X-Workspace-Id` header + workspace switcher in UI
- [x] WebSocket chat/run scoped to active workspace
- [x] Legacy data migration to personal workspaces on startup

## v1.2 — SSO / OAuth (done)

- [x] Google + Microsoft OAuth, callback page, SSO status in Settings

## v1.1 — Admin operations (done)

- [x] Model provider admin, audit export, password change, login username fix

## v1.0 — Launch (done)

- [x] Production Docker, docs, demo environment

## Remaining for full enterprise product

| Feature | Est. effort |
|---------|-------------|
| Advanced workflow nodes | 1 week |
| Multiple model providers + key vault | 3–5 days |
| Fine-tune & evaluation | 2–3 weeks |

**~2–4 weeks part-time** to full Bisheng-class parity from v1.3.
