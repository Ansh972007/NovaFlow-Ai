# NovaFlow deployment

## Local development

### 1. Start the NovaFlow API (backend)

The API must be running on **port 3001** before you sign in.

From this repo:

```powershell
.\deploy\start-backend.ps1
```

Or manually — see `deploy/start-backend.ps1` for the exact command used on your machine.

### 2. Start the NovaFlow web app

```bash
cp .env.example .env.local
npm install
npm run dev
```

Open **http://localhost:3000**

Next.js proxies `/api/*` → your NovaFlow API at `NEXT_PUBLIC_API_URL` (default `http://localhost:3001`).

### 3. Verify connection

- Login page shows no “API offline” warning
- Or open **http://localhost:3000/api/health** — should return `{"ok":true,...}`

## Ports

| Service | Port |
|---------|------|
| NovaFlow Web | 3000 |
| NovaFlow API | 3001 |

## Production (future)

- Build: `npm run build && npm start`
- Serve behind nginx with API upstream
- Lite Docker compose coming in v0.4
