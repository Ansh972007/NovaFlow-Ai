# Optimization Engine

Location: `backend/app/eiap/optimization.py`

## Behavior

`run_optimization_scan()` scans selected domains and persists recommendations. **Nothing is applied automatically.**

## Domains

`workflow`, `agent`, `knowledge`, `connectivity`, `finops`

Each domain module exposes `recommend()` which reuses that layer's analytics and writes advisory `EIAPRecommendation` rows (status `open`).

## Recommendation lifecycle

```
open → approved → applied
   ↘ dismissed
```

- `applied` requires prior `approved` (enforced in router)
- Deduplicated by (workspace, domain, title) while `open`

## API

- `POST /eiap/optimize` — run scan
- `GET /eiap/recommendations` — list (filter by domain/status)
- `POST /eiap/recommendations/{id}/approve`
- `POST /eiap/recommendations/{id}/dismiss`
- `POST /eiap/recommendations/{id}/applied`

## Events

Emits `EIAPOptimizationScan` via Platform Intelligence.
