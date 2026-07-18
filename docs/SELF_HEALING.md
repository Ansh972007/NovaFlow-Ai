# Self-Healing Platform

Location: `backend/app/platform_intelligence/healing/`

## Detection

`detectors.py` monitors:
- High error rates per subsystem
- High latency (>5s avg)
- Open circuit breakers

## Circuit breakers

`circuit_breaker.py` — per-subsystem breakers with:
- Failure threshold (default 5)
- Recovery window (60s)
- States: closed → open → half_open

## Actions

| Finding | Action |
|---------|--------|
| `high_error_rate` | Open circuit breaker |
| `high_latency` | Graceful degradation recommendation |
| `circuit_open` | Provider failover recommendation |

## API

`GET /platform/intelligence/dashboard/incidents`

## Recovery

Automatic half-open probe after recovery window. Manual reset via process restart or future admin API.
