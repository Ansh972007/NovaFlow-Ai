# Tool Runtime

Location: `backend/app/runtime/tools.py`  
Implementation: delegates to `app/services/agent_tools.py`

## Supported tools

| Tool | Description |
|------|-------------|
| `calculator` | Safe math evaluation |
| `kb_search` | Semantic knowledge search |
| `summarize` | 3-bullet summary via LLM |
| `translate_en` | Translate to English |
| `datetime` | UTC timestamp |
| `web_fetch` | HTTP fetch (SSRF-protected) |
| `regex_extract` | Pattern extraction |
| `json_parse` | JSON key listing |
| `word_count` | Word/char/line counts |

Future integrations (email, calendar, Slack, GitHub, Drive, webhook) extend `_run_tool` through the same `execute_tool()` entry point.

## Execution flow

1. Permission check (`KNOWLEDGE_READ` for `kb_search`)
2. Tool selection heuristics (`_select_tools`)
3. Ordered execution (evidence before synthesis)
4. Results capped at 4000 chars
5. Output validation before return

## Agent integration

`agents.py` → `execute_tools()` → `execute_tool()` → `_run_tool()`

## Custom tools

Register in `BUILTIN_TOOLS` and implement in `_run_tool`. All paths must use `RuntimeContext` for tenant scope.

## Security

- `web_fetch` uses `assert_safe_url()` (SSRF protection)
- Redirects blocked
- Script tags stripped from HTML responses
