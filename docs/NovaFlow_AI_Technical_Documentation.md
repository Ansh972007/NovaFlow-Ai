# NovaFlow AI — Enterprise Engineering Specification & Technical Architecture

```
███╗   ██╗ ██████╗ ██╗   ██╗ █████╗ ███████╗██╗      ██████╗ ██╗    ██╗     █████╗ ██╗
████╗  ██║██╔═══██╗██║   ██║██╔══██╗██╔════╝██║     ██╔═══██╗██║    ██║    ██╔══██╗██║
██╔██╗ ██║██║   ██║██║   ██║███████║█████╗  ██║     ██║   ██║██║ █╗ ██║    ███████║██║
██║╚██╗██║██║   ██║╚██╗ ██╔╝██╔══██║██╔══╝  ██║     ██║   ██║██║███╗██║    ██╔══██║██║
██║ ╚████║╚██████╔╝ ╚████╔╝ ██║  ██║██║     ███████╗╚██████╔╝╚███╔███╔╝    ██║  ██║██║
╚═╝  ╚═══╝ ╚═════╝   ╚═══╝  ╚═╝  ╚═╝╚═╝     ╚══════╝ ╚═════╝  ╚══╝╚══╝     ╚═╝  ╚═╝╚═╝
```

---

## Document Control & Metadata

