# NovaFlow Enterprise Master Manual Testing Guide
## Production User Acceptance Testing (UAT) & QA Manual

This document is the official testing manual for the NovaFlow platform. It provides step-by-step instructions for QA Engineers, Beta Testers, Developers, and Product Managers to verify the entire platform before public release.

---

## Table of Contents
1. [Introduction](#1-introduction)
2. [Testing Rules & Protocol](#2-testing-rules--protocol)
3. [Testing Environment Setup](#3-testing-environment-setup)
4. [Required Accounts & API Keys](#4-required-accounts--api-keys)
5. [Required Sample Test Data](#5-required-sample-test-data)
6. [Master Testing Checklist](#6-master-testing-checklist)
7. [Page-by-Page Manual Testing](#7-page-by-page-manual-testing)
    - [7.1. Landing & Authentication Pages](#71-landing--authentication-pages)
    - [7.2. Main Dashboard](#72-main-dashboard)
    - [7.3. Workflow Builder](#73-workflow-builder)
    - [7.4. Marketplace & Integration Catalog](#74-marketplace--integration-catalog)
    - [7.5. Knowledge Management](#75-knowledge-management)
    - [7.6. Conversational Chat Client](#76-conversational-chat-client)
    - [7.7. Voice Assistant Lab](#77-voice-assistant-lab)
    - [7.8. Model Benchmarking Lab](#78-model-benchmarking-lab)
    - [7.9. Evaluation Arena](#79-evaluation-arena)
    - [7.10. Settings & Workspaces](#710-settings--workspaces)
    - [7.11. Notifications Widget & Center](#711-notifications-widget--center)
8. [Module-Specific Testing](#8-module-specific-testing)
    - [8.1. Workflow Builder Execution](#81-workflow-builder-execution)
    - [8.2. Voice AI & Streaming Telephony](#82-voice-ai--streaming-telephony)
    - [8.3. Knowledge RAG Pipeline](#83-knowledge-rag-pipeline)
    - [8.4. Third-Party Connectors](#84-third-party-connectors)
9. [Non-Functional Testing](#9-non-functional-testing)
    - [9.1. Security & Isolation (RBAC/Multi-Tenant)](#91-security--isolation-rbacmulti-tenant)
    - [9.2. Performance & Stress Testing](#92-performance--stress-testing)
    - [9.3. Cross-Browser & Mobile Responsiveness](#93-cross-browser--mobile-responsiveness)
    - [9.4. Accessibility (WCAG 2.1 AA)](#94-accessibility-wcag-21-aa)
10. [End-to-End User Journeys](#10-end-to-end-user-journeys)
11. [Final Production Certification](#11-final-production-certification)
    - [11.1. Go-Live Checklists](#111-go-live-checklists)
    - [11.2. Defect Severity & Classification](#112-defect-severity--classification)
    - [11.3. QA Sign-off Template](#113-qa-sign-off-template)

---

## 1. Introduction
NovaFlow is an enterprise-grade AI automation platform that combines multi-agent orchestration, Retrieval-Augmented Generation (RAG) knowledge management, voice assistants, and dynamic workflow building. This testing handbook covers every component, route, database state mutation, and WebSocket event within the application.

---

## 2. Testing Rules & Protocol
1. **Zero Assumption Policy**: Every test case must be executed exactly as written.
2. **State Hygiene**: Reset the application state or register a new workspace/tenant before running integration tests.
3. **Log Monitoring**: Keep terminal panels running `docker compose logs -f api` and browser DevTools open to capture issues instantly.
4. **Data Privacy**: Never use production credentials, real client secrets, or private keys during testing. Use the mock data provided in this guide.

---

## 3. Testing Environment Setup
Before beginning, verify that the local or staging environment matches this configuration:
* **Operating Systems**: Windows 11, macOS Sequoia, or Ubuntu 22.04 LTS
* **Required Software**: Docker Desktop (Engine 24.0.0+), Docker Compose (v2.20.0+)
* **Browsers**: Google Chrome (v120+), Mozilla Firefox (v120+), Apple Safari (v17+), Microsoft Edge (v120+)
* **Screen Resolutions**: Desktop (1920x1080), Tablet (1024x768), Mobile (375x812)
* **Default Services ports**:
    * Frontend React/Next.js: `http://localhost:3000`
    * Backend FastAPI: `http://localhost:3001`
    * MySQL Database: Port `3306`
    * Redis Queue & Cache: Port `6379`
    * Milvus Vector DB: Port `19530`

---

## 4. Required Accounts & API Keys

| Provider | Purpose | How to Obtain | Where to Configure | Verification Action |
|---|---|---|---|---|
| **OpenRouter** | Main LLM API router | Register at openrouter.ai, generate a test key. | Settings -> Model Providers | Run Model Test connection check. |
| **OpenAI** | Alternative API fallback | Create developer account at platform.openai.com | Settings -> Model Providers | Test text completion stream in Model Lab. |
| **Google Console** | Google Drive Connector | Create project on Google Cloud, configure OAuth. | Settings -> Credentials | Authenticate OAuth flow on Connector tab. |
| **AWS S3** | Object storage test | Create IAM user, grant S3 write/read policies. | Settings -> Credentials | Upload a PDF to Knowledge. |
| **SMTP Server** | Email system testing | Use Mailtrap.io API or local dummy SMTP server. | backend/app/config.py | Click "Send Test Notification Email". |

---

## 5. Required Sample Test Data

* **Test User Accounts**:
    * `enterprise_admin@novaflow.test` / `Password123!` (Owner)
    * `editor_user@novaflow.test` / `Password123!` (Editor)
    * `viewer_user@novaflow.test` / `Password123!` (Viewer)
* **Sample Files**:
    * `valid_doc.md`: Standard markdown document (20KB, UTF-8 encoded text).
    * `scanned_ocr.jpg`: Image containing typed text to test OCR ingestion.
    * `oversized_data.pdf`: PDF file larger than 100MB to test upload limits.
    * `corrupt_doc.docx`: File with modified bytes to test error handling.

---

## 6. Master Testing Checklist

- [ ] Verify User Registration, Login, and Multi-Factor Authentication.
- [ ] Verify Workspace creation and RBAC permissions (Owner vs Editor vs Viewer).
- [ ] Verify Background document processing (FastAPI `BackgroundTasks`).
- [ ] Verify Assistant RAG System Note and document name list awareness.
- [ ] Verify Workflow Builder canvas (Adding nodes, linking edges, saving layout).
- [ ] Verify Real-time Notifications widget over WebSockets.
- [ ] Verify Voice AI streaming and failover.

---

## 7. Page-by-Page Manual Testing

### 7.1. Landing & Authentication Pages

#### Test Case Auth-001: User Registration
* **Purpose**: Verify a new user can sign up for a tenant account.
* **Preconditions**: Staging instance is clean. Database is running.
* **Step-by-Step Actions**:
    1. Navigate to `http://localhost:3000/register`.
    2. Enter name `QA Lead`, email `qa_lead@novaflow.test`, password `Password123!`.
    3. Click "Submit".
* **Expected UI**: "Verification email sent" toast displays. Directs user to validation page.
* **Expected Backend Behaviour**: Returns `200 OK` from `/api/v1/auth/register`. Enqueues confirmation email.
* **Expected Database Behaviour**: A new row is inserted into the `users` table with status `pending`.
* **Pass Criteria**: Registration succeeds. Row is created.
* **Fail Criteria**: Server returns `500 Internal Error`. Duplicate email restriction fails.

---

### 7.2. Main Dashboard

#### Test Case Dash-001: Real-time Stats Load
* **Purpose**: Verify total usage, active tasks, and execution trends load.
* **Preconditions**: Logged in as `enterprise_admin@novaflow.test`.
* **Step-by-Step Actions**:
    1. Navigate to `/dashboard`.
    2. Check performance graphs.
* **Expected UI**: Dashboard charts animate and display correctly without placeholders.
* **Pass Criteria**: Metrics load within 1.5 seconds.
* **Fail Criteria**: Charts stay blank, displaying loading spinners indefinitely.

---

### 7.3. Workflow Builder

#### Test Case Flow-001: Node Orchestration & Canvas
* **Purpose**: Verify node generation, manipulation, and connections on the React Flow canvas.
* **Preconditions**: Logged in. Workspace is set to editor.
* **Step-by-Step Actions**:
    1. Drag an `Agent Node` and a `Trigger Node` onto the canvas.
    2. Draw a line from the output of the Trigger to the input of the Agent.
    3. Click "Save Workflow".
* **Expected UI**: Nodes connect cleanly. Connection lines snap smoothly. Action notification toast says "Workflow saved".
* **Expected Backend Behaviour**: POST request to `/api/v1/workflows/save` with node JSON payloads returns `200 OK`.
* **Expected Database Behaviour**: The `workflows` table updates the JSON schema block.
* **Pass Criteria**: Canvas configuration is saved without loss.
* **Negative Testing**: Draw a cyclical reference loop. Canvas must validation-error and block saving.

---

### 7.4. Marketplace & Integration Catalog

#### Test Case Market-001: Connector Setup
* **Purpose**: Configure third-party integrations from the catalog.
* **Preconditions**: OAuth configuration variables exist in the backend.
* **Step-by-Step Actions**:
    1. Go to `/marketplace`.
    2. Click "Configure Google Drive".
    3. Enter mock Client ID and Secret, then save.
* **Expected UI**: Active indicator turns green.
* **Pass Criteria**: Credentials validate. Config stores successfully.

---

### 7.5. Knowledge Management

#### Test Case Know-001: Bulk File Upload (FastAPI Background Ingestion)
* **Purpose**: Verify that multiple markdown documents process quickly in the background.
* **Preconditions**: A new knowledge base has been created.
* **Step-by-Step Actions**:
    1. Go to `/knowledge`, open your Knowledge Base.
    2. Drag and drop 30 `.md` files (approx 20KB each) into the upload container.
    3. Click "Upload & Process".
* **Expected UI**: UI immediately reports files are "Processing" and remains interactive. Status updates asynchronously.
* **Expected Backend Behaviour**: Backend issues a `200 OK` immediately. FastAPI schedules a `BackgroundTasks` thread to process chunking and vector insertions in the background.
* **Pass Criteria**: Upload returns instantly. Files transition from `Pending` (status 5) to `Success` (status 2) without freezing the UI.

---

### 7.6. Conversational Chat Client

#### Test Case Chat-001: Document Name List System Note Injection
* **Purpose**: Verify the chat assistant can list your uploaded documents even with low semantic query overlap.
* **Preconditions**: At least 5 documents are uploaded to the Knowledge Base linked to the "Document Q&A" assistant.
* **Step-by-Step Actions**:
    1. Open `/chat` with "Document Q&A" assistant.
    2. Ask: *"What documents are currently in my knowledge base?"*
* **Expected UI**: Assistant responds with a clear list of the uploaded filenames.
* **Expected Backend Behaviour**: The RAG retrieval engine retrieves file records and injects a `System Note` in the LLM prompt listing files.
* **Pass Criteria**: Assistant correctly names the uploaded files.

#### Test Case Chat-002: Full Document Fetching
* **Purpose**: Verify the assistant can read a full file context when requested.
* **Preconditions**: `SECRET_MANAGEMENT.md` is uploaded.
* **Step-by-Step Actions**:
    1. In the chat, type: *"Give me the full contents of SECRET_MANAGEMENT.md"*.
* **Expected UI**: Assistant prints out the complete document details and features.
* **Expected Backend Behaviour**: The retrieval engine intercepts the query, retrieves all sequential chunks of `SECRET_MANAGEMENT.md` from the database, and injects it into context.
* **Pass Criteria**: The assistant returns full contents rather than a truncated snippet.

---

### 7.7. Voice Assistant Lab

#### Test Case Voice-001: Speech-to-Text Streaming
* **Purpose**: Verify voice input processes correctly.
* **Preconditions**: Microphone permissions granted.
* **Step-by-Step Actions**:
    1. Navigate to `/voice`.
    2. Click the microphone button and say: *"Hello, what is the server status?"*
* **Expected UI**: Waveform animations active. Text transcription streams onto screen in real-time.
* **Pass Criteria**: Audio stream processes and assistant speaks back response.

---

### 7.8. Model Benchmarking Lab

#### Test Case Bench-001: Run Comparative Models
* **Purpose**: Test text outputs across multiple active model engines.
* **Preconditions**: Both OpenRouter and OpenAI API keys configured.
* **Step-by-Step Actions**:
    1. Navigate to `/model-lab`.
    2. Type test prompt: *"Translate 'hello' to Spanish"*.
    3. Select models `Gemini Pro` and `GPT-4o`, then click "Compare".
* **Expected UI**: Side-by-side output screens show streaming text simultaneously.
* **Pass Criteria**: Both models generate and complete stream outputs.

---

### 7.9. Evaluation Arena

#### Test Case Eval-001: Prompt Quality scoring
* **Purpose**: Test prompt scoring metrics.
* **Step-by-Step Actions**:
    1. Navigate to `/evaluation`.
    2. Input a system instruction prompt. Click "Run Evaluation Suite".
* **Expected UI**: Displays latency, cost, and hallucination scores.
* **Pass Criteria**: Metrics calculate successfully.

---

### 7.10. Settings & Workspaces

#### Test Case Set-001: Create and Switch Workspaces
* **Purpose**: Verify multi-tenant workspace separation.
* **Step-by-Step Actions**:
    1. Go to Settings -> Workspaces.
    2. Create `Workspace B`. Switch to it.
* **Expected UI**: Dashboard switches context. Empty screens load since no files are in Workspace B.
* **Expected Database Behaviour**: Workspace entity created with Owner association.
* **Pass Criteria**: Workspace Switch successful.

---

### 7.11. Notifications Widget & Center

#### Test Case Notif-001: Real-time Notification Bell & WebSockets
* **Purpose**: Verify background notifications push instantly to the user's dashboard.
* **Preconditions**: WebSocket connection established.
* **Step-by-Step Actions**:
    1. Trigger a background workflow failure.
    2. Look at the notification bell icon.
* **Expected UI**: Red badge increment count appears on the bell icon. Toast notification slides in. Clicking bell shows details of failure.
* **Expected WebSocket Behaviour**: WS payload `type: notification` received.
* **Pass Criteria**: Notification displays in real-time.

---

## 8. Module-Specific Testing

### 8.1. Workflow Builder Execution
* **TC-WF-001 (Failover)**: Trigger a node execution timeout. Verify execution transitions to alternative paths.
* **TC-WF-002 (State Resume)**: Pause an active execution, verify DB state updates, then click Resume to process successfully.

### 8.2. Voice AI & Streaming Telephony
* **TC-VOICE-001 (Noise Filtering)**: Run streaming audio with background ambient noise. Text transcription should remain >90% accurate.
* **TC-VOICE-002 (Language Auto-Switch)**: Speak mixed Hinglish context (*"aab call disconnect karke log show karo"*). Voice assistant must process context correctly.

### 8.3. Knowledge RAG Pipeline
* **TC-RAG-001 (OCR Validation)**: Upload `scanned_ocr.jpg`. Verify database contains readable strings rather than metadata.
* **TC-RAG-002 (Corrupted File Rejection)**: Upload `corrupt_doc.docx`. Server must catch error, label status as `Failed` (status 3), and output clear error logs.

### 8.4. Third-Party Connectors
* **TC-CONN-001 (S3 Integration)**: Configure credentials. Run sync. Verify files populate in knowledge base dynamically.

---

## 9. Non-Functional Testing

### 9.1. Security & Isolation (RBAC/Multi-Tenant)
* **TC-SEC-001 (Workspace Data Leaking)**: Log in as `viewer_user` on Workspace A. Make API request using JWT token for Workspace B's resource IDs. Server must block with `403 Forbidden`.
* **TC-SEC-002 (Rate Limit Protection)**: Run parallel curl script with 100 requests/sec. API must return `429 Too Many Requests`.

### 9.2. Performance & Stress Testing
* **TC-PERF-001 (Large Scale Payload)**: Execute a workflow with 200 nodes. Canvas interface must maintain a rendering speed of >50 FPS. Memory leak checks using Chrome profiler must display no growing memory heap.

### 9.3. Cross-Browser & Mobile Responsiveness
* **TC-RESP-001 (Mobile Layout)**: Open on Safari iOS. Verify workflow cards and navigation menus collapse into a hamburger layout. No elements should clip.

### 9.4. Accessibility (WCAG 2.1 AA)
* **TC-ACC-001**: Verify color contrast ratios for dark theme components are at least 4.5:1. Aria labels must be defined on all builder buttons.

---

## 10. End-to-End User Journeys

### User Journey E2E-001: Enterprise Agent Onboarding Flow
1. **Signup**: Register as a new user. Log in.
2. **Workspace Creation**: Create an isolated team workspace named `Product QA Workspace`.
3. **Upload Knowledge**: Drag and drop 15 product user manuals (Markdown and PDF). Verify processing completes in background.
4. **Connect Integrations**: Authenticate Google Drive integration. Sync client folder.
5. **Create Assistant**: Link the documents to a new assistant named `Platform Agent`.
6. **Chat Testing**: Start conversation. Verify document name lists and full retrieval flows work properly.
7. **Log out**: Click profile, select Log Out. Verify session token is invalidated.

---

## 11. Final Production Certification

### 11.1. Go-Live Checklists
- [ ] Database Schema migrations completed (Alembic HEAD).
- [ ] Environment variables configured correctly (production API Keys, database configurations).
- [ ] Milvus index created for dense vector configurations.
- [ ] Rate limits tuned for security.
- [ ] All security groups locked (No public database access).

### 11.2. Defect Severity & Classification
* **Critical**: Platform crashes, user isolation breached, or core workflows completely broken.
* **High**: A major feature (e.g. Chat, Document Upload, Voice Assistant) does not work.
* **Medium**: Broken layout UI/UX, or minor visual glitches.
* **Low**: Typo in texts, minor styling inconsistencies.

### 11.3. QA Sign-off Template

```markdown
# NovaFlow QA Test Execution Report
Date: ________________________
Tester Name: _________________
Build Version: _______________
Environment: (Staging/Prod) ___

| Test Suite | Total Run | Pass | Fail | Blocked |
|---|---|---|---|---|
| Authentication & Workspace | | | | |
| Knowledge Base Ingestion | | | | |
| RAG Retrieval & Chat | | | | |
| Workflow Builder Canvas | | | | |
| Notifications Engine | | | | |

QA Certification Verdict: (APPROVED / DECLINED)
Sign-off Signature: ________________________________________
```
