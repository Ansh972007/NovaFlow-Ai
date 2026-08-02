# NovaFlow AI Operating System (AIOS)
## Enterprise Governance & Extensibility Specification (v12.4 Edition)

This document establishes the permanent governance layer, extension SDK contracts, Architecture Decision Records (ADRs), and code standards for NovaFlow AIOS.

---

## Section 1: Universal Plugin & Extension SDK

The Extension SDK allows developers to build custom planners, agents, capabilities, and connectors. Every extension must register a manifest and run inside an isolated sandbox.

```
[Plugin Manifest] ──► [Extension Loader] ──► [Capability Sandbox / Virtual Environment]
```

### Manifest Schema
```json
{
  "plugin_id": "plugin_custom_ocr",
  "version": "1.0.0",
  "category": "ocr",
  "entry_point": "custom_ocr.py:CustomOCRExtension",
  "permissions": ["file_read"],
  "dependencies": ["tesseract-ocr"]
}
```

---

## Section 2: Enterprise AI Model Governance

NovaFlow implements an automated AI routing filter that guarantees compliance with HIPAA, GDPR, and regional residency restrictions before model queries are executed.

```
[Inference Request] ──► [GDPR / HIPAA PII Filter] ──► [Region Routing Gate] ──► [LLM Endpoints]
```

* **Sensitive Data Policies**: Requests containing pattern matches for PII (such as Social Security or Passport numbers) are intercepted, logged as warning compliance events, and rejected before token packaging.

---

## Section 3: Architecture Decision Records (ADRs)

### ADR-001: Why AI Kernel Core
* **Context**: Legacy architecture decoupled route handling from capability execution logic.
* **Decision**: Establish a centralized **AI Kernel** intercepting all project compilation, scheduling, and event routes.
* **Consequences**: Standardized API lifecycle tracking and guaranteed SOC2 audit tracing.

### ADR-002: Why Solution Graph abstraction
* **Context**: Mapping business requirements straight to workflows limits agent and database options.
* **Decision**: Solution Graph represents the intermediate architectural blueprint prior to workflow execution.

### ADR-003: Why Capability DNA schemas
* **Context**: Need dynamic validation of inputs and outputs for custom and preset providers.
* **Decision**: Capability DNA registry specifies strict, static typing schemas.

### ADR-004: Why Universal Registry model
* **Context**: Need platform discovery of workflows, connectors, and prompts.
* **Decision**: Unified catalog index for all reusable system components.

### ADR-005: Why Hierarchical Memory graph
* **Context**: Chat history was mixed, creating risk of cross-workspace leaks.
* **Decision**: Memory is partitioned from global scope down to agent run instances.

### ADR-006: Why Digital Twin Sandbox
* **Context**: Deploying custom integrations could lead to API rate limit crashes.
* **Decision**: Runs mock event trials to trace error loops before staging.

### ADR-007: Why Marketplace Indexing
* **Context**: Users need cross-organization sharing of prompt packs and integrations.
* **Decision**: Universal repository supporting version tracking.

### ADR-008: Why Event-Driven Architecture
* **Context**: Document RAG indexing blocks primary web thread pools.
* **Decision**: Run heavy jobs inside Celery queues.

### ADR-009: Why Component Reuse Engine
* **Context**: Recompiling identical connectors wastes VRAM and database storage.
* **Decision**: Reuse matched nodes first.

### ADR-010: Why AIOS instead of Workflow Platforms
* **Context**: Workflows represent only one possible execution path.
* **Decision**: Transition to a goal-oriented operating system that determines execution topology.

---

## Section 4: Architecture Governance
* **Breaking Changes**: Requires a formal RFC approval process and a minor version bump (e.g. `v12.0` -> `v12.1`).
* **Deprecation Window**: Deprecated capabilities are kept active for 2 minor releases to support legacy Solution Graphs.

---

## Section 5: Enterprise Coding Standards
* **Python**: Enforce type hints, Pydantic data schemas, and SQLAlchemy ORM boundaries.
* **React/Next.js**: Strict TS interfaces, decoupled contexts (e.g. `LlmProviderContext`), and responsive CSS layouts.

---

## Section 6: Contribution Model
* **PR Process**: Every contribution requires:
  * OWASP vulnerability scans.
  * Re-running the 163 backend test regression suite.
  * Verified developer signatures.

---

## Section 7: Long-Term Maintenance
* **LTS Window**: Major releases (e.g., `v12.0.0`) receive security hotfixes and patch updates for 3 years.
* **Audit Schedule**: External SOC2 audits run every 12 months.

---

## Section 8: Release Management
```
[Alpha (Nightly)] ──► [Beta (Feature Freeze)] ──► [Release Candidate] ──► [Stable (LTS)]
```

---

## Section 9: Developer Handbook
* **Git Standards**: Use conventional commits (e.g., `feat(kernel): add failover router`).
* **PR Checklist**: Verify tenant isolation filters are present in all database query routes.

---

## Section 10: Final Architecture Freeze
The following components are marked **IMMUTABLE**:
1. **AI Kernel Core Router Interfaces**.
2. **Project Graph Schema definition models**.
3. **Tenancy isolation parameters**.

The registry catalog and custom connector plugins are **EXTENSIBLE**.
