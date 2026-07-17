import json
import math
import re
from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.services.knowledge import search_chunks_semantic
from app.services.llm import stream_chat_sync

BUILTIN_TOOLS: dict[str, str] = {
    "calculator": "Evaluate math expressions safely",
    "kb_search": "Search linked knowledge bases",
    "summarize": "Summarize text in 3 bullet points",
    "translate_en": "Translate input to English",
    "datetime": "Current date/time in UTC",
    "web_fetch": "Fetch a URL and return text excerpt",
    "regex_extract": "Extract text with a regex pattern",
    "json_parse": "Parse JSON and return formatted keys",
    "word_count": "Count words and characters in text",
}

DEFAULT_AGENT_SYSTEM = (
    "You are a careful NovaFlow agent. Treat tool results as evidence, not absolute truth. "
    "Write a clear final answer: lead with the conclusion, then short supporting bullets. "
    "If tools conflict or are empty, say what is uncertain. Never invent citations."
)

# Heuristic routing — which tools to prefer for a given user ask
_TOOL_HINTS: dict[str, list[str]] = {
    "calculator": [r"\d+\s*[\+\-\*/]\s*\d+", r"\bcalc", r"\bmath\b", r"sqrt\(", r"\bpercent"],
    "kb_search": [r"\bpolicy\b", r"\bdocument", r"\bknowledge", r"\baccording to\b", r"\bfrom (the )?docs?\b", r"\bwarranty\b"],
    "summarize": [r"\bsummar", r"\btldr\b", r"\bkey points?\b", r"\bbrief(ly)?\b"],
    "translate_en": [r"\btranslat", r"\bto english\b", r"\benglis[hz]\b"],
    "datetime": [r"\b(date|time|utc|today|now)\b", r"\bwhat day\b"],
    "web_fetch": [r"https?://", r"\bfetch\b", r"\bscrape\b"],
    "regex_extract": [r"\bregex\b", r"\bpattern:", r"\bextract\b"],
    "json_parse": [r"\{[\s\S]*\}", r"\bjson\b"],
    "word_count": [r"\bword count\b", r"\bhow many words\b", r"\bchar(acter)?s?\b"],
}


def list_builtin_tools() -> list[dict]:
    return [{"id": k, "description": v} for k, v in BUILTIN_TOOLS.items()]


def _safe_calc(expr: str) -> str:
    raw = (expr or "").strip()
    cleaned = re.sub(r"[^0-9+\-*/().%\s]", "", raw)
    if not cleaned.strip() or not re.search(r"\d", cleaned):
        return "0"
    if re.fullmatch(r"[\s()+\-*/.%]*", cleaned) and not re.search(r"\d", cleaned):
        return "0"
    try:
        return str(eval(cleaned, {"__builtins__": {}}, {"sqrt": math.sqrt, "pow": pow}))
    except Exception as exc:
        return f"Error: {exc}"


def _select_tools(user_input: str, tool_ids: list[str], max_tools: int = 3) -> list[str]:
    """Pick the most relevant enabled tools instead of running every tool blindly."""
    text = user_input or ""
    scored: list[tuple[float, str]] = []
    for tid in tool_ids:
        hints = _TOOL_HINTS.get(tid) or []
        score = 0.0
        for pat in hints:
            if re.search(pat, text, re.I):
                score += 1.0
        # Soft priors so common tools still get a chance when nothing matches
        if tid == "kb_search":
            score += 0.15
        if tid == "summarize" and len(text) > 600:
            score += 0.4
        if score > 0:
            scored.append((score, tid))
    scored.sort(key=lambda x: -x[0])
    if scored:
        return [t for _, t in scored[:max_tools]]
    # Fallback: run at most two tools (kb first if linked-capable, else first two)
    preferred = [t for t in ("kb_search", "summarize", "datetime") if t in tool_ids]
    if preferred:
        return preferred[:max_tools]
    return tool_ids[:max_tools]


