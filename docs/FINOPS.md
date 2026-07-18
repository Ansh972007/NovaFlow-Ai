# FinOps Platform

Location: `backend/app/platform_intelligence/finops/ledger.py`

## Cost tracking

| Cost type | Source |
|-----------|--------|
| `llm` | AI Runtime token usage |
| `embedding` | (extensible) |
| `workflow` | (extensible) |
| `storage` | (extensible) |

## Storage

`cost_ledger` table — workspace + organization scoped.

## Budgets

`platform_budgets` — monthly USD limit per workspace.

## API

- `GET /platform/intelligence/dashboard/billing`
- `GET /platform/intelligence/budget`
- `PUT /platform/intelligence/budget`

## Features

- 30-day cost summary by type
- Monthly forecast (7-day average × 30)
- Cost anomaly detection (>$1/day spikes)
- Policy integration — block when over budget

## Model pricing

Reuses `services/receipt.py` `estimate_cost_usd()`.
