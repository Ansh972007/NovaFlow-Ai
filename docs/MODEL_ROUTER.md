# Model Router

Location: `backend/app/runtime/router.py`

## Purpose

Automatically choose the best model for each request using configurable routing policies, without changing callers.

## Routing order

1. **Workspace A/B routes** — `pick_ab_model()` from existing `ab_routing` service
2. **Policy hints** — latency, cost, or context-window preferences
3. **Provider default** — active model from Settings vault

## Policies

| Policy | Use case |
|--------|----------|
| `default` | Standard chat and agents |
| `low_latency` | Prefer fast models (gpt-4o-mini, haiku, gemini-flash) |
| `low_cost` | Cost-optimized models |
| `large_context` | Long-context models (gpt-4o, claude-sonnet) |

Pass `routing_policy` on `ChatRequest` to override.

## Provider abstraction

`providers.py` wraps `llm_providers` and maps aliases:

- OpenAI, Anthropic, Azure OpenAI, OpenRouter, custom (Ollama / any OpenAI-compatible endpoint)
- Gemini, DeepSeek, Mistral, Qwen → routed via OpenRouter or custom base URL

Providers are hot-swappable via Settings; runtime reads active config per request.

## Observability

Each decision records:

- `model`, `provider_type`, `policy`, `reason`, `route_id` (if A/B)

## Extension

Add new policies in `router.py` `_POLICY_MODEL_HINTS` or workspace-level rules in a future `RoutingRule` table without changing `AIRuntime` callers.
