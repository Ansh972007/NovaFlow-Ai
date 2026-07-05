# User guide

NovaFlow AI is an enterprise workspace for building and running AI assistants, knowledge bases (RAG), and visual workflows.

## Sign in

1. Open the app URL (default **http://localhost:3000**).
2. Sign in with your username and password.
3. New workspaces: complete the **setup wizard** to create your first assistant from a template.

Default demo accounts (when using `start-demo.ps1`):

- **Admin:** `admin` + password from `deploy/.env.production`
- **Viewer:** `demo` / `demo123` (read-only)

## Dashboard

The dashboard shows workspace stats, 7-day activity charts, and top assistants/workflows by usage.

## Chat

1. Go to **Chat** in the sidebar.
2. Select a **published** assistant from the list.
3. Type a message — responses stream in real time via WebSocket.
4. If the assistant has linked knowledge bases, relevant document chunks are retrieved automatically (RAG).

**Tip:** Publish assistants from **Apps → [assistant] → Publish** before they appear in chat.

## Apps (Assistant Studio)

Each assistant has:

- **Identity** — name and description shown in chat
- **System prompt** — core instructions (minimum 20 characters)
- **Knowledge (RAG)** — link one or more document libraries
- **Analytics** — 7-day chat activity chart

Actions:

| Action | Who |
|--------|-----|
| Save, publish, delete | Admin, Editor |
| View only | Viewer |

## Knowledge bases

1. **Knowledge** → **Create library**
2. Upload PDF, TXT, MD, or CSV files
3. Click **Process** to chunk and embed documents
4. Use **Q&A preview** to test chunk search
5. Link the library to an assistant in Assistant Studio

Processing requires an OpenAI API key for vector embeddings; without it, keyword search is used as fallback.

## Workflows

Workflows are visual pipelines: **trigger → retrieve → LLM → output**.

1. **Workflows** → create from a template (RAG, Support, Research)
2. Open the builder — drag nodes, configure retrieve/LLM steps
3. **Test** tab — run with sample input; steps and LLM output stream live over WebSocket
4. **Publish** to enable workflow chat

Published workflows appear in Chat alongside assistants.

## Settings

- **Profile** — account info
- **Team & roles** (admin only) — assign **admin**, **editor**, or **viewer**
  - **Viewer:** can browse chat, apps, knowledge, workflows but cannot create, edit, delete, or run tests

## Roles

| Role | Permissions |
|------|-------------|
| **Admin** | Full access + team management |
| **Editor** | Create/edit assistants, knowledge, workflows |
| **Viewer** | Read-only across studio pages |

## Tips

- Set `OPENAI_API_KEY` on the backend for production-quality chat and embeddings.
- Re-run the setup wizard from **Settings** to add another starter assistant.
- Check **http://localhost:3001/health** if the UI reports the API is offline.

## Getting help

- [Deployment guide](./deployment.md) — production Docker, HTTPS, troubleshooting
- [Architecture](./architecture.md) — system overview
- [Roadmap](./roadmap.md) — version history
