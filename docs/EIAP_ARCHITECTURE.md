# EIAP Architecture

NovaFlow Enterprise Intelligence & Autonomy Platform (`backend/app/eiap/`) is the **strategic intelligence layer**. It continuously observes, evaluates, predicts, optimizes, governs, and recommends improvements across the entire NovaFlow ecosystem.

## Non-negotiable principle

EIAP **never replaces** AI Runtime, AgentOS, Workflow Intelligence, Knowledge OS, Connectivity, or Platform Intelligence. It **orchestrates intelligence across them** by reusing their observability/analytics services. It **never applies changes automatically** — every recommendation is approval-gated.

## Position in stack

```
Security → Platform → Data → AI Runtime → Workflow Intelligence → Platform Intelligence
→ Conversation → Knowledge OS → Agent OS → Connectivity → EIAP
```

## Modules

| Module | Reuses | Purpose |
|--------|--------|---------|
| `observability.py` | all layer observability | Unified system health score |
| `workflow_intel.py` | `workflow_intelligence.observability` | Failure/latency analysis + recs |
| `agent_intel.py` | `agent_os.analytics`, `learning` | Scorecards, rankings, recs |
| `knowledge_intel.py` | `knowledge_os.curator` | Stale/duplicate/weak detection + recs |
| `connectivity_intel.py` | `connectivity.analytics`, `observability` | Connector health + fallback recs |
| `model_intel.py` | `PlatformMetric` telemetry | Provider benchmarking + best-per-task |
| `prediction.py` | `capacity.planner`, `finops.ledger` | Growth/cost forecasts |
| `finops.py` | `finops.ledger` | Cost optimization recs |
| `optimization.py` | all domain modules | Approval-gated recommendation scan |
| `governance.py` | observability + audit | Compliance, security posture, health |
| `reporting.py` | all | Daily/weekly/monthly/executive reports |
| `recommendations.py` | — | Approval-gated recommendation store |

## Data model

| Table | Purpose |
|-------|---------|
| `eiap_recommendations` | Approval-gated suggestions (`open`→`approved`→`applied`/`dismissed`) |
| `eiap_reports` | Generated report snapshots |

## API

Prefix: `/api/v1/eiap/*`

## Health

`"intelligence_autonomy": "enterprise-v1"` on `/health`

See: `OPTIMIZATION_ENGINE.md`, `PREDICTION_ENGINE.md`, `GOVERNANCE_ENGINE.md`, `MODEL_BENCHMARKING.md`, `AUTONOMY_GUIDE.md`.