def _followup_input(tool_id: str, user_input: str, prior_results: list[dict[str, Any]]) -> str:
    """For step-2 tools (e.g. summarize), prefer richer prior tool output over raw user text."""
    if tool_id not in ("summarize", "translate_en", "word_count", "regex_extract", "json_parse"):
        return user_input
    kb = next((r for r in prior_results if r.get("tool") == "kb_search"), None)
    web = next((r for r in prior_results if r.get("tool") == "web_fetch"), None)
    blob = ""
    if kb and kb.get("result") and "(no knowledge" not in (kb.get("result") or ""):
        blob = kb["result"]
    elif web and web.get("result") and not str(web.get("result") or "").startswith("Fetch error"):
        blob = web["result"]
    if blob:
        return f"User request: {user_input}\n\nSource material:\n{blob[:5000]}"
    return user_input


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
            return "(no knowledge matches)"
        lines = []
        for i, h in enumerate(hits, 1):
            src = h.get("file_name") or "document"
            text = (h.get("text") or "").strip()[:400]
            method = h.get("method") or ""
            tag = f" [{method}]" if method else ""
            lines.append(f"[{i}] {src}{tag}: {text}")
        return "\n".join(lines)
    if tool_id == "kb_search" and not knowledge_id:
        return "(no knowledge base linked to this agent)"
    if tool_id == "summarize":
        return await stream_chat_sync(
            (
                "Summarize the text in exactly 3 crisp bullet points. "
                "Each bullet ≤ 20 words. No intro/outro."
            ),
            user_input[:6000],
            db=db,
            workspace_id=workspace_id,
        )
    if tool_id == "translate_en":
        return await stream_chat_sync(
            "Translate to clear natural English. Output the translation only — no commentary.",
            user_input[:6000],
            db=db,
            workspace_id=workspace_id,
        )
    if tool_id == "datetime":
        return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    if tool_id == "web_fetch":
        from app.security.ssrf import SafeUrlError, assert_safe_url

        url_match = re.search(r"https?://[^\s]+", user_input)
        if not url_match:
            return "No URL found in input"
        url = url_match.group(0).rstrip(".,)")
        try:
            url = assert_safe_url(url, allow_http=True)
        except SafeUrlError as exc:
            return f"URL blocked by security policy: {exc}"
        try:
            async with httpx.AsyncClient(timeout=15, follow_redirects=False) as client:
                res = await client.get(url)
                if res.is_redirect:
                    return "Redirects are blocked for security"
                text = re.sub(r"<script[\s\S]*?</script>", " ", res.text or "", flags=re.I)
                text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.I)
                text = re.sub(r"<[^>]+>", " ", text)
                text = re.sub(r"\s+", " ", text).strip()
                return text[:4000] or f"(empty response, status {res.status_code})"
        except Exception as exc:
            return f"Fetch error: {exc}"
    if tool_id == "regex_extract":
        pattern = re.search(r"pattern[:\s]+(.+)", user_input, re.I)
        pat = pattern.group(1).strip() if pattern else r"\b[A-Z][a-z]+\b"
        try:
            matches = re.findall(pat, user_input, re.MULTILINE)[:50]
            return "\n".join(matches) if matches else "(no matches)"
        except re.error as exc:
            return f"Regex error: {exc}"
    if tool_id == "json_parse":
        blob = user_input
        start = user_input.find("{")
        if start < 0:
            start = user_input.find("[")
        if start >= 0:
            blob = user_input[start:]
        try:
            data = json.loads(blob)
            if isinstance(data, dict):
                lines = [f"{k}: {json.dumps(v, ensure_ascii=False)[:120]}" for k, v in list(data.items())[:40]]
                return "\n".join(lines)
            return f"Array with {len(data)} items" if isinstance(data, list) else str(data)
        except json.JSONDecodeError as exc:
            return f"JSON error: {exc}"
    if tool_id == "word_count":
        words = len(re.findall(r"\b\w+\b", user_input))
        chars = len(user_input)
        lines = len(user_input.splitlines())
        return f"words={words}, chars={chars}, lines={lines}"
    return f"Unknown tool: {tool_id}"


def _format_tool_block(tool_results: list[dict[str, Any]]) -> str:
    parts = []
    for row in tool_results:
        tid = row.get("tool") or "tool"
        result = (row.get("result") or "").strip()
        parts.append(f"### {tid}\n{result}")
    return "\n\n".join(parts)


# Prefer gathering evidence before synthesis tools
_TOOL_ORDER = {
    "datetime": 0,
    "calculator": 1,
    "kb_search": 2,
    "web_fetch": 3,
    "json_parse": 4,
    "regex_extract": 5,
    "word_count": 6,
    "summarize": 8,
    "translate_en": 9,
}


async def run_agent(
    db: Session,
    user_input: str,
    tool_ids: list[str],
    *,
    knowledge_id: int | None = None,
    workspace_id: int | None = None,
    system: str = DEFAULT_AGENT_SYSTEM,
) -> dict[str, Any]:
    tool_ids = [t for t in (tool_ids or []) if t in BUILTIN_TOOLS][:5]
    system = (system or "").strip() or DEFAULT_AGENT_SYSTEM
    if not tool_ids:
        output = await stream_chat_sync(system, user_input, db=db, workspace_id=workspace_id)
        return {"output": output, "tool_results": [], "tools": [], "selected_tools": []}

    selected = _select_tools(user_input, tool_ids, max_tools=min(3, len(tool_ids)))
    selected = sorted(selected, key=lambda t: _TOOL_ORDER.get(t, 5))

    tool_results: list[dict[str, Any]] = []
    for tid in selected:
        tool_arg = _followup_input(tid, user_input, tool_results)
        result = await _run_tool(
            db, tid, tool_arg, knowledge_id=knowledge_id, workspace_id=workspace_id
        )
        tool_results.append({"tool": tid, "result": result[:2000]})

    block = _format_tool_block(tool_results)
    prompt = (
        f"## User request\n{user_input}\n\n"
        f"## Tool results (selected: {', '.join(selected)})\n{block}\n\n"
        f"## Your job\nSynthesize a final answer for the user. "
        f"Prefer concrete statements grounded in the tool results. "
        f"If a tool was irrelevant or empty, ignore it silently."
    )
    output = await stream_chat_sync(system, prompt, db=db, workspace_id=workspace_id)
    return {
        "output": output,
        "tool_results": tool_results,
        "tools": tool_ids,
        "selected_tools": selected,
    }
