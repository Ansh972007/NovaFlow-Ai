# Capacity Planning

Location: `backend/app/platform_intelligence/capacity/planner.py`

## Predictions (30-day basis)

- Chat event volume
- Workflow run volume
- Workflow/KB counts

## Recommendations

Auto-generated based on thresholds:
- High chat volume → dedicated runtime pool
- High workflow runs → queue workers
- Many KBs → vector partitioning

## API

`GET /platform/intelligence/capacity`

## Future

CPU/memory/bandwidth metrics from host agent or K8s metrics server.
