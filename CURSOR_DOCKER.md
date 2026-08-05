# Cursor + Docker on 16 GB RAM

Use this mode so Cursor and Docker can run at the same time.

## Why you still saw Apps + Projects

The **source** already merged Apps into Projects (nav = Projects only; `/apps` redirects).
The **Docker web image** was old and still contained the Apps nav. Rebuild the web image to fix the UI.

## Rebuild web UI (Projects-only) without Docker OOM

```powershell
.\scripts\rebuild-web-safe.ps1
```

This builds Next.js on the host, packs `Dockerfile.web` into `novaflow-web:local`, then starts the Cursor-safe stack.

## Daily start / stop

```powershell
.\scripts\cursor-stack-up.ps1
.\scripts\cursor-stack-down.ps1
```

## First-time RAM cap (once)

```powershell
.\scripts\apply-docker-ram-cap.ps1
```

## URLs

- Web: http://localhost:3000
- API: http://localhost:3001/health
- Login: username from `NOVAFLOW_ADMIN_USER` + password from `NOVAFLOW_ADMIN_PASSWORD` (change on first login)

## Advanced chat (API + web)

After pulling Advanced Friendly Chat changes, rebuild **both** images (close Cursor first if RAM is tight):

```powershell
# API (backend composer / Agent OS bridge)
docker compose build api
# ensure cursor stack uses :latest
docker tag novaflow-api:latest novaflow-api:latest

# Web (guided cards, status strip, category starters)
.\scripts\rebuild-web-safe.ps1
```

Or start the stack after images exist:

```powershell
.\scripts\cursor-stack-up.ps1
```

Hard-refresh http://localhost:3000. Try: category starters → Approve → Deploy.

**Do not** start Docker while editing in Cursor on 16 GB machines — finish code first, then rebuild.

## Chat Superpower (API + web)

After Superpower changes (ops bus, Agent OS execute in chat, voice commands, capabilities/workflows cards), rebuild **API and web** before testing:

```powershell
# Close Cursor first on 16 GB machines
docker compose build api
.\scripts\rebuild-web-safe.ps1
.\scripts\cursor-stack-up.ps1
```

Smoke checks after hard-refresh:

- Chat: “What can you do?” → capabilities card
- “List my workflows” / “Run my last workflow”
- Agent goal → Continue/approve → agent result card
- Voice: “approve”, “navigate to credentials”
- Heal twice → “Heal again” ask card

## Enterprise Chat OS (API + web)

After Enterprise Chat OS changes (schedules, EIAP health/finops/compliance, export/share, audit, vault, integrations, RBAC gates, playbooks), rebuild **API and web**:

```powershell
# Close Cursor first on 16 GB machines — do not run Docker while Cursor is open
docker compose build api
.\scripts\rebuild-web-safe.ps1
.\scripts\cursor-stack-up.ps1
```

Smoke checks:

- “What can you do?” lists enterprise skills
- “List schedules” / “Workspace health” / “FinOps summary” / “Compliance report”
- “Export this chat as markdown” / “Share this chat”
- “Run incident playbook” → stepped chips
- Viewer cannot export/schedule → permission denied card

## Universal Field Work Chat (API + web)

After Universal Field Work Chat changes (router, domain recipes, generic workflow fallback, Q&A→workflow chips), rebuild **API and web**:

```powershell
# Close Cursor first on 16 GB machines
docker compose build api
.\scripts\rebuild-web-safe.ps1
.\scripts\cursor-stack-up.ps1
```

Smoke checks:

- “Automate invoice reminders from my documents every Monday” → solution card
- “Onboard new hires with a welcome email” → HR-style plan
- “What is RAG?” → normal answer + “Build a workflow for this” chip
- “List my workflows” → still ops
- Vague “automate my work” → field clarify chips

## Requirements Fulfillment (API + web)

After Requirements Fulfillment + policy gates:

```powershell
docker compose build api
.\scripts\rebuild-web-safe.ps1
.\scripts\cursor-stack-up.ps1
```

Smoke:

- `Capture requirements: onboard new hires with welcome email`
- `Show requirements` → checklist card
- `Fulfill these requirements` → solution + fulfillment progress
- Approve → Test → Deploy updates checklist
- `Show chat policy` lists workspace policies (empty = allow + RBAC)

## Enterprise Compose + Test + GB Uploads (API + web)

After Fast Compose / Enterprise sandbox / 2 GB chat uploads:

```powershell
# Close Cursor first on 16 GB machines
docker compose build api
.\scripts\rebuild-web-safe.ps1
.\scripts\cursor-stack-up.ps1
```

Env (optional):

- `MAX_CHAT_UPLOAD_BYTES` — default `2147483648` (2 GiB) for chunked chat attachments
- `SYNC_EXTRACT_MAX_BYTES` — default `33554432` (32 MB); larger files extract in background
- `MAX_UPLOAD_BYTES` — still 25 MB for single-shot uploads

Smoke:

