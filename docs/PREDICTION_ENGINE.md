# Prediction Engine

Location: `backend/app/eiap/prediction.py`

## Forecasts

Trend-based projections (7d → 30d/90d) for:

- Agent runs
- Connector events
- Workflow runs
- Vector chunk / knowledge base growth
- Cost (via `finops.forecast_monthly`)
- Capacity (via `capacity.planner.capacity_forecast`)

## Method

Rolling 7-day counts extrapolated linearly. No model retraining — purely analytical.

## API

`GET /eiap/predictions`

## Reuse

Delegates cost and capacity to Platform Intelligence; only aggregates and projects.
