# Workflow Engine Architecture

NovaFlow workflow execution lives in `backend/app/services/workflow.py`. The **Workflow Intelligence Platform** (`backend/app/workflow_intelligence/`) extends it without replacing APIs or UI.

## Layers

| Layer | Package | Role |
|-------|---------|------|
| Engine | `services/workflow.py` | Graph execution, HITL, scheduling |
| Intelligence | `workflow_intelligence/` | Validate, plan, optimize, debug, test |
| AI Runtime | `runtime/` | LLM, agent, knowledge nodes (via bridge) |
| Platform | `platform/` | Tenant scope, permissions, audit |

## Execution flow

```
Trigger (API / webhook / schedule / WS)
  → PlatformContext / tenant resolution
  → run_workflow()
  → RuntimeContext (trace_id)
  → _execute_graph() — topo order
  → AI Runtime bridge (retrieve, llm, agent)
  → WorkflowRun + UsageEvent + audit
```

## Graph format

JSON `{ nodes: [{id, type, x, y, data}], edges: [{from, to}] }`

## Intelligence endpoints

Prefix: `/api/v1/workflow/intelligence/*` — see sub-docs.

## Publish gate

Publishing (`POST /workflow/status` with `status=1`) runs validation + security checks. Errors block publish.

## Health

`/health` reports `"workflow_intelligence": "enterprise-v1"`.
