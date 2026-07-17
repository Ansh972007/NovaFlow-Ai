# NovaFlow Enterprise AI Runtime

The AI Runtime (`backend/app/runtime/`) is the **single orchestration layer** for every AI capability in NovaFlow. Routers and services delegate here; they must not assemble prompts, select providers, or execute tools directly.

## Pipeline

Every request flows through:

```
Authentication
  → PlatformContext / RuntimeContext
  → Permission Validation
  → Memory Resolver
  → Knowledge Resolver
  → Context Builder (Prompt Compiler)
  → Model Router
  → Tool Router (agents)
  → Execution Engine
  → Output Validator
  → Audit
  → Response
```

## Package layout

| Module | Responsibility |
|--------|----------------|
| `context.py` | `RuntimeContext` bound to tenant + audit |
| `pipeline.py` | `AIRuntime` — chat, knowledge Q&A, agents |
| `providers.py` | Provider registry (OpenAI, Anthropic, Azure, Ollama, OpenRouter, …) |
| `router.py` | Model routing policies |
| `prompt.py` | **Prompt compiler** — only place prompts are assembled |
| `memory.py` | Conversation, workspace, agent, pinned memory |
| `knowledge.py` | Tenant-aware hybrid retrieval |
| `tools.py` | Unified tool execution |
| `agents.py` | Agent loop + multi-agent roles |
| `execution.py` | Provider HTTP streaming/sync |
| `streaming.py` | SSE/WS chunk streaming + cancellation |
| `validation.py` | JSON, markdown, tool output validation |
| `observability.py` | Latency, tokens, cost, cache hits |
| `cache.py` | Tenant-aware prompt/knowledge/tool caches |

## Integration points

| Entry | Runtime method |
|-------|----------------|
| WebSocket assistant chat | `AIRuntime.chat_stream()` |
| `/agents/run` | `AIRuntime.run_agent()` |
| `/knowledge/answer` | `AIRuntime.knowledge_answer()` |
| Legacy `run_agent()` | Facade → runtime |

## Foundations (do not bypass)

- `PlatformContext` / `TenantContext`
- Permission engine (`Permission.ASSISTANT_READ`, `AGENT_RUN`, `KNOWLEDGE_READ`, …)
- Security (`ai_guard`, SSRF, rate limits)
- Audit (`ctx.audit()`)
- Data platform (vectors, cache, storage)

## Health

`/health` reports `"ai_runtime": "enterprise-v1"`.

## Adding a new AI feature

1. Build a `RuntimeContext` from `PlatformContext` or WebSocket tenant resolution.
2. Create `AIRuntime(ctx)`.
3. Call `chat`, `chat_stream`, `run_agent`, or extend `pipeline.py`.
4. Never call `stream_chat` or assemble RAG prompts in routers.

See also: `MODEL_ROUTER.md`, `PROMPT_COMPILER.md`, `MEMORY_ENGINE.md`, `KNOWLEDGE_RUNTIME.md`, `TOOL_RUNTIME.md`, `AGENT_RUNTIME.md`, `STREAMING_RUNTIME.md`.
