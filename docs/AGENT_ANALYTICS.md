# Agent Analytics

Location: `backend/app/agent_os/analytics.py`, `learning.py`

## Metrics

- Success/failure rates
- Tool quality
- Knowledge quality
- Latency and cost
- Confidence scores

## Leaderboard

`agent_leaderboard()` ranks agents by success rate and confidence.

## API

- `GET /agent-os/analytics`
- `GET /agent-os/analytics/failures`

## Learning

Records stored in `agent_learning_records` — improves planning recommendations, does **not** retrain models.