| Specification Attribute | Specification Detail |
| :--- | :--- |
| **System Name** | NovaFlow AI (Enterprise AI Operating System & Automation Fabric) |
| **System Version** | `9.9.0` (Production Kernel Baseline) |
| **Document Classification** | Enterprise Technical Specification & Internal Reference Manual |
| **Target Audience** | Enterprise Architects, Senior Backend/Frontend Engineers, SREs, Security Auditors |
| **Source of Truth** | Production Codebase (`src/`, `backend/app/`, `deploy/`) |
| **Document Status** | Approved & Fully Reconciled with Live Implementation |

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Product Overview & Problem Statement](#2-product-overview--problem-statement)
3. [Core Engineering Goals & Architectural Principles](#3-core-engineering-goals--architectural-principles)
4. [High-Level System Architecture](#4-high-level-system-architecture)
5. [Technology Stack & Dependency Inventory](#5-technology-stack--dependency-inventory)
6. [Repository & Codebase Organization](#6-repository--codebase-organization)
7. [Frontend Architecture (Next.js 16 / React 19)](#7-frontend-architecture-nextjs-16--react-19)
8. [Backend Architecture (FastAPI & Async Kernel)](#8-backend-architecture-fastapi--async-kernel)
9. [Authentication, Security & Cryptography](#9-authentication-security--cryptography)
10. [Multi-Tenancy & Workspace RBAC Architecture](#10-multi-tenancy--workspace-rbac-architecture)
11. [Universal AI Chat & Conversational Subsystem](#11-universal-ai-chat--conversational-subsystem)
12. [AIOS Composer & Autonomous Execution Pipeline](#12-aios-composer--autonomous-execution-pipeline)
13. [Workflow Graph Engine & Node Execution Subsystem](#13-workflow-graph-engine--node-execution-subsystem)
14. [Knowledge Base, Document Ingestion & RAG Subsystem](#14-knowledge-base-document-ingestion--rag-subsystem)
15. [Credential Vault & Secret Management](#15-credential-vault--secret-management)
16. [Omni-Channel Integrations Subsystem](#16-omni-channel-integrations-subsystem)
17. [Telegram Bot & Webhook Gateway](#17-telegram-bot--webhook-gateway)
18. [Agent OS & Autonomous Subagents](#18-agent-os--autonomous-subagents)
19. [Model Lab & LLM Provider Routing](#19-model-lab--llm-provider-routing)
20. [Evaluation, Guardrails & Quality Assurance](#20-evaluation-guardrails--quality-assurance)
21. [REST API Architecture & Comprehensive Endpoint Catalog](#21-rest-api-architecture--comprehensive-endpoint-catalog)
22. [WebSocket Protocols & Real-Time Specifications](#22-websocket-protocols--real-time-specifications)
23. [Database Architecture & Complete Entity-Relationship Model](#23-database-architecture--complete-entity-relationship-model)
24. [Redis Caching, State & Real-Time Presence](#24-redis-caching-state--real-time-presence)
25. [Docker Containerization & Infrastructure Topologies](#25-docker-containerization--infrastructure-topologies)
26. [Environment Variables & Configuration Matrix](#26-environment-variables--configuration-matrix)
27. [Testing, Quality Verification & CI/CD Pipelines](#27-testing-quality-verification--cicd-pipelines)
28. [Error Handling, Fault Tolerance & Self-Healing](#28-error-handling-fault-tolerance--self-healing)
29. [Security Architecture & Audit Trails](#29-security-architecture--audit-trails)
30. [Production Deployment, Reverse Proxies & Tunnels](#30-production-deployment-reverse-proxies--tunnels)
31. [Developer Extension & Node Authoring Guide](#31-developer-extension--node-authoring-guide)
32. [Diagnostic Procedures & Troubleshooting Runbook](#32-diagnostic-procedures--troubleshooting-runbook)
33. [Future Technical Roadmap](#33-future-technical-roadmap)
34. [Conclusion & Engineering Summary](#34-conclusion--engineering-summary)

---

## 1. Executive Summary

NovaFlow AI is an enterprise-grade AI Operating System (AIOS) and autonomous automation platform. It bridges the gap between conversational generative AI, structured graph execution engines, multi-tenant enterprise knowledge management (RAG), encrypted credential vaults, and multi-channel communication protocols.

Unlike conventional chatbots that are restricted to prompt-response text exchanges, NovaFlow AI operates as a unified cognitive execution environment. Through its **AIOS Composer** and **Universal Chat Bridge**, natural language requests are autonomously parsed, planned, synthesized into executable Directed Acyclic Graphs (DAGs), validated against workspace credential gates, tested in ephemeral sandboxes, and deployed directly to production workflows or autonomous background subagents.

---

## 2. Product Overview & Problem Statement

### 2.1 The Enterprise Problem Space
1. **Tooling Fragmentation**: Modern organizations utilize disjointed stacks for conversational chat, automation workflow builders, document search/RAG, and API credential management.
2. **Brittle Prompt Chains**: Traditional generative chat lacks deterministic execution, typed node boundaries, and auditable error recovery.
3. **High Automation Friction**: Translating a business requirement into an automated workflow requires deep visual node programming or custom API code.
4. **Security & Secret Leakage**: Storing third-party tokens (Telegram bots, Slack tokens, SMTP credentials, LLM API keys) across fragmented systems leads to credential exposure.

### 2.2 The NovaFlow AI Solution
NovaFlow AI consolidates these paradigms into a single unified workspace:
- **Universal Chat Interface**: A single terminal where users can converse, compose workflows, trigger executions, query private knowledge, review pending human approvals, and deploy bots.
- **Autonomous AIOS Kernel**: Translates user intents into complete multi-node visual workflows, automatically performs gap analysis on missing API credentials, and constructs verified execution blueprints.
- **Enterprise Graph Execution Engine**: A deterministic topological execution runtime supporting streaming LLMs, custom Python/JavaScript code execution, conditional routing, loops, sub-workflows, and human-in-the-loop pauses.
- **Hybrid RAG & Knowledge Hub**: Multi-file parsing (PDF, Markdown, TXT, CSV), semantic chunking, dual-backend vector storage (Milvus / In-Memory cosine), and retrieval-augmented generation.
- **Zero-Trust Credential Vault**: AES-256-GCM encrypted per-workspace vault with granular permission enforcement and automatic credential resolution for both system providers and end-user accounts.

```mermaid
graph LR
    subgraph "User Interaction"
        A[Universal Chat] --> B[AIOS Engine]
        C[Visual Studio Canvas] --> D[Workflow Graph]
    end
    subgraph "Cognitive Kernel"
        B --> E[Intent Classifier]
        E --> F[Planner & Blueprint]
        F --> D
    end
    subgraph "Execution & Knowledge"
        D --> G[Graph Runtime]
        G --> H[LLM Node Vault]
        G --> I[RAG Knowledge Store]
        G --> J[External Integrations]
    end
```

---

## 3. Core Engineering Goals & Architectural Principles

1. **Source-of-Truth Determinism**: Workflows are stored as declarative JSON graphs with explicit node schemas, typed ports, and deterministic parameter bindings.
2. **Zero-Trust Multi-Tenancy**: Every entity (workflows, credentials, knowledge files, conversation threads, execution logs) is strictly partitioned by `workspace_id` with enforced RBAC (`admin`, `editor`, `viewer`).
3. **Dynamic Protocol Agnosticism**: Workflows can be triggered identically via Web UI, REST API (`/api/v1/workflow/run`), WebSocket stream, Cron schedule, or incoming Webhooks (Telegram, Gmail, GitHub).
4. **Resilient Failover & Offline Capability**: Dual vector backend (Milvus with seamless Fallback Vector engine), dynamic Ngrok/Localhost resolution, and fault-tolerant secret masking ensure uninterrupted service across cloud and on-premise environments.

---

## 4. High-Level System Architecture

The NovaFlow AI platform comprises four decoupled yet tightly integrated tiers:

```mermaid
flowchart TD
    subgraph "Tier 1: Client Layer"
        UI[Next.js 16 / React 19 Single Page App]
        ExtClient[External Clients / Webhook Sources]
    end

    subgraph "Tier 2: API Gateway & Security"
        GW[FastAPI Gateway / Port 3001]
        Trace[TraceMiddleware]
        SecHead[SecurityHeadersMiddleware]
        ErrHand[GlobalErrorHandlerMiddleware]
        CORS[CORS Policy Guard]
    end

    subgraph "Tier 3: Core Service & Kernel Engines"
        ChatWS[Chat WebSocket Router]
        AIOS[AIOS Composer & Kernel]
        WfEngine[Workflow Graph Execution Engine]
        KnowOS[Knowledge OS & RAG Retrieval]
        Vault[Credential Vault & Encryption Service]
        IntSvc[Integrations & Telegram Gateway]
    end

    subgraph "Tier 4: Persistence & Storage Tier"
        MySQL[(MySQL 8.0 / PostgreSQL Relational DB)]
        Redis[(Redis 7.0 Cache & Presence)]
        Milvus[(Milvus Vector DB / SQLite Fallback)]
        DiskStore[(Local Object / File Storage)]
    end

    UI -->|REST / HTTP| GW
    UI -->|WebSocket / WS| ChatWS
    ExtClient -->|Webhooks / REST| GW

    GW --> Trace --> SecHead --> ErrHand --> CORS

    CORS --> AIOS
    CORS --> WfEngine
    CORS --> KnowOS
    CORS --> Vault
    CORS --> IntSvc

    ChatWS <--> AIOS
    AIOS <--> WfEngine
    WfEngine <--> Vault
    WfEngine <--> KnowOS
    WfEngine <--> IntSvc

    WfEngine --> MySQL
    KnowOS --> Milvus
    KnowOS --> DiskStore
    ChatWS --> Redis
    AIOS --> MySQL
    Vault --> MySQL
```

---

## 5. Technology Stack & Dependency Inventory

### 5.1 Frontend Technology Stack
| Package / Framework | Version | Purpose & Architectural Justification |
| :--- | :--- | :--- |
| **Next.js** | `16.2.10` | React App Router framework, SSR layout rendering, zero-config asset bundling. |
| **React & React DOM** | `19.2.4` | Modern component architecture, server/client boundary controls, concurrent hooks. |
| **Tailwind CSS** | `^4.0.0` | Declarative, high-performance styling engine with custom glassmorphism design tokens. |
| **Framer Motion** | `^12.42.2` | Fluid micro-animations, layout transitions, and interactive canvas components. |
| **Axios** | `^1.18.1` | Configurable HTTP client with request/response interceptors for JWT & Workspace headers. |
| **Recharts** | `^3.9.2` | Data visualization for execution analytics, node metrics, and model evaluations. |
| **jsencrypt** | `^3.5.4` | Client-side RSA public key encryption for password transmission during authentication. |
| **ESLint** | `^9.0.0` | Code quality enforcement and strict syntax validation. |

### 5.2 Backend Technology Stack
| Package / Library | Version | Purpose & Architectural Justification |
| :--- | :--- | :--- |
| **FastAPI** | `0.115.6` | High-throughput asynchronous ASGI web framework with OpenAPI validation. |
| **Uvicorn** | `0.32.1` | ASGI web server implementation with standard event loop and protocol workers. |
| **SQLAlchemy** | `2.0.36` | Advanced ORM and SQL toolkit supporting MySQL, PostgreSQL, and SQLite. |
| **PyMySQL** | `1.1.1` | Pure-Python MySQL client library for relational database connectivity. |
| **Cryptography** | `44.0.0` | Enterprise cryptographic primitives (AES-256-GCM, RSA key generation, Fernet). |
| **Python-Jose** | `3.3.0` | Cryptographic JWT token encoding, decoding, and signature verification. |
| **Argon2-cffi** | `23.1.0` | Secure password hashing algorithm conforming to modern OWASP guidelines. |
| **HTTPX** | `0.28.1` | Asynchronous HTTP client with connection pooling for downstream LLM & API dispatch. |
| **PyMilvus** | `2.4.9` | Official Python SDK for Milvus vector database clustering and similarity indexing. |
| **Redis-py** | `5.2.1` | Redis client for presence state, distributed locks, and session streaming. |
| **PyPDF** | `5.1.0` | Document extraction and text mining for enterprise PDF ingestion. |
| **Alembic** | `1.14.0` | Database schema migration tool for relational model versioning. |
| **Pydantic** | `2.10.4` | Data parsing, type validation, and declarative schema models. |
| **PyTest** | `8.3.4` | Automated testing framework for unit, integration, and smoke test suites. |

---

## 6. Repository & Codebase Organization

```
novaflow-ai/
├── backend/                             # Python ASGI Application Kernel
│   ├── alembic/                         # Database Migration Versions & Environment
│   ├── app/                             # Core Application Modules
│   │   ├── agent_os/                    # Autonomous Subagents & Supervisor Kernel
│   │   ├── composer/                    # AIOS Natural Language to Workflow Engine
│   │   ├── connectivity/                # Multi-System Connector Framework & Webhooks
│   │   ├── conversation/                # Thread Persistence, Compaction & Memory
│   │   ├── data/                        # Pluggable Storage & Cache Abstractions
│   │   ├── eiap/                        # Enterprise Integration & App Protocol
│   │   ├── knowledge_os/                # Graph Knowledge & Document Pipeline
│   │   ├── platform/                    # Multi-Tenancy & Workspace Governance
│   │   ├── platform_intelligence/       # OpenTelemetry Distributed Tracing
│   │   ├── routers/                     # REST & WebSocket Route Controllers (30+ Routers)
│   │   ├── runtime/                     # AI Execution Engine & LLM Provider Gateway
│   │   ├── sandbox/                     # Ephemeral Workflow Sandboxing & Verification
│   │   ├── security/                    # Cryptography, Middleware & RBAC Policies
│   │   ├── services/                    # Business Logic, RAG, Integrations & Auth Services
│   │   ├── voice/                       # Audio Transcription & Real-Time Audio Engine
│   │   ├── workflow_intelligence/       # Graph Self-Healing & Anomaly Detectors
│   │   ├── config.py                    # Environment Configuration & Defaults
│   │   ├── crypto.py                    # RSA & AES Cryptographic Utilities
│   │   ├── database.py                  # SQLAlchemy Database Schema & Models
│   │   ├── deps.py                      # Dependency Injection & Token Resolvers
│   │   ├── main.py                      # FastAPI Application Entrypoint & Lifespan
│   │   └── schemas.py                   # Global Pydantic API Response Schemas
│   ├── tests/                           # Complete Test Suites (Smoke, Real Pipeline, APIs)
│   ├── Dockerfile                       # Backend Container Build Definition
│   ├── requirements.txt                 # Exact Production Python Dependencies
│   └── alembic.ini                      # Database Migration Configuration
│
├── src/                                 # Frontend Single Page Application (Next.js 16)
│   ├── app/                             # Next.js App Router Structure
│   │   ├── apps/                        # Published App Catalog & Custom UI Launchers
│   │   ├── chat/                        # Universal AI Chat & AIOS Visual Split Canvas
│   │   ├── credentials/                 # Encrypted Workspace Credential Vault UI
│   │   ├── dashboard/                   # Workspace Analytics, Metrics & System Health
│   │   ├── developer/                   # Developer API Playground & SDK Access
│   │   ├── evaluation/                  # Automated Model & Workflow Benchmark UI
│   │   ├── knowledge/                   # Document Libraries & Vector Indexing UI
│   │   ├── login/                       # Secure RSA-Encrypted Login / Registration
│   │   ├── marketplace/                 # Open Community Workflow & Agent Marketplace
│   │   ├── model-lab/                   # LLM Multi-Model Comparison & Prompt Playground
│   │   ├── projects/                    # Project Spaces & Team Workspace Folders
│   │   ├── runs/                        # Historical Execution Logs & Step Traces
│   │   ├── settings/                    # Workspace Settings, Members & Integrations
│   │   ├── setup/                       # First-Time Admin Wizard & Key Setup
│   │   ├── workflows/                   # Visual ReactFlow Node Canvas & Builder
│   │   ├── globals.css                  # Global Styles, CSS Tokens & Animations
│   │   └── layout.js                    # Root Layout, Theme Provider & Navigation Shell
│   ├── components/                      # Reusable UI Component Library
│   │   ├── chat/                        # ChatSidebar, MessageStream, CardRenderer
│   │   ├── common/                      # Modal, Button, Toast, Input, Badge Components
│   │   ├── layout/                      # AppHeader, WorkspaceSwitcher, SidebarNav
│   │   └── workflow/                    # Visual Graph Canvas, NodePalette, ConfigDrawer
│   ├── hooks/                           # Custom React State & WebSocket Hooks
│   │   ├── useAssistantChat.js          # Chat WebSocket Client & Event Dispatcher
│   │   ├── useAuth.js                   # Authentication & Session Hook
│   │   └── useWorkspace.js              # Active Workspace Context & Role Guard
│   └── lib/                             # Utility & API Client Layer
│       ├── api/                         # Axios REST API Clients (Auth, Workflows, Vault)
│       └── chat/                        # Local Storage Thread History & Message Cache
│
├── deploy/                              # Production Docker & Infrastructure Configurations
├── docs/                                # Technical Architecture & Developer Guides
├── public/                              # Static Brand Assets, Favicons & Vector Icons
├── scripts/                             # Operational & Deployment Automation Scripts
├── docker-compose.yml                   # Complete 5-Service Docker Stack (MySQL, Redis, Milvus, API, Web)
├── package.json                         # Node.js Dependencies & Script Manifest
└── README.md                            # High-Impact Developer & Operational Guide
```

---

## 7. Frontend Architecture (Next.js 16 / React 19)

### 7.1 Architecture & Page Routing
The frontend is constructed using Next.js 16 App Router architecture. It uses Client Components (`"use client"`) for stateful, real-time UI components and dynamic data hydration.

```mermaid
graph TD
    RootLayout[src/app/layout.js] --> NavShell[Top Navigation & Workspace Switcher]
    NavShell --> ChatRoute[src/app/chat/ChatPageClient.js]
    NavShell --> WfRoute[src/app/workflows/WorkflowEditorClient.js]
    NavShell --> KnowRoute[src/app/knowledge/KnowledgeListClient.js]
    NavShell --> CredRoute[src/app/credentials/CredentialsClient.js]
    NavShell --> RunsRoute[src/app/runs/WorkflowRunsClient.js]

    ChatRoute --> useChatHook[src/hooks/useAssistantChat.js]
    useChatHook --> ChatSocket[WebSocket: /api/v1/chat/ws]
    ChatRoute --> ChatSidebar[src/components/chat/ChatSidebar.jsx]
    ChatRoute --> AIOSCardRenderer[AIOS Action & Blueprint Cards]
```

### 7.2 Core Frontend State Modules
- **`useAssistantChat.js`**: Manages real-time bidirectional WebSocket connection (`/api/v1/chat/ws`). Handles streaming LLM chunks, AIOS execution blueprints, interactive human approval cards, and connection retry states.
- **`src/lib/api/axios.js`**: Global Axios instance configured with request interceptors that automatically attach:
  - `Authorization: Bearer <token>`
  - `X-Workspace-Id: <active_workspace_id>`
  - `X-Api-Key: <user_api_key>` (when configured)

---

## 8. Backend Architecture (FastAPI & Async Kernel)

### 8.1 Lifespan & Application Initialization
On startup (`backend/app/main.py`), the ASGI kernel executes a structured lifecycle:
1. Validates JWT secret entropy and verifies production password rules.
2. Initializes database tables via SQLAlchemy declarative models (`init_db()`).
3. Ensures initial Admin account and default personal workspace existence.
4. Auto-seeds default LLM providers (OpenRouter, OpenAI, Anthropic, Gemini, Groq, Ollama) and loads workspace configuration.
5. Initializes vector storage backends and spawns background evaluation schedulers.

### 8.2 Middleware Pipeline Execution Order
```mermaid
sequenceDiagram
    participant Request
    participant Trace as TraceMiddleware
    participant Sec as SecurityHeadersMiddleware
    participant Err as GlobalErrorHandlerMiddleware
    participant CORS as CORSMiddleware
    participant Router as API / WebSocket Router

    Request->>Trace: Incoming HTTP / WS Request
    Trace->>Sec: Inject X-Trace-Id & Start Timing
    Sec->>Err: Apply HSTS, X-Content-Type-Options, CSP
    Err->>CORS: Wrap in Global Exception Handler
    CORS->>Router: Validate Origin & Allowed Headers
    Router-->>Request: Return Standardized JSON / WS Stream
```

---

## 9. Authentication, Security & Cryptography

### 9.1 Authentication Protocols
1. **Password Authentication**:
   - Client fetches RSA public key (`GET /api/v1/auth/public_key`).
   - Client encrypts password using RSA PKCS#1 v1.5 padding before transmission.
   - Server decrypts password via server-side RSA private key and validates hash using **Argon2id** (`argon2-cffi`).
2. **JWT Token Structure**:
   - Access tokens signed via HMAC-SHA256 (`HS256`).
   - Tokens embed `user_id`, `username`, `role`, `workspace_id`, and expiration timestamp (`exp`).
3. **Google SSO & OAuth 2.0**:
   - Full Authorization Code flow with state verification (`/api/v1/auth/oauth/google/start` and callback).
4. **API Key Authentication**:
   - Workspace and user-scoped API keys (`nvf_...`) validated via `X-Api-Key` header with granular scope checks.

---

## 10. Multi-Tenancy & Workspace RBAC Architecture

### 10.1 Workspace Tenancy Model
Every operational entity in NovaFlow AI is partitioned by `workspace_id`.
- **Personal Workspaces**: Automatically created upon user registration.
- **Enterprise Team Workspaces**: Allow multi-user collaboration with explicit RBAC role assignment:
  - **`admin`**: Full administrative rights, workspace settings, integrations, credential vault management, member invitations.
  - **`editor`**: Create, edit, publish, execute workflows, manage knowledge bases, run model evaluations.
  - **`viewer`**: Read-only access to workflows, knowledge bases, and run execution histories.

```mermaid
graph TD
    User[Enterprise User] --> MemberRel[UserWorkspace Role Binding]
    MemberRel --> Workspace[Workspace Context ID]
    Workspace --> WFs[Workflows]
    Workspace --> Vault[Credentials Vault]
    Workspace --> KB[Knowledge Bases]
    Workspace --> Conv[Conversations]
    Workspace --> Runs[Execution Runs]
```

---

## 11. Universal AI Chat & Conversational Subsystem

The Universal Chat system (`src/app/chat/ChatPageClient.js` + `backend/app/routers/chat_ws.py` + `backend/app/composer/chat_bridge.py`) serves as the central command center of NovaFlow AI.

```mermaid
sequenceDiagram
    participant User as Frontend (useAssistantChat)
    participant WS as WebSocket (/api/v1/chat/ws)
    participant Bridge as Chat Bridge (chat_bridge.py)
    participant Kernel as AIOS Kernel (kernel.py)
    participant Runtime as AI Runtime (ai_runtime.py)
    participant DB as MySQL Database

    User->>WS: Send JSON {type: "user_message", text: "Create Slack alerting workflow"}
    WS->>Bridge: bridge_chat_turn(db, user, workspace_id, text)
    Bridge->>Kernel: Classify Intent & Extract Constraints
    Kernel-->>Bridge: Intent = "COMPOSE_WORKFLOW", Generated Blueprint
    Bridge->>Runtime: Synthesize Complete DAG Workflow Graph
    Runtime-->>Bridge: Valid Graph JSON {nodes, edges}
    Bridge->>DB: Save Workflow & Conversation Record
    Bridge-->>WS: Emit Stream Chunk + Action Card {blueprint, actions: ["test", "deploy"]}
    WS-->>User: Render Interactive Canvas & Execution Blueprint Card
```

---

## 12. AIOS Composer & Autonomous Execution Pipeline

### 12.1 Intent Routing & Action Matrix
The AIOS Composer evaluates each incoming message against seven operational modes:

| Intent Category | Identification Heuristic | Downstream Action & Execution Path |
| :--- | :--- | :--- |
| **`COMPOSE_WORKFLOW`** | User requests building, designing, or generating an automated pipeline. | Invokes `aios_planner.py` to create a Solution Blueprint, calls `aios_composer.py` to emit valid ReactFlow nodes and edges, checks for credential gaps, and outputs visual action cards. |
| **`RUN_WORKFLOW`** | User commands running or triggering an existing workflow. | Resolves published workflow ID, maps input variables, dispatches execution via `run_workflow()`, and streams step-by-step progress. |
| **`KNOWLEDGE_QUERY`** | User asks questions referencing private documents or knowledge bases. | Performs semantic vector search via `query_knowledge_base()`, retrieves top chunk passages, and injects context into RAG prompt. |
| **`CREDENTIAL_ACTION`** | User provides API keys, tokens, or asks to connect integrations. | Encrypts secrets into `CredentialVaultEntry` using AES-256-GCM and verifies connection health. |
| **`APPROVAL_RESPONSE`** | User approves/rejects a human-in-the-loop workflow breakpoint. | Resumes suspended execution queue from `WorkflowPendingRun`. |
| **`DIRECT_QA`** | General knowledge inquiry or coding question. | Streams LLM response directly via configured primary provider with conversation memory context. |

---

## 13. Workflow Graph Engine & Node Execution Subsystem

### 13.1 Graph Representation & Node Taxonomy
Workflows are represented as Directed Acyclic Graphs with JSON schema:
```json
{
  "nodes": [
    {"id": "trigger_1", "type": "trigger", "data": {"trigger_type": "webhook"}},
    {"id": "llm_1", "type": "llm", "data": {"prompt": "Analyze input: {{trigger_1.output}}", "model": "gpt-4o"}},
    {"id": "notify_1", "type": "notify", "data": {"channel": "telegram", "message": "{{llm_1.output}}"}}
  ],
  "edges": [
    {"id": "e1-2", "source": "trigger_1", "target": "llm_1"},
    {"id": "e2-3", "source": "llm_1", "target": "notify_1"}
  ]
}
```

### 13.2 Implemented Builtin Node Registry
The workflow execution engine (`backend/app/services/workflow.py`) natively supports:
1. **`trigger`**: Manual trigger, Webhook trigger, Telegram webhook, Cron schedule, Event bus trigger.
2. **`llm`**: Multi-provider generative text generation, prompt templating, dynamic vault credential selector.
3. **`code`**: Secure sandboxed Python/JavaScript execution with input variable mapping.
4. **`condition`**: Logical branching (`equals`, `contains`, `regex`, `greater_than`).
5. **`knowledge` / `retrieval`**: RAG query injection against selected knowledge bases.
6. **`notify`**: Multi-channel message dispatch (Telegram, Email/SMTP, Slack, Discord, Webhook POST).
7. **`human_approval`**: Halts workflow run until authorized by an administrator or chat card action.
8. **`subworkflow`**: Modular nested workflow execution with input/output port bindings.
9. **`output`**: Final response collector and payload formatter.

---

## 14. Knowledge Base, Document Ingestion & RAG Subsystem

### 14.1 Document Ingestion Pipeline
```mermaid
flowchart LR
    Upload[PDF / TXT / MD Upload] --> Extract[Text Extraction / PyPDF]
    Extract --> Chunk[Recursive Character Chunking]
    Chunk --> Embed[Embedding Generator]
    Embed --> Store[(Milvus Vector DB / Cosine Index)]
```

### 14.2 Vector Search & Retrieval
1. Incoming query is embedded using configured embedding model.
2. Similarity search performed across collection filtered by `workspace_id` and `knowledge_base_id`.
3. Top-K chunk contexts concatenated and injected into LLM prompt with provenance citations.

---

## 15. Credential Vault & Secret Management

### 15.1 Encryption Architecture
Secrets (API tokens, bot keys, SMTP passwords) are encrypted using **AES-256-GCM** authenticated encryption:
- Key derivation utilizes master `ENCRYPTION_KEY` configured in server environment.
- Stored payload includes initialization vector (IV), encrypted ciphertext, and authentication tag.
- Decrypted in-memory only during transient execution of downstream API requests.
- All API serialization endpoints mask secrets (e.g. `••••••••`) to prevent client-side credential exposure.

---

## 16. Omni-Channel Integrations Subsystem

| Integration | Supported Transport | Authentication Mechanism | Core Capabilities |
| :--- | :--- | :--- | :--- |
| **Telegram** | Webhook / Long-Polling | Bot Token | Dynamic bidirectional messaging, `/greetings` command handling, public bot chats. |
| **Gmail** | OAuth 2.0 / SMTP | Google OAuth Token / App Password | Automated email generation, LLM digest reports, dynamic subject lines. |
| **Slack** | Incoming Webhook / Bot | Bot User OAuth Token | Channel alerts, interactive notification blocks. |
| **Discord** | Webhook | Webhook URL | Automated channel alerts and formatted embeds. |
| **Jira** | REST API | Email + API Token | Automated issue creation, status updates. |
| **Custom Webhook** | HTTPS POST | HMAC Secret / Bearer Token | Arbitrary external system invocation. |

---

## 17. Telegram Bot & Webhook Gateway

### 17.1 Public Telegram Webhook Architecture
NovaFlow AI features a production Telegram gateway allowing any user to interact with workflows via Telegram bots (e.g., `@Novaflow_text_bot`):

```mermaid
sequenceDiagram
    participant User as Telegram User (Phone)
    participant TG as Telegram Cloud Server
    participant Webhook as NovaFlow Gateway (/api/v1/integrations/telegram/webhook/{id})
    participant WF as Workflow Engine

    User->>TG: Send "/greetings" or "Analyze quarterly sales"
    TG->>Webhook: POST JSON Update (message, chat_id, from)
    Webhook->>Webhook: parse_telegram_input() -> Extract chat_id, user_name
    alt Is /greetings or /start
        Webhook->>TG: Send "Hello {user_name}! 👋 Welcome to NovaFlow AI..."
    end
    Webhook->>WF: Execute Workflow with extra_context={chat_id, user_name}
    WF->>TG: Dispatch Final LLM Output directly to Telegram Chat
    TG-->>User: Display Response on Phone
```

---

## 18. Agent OS & Autonomous Subagents

The Agent OS subsystem (`backend/app/agent_os/`) provides long-running autonomous execution:
- **`SavedAgent` & `AgentRun`**: Models for autonomous worker agents with specialized system prompts and tool access.
- **Checkpointing**: Real-time state preservation in `AgentCheckpoint` for resuming tasks across server restarts.
- **Plan Sessions & Supervision**: Multi-step plan tracking (`AgentPlanSession`) and supervisor verification (`AgentVerificationReport`).

---

## 19. Model Lab & LLM Provider Routing

NovaFlow AI supports dynamic model switching across 6+ providers:
- **OpenRouter** (Unified multi-model access)
- **OpenAI** (GPT-4o, GPT-4o-mini, o1, o3-mini)
- **Anthropic** (Claude 3.5 Sonnet, Claude 3.7 Sonnet)
- **Google Gemini** (Gemini 2.0 Flash, Gemini 1.5 Pro)
- **Groq** (Llama 3.3 70B, DeepSeek R1 Distill)
- **Ollama** (Local self-hosted models)

---

## 20. Evaluation, Guardrails & Quality Assurance

The built-in evaluation framework (`backend/app/routers/evaluation.py` + `backend/app/services/eval_scheduler.py`) provides:
- **Test Suites (`EvalSuite`)**: Sets of test cases with expected outputs and assertions.
- **Automated Regression Runs (`EvalRun`)**: Automated scoring of workflow outputs against benchmarks.
- **Background Cron Evaluation (`EvalSchedule`)**: Scheduled test runs with automatic alerting on score drops.

---

## 21. REST API Architecture & Comprehensive Endpoint Catalog

All REST APIs are served under `/api/v1/`. Key route groups include:

### 21.1 Authentication & User Management (`/auth`, `/user`, `/users`)
- `POST /api/v1/auth/login`: Authenticate user with RSA encrypted password; returns JWT.
- `GET /api/v1/auth/public_key`: Retrieve RSA public key for client-side password encryption.
- `GET /api/v1/auth/me`: Fetch authenticated user profile and active workspace info.
- `GET /api/v1/auth/oauth/google/start`: Initiate Google OAuth SSO.
- `GET /api/v1/auth/oauth/google/callback`: Handle Google OAuth callback and token exchange.
- `GET /api/v1/users`: List workspace users (admin only).
- `POST /api/v1/users`: Create new workspace user.

### 21.2 Workflows & Execution (`/workflow`)
- `GET /api/v1/workflow/list`: List all workflows in active workspace.
- `POST /api/v1/workflow/create`: Create new empty workflow.
- `GET /api/v1/workflow/{id}`: Retrieve workflow details and graph JSON.
- `PUT /api/v1/workflow/{id}`: Update workflow graph nodes, edges, and configuration.
- `POST /api/v1/workflow/{id}/publish`: Publish workflow to production.
- `DELETE /api/v1/workflow/{id}`: Delete workflow.
- `POST /api/v1/workflow/run`: Execute workflow by ID or payload.
- `GET /api/v1/workflow/runs`: List historical execution logs with step details.

### 21.3 Knowledge Bases & RAG (`/knowledge`)
- `GET /api/v1/knowledge/list`: List knowledge bases in workspace.
- `POST /api/v1/knowledge/create`: Create a new knowledge base.
- `POST /api/v1/knowledge/upload/{id}`: Upload and parse document file (PDF, TXT, MD).
- `POST /api/v1/knowledge/query`: Perform semantic similarity search across knowledge base.
- `DELETE /api/v1/knowledge/{id}`: Delete knowledge base, chunks, and disk files.

### 21.4 Credential Vault & Integrations (`/credentials`, `/integrations`)
- `GET /api/v1/credentials`: List masked credentials in active workspace.
- `POST /api/v1/credentials`: Store new encrypted credential entry.
- `DELETE /api/v1/credentials/{id}`: Delete credential entry.
- `GET /api/v1/integrations/health`: Check integration status (Telegram, SMTP, Jira, etc.).
- `POST /api/v1/integrations/telegram/webhook/{workflow_id}`: Public Telegram webhook receiver.

---

## 22. WebSocket Protocols & Real-Time Specifications

### 22.1 Universal Chat WebSocket (`/api/v1/chat/ws`)
- **Connection Handshake**: `ws://<host>/api/v1/chat/ws?token=<jwt_token>&workspace_id=<id>`
- **Client Messages**:
  - `{"type": "user_message", "text": "<prompt>", "session_id": "<id>"}`
  - `{"type": "approve_action", "pending_run_id": 123, "action": "approve"}`
- **Server Events**:
  - `{"type": "chunk", "content": "<streaming text>"}`
  - `{"type": "aios_blueprint", "blueprint": {...}}`
  - `{"type": "card", "card_type": "workflow_created", "data": {...}}`
  - `{"type": "error", "message": "<error details>"}`

---

## 23. Database Architecture & Complete Entity-Relationship Model

```mermaid
erDiagram
    User ||--o{ UserWorkspace : belongs_to
    User ||--o{ Workflow : owns
    User ||--o{ Conversation : owns
    Workspace ||--o{ UserWorkspace : contains
    Workspace ||--o{ Workflow : contains
    Workspace ||--o{ KnowledgeBase : contains
    Workspace ||--o{ CredentialVaultEntry : contains
    Workspace ||--o{ WorkspaceIntegration : contains
    Workflow ||--o{ WorkflowRun : generates
    Workflow ||--o{ WorkflowVersion : versions
    KnowledgeBase ||--o{ KnowledgeFile : contains
    KnowledgeFile ||--o{ KnowledgeChunk : chunks
    Conversation ||--o{ Message : contains
```

---

## 24. Redis Caching, State & Real-Time Presence

Redis 7.0 is utilized for:
1. **Real-time User Presence**: Tracking collaborative workflow editors (`WorkflowPresenceSession`).
2. **WebSocket Session Caching**: Preserving transient stream states and message buffers.
3. **Distributed Rate Limiting**: Throttling public webhook endpoints and API keys.

---

## 25. Docker Containerization & Infrastructure Topologies

### 25.1 Production Docker Compose Architecture (`docker-compose.yml`)
The platform runs as a coordinated 5-container architecture:

```mermaid
graph TD
    subgraph "Docker Network (novaflow-network)"
        Web[novaflow-web: Next.js Port 3000]
        API[novaflow-api: FastAPI Port 3001]
        MySQL[(novaflow-mysql: Port 3306)]
        Redis[(novaflow-redis: Port 6379)]
        Milvus[(novaflow-milvus: Port 19530)]
    end

    Web -->|HTTP / Reverse Proxy| API
    API --> MySQL
    API --> Redis
    API --> Milvus
```

---

## 26. Environment Variables & Configuration Matrix

| Variable Name | Purpose | Example / Default | Mandatory in Production |
| :--- | :--- | :--- | :--- |
| `NOVAFLOW_ENV` | Environment mode (`development` / `production`) | `production` | Yes |
| `DATABASE_URL` | SQLAlchemy relational database connection string | `mysql+pymysql://root:root@novaflow-mysql:3306/novaflow` | Yes |
| `REDIS_URL` | Redis cache and presence connection string | `redis://novaflow-redis:6379/0` | Yes |
| `MILVUS_HOST` | Milvus vector database host | `novaflow-milvus` | Yes |
| `MILVUS_PORT` | Milvus vector database port | `19530` | Yes |
| `JWT_SECRET` | Cryptographic key for signing JWT tokens | `<high-entropy-64-char-hex>` | Yes |
| `ENCRYPTION_KEY` | AES-256-GCM master key for credential vault | `<high-entropy-base64-key>` | Yes |
| `PUBLIC_BASE_URL` | Public HTTPS gateway URL (for webhooks & OAuth) | `https://api.yourdomain.com` | Optional (Auto-resolved) |

---

## 27. Testing, Quality Verification & CI/CD Pipelines

### 27.1 Test Suites (`backend/tests/`)
- `test_smoke.py`: End-to-end sanity tests covering authentication, workspace creation, workflow CRUD, credential storage, and integrations health.
- `test_real_pipeline.py`: Comprehensive live execution verification of the AIOS Composer and node graph execution pipeline.
- `test_chat_aios_bridge.py`: Full simulation of conversational turns, blueprint synthesis, and card emission.

### 27.2 Running Tests
```bash
# Execute backend test suite
cd backend
python -m pytest tests/test_smoke.py -v

# Execute full repository verification
npm run verify
```

---

## 28. Error Handling, Fault Tolerance & Self-Healing

1. **Global Error Handler**: `GlobalErrorHandlerMiddleware` catches all unhandled exceptions, logs full stack traces with unique `Ref: <ID>`, and returns safe RFC 7807 JSON error responses.
2. **Vector Store Fallback**: If Milvus is unreachable, the system automatically falls back to the internal In-Memory Cosine Vector engine without crashing running workflows.
3. **Dynamic Public URL Resolution**: Integrations automatically detect live Ngrok tunnels or fall back cleanly to `http://localhost:3001` when offline.

---

## 29. Security Architecture & Audit Trails

- **Zero Unencrypted Passwords**: Argon2id hashing with secure salts.
- **Zero Raw Secrets in Logs**: All tokens and API keys are automatically stripped or masked before log emission.
- **Audit Logging**: All credential mutations, permission updates, and login attempts are permanently recorded in `SecurityAuditLog`.

---

## 30. Production Deployment, Reverse Proxies & Tunnels

For production deployments behind Nginx or Cloudflare:
```nginx
server {
    server_name novaflow.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:3001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /api/v1/chat/ws {
        proxy_pass http://127.0.0.1:3001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "Upgrade";
    }
}
```

---

## 31. Developer Extension & Node Authoring Guide

To add a new custom node type to the Workflow Engine:
1. Define the node schema in `backend/app/services/node_registry.py`.
2. Implement execution logic in `backend/app/services/workflow.py` (`_execute_single_node`).
3. Add custom frontend icon and port configuration in `src/components/workflow/`.

---

## 32. Diagnostic Procedures & Troubleshooting Runbook

| Symptom | Probable Cause | Corrective Action |
| :--- | :--- | :--- |
| **`Error 400: redirect_uri_mismatch`** | Google Cloud Console missing authorized callback URL. | Add `http://localhost:3001/api/v1/integrations/gmail/oauth/callback` and `.../auth/oauth/google/callback` to Authorized Redirect URIs in Google Cloud Console. |
| **`500 Internal Server Error` on Webhook** | Invalid parameter format or missing bot token. | Verify bot token in Credentials page and review `docker logs novaflow-api --tail 50`. |
| **Milvus Connection Refused** | Milvus standalone container starting up or unhealthy. | System automatically operates in fallback vector mode; restart via `docker compose restart novaflow-milvus`. |

---

## 33. Future Technical Roadmap

1. **Distributed Multi-Agent Consensus**: Swarm intelligence for multi-agent competitive debate and consensus voting.
2. **Native WASM Code Execution**: In-browser and serverless WebAssembly execution for ultra-fast, sandbox-isolated code nodes.
3. **Fine-Tuning Data Loop**: Automated curation of production workflow execution traces into LoRA fine-tuning datasets.

---

## 34. Conclusion & Engineering Summary

NovaFlow AI delivers a complete, production-verified, enterprise-grade AI Operating System. By unifying natural language intent synthesis, visual graph programming, encrypted credential governance, hybrid RAG knowledge retrieval, and multi-channel messaging protocols, it establishes a reliable and scalable foundation for enterprise AI automation.
