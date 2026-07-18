# Workflow Execution

## Engine

`backend/app/services/workflow.py` — `run_workflow()`, `_execute_graph()`

## Intelligence enhancements

| Feature | Implementation |
|---------|----------------|
| AI Runtime bridge | `workflow_intelligence/execution/runtime_bridge.py` |
| Checkpointing | `WorkflowExecutionCheckpoint` + `execution/checkpoint.py` |
| Retry | `with_retry()` exponential backoff |
| Trace ID | Per-run `trace_id` on steps and UsageEvent |
| HITL pause/resume | Existing `WorkflowPendingRun` |
| Idempotency | `ExecutionContext.idempotency_key` (extensible) |

## Node execution

All `llm`, `agent`, `retrieve`, `loop`, `parallel` nodes route through **Enterprise AI Runtime** (permissions, prompt compiler, audit).

## Publish gate

Publishing requires `check_publish_ready()` — validation + security pass.

## Scheduling

`workflow_scheduler.py` — cron via `worker_tenant()` for tenant isolation.

## Webhook / integrations

Slack, Telegram, inbound webhook — unchanged APIs, inherit runtime on execution.
