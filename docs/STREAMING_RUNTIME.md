# Streaming Runtime

Location: `backend/app/runtime/streaming.py`  
WebSocket integration: `backend/app/routers/chat_ws.py`

## Protocol (unchanged)

WebSocket clients receive the same event shapes:

| Event | Payload |
|-------|---------|
| `start` | Stream beginning |
| `stream` | `{ message: { content, reasoning_content } }` |
| `end` | Full buffer + receipt |
| `close` | Connection complete |
| `error` | Error message |

## Features

- **Chunk streaming** — token-by-token from provider HTTP stream
- **Cancellation** — `cancel_event` on `RuntimeContext`; client `action: stop`
- **Validation** — final buffer passed through markdown validator
- **Metrics** — latency, tokens, cost attached to usage logs

## SSE

SSE endpoints can wrap `AIRuntime.chat_stream()` with `text/event-stream` framing (same token iterator).

## Reconnect

Clients should resend `chatHistory` on reconnect; runtime uses history for conversation memory.

## Implementation

```python
async for token in runtime.chat_stream(chat_request, usage_out=usage):
    await websocket.send_json({"type": "stream", "message": {"content": token}})
```

Provider streaming is handled by `app/services/llm.py` (`stream_chat`); runtime adds permissions, memory, knowledge, prompt compilation, audit, and observability.
