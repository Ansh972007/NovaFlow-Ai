# Tool Orchestration

Location: `backend/app/services/agent_tools.py`, `runtime/tools.py`, `agent_os/safety.py`

## Builtin tools

`calculator`, `kb_search`, `summarize`, `translate_en`, `datetime`, `web_fetch`, `regex_extract`, `json_parse`, `word_count`

## Rules

- All tools execute through AI Runtime `execute_tools()`
- `kb_search` routes through Knowledge OS `retrieve_for_agent()`
- Tool permissions validated via `validate_tool_permissions()`
- High-risk combinations trigger approval via HITL

## API

`GET /agent-os/tools`
