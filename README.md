<div align="center">

# ⚡ NovaFlow AI

### *Enterprise AI Operating System, Autonomous Workflow Fabric & Knowledge Engine*

[![Production Ready](https://img.shields.io/badge/status-production--ready-00C853?style=for-the-badge&logo=shield)](https://github.com/Ansh972007/NovaFlow-Ai)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.6-009688?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-16.2.10-black?style=for-the-badge&logo=next.js)](https://nextjs.org/)
[![React](https://img.shields.io/badge/React-19.2.4-61DAFB?style=for-the-badge&logo=react)](https://react.dev/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker)](https://www.docker.com/)
[![Milvus](https://img.shields.io/badge/Milvus-2.4.9-00B0FF?style=for-the-badge&logo=redis)](https://milvus.io/)
[![License](https://img.shields.io/badge/license-MIT-blue?style=for-the-badge)](LICENSE)

<br/>

**Build, automate, orchestrate, and deploy production AI agents and multi-node workflows from a single unified enterprise workspace.**

[Explore Architecture](#-system-architecture) • [Key Features](#-key-features) • [Quickstart Guide](#-quickstart--installation) • [REST API Catalog](#-rest-api-overview) • [Technical Documentation](docs/NovaFlow_AI_Technical_Documentation.md)

</div>

---

## 📖 Table of Contents

- [Overview & Vision](#-overview--vision)
- [Why NovaFlow AI?](#-why-novaflow-ai)
- [System Architecture](#-system-architecture)
- [Key Features](#-key-features)
- [Tech Stack & Dependencies](#-tech-stack--dependencies)
- [Universal AI Chat & AIOS Composer](#-universal-ai-chat--aios-composer)
- [Workflow Execution Engine](#-workflow-execution-engine)
- [Knowledge Base & RAG Pipeline](#-knowledge-base--rag-pipeline)
- [Zero-Trust Credential Vault](#-zero-trust-credential-vault)
- [Omni-Channel Integrations & Telegram Gateway](#-omni-channel-integrations--telegram-gateway)
- [Authentication & Multi-Tenancy (RBAC)](#-authentication--multi-tenancy-rbac)
- [REST API Overview](#-rest-api-overview)
- [WebSocket Protocols](#-websocket-protocols)
- [Database Schema & ER Model](#-database-schema--er-model)
- [Quickstart & Installation](#-quickstart--installation)
- [Configuration & Environment Variables](#-configuration--environment-variables)
- [Testing & Quality Verification](#-testing--quality-verification)
- [Troubleshooting Runbook](#-troubleshooting-runbook)
- [Future Roadmap](#-future-roadmap)
- [License & Authors](#-license--authors)

---

## 🌟 Overview & Vision

**NovaFlow AI** is a comprehensive, enterprise-grade AI Operating System (AIOS) designed to bridge the gap between conversational AI, deterministic graph automation, multi-tenant document intelligence (RAG), and secure multi-channel integrations.

Traditional AI platforms force teams into siloed tools: one platform for prompt chat, another for visual workflow building, a third for vector search, and custom code for third-party bots. **NovaFlow AI consolidates these into a unified cognitive execution environment.**

```mermaid
graph LR
    subgraph "Unified Input"
        A[Universal Natural Language Chat]
        B[Visual Graph Studio]
        C[Telegram / Slack / Webhook Inbound]
    end

    subgraph "NovaFlow Cognitive Kernel"
        D[AIOS Intent Classifier]
        E[Autonomous Workflow Composer]
        F[Graph Execution Engine]
        G[RAG Knowledge Store]
        H[AES-256 Encrypted Vault]
    end

    subgraph "Automated Action"
        I[Live Webhook Execution]
        J[Gmail & Telegram Notification]
        K[LLM Provider Routing]
        L[Database & API Actions]
    end

    A --> D --> E --> F
    B --> F
    C --> F
    F --> G
    F --> H
    F --> I
    F --> J
    F --> K
    F --> L
```

---

## 💡 Why NovaFlow AI?

| Capability | Basic AI Chatbots | Traditional Workflow Builders | NovaFlow AI Platform |
| :--- | :---: | :---: | :---: |
| **Conversational Intelligence** | ✅ | ❌ | ✅ **Real-Time Streaming + Memory** |
| **Autonomous Workflow Synthesis** | ❌ | ❌ | ✅ **Natural Language to Visual DAGs** |
| **Encrypted Credential Vault** | ❌ | ⚠️ (Plaintext / Basic) | ✅ **AES-256-GCM + RBAC Partitioned** |
| **Omni-Channel Webhook Gateway** | ❌ | ⚠️ (Complex Setup) | ✅ **Built-in Telegram, Gmail, Slack** |
| **Hybrid Document RAG** | ⚠️ (Single File) | ❌ | ✅ **Milvus + In-Memory Fallback Vector Engine** |
| **Human-in-the-Loop Pauses** | ❌ | ⚠️ (Polling-based) | ✅ **Native WebSocket Action Cards** |
| **Zero-Trust Multi-Tenancy** | ❌ | ⚠️ (Add-on) | ✅ **Workspace-Scoped RBAC Built-in** |

---

## 🏗️ System Architecture

NovaFlow AI is architected as a high-throughput, microservice-ready Docker stack:

```mermaid
flowchart TD
    subgraph "Client Tier"
        UI["Next.js 16 / React 19 SPA (Port 3000)"]
        TG["Telegram Public Users / External Clients"]
    end

    subgraph "Gateway & Middleware Tier"
        API["FastAPI ASGI Kernel (Port 3001)"]
        Trace["TraceMiddleware (OpenTelemetry Spans)"]
        SecHead["SecurityHeadersMiddleware (HSTS, CSP)"]
        ErrGuard["GlobalErrorHandlerMiddleware"]
        CORS["Strict CORS Policy Guard"]
    end

    subgraph "Core Execution Engines"
        ChatWS["Chat WebSocket Router (/chat/ws)"]
        AIOS["AIOS Composer & Kernel"]
        GraphEngine["Workflow Graph Engine"]
        RAG["Knowledge OS & Vector Ingestion"]
        Vault["Credential Vault & Encryption"]
        IntGateway["Integrations & Webhook Router"]
    end

    subgraph "Persistence & Infrastructure Tier"
        MySQL[("MySQL 8.0 Relational DB")]
        Redis[("Redis 7.0 Cache & Presence")]
        Milvus[("Milvus 2.4.9 Vector DB")]
        Disk[("Local / Object Document Storage")]
    end

    UI -->|REST & WebSocket| API
    TG -->|Public HTTPS Webhooks| API

    API --> Trace --> SecHead --> ErrGuard --> CORS

    CORS --> ChatWS
    CORS --> AIOS
    CORS --> GraphEngine
    CORS --> RAG
    CORS --> Vault
    CORS --> IntGateway

    ChatWS <--> AIOS
    AIOS <--> GraphEngine
    GraphEngine <--> Vault
    GraphEngine <--> RAG
    GraphEngine <--> IntGateway

    GraphEngine --> MySQL
    AIOS --> MySQL
    Vault --> MySQL
    RAG --> Milvus
    RAG --> Disk
    ChatWS --> Redis
```

---

## ✨ Key Features

### 1. 💬 Universal AI Chat & AIOS Composer
- Real-time bi-directional streaming over WebSockets (`/api/v1/chat/ws`).
- **Autonomous Intent Classification**: Distinguishes between General Q&A, Workflow Generation, Workflow Execution, Knowledge Retrieval, and Credential Provisioning.
- **Visual Action Cards**: Automatically generates interactive UI cards for workflow creation, testing, execution blueprints, and human authorization.

### 2. ⚡ Visual Workflow Studio & Graph Execution Engine
- Full drag-and-drop node graph canvas powered by ReactFlow.
- Deterministic topological graph traversal with support for sequential steps, parallel branches, and conditional routing.
- Comprehensive node taxonomy: `trigger`, `llm`, `code`, `condition`, `knowledge`, `notify`, `human_approval`, `subworkflow`, `output`.

### 3. 📚 Knowledge Base & Hybrid RAG Subsystem
- Automated document ingestion supporting PDF, Markdown, Plaintext, and CSV.
- Semantic chunking with recursive sliding windows and chunk hash deduplication.
- Dual-engine vector storage: **Milvus Vector DB** for high-scale enterprise deployments with automatic fallback to internal In-Memory Cosine Vector indexing.

### 4. 🔐 Zero-Trust Credential Vault
- **AES-256-GCM** authenticated encryption for API keys, bot tokens, and OAuth secrets.
- Dynamic credential resolution: Workflows can select vault keys directly via UI dropdowns or resolve active system providers.
- Strict workspace-level isolation preventing cross-tenant secret leakage.

### 5. 🤖 Omni-Channel Integrations & Public Telegram Gateway
- **Telegram Bot Webhook**: Built-in webhook handler supporting public bots (e.g. `@Novaflow_text_bot`), dynamic sender extraction, and custom command actions (e.g. `/greetings`).
- **Gmail / Email Integration**: Automated email digest generation, dynamic subject lines, and Google OAuth 2.0 / SMTP support.
- **Slack, Discord & Jira**: Webhook alerting and automated ticket dispatch.

### 6. 👥 Enterprise Multi-Tenancy & RBAC
- Personal and team workspace partitioning.
- Granular Role-Based Access Control (`admin`, `editor`, `viewer`).
- RSA client-side encrypted password transmission and Argon2id secure password hashing.

---

## 🛠️ Tech Stack & Dependencies

### Frontend Architecture
| Package / Dependency | Version | Purpose |
| :--- | :--- | :--- |
| **Next.js** | `16.2.10` | React App Router, SSR layouts, optimized asset pipeline. |
| **React & React DOM** | `19.2.4` | Modern component architecture, server/client boundaries. |
| **Tailwind CSS** | `^4.0.0` | Declarative responsive styling and glassmorphism design tokens. |
| **Framer Motion** | `^12.42.2` | Fluid UI animations, canvas interactions, and drawer transitions. |
| **Axios** | `^1.18.1` | REST client with automatic JWT & Workspace interceptors. |
| **Recharts** | `^3.9.2` | Interactive charts for execution metrics and analytics. |
| **jsencrypt** | `^3.5.4` | RSA public-key encryption for secure password submission. |

### Backend Architecture
| Package / Dependency | Version | Purpose |
| :--- | :--- | :--- |
| **FastAPI** | `0.115.6` | Asynchronous ASGI web framework and OpenAPI contract generator. |
| **Uvicorn** | `0.32.1` | ASGI production server with high-concurrency event loops. |
| **SQLAlchemy** | `2.0.36` | Advanced relational ORM supporting MySQL, PostgreSQL, SQLite. |
| **PyMySQL** | `1.1.1` | Pure-Python MySQL connector. |
| **Cryptography** | `44.0.0` | AES-256-GCM, RSA keypair generation, and cryptographic hashing. |
| **Python-Jose** | `3.3.0` | JWT encoding, decoding, and signature validation. |
| **Argon2-cffi** | `23.1.0` | State-of-the-art secure password hashing. |
| **HTTPX** | `0.28.1` | Asynchronous HTTP client with connection pooling. |
| **PyMilvus** | `2.4.9` | Vector similarity indexing and Milvus cluster client. |
| **Redis-py** | `5.2.1` | Redis caching, user presence tracking, and stream buffering. |
| **PyPDF** | `5.1.0` | Enterprise document text parsing and chunking. |
| **Pydantic** | `2.10.4` | Type validation, schema serialization, and request validation. |
| **PyTest** | `8.3.4` | Automated test suite execution. |

---

## 💬 Universal AI Chat & AIOS Composer

The Universal Chat system (`src/app/chat/ChatPageClient.js`) connects to `/api/v1/chat/ws` to provide a unified conversational terminal.

```mermaid
sequenceDiagram
    participant User as User / Frontend
    participant WS as /api/v1/chat/ws
    participant Bridge as Chat Bridge (chat_bridge.py)
    participant AIOS as AIOS Kernel (kernel.py)
    participant Runtime as AI Runtime (ai_runtime.py)
    participant Engine as Workflow Engine

    User->>WS: "Build a workflow to analyze support emails and alert on Telegram"
    WS->>Bridge: bridge_chat_turn()
    Bridge->>AIOS: Classify Intent -> "COMPOSE_WORKFLOW"
    AIOS->>Runtime: Synthesize Solution Blueprint & ReactFlow DAG
    Runtime-->>Bridge: Valid Graph JSON {nodes, edges}
    Bridge-->>WS: Stream response + Emit Blueprint Action Card
    WS-->>User: Display interactive card with "Test" & "Deploy" buttons
    User->>WS: Click "Deploy"
    WS->>Engine: Publish Workflow to Workspace
    Engine-->>WS: Workflow Live & Webhook Registered
```

---

## ⚡ Workflow Execution Engine

Workflows are executed deterministically through `run_workflow()` in `backend/app/services/workflow.py`:

```mermaid
flowchart LR
    Trigger[Trigger Node: Webhook / Cron / Manual] --> Context[Initialize Execution Context]
    Context --> LLM[LLM Node: Template Prompt + Vault Credential]
    LLM --> Branch{Condition Node}
    Branch -->|True| Notify[Notify Node: Telegram / Email]
    Branch -->|False| Fallback[Code / Fallback Node]
    Notify --> Output[Output Node: Return Final JSON Response]
    Fallback --> Output
```

- **Variable Resolution**: Supports dynamic Jinja-style parameter templating (e.g. `{{trigger.output}}`, `{{llm.output}}`, `{{user_name}}`, `{{chat_id}}`).
- **Human-in-the-Loop**: Halts execution state in `WorkflowPendingRun` until an authorized user sends an approval token.
- **Trace Observability**: Emits detailed step logs with execution latency (`duration_ms`), status (`ok` / `error`), and trace IDs.

---

## 📚 Knowledge Base & RAG Pipeline

NovaFlow AI features an enterprise document ingestion and semantic retrieval subsystem:

1. **Document Ingestion**: Upload PDF, Markdown, TXT, or CSV files via `POST /api/v1/knowledge/upload/{id}`.
2. **Text Extraction & Chunking**: Extracts text using `pypdf`, strips control characters, and performs recursive chunking with configurable overlap.
3. **Vector Indexing**: Emits embedding vectors into **Milvus 2.4.9** collections filtered by `workspace_id`.
4. **Resilient Fallback**: If Milvus is unavailable, seamlessly indexes into memory for uninterrupted cosine similarity querying.

---

## 🔐 Zero-Trust Credential Vault

All sensitive third-party tokens are stored in the `CredentialVaultEntry` table using **AES-256-GCM authenticated encryption**:

- **Masked API Responses**: Client endpoints always mask secret values (e.g. `••••••••`) to ensure tokens are never exposed in browser devtools.
- **Granular Node Binding**: Workflow nodes (e.g. LLM Node, Notify Node) bind to vault credentials via `credential_id`, automatically decrypting in-memory only during transient HTTP requests.
- **Workspace Isolation**: Credentials cannot be accessed across workspace boundaries.

---

## 🤖 Omni-Channel Integrations & Telegram Gateway

NovaFlow AI includes built-in integrations with zero third-party middleware:

### Telegram Public Gateway
- Any user on any mobile device can message your Telegram bot (e.g., `@Novaflow_text_bot`).
- Incoming updates are parsed by `parse_telegram_input()`, resolving `chat_id`, `user_name`, and message `text`.
- **Command Handling**: Sending `/greetings` or `/start` generates an instant personalized welcome:
  > *"Hello Ansh! 👋 Welcome to NovaFlow AI. How can I assist you today?"*
- Workflows automatically receive `{{user_name}}` and `{{chat_id}}` in their execution context to reply directly to the sender.

### Gmail & SMTP
- Dynamic OAuth 2.0 Authorization Code flow with Google Cloud Console.
- Dynamic fallback to Localhost (`http://localhost:3001`) or live Ngrok HTTPS tunnels.
- Automated email digests with AI-generated dynamic subjects.

---

## 👥 Authentication & Multi-Tenancy (RBAC)

### User Authentication Lifecycle
1. **Client-Side RSA Encryption**: The frontend fetches the public key from `GET /api/v1/auth/public_key` and encrypts the user's password prior to transmission.
2. **Argon2id Password Hashing**: The backend decrypts the password and verifies it against salted Argon2id hashes.
3. **JWT Access Tokens**: Issues signed HS256 JWT tokens embedding `user_id`, `role`, and active `workspace_id`.

### Role-Based Access Control (RBAC)
- **`admin`**: Workspace management, integration configuration, member management, credential creation.
- **`editor`**: Workflow authoring, knowledge indexing, model testing, workflow publishing.
- **`viewer`**: Read-only view of workflows, knowledge bases, and execution traces.

---

## 🌐 REST API Overview

All API endpoints are served under `/api/v1/`:

| API Group | Method | Endpoint | Description |
| :--- | :---: | :--- | :--- |
| **Auth** | `POST` | `/api/v1/auth/login` | Authenticate user with RSA encrypted password. |
| **Auth** | `GET` | `/api/v1/auth/public_key` | Fetch RSA public key for password encryption. |
| **Auth** | `GET` | `/api/v1/auth/oauth/google/start` | Initiate Google OAuth SSO. |
| **Workflows** | `GET` | `/api/v1/workflow/list` | List all workflows in the active workspace. |
| **Workflows** | `POST` | `/api/v1/workflow/create` | Create a new workflow canvas. |
| **Workflows** | `POST` | `/api/v1/workflow/run` | Execute a workflow by ID or payload. |
| **Workflows** | `GET` | `/api/v1/workflow/runs` | Retrieve execution run history and step logs. |
| **Knowledge** | `GET` | `/api/v1/knowledge/list` | List knowledge bases in workspace. |
| **Knowledge** | `POST` | `/api/v1/knowledge/upload/{id}` | Upload and parse document file. |
| **Knowledge** | `POST` | `/api/v1/knowledge/query` | Semantic vector query against knowledge base. |
| **Credentials** | `GET` | `/api/v1/credentials` | List masked credentials in vault. |
| **Credentials** | `POST` | `/api/v1/credentials` | Add new encrypted credential entry. |
| **Integrations** | `GET` | `/api/v1/integrations/health` | Check status of Telegram, SMTP, and OAuth. |
| **Integrations** | `POST` | `/api/v1/integrations/telegram/webhook/{id}` | Public Telegram webhook receiver. |

---

## 🔌 WebSocket Protocols

### Universal Chat WebSocket (`/api/v1/chat/ws`)
- **URL**: `ws://<host>:3001/api/v1/chat/ws?token=<jwt_token>&workspace_id=<id>`
- **Client → Server Frame**:
  ```json
  {
    "type": "user_message",
    "text": "Create an automated customer inquiry workflow",
    "session_id": "session_123"
  }
  ```
- **Server → Client Frames**:
  - `chunk`: Streaming LLM response token.
  - `aios_blueprint`: Complete workflow plan and step blueprint.
  - `card`: Interactive visual card (`workflow_created`, `approval_request`).
  - `error`: Formatted error message.

---

## 🗄️ Database Schema & ER Model

```mermaid
erDiagram
    User ||--o{ UserWorkspace : belongs_to
    User ||--o{ Workflow : creates
    User ||--o{ Conversation : initiates
    Workspace ||--o{ UserWorkspace : contains
    Workspace ||--o{ Workflow : contains
    Workspace ||--o{ KnowledgeBase : contains
    Workspace ||--o{ CredentialVaultEntry : contains
    Workspace ||--o{ WorkspaceIntegration : contains
    Workflow ||--o{ WorkflowRun : executes
    Workflow ||--o{ WorkflowVersion : versions
    KnowledgeBase ||--o{ KnowledgeFile : stores
    KnowledgeFile ||--o{ KnowledgeChunk : indexes
    Conversation ||--o{ Message : stores
```

---

## 🚀 Quickstart & Installation

### Prerequisites
- [Docker & Docker Compose](https://www.docker.com/) (Recommended)
- Node.js `v20+` & Python `3.11+` (For native local development)
- Git

### 1. Clone the Repository
```bash
git clone https://github.com/Ansh972007/NovaFlow-Ai.git
cd NovaFlow-Ai
```

### 2. Docker One-Command Deployment (Recommended)
```bash
# 1. Create environment configuration from template
cp .env.example .env

# 2. Build and start all 5 services
docker compose up -d --build
```

Access the services:
- 🌐 **Frontend Application**: `http://localhost:3000`
- ⚙️ **Backend API Gateway**: `http://localhost:3001`
- 📑 **OpenAPI Swagger Docs**: `http://localhost:3001/docs`

---

## ⚙️ Configuration & Environment Variables

Key configuration variables in `.env`:

```env
# Application Environment
NOVAFLOW_ENV=production
ADMIN_USER=admin
ADMIN_PASSWORD=YourStrongAdminPassword123!

# Relational Database (MySQL)
DATABASE_URL=mysql+pymysql://root:root@novaflow-mysql:3306/novaflow

# Redis Cache
REDIS_URL=redis://novaflow-redis:6379/0

# Milvus Vector Database
MILVUS_HOST=novaflow-milvus
MILVUS_PORT=19530

# Cryptography & Security
JWT_SECRET=generate_a_secure_64_character_hex_string_for_production
ENCRYPTION_KEY=generate_a_secure_base64_encryption_key_for_vault

# Optional Public Gateway (for Telegram Webhooks & Google OAuth)
PUBLIC_BASE_URL=
```

---

## 🧪 Testing & Quality Verification

NovaFlow AI maintains rigorous automated test suites covering smoke tests, real execution pipelines, and API contracts:

```bash
# Run backend smoke tests
cd backend
python -m pytest tests/test_smoke.py -v

# Run real pipeline execution tests
python -m pytest tests/test_real_pipeline.py -v

# Run full project verification (Lint + Backend Tests)
cd ..
npm run verify
```

---

## 🔧 Troubleshooting Runbook

| Error / Symptom | Root Cause | Solution |
| :--- | :--- | :--- |
| **`Error 400: redirect_uri_mismatch`** (Google OAuth) | Google Cloud Console missing exact callback URL. | Add `http://localhost:3001/api/v1/integrations/gmail/oauth/callback` and `.../auth/oauth/google/callback` to **Authorized redirect URIs** in Google Cloud Console. |
| **`Telegram 500 Internal Server Error`** | Webhook parameter order mismatch or invalid bot token. | Verify bot token in Credentials page. Update is handled automatically in `v9.9.0`. |
| **`Milvus Connection Refused`** | Milvus container initializing or memory limit reached. | The system automatically operates in In-Memory Fallback mode. Check status with `docker compose ps`. |

---

## 🗺️ Future Roadmap

- [ ] **Multi-Agent Swarm Debate**: Autonomous multi-agent consensus voting on complex coding and analytical tasks.
- [ ] **WASM Sandboxed Execution**: In-browser WebAssembly execution for ultra-fast, zero-overhead code nodes.
- [ ] **Fine-Tuning Flywheel**: Direct conversion of production execution traces into instruction-tuning datasets.

---

## 📄 License & Authors

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

Developed with ❤️ by **[Ansh Vekariya](https://github.com/Ansh972007)** and the NovaFlow AI Engineering Team.
