# Autonomy Guide

Location: `backend/app/eiap/`

## Golden rule

**EIAP never changes anything automatically.** It observes, analyzes, predicts, and recommends. Every recommendation requires explicit human approval before it can be acted upon.

## Autonomy boundary

| EIAP does | EIAP does NOT |
|-----------|---------------|
| Analyze telemetry | Execute workflows |
| Score agents | Modify agent configs |
| Detect stale knowledge | Re-index automatically |
| Benchmark models | Switch providers automatically |
| Forecast cost/growth | Change budgets |
| Generate recommendations | Apply recommendations |

## Approval workflow

1. `POST /eiap/optimize` generates `open` recommendations
2. Human reviews via `GET /eiap/recommendations`
3. `approve` / `dismiss`
4. After external action, `applied` (requires prior approval)

## Reuse contract

EIAP imports and calls existing layer services only. It contains **no** independent runtime, workflow execution, retrieval, agent orchestration, or connector logic. If a capability exists in a locked foundation, EIAP reuses it.

## Extending

New intelligence domains should:
- Add a `<domain>_intel.py` module that reuses the corresponding layer's analytics
- Emit `EIAPRecommendation` rows (status `open`)
- Register in `optimization.run_optimization_scan()`
