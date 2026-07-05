import json
import math
import re
from typing import Any

from sqlalchemy.orm import Session

from app.services.knowledge import search_chunks_semantic
from app.services.llm import stream_chat_sync

BUILTIN_TOOLS: dict[str, str] = {
    "calculator": "Evaluate math expressions safely",
    "kb_search": "Search linked knowledge bases",
    "summarize": "Summarize text in 3 bullet points",
    "translate_en": "Translate input to English",
}


def list_builtin_tools() -> list[dict]:
    return [{"id": k, "description": v} for k, v in BUILTIN_TOOLS.items()]


def _safe_calc(expr: str) -> str:
    expr = re.sub(r"[^0-9+\-*/().%\s]", "", expr or "")
    if not expr.strip():
        return "0"
    try:
        return str(eval(expr, {"__builtins__": {}}, {"sqrt": math.sqrt, "pow": pow}))
    except Exception as exc:
        return f"Error: {exc}"


async def _run_tool(
    db: Session,
    tool_id: str,
    user_input: str,
    *,
    knowledge_id: int | None = None,
    workspace_id: int | None = None,
) -> str:
    if tool_id == "calculator":
        nums = re.findall(r"[\d.+\-*/()]+", user_input)
        return _safe_calc(nums[0] if nums else user_input)
    if tool_id == "kb_search" and knowledge_id:
        hits = search_chunks_semantic(db, knowledge_id, user_input, 5)
        if not hits:
            return "(no results)"
        return "\n".join(f"- {(h.get('text') or '')[:300]}" for h in hits)
    if tool_id == "summarize":
        return await stream_chat_sync(
            "Summarize in exactly 3 bullet points.",
            user_input[:6000],
            db=db,
            workspace_id=workspace_id,
        )
    if tool_id == "translate_en":
        return await stream_chat_sync(
            "Translate to English. Output translation only.",
            user_input[:6000],
            db=db,
            workspace_id=workspace_id,
        )
    return f"Unknown tool: {tool_id}"


async def run_agent(
    db: Session,
    user_input: str,
    tool_ids: list[str],
    *,
    knowledge_id: int | None = None,
    workspace_id: int | None = None,
    system: str = "You are a helpful agent. Use tool results when relevant.",
) -> str:
    tool_ids = [t for t in (tool_ids or []) if t in BUILTIN_TOOLS][:5]
    if not tool_ids:
        return await stream_chat_sync(system, user_input, db=db, workspace_id=workspace_id)

    tool_results: list[dict[str, Any]] = []
    for tid in tool_ids:
        result = await _run_tool(db, tid, user_input, knowledge_id=knowledge_id, workspace_id=workspace_id)
        tool_results.append({"tool": tid, "result": result[:2000]})

    block = json.dumps(tool_results, indent=2)
    prompt = f"{user_input}\n\n--- Tool results ---\n{block}"
    return await stream_chat_sync(system, prompt, db=db, workspace_id=workspace_id)
