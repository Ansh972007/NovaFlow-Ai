# 🚀 NovaFlow AI — Complete Free Git-Based Production Deployment Guide

This guide provides the complete, step-by-step instructions for deploying NovaFlow AI to a **100% free-tier cloud architecture** directly from GitHub.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          TARGET ARCHITECTURE                                │
├─────────────────────────────────────────────────────────────────────────────┤
│  GitHub Repository (Source)                                                 │
│    ├── Vercel Web Service       ──►  Next.js 16 / React 19 Frontend         │
│    ├── Render Web Service       ──►  FastAPI Backend (Docker Container)     │
│    ├── Supabase Project         ──►  Cloud PostgreSQL 15 Relational DB      │
│    ├── Upstash Redis            ──►  Serverless Redis Cache & Presence      │
│    └── External Services        ──►  LLM Providers, Telegram & Google OAuth │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 📋 Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Step 1: Database Setup (Supabase PostgreSQL)](#2-step-1-database-setup-supabase-postgresql)
3. [Step 2: Cache & Presence Setup (Upstash Redis)](#3-step-2-cache--presence-setup-upstash-redis)
4. [Step 3: Backend Deployment (Render Web Service via Docker)](#4-step-3-backend-deployment-render-web-service-via-docker)
5. [Step 4: Frontend Deployment (Vercel)](#5-step-4-frontend-deployment-vercel)
6. [Step 5: Database Migrations](#6-step-5-database-migrations)
7. [Step 6: Telegram Webhook & Integration Setup](#7-step-6-telegram-webhook--integration-setup)
8. [Step 7: Production Verification & Smoke Testing](#8-step-7-production-verification--smoke-testing)
9. [Troubleshooting & Free-Tier Cold Starts](#9-troubleshooting--free-tier-cold-starts)

---

## 1. Prerequisites

Before starting, create free accounts on the following platforms:
- **[GitHub](https://github.com/)** (To host your source repository)
- **[Supabase](https://supabase.com/)** (Free 500 MB PostgreSQL database)
- **[Upstash](https://upstash.com/)** (Free Serverless Redis with TLS)
- **[Render](https://render.com/)** (Free Python Web Service)
- **[Vercel](https://vercel.com/)** (Free Next.js hosting)

---

## 2. Step 1: Database Setup (Supabase PostgreSQL)

1. Log into **[Supabase Console](https://supabase.com/dashboard)** and click **New Project**.
2. Set a **Project Name** (e.g. `novaflow-db`) and generate a strong **Database Password**.
3. Choose your nearest region (e.g. `US East`, `EU West`, `AP South`).
4. Once provisioned, go to **Project Settings** → **Database** → **Connection String** → Select **URI** (or **Session Pooler** on port `6543`).
5. Copy your connection string:
   ```text
   postgresql://postgres.[YOUR-PROJECT-REF]:[YOUR-PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres
   ```
   *(Note: NovaFlow automatically normalizes `postgres://` or `postgresql://` URLs).*

---

## 3. Step 2: Cache & Presence Setup (Upstash Redis)

1. Log into **[Upstash Console](https://console.upstash.com/)** and click **Create Database**.
2. Set a **Name** (e.g. `novaflow-redis`) and choose your preferred cloud/region.
3. Once created, scroll down to **REST & Redis Connection Details**.
4. Select **`redis-py`** or copy the **`rediss://...`** TLS connection string:
   ```text
   rediss://default:[YOUR-PASSWORD]@[YOUR-ENDPOINT].upstash.io:6379
   ```

---

## 4. Step 3: Backend Deployment (Render Web Service via Docker)

1. Log into **[Render Dashboard](https://dashboard.render.com/)**.
2. Click **New +** → **Web Service** → Connect your **`NovaFlow-Ai`** GitHub repository.
3. Configure the service settings:
   - **Name**: `novaflow-api`
   - **Region**: Singapore (or nearest to your Supabase region)
   - **Language / Environment**: `Docker`
   - **Root Directory**: `backend`
   - **Dockerfile Path**: `Dockerfile` (or leave default)
   - **Docker Context**: `.` (or leave default)
   - **Plan**: `Free`
4. Under **Advanced** → **Health Check Path**, enter: `/health`
5. Under **Environment Variables**, add the following:

| Key | Value | Notes |
| :--- | :--- | :--- |
| `NOVAFLOW_ENV` | `production` | Enables production security mode. |
| `DATABASE_URL` | `<your-supabase-connection-string>` | From Step 1. |
| `REDIS_URL` | `<your-upstash-connection-string>` | From Step 2. |
| `JWT_SECRET` | `<random-64-character-hex-string>` | Secret key for JWT signing. |
| `ENCRYPTION_KEY` | `<random-32-byte-base64-key>` | Master key for AES-256 vault. |
| `ALLOW_PASSWORD_LOGIN` | `1` | Allows username & password login. |
| `ALLOW_PUBLIC_REGISTER` | `1` | Allows new user registration. |
| `GMAIL_ONLY_AUTH` | `0` | Allows any email address to register. |
| `FRONTEND_URL` | `https://novaflow-ai.vercel.app` | Updated in Step 4. |

6. Click **Create Web Service**. Render will build and launch your backend at:
   `https://novaflow-ai.onrender.com`

---

## 5. Step 4: Frontend Deployment (Vercel)

1. Log into **[Vercel Dashboard](https://vercel.com/dashboard)**.
2. Click **Add New...** → **Project** → Import your **`NovaFlow-Ai`** GitHub repository (`Ansh972007/NovaFlow-Ai`).
3. In the project configuration:
   - **Framework Preset**: `Next.js`
   - **Root Directory**: `./` (leave default repository root)
   - **Build Command**: `npm run build`
   - **Install Command**: `npm install`
4. Expand **Environment Variables** and add:

| Key | Value | Description |
| :--- | :--- | :--- |
| `NEXT_PUBLIC_API_URL` | `https://novaflow-ai.onrender.com` | Your Render Backend URL from Step 3. |
| `NEXT_PUBLIC_APP_NAME` | `NovaFlow AI` | App Brand Title. |
| `NEXT_PUBLIC_UNIVERSAL_CHAT_ENABLED` | `true` | Enables real-time AIOS Chat. |

5. Click **Deploy**. Vercel will build and publish your frontend at:
   `https://novaflow-ai.vercel.app`
6. *(Important)* Return to your Render backend dashboard and ensure `FRONTEND_URL` is set to `https://novaflow-ai.vercel.app`.

---

## 6. Step 5: Database Migrations

NovaFlow AI automatically initializes all relational tables on first boot (`init_db()`).

To manually run or inspect Alembic migrations:
```bash
# In local shell or Render SSH terminal
cd backend
alembic upgrade head
```

---

## 7. Step 6: Telegram Webhook & Integration Setup

1. Message **`@BotFather`** on Telegram and create a bot using `/newbot`.
2. Copy your **Bot Token** (e.g. `123456789:ABCdef...`).
3. Log into your deployed NovaFlow web app at `https://novaflow-ai.vercel.app`.
4. Navigate to **Credentials Vault** → Click **+ Add Credential** → Choose **Telegram Bot Token** → Enter your token.
5. In your workflow canvas, add a **Telegram Trigger** or **Notify Node**.
6. The public webhook is automatically registered at:
   `https://novaflow-ai.onrender.com/api/v1/integrations/telegram/webhook/<workflow_id>`
7. Test your bot on any mobile device by sending **`/greetings`**!

---

## 8. Step 7: Production Verification & Smoke Testing

Verify the deployed stack with these checks:
1. **Liveness Probe**: Open `https://novaflow-ai.onrender.com/api/health` → Should return `{"status": "ok", "service": "novaflow-api"}`.
2. **Swagger Docs**: Open `https://novaflow-ai.onrender.com/docs` → Browse interactive OpenAPI documentation.
3. **Frontend Hydration**: Open `https://novaflow-ai.vercel.app` → Register an account and log in.
4. **WebSocket Test**: Open the **Chat** page → Send a prompt → Verify real-time streaming tokens and action card rendering over `wss://novaflow-ai.onrender.com`.
5. **Workflow Execution**: Build a 3-node workflow and click **Run** → Verify execution step logs in **Runs** history.

---

## 9. Troubleshooting & Free-Tier Cold Starts

### Render Free-Tier Sleeping
- **Behavior**: Render free web services spin down after 15 minutes of inactivity. The first incoming request will take ~30–50 seconds to wake up the service.
- **Frontend Handling**: The NovaFlow frontend includes automatic retry interceptors and visual loading indicators while waiting for the backend to wake up.

### Google OAuth `redirect_uri_mismatch`
- In **Google Cloud Console**, add your production callback URL under **Authorized redirect URIs**:
  ```text
  https://novaflow-ai.onrender.com/api/v1/integrations/gmail/oauth/callback
  https://novaflow-ai.onrender.com/api/v1/auth/oauth/google/callback
  ```

---

🎉 **Congratulations! Your NovaFlow AI platform is now live in production at https://novaflow-ai.vercel.app!**
