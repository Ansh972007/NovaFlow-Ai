# Model Benchmarking

Location: `backend/app/eiap/model_intel.py`

## Data source

`PlatformMetric` telemetry recorded by AI Runtime — EIAP **never calls providers directly**.

## Metrics per model

- Calls, error rate
- Average latency
- Total cost + average cost per call
- Token volume

## Recommendation priorities

| Priority | Optimizes for |
|----------|---------------|
| `cost` | Lowest cost per call |
| `latency` | Fastest response |
| `quality` | Lowest error rate |
| `balanced` | Error rate → latency → cost |

## API

- `GET /eiap/models/benchmark?days=30`
- `GET /eiap/models/recommend?priority=balanced`

## Providers covered

Any provider that emits runtime telemetry: GPT, Claude, Gemini, Mistral, Groq, Ollama, OpenRouter, Azure OpenAI.
