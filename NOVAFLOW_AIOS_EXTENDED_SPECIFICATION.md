# NovaFlow AI Operating System (AIOS)
## Extended Enterprise Engineering Specification (v12.3 Edition)

This specification expands the core NovaFlow AIOS platform with the required enterprise infrastructure layers, ensuring point-to-point compatibility with previous constitutions and the v12.2 specification.

---

## Section 1: Enterprise Event Bus Specification
NovaFlow uses an event-driven system with Celery and RabbitMQ/Redis to coordinate asynchronous actions.

```
[Agent Tool Execution] ──► [Event: AgentRunStarted] ──► [Event Bus Broker] ──► [Audit Log Consumer]
                                                                        │
                                                                        ▼
                                                             [Telemetry Store Consumer]
```

### Event Schema Layout
```json
{
  "event_id": "evt_94b38c29",
  "event_type": "solution.compile.started",
  "producer": "composer_kernel_v12",
  "timestamp": "2026-08-01T13:35:00Z",
  "correlation_id": "corr_c38d1921",
  "payload": {
    "project_id": "proj_001",
    "solution_id": "sol_448",
    "trigger_type": "user_prompt"
  }
}
```
* **Dead Letter Queue (DLQ)**: Events failing 3 retry attempts are moved to the DLQ (`aios_dead_letter_queue`) for administrator inspection.

---

## Section 2: Frontend Architecture Specification
The Next.js client layout uses a decoupled context structure:

```
[Main Providers Router Page]
       │
       ├─► [Project Explorer Component] ─► Context: ProjectContext
       ├─► [Solution Graph Designer]    ─► Context: CanvasContext
       └─► [Execution Inspector Tab]    ─► Context: LogInspectorContext
```

### Pages & Capabilities UI
* **AIOS Dashboard**: High-level execution metrics (latency, token spends, running digital twin states).
* **Project Explorer**: Workspace view mapping goals to current Solution Graphs.
* **Credential Center**: Secret mapping grid with JIT verification hooks.

---

## Section 3: Redis Architecture
Redis serves as the caching layer, rate limiter, and distributed lock manager:

```
🔑 Key: aios:lock:project:[id]       --> Distributed Lock (Mutex)
🔑 Key: aios:rate:token:[tenant_id]  --> Token Rate Limiting bucket
🔑 Key: aios:cache:solution:[id]     --> Solution Graph layout JSON
```

* **TTL Policy**: Caching keys expire in 3600 seconds. Session locks use a 30-second lease with automated heartbeat renewal.

---

## Section 4: Vector Database (Milvus/Qdrant) Architecture
* **Collections**: `knowledge_partitions`, `capability_embeddings`.
* **Metadata Schema**:
  ```json
  {
    "workspace_id": "int32",
    "document_id": "string",
    "chunk_index": "int32",
    "version": "string"
  }
  ```
* **Compaction**: Automatic compaction runs during low-traffic hours (02:00 UTC daily).

---

## Section 5: Universal Marketplace Lifecycle
Marketplace assets (workflows, connectors, knowledge packs, prompts) proceed through the following stages:

```
[Draft] ──► [Private Verification Scan] ──► [Internal Release] ──► [Verified / Marketplace Deployed]
```
* **Security Scan**: Assets are parsed to check for malicious URLs, directory traversals, or unescaped environment accesses.

---

## Section 6: Versioning Strategy
NovaFlow uses semantic versioning (`MAJOR.MINOR.PATCH`) mapped directly to database records. Toggling back immediately targets database pointers to the target revision ID:

```
Project Graph v1.4.0 (Active) ──► (Rollback Trigger) ──► Point to v1.3.1
```

---

## Section 7: Monitoring Specification
* **Latency Tracks**: p50, p90, and p99 completion latency.
* **Celery Queues**: Number of pending RAG compile jobs inside `heavy_tasks_queue`.

---

## Section 8: Enterprise Multi-Tenancy
* **Data Isolation**: Workspace IDs are validated at the database connection layer via tenancy filters.
* **Secrets Isolation**: Secret decryption keys are isolated per user session to prevent cross-tenant key leakage.

---

## Section 9: AI Decision Engine Pipeline
```
[User Requirement]
       │
       ▼
[Gap Analysis Mapping]
       │
       ├─► Need Workflow?  ──► (True/False)
       ├─► Need Database?  ──► (True/False)
       └─► Need Connector? ──► (True/False)
       │
       ▼
[Solution Graph Generation]
```

---

## Section 10: Definition of Done
A phase is marked completed only when:
* All unit and integration tests compile.
* OWASP security scans report zero high-severity warnings.
* Next.js production compilations build successfully.

---

## Section 11: Disaster Recovery Plan
* **Backups**: Auto-backups run every 6 hours.
* **Point-in-Time Recovery**: Database transaction logs allow recovering states to any sub-second timestamp in the last 7 days.

---

## Section 12: Observability (OpenTelemetry)
* **Trace IDs**: Propagation of `Trace-ID` and `Span-ID` through API routers, Celery tasks, and inference servers.
* **Structured Logging**: Logs are generated in JSON format to match index requirements.

---

## Section 13: Performance Budgets
* **Maximum Graph Compilation Time**: 15 seconds.
* **Average Inference Proxy Latency**: 250 milliseconds (overhead).

---

## Section 14: Security Hardening
* **Supply Chain Verification**: Dynamic dependency scans (e.g. Snyk) run during container builds.
* **Rotation**: API keys rotate automatically every 90 days.

---

## Section 15: Developer Experience
* **Local Harness**: Debugging tool allows devs to test tool executions inside local Docker sandboxes.
* **Hot Reload**: Fast API code adjustments automatically reload workers during local development.