- Invoice/HR goal → express compose + enterprise test suite card + compose timing
- Attach multi-MB file → chunked progress; say **index attachments** → `indexing` knowledge card
- Chunk-init over 2 GB → rejected
- Approve / Retest / Fix & retest chips on sandbox card

## Chat Powerhouse — 12 mega tools (API + web)

After Powerhouse (diff, versions, eval, receipt, debug, KG, collab, kill switch, simulate, SLA, change requests, digests):

```powershell
# Close Cursor first on 16 GB machines
docker compose build api
.\scripts\rebuild-web-safe.ps1
.\scripts\cursor-stack-up.ps1
```

Smoke phrases:

- `Show powerhouse` → catalog of 12 tools
- `Diff my workflow` / `Show workflow versions`
- `Eval scorecard` / `Run simulation lab`
- `Show cost receipt`
- `Debug last run` / `SLA reliability brief`
- `Explore knowledge graph`
- `Open collab war room`
- `Kill switch` → confirm card → `Confirm kill switch`
- `Propose change: add Slack notify` → `Apply change request`
- `Digest attachments to workflows`

## Friendly Chat + Clear Voice (API + web)

After plain-English narratives, empty-bubble/guide fixes, and voice polish:

```powershell
docker compose build api
.\scripts\rebuild-web-safe.ps1
.\scripts\cursor-stack-up.ps1
```

Smoke:

- Ask to email someone daily → reply names the address, asks for email login in plain English (no UUID / “Generic Field Automation”)
- Guide description appears at most once per session
- No blank assistant bubbles between cards
- Voice: “impliment it for mr” → composer shows polished “Implement it for me.” with Heard: chip

## Pre-deploy security (git-ready)

Before pushing / going live:

1. Set strong secrets (never commit them):
   - `NOVAFLOW_ENV=production`
   - `JWT_SECRET` (≥32 random bytes)
   - `NOVAFLOW_ADMIN_PASSWORD` (≥16 chars, not a known default)
   - Optional: `NOVAFLOW_VAULT_KEY` (separate from JWT)
2. Public `/health` is liveness-only; use `/health/detail` as admin for diagnostics
3. First admin must change password on login (`must_change_password`)
4. Public registration is off in production unless `ALLOW_PUBLIC_REGISTER=1`
5. Automated gate: `cd backend; python -m pytest tests/test_security_foundation.py tests/test_smoke.py -k "health or must_change or bootstrap or upload_id or login" -q`

Out-of-Cursor smoke (16 GB): close Cursor → build images → set env → login → change password → Credentials → one chat Approve/Test.

## Chat Unity + Credentials (API + web)

After one-reply / vault / NL credential fixes:

```powershell
docker compose build api
.\scripts\rebuild-web-safe.ps1
.\scripts\cursor-stack-up.ps1
```

Smoke:

- Ask for daily email → **one** assistant reply + **one** plan card (no empty bubbles / guide spam)
- Save SMTP in **Credentials**, then ask again → chat says email login found, does **not** re-ask for smtp_password
- Paste: `my email is you@gmail.com and its pass is xxxx xxxx xxxx xxxx` → Credentials saved card + Approve chip (secret redacted in history)
- Paste bare Gmail app password while a plan is pending → saved, not demo RAG handbook

## Universal Automation Pack (API + web)

Channel-aware compose for Telegram, Slack, Outlook, Google Auth, Shopify, WhatsApp, YouTube, Jira, HubSpot/custom HTTP, etc.:

```powershell
docker compose build api
.\scripts\rebuild-web-safe.ps1
.\scripts\cursor-stack-up.ps1
```

Smoke phrases:

- `Build Shopify order sync` → Shopify plan title + shopify_* credential chips (one card)
- `Connect Google Sheets via Google OAuth` → Google OAuth missing fields; paste `google client_id: … client_secret: … refresh_token: …`
- `Send Outlook mail digests` → Outlook / Microsoft Graph paste hints
- `Automate HubSpot CRM sync via API` → Custom API plan; paste `api_key: … base_url: https://…`
- `Build a telegram support bot` → Telegram token ask (unchanged path)
- Save channel secrets on **Credentials** or paste in chat → gaps clear; **Approve → Test → Deploy**

## Chat God-Tier — Depth + Autopilot + Forge (API + web)

After Powerhouse depth, Chat Autopilot, and Chat Forge 12:

```powershell
docker compose build api
.\scripts\rebuild-web-safe.ps1
.\scripts\cursor-stack-up.ps1
```

Smoke phrases:

- `Show powerhouse` / `Show forge` → tool catalogs
- `Run incident autopilot` → step checklist card; `Confirm autopilot` to continue past destructive steps
- `Autopilot status` / `Cancel autopilot`
- `Show prompt drift` / `Show A/B routes` / `Open webhook studio`
- `List project packs` / `Scan for publish` / `Find reusable template`
- `Model lab costs` / `OCR attachments to workflow` / `GitHub issue bridge`
- `Import CSV from chat` / `Generate solution docs` / `Run solution assertions`
