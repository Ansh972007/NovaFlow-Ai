# Prompt Compiler

Location: `backend/app/runtime/prompt.py`

## Rule

**No module may assemble prompts manually.** All system and user messages for AI execution must go through `compile_prompt()`.

## Inputs (`PromptInputs`)

| Field | Source |
|-------|--------|
| `system_prompt` | Assistant / agent / workflow system |
| `workspace_context` | Workspace metadata |
| `knowledge_context` | Knowledge resolver (RAG) |
| `conversation_context` | Summarized prior turns |
| `memory_context` | Memory resolver |
| `tools_context` | Available tools list |
| `user_prompt` | Sanitized user message |
| `safety_instructions` | Built-in injection / harm refusal |
| `extra_instructions` | Optional overrides |

## Output (`CompiledPrompt`)

- `system` — full compiled system message
- `user` — user message
- `messages_preview` — truncated preview for audit/logs

## Section order

1. System prompt
2. Workspace context
3. Memory
4. Knowledge (with citation instructions)
5. Tools
6. Conversation summary
7. Extra instructions
8. Safety instructions

## Security

User input is sanitized and injection-checked in `AIRuntime._guard_input()` **before** compilation.

## Usage

```python
from app.runtime.prompt import PromptInputs, compile_prompt

compiled = compile_prompt(PromptInputs(
    system_prompt=assistant.prompt,
    knowledge_context=kb.context,
    memory_context=mem.combined(),
    user_prompt=user_message,
))
# Pass compiled.system and compiled.user to execution engine
```
