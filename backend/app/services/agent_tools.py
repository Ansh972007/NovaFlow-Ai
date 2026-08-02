import json
import math
import re
from datetime import datetime, timezone
from typing import Any

import httpx
from pathlib import Path
from sqlalchemy.orm import Session

from app.services.llm import stream_chat_sync

BUILTIN_TOOLS: dict[str, str] = {
    "kb_search": "Search linked knowledge bases",
    "datetime": "Current date/time in UTC",
    "web_fetch": "Fetch a URL and return text excerpt",
    "regex_extract": "Extract text with a regex pattern",
    "json_parse": "Parse JSON and return formatted keys",
    "file_peek": "Peek at a text file's contents safely (specify path)",
    "dir_list": "List directory files and folders structure (specify path)",
    "file_write": "Write or update a file's contents safely (specify path and content)",
    "shell_run": "Execute a command in the workspace terminal and return output (specify command)",
}

DEFAULT_AGENT_SYSTEM = (
    "You are a careful NovaFlow agent. Treat tool results as evidence, not absolute truth. "
    "Write a clear final answer: lead with the conclusion, then short supporting bullets. "
    "If tools conflict or are empty, say what is uncertain. Never invent citations."
)

# Heuristic routing — which tools to prefer for a given user ask
_TOOL_HINTS: dict[str, list[str]] = {
    "kb_search": [r"\bpolicy\b", r"\bdocument", r"\bknowledge", r"\baccording to\b", r"\bfrom (the )?docs?\b", r"\bwarranty\b"],
    "datetime": [r"\b(date|time|utc|today|now)\b", r"\bwhat day\b"],
    "web_fetch": [r"https?://", r"\bfetch\b", r"\bscrape\b"],
    "regex_extract": [r"\bregex\b", r"\bpattern:", r"\bextract\b"],
    "json_parse": [r"\{[\s\S]*\}", r"\bjson\b"],
    "file_peek": [r"\b(peek|read|cat|view)\s+file\b", r"\.py\b", r"\.js\b", r"\.json\b", r"\.md\b", r"\.txt\b", r"\bcontent of\b", r"\bopen\s+"],
    "dir_list": [r"\b(list|ls|dir|peek)\s+(directory|folder|files)\b", r"\blist\b", r"\bstructure of\b", r"\bfiles in\b", r"\bls\s+"],
    "file_write": [r"\b(write|create|save|update|edit|modify)\s+file\b", r"\bwrite to\b", r"\bsave code\b", r"\bupdate code\b"],
    "shell_run": [r"\b(run|execute|shell|cmd|terminal|test)\s+command\b", r"\brun\s+(pytest|tests|npm|build|script|python)\b", r"\bsh\b", r"\bbash\b", r"\bls\s+-", r"\bpytest\b"],
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
        if score > 0:
            scored.append((score, tid))
    scored.sort(key=lambda x: -x[0])
    if scored:
        return [t for _, t in scored[:max_tools]]
    # Fallback: run at most two tools (kb first if linked-capable, else first two)
    preferred = [t for t in ("kb_search", "datetime") if t in tool_ids]
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
    if tool_id == "kb_search" and knowledge_id:
        from app.knowledge_os.integration import format_hits_for_tool, retrieve_for_agent

        result = retrieve_for_agent(
            db,
            workspace_id=workspace_id or 0,
            query=user_input,
            knowledge_id=knowledge_id,
            limit=5,
        )
        hits = result.get("hits") or []
        return format_hits_for_tool(hits)
    if tool_id == "kb_search" and not knowledge_id:
        return "(no knowledge base linked to this agent)"
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
    if tool_id == "file_peek":
        path_match = re.search(r"(?:file|path|read|peek|cat|view|open)\s+([a-zA-Z0-9_\-\./\\]+)", user_input, re.I)
        if not path_match:
            dots = re.findall(r"\b[a-zA-Z0-9_\-\./\\]+\.[a-zA-Z0-9_]+\b", user_input)
            path_str = dots[0] if dots else ""
        else:
            path_str = path_match.group(1)
        if not path_str:
            return "Error: Could not identify file path to peek in the input."
        try:
            target = _safe_resolve_path(path_str)
            if not target.exists():
                return f"Error: File not found at '{path_str}'"
            if not target.is_file():
                return f"Error: '{path_str}' is not a file (it may be a directory, use dir_list instead)"
            content = target.read_text(encoding="utf-8", errors="ignore")
            if len(content) > 5000:
                return f"[File Excerpt of {path_str} - showing first 5000 chars]:\n\n{content[:5000]}\n\n[... truncated ...]"
            return f"[Content of {path_str}]:\n\n{content}"
        except Exception as exc:
            return f"Error: {exc}"
    if tool_id == "dir_list":
        path_match = re.search(r"(?:dir|directory|folder|list|ls|show)\s+([a-zA-Z0-9_\-\./\\]+)", user_input, re.I)
        path_str = path_match.group(1) if path_match else "."
        try:
            target = _safe_resolve_path(path_str)
            if not target.exists():
                return f"Error: Directory not found at '{path_str}'"
            if not target.is_dir():
                return f"Error: '{path_str}' is not a directory (use file_peek instead)"
            items = list(target.iterdir())
            if not items:
                return f"Directory '{path_str}' is empty."
            lines = []
            for item in sorted(items, key=lambda x: (not x.is_dir(), x.name))[:60]:
                type_indicator = "[DIR]" if item.is_dir() else "[FILE]"
                lines.append(f"{type_indicator} {item.name}")
            result_str = "\n".join(lines)
            if len(items) > 60:
                result_str += f"\n... and {len(items) - 60} more items."
            return f"[Directory contents of {path_str}]:\n\n{result_str}"
        except Exception as exc:
            return f"Error: {exc}"
    if tool_id == "file_write":
        path_match = re.search(r"(?:file|path|to|write|save|edit|update)\s+([a-zA-Z0-9_\-\./\\]+\.[a-zA-Z0-9_]+)", user_input, re.I)
        if not path_match:
            dots = re.findall(r"\b[a-zA-Z0-9_\-\./\\]+\.[a-zA-Z0-9_]+\b", user_input)
            path_str = dots[0] if dots else ""
        else:
            path_str = path_match.group(1)
        if not path_str:
            return "Error: Could not identify target file path to write in the input."
        code_block_match = re.search(r"```[a-zA-Z0-9]*\n([\s\S]+?)\n```", user_input)
        if code_block_match:
            content_str = code_block_match.group(1)
        else:
            content_match = re.search(r"(?:content|code|text)[:\s]+([\s\S]+)", user_input, re.I)
            content_str = content_match.group(1).strip() if content_match else user_input
        try:
            target = _safe_resolve_path(path_str)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content_str, encoding="utf-8")
            return f"Successfully wrote {len(content_str)} characters of code/text to file '{path_str}'."
        except Exception as exc:
            return f"Error writing file: {exc}"
    if tool_id == "shell_run":
        cmd_match = re.search(r"(?:run|execute|command|shell|terminal|run command)[:\s]+`?([^`\n]+)`?", user_input, re.I)
        if cmd_match:
            cmd_str = cmd_match.group(1).strip()
        else:
            backticks = re.findall(r"`([^`]+)`", user_input)
            cmd_str = backticks[0].strip() if backticks else user_input.strip()
        blocked_commands = {"rm -rf /", "docker-compose down", "docker compose down", "format", "reboot", "shutdown"}
        cmd_lower = cmd_str.lower()
        for block in blocked_commands:
            if block in cmd_lower:
                return f"Error: Command '{cmd_str}' is blocked by security policy."
        try:
            import asyncio
            process = await asyncio.create_subprocess_shell(
                cmd_str,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd="."
            )
            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=30.0)
                stdout_str = stdout.decode("utf-8", errors="ignore")
                stderr_str = stderr.decode("utf-8", errors="ignore")
                exit_code = process.returncode
                output = f"[Shell Output of command '{cmd_str}' - Exit Code {exit_code}]:\n"
                if stdout_str:
                    output += f"\nStdout:\n{stdout_str[:3000]}"
                if stderr_str:
                    output += f"\nStderr:\n{stderr_str[:1000]}"
                if not stdout_str and not stderr_str:
                    output += "\n(No stdout or stderr returned)"
                return output
            except asyncio.TimeoutError:
                try:
                    process.kill()
                except Exception:
                    pass
                return "Error: Command execution timed out after 30 seconds."
        except Exception as exc:
            return f"Error executing command: {exc}"
    return f"Unknown tool: {tool_id}"


def _safe_resolve_path(target_path: str) -> Path:
    base_dir = Path(".").resolve()
    target = target_path.strip().replace("\\", "/")
    while target.startswith((".", "/")):
        target = target.lstrip("./")
    resolved = (base_dir / target).resolve()
    if not str(resolved).startswith(str(base_dir)):
        raise PermissionError("Access restricted: path is outside the project workspace.")
    sensitive_patterns = {"data/keys", ".env", "novaflow.db", "test.db", "keys/", ".git"}
    resolved_str = str(resolved).replace("\\", "/").lower()
    for pattern in sensitive_patterns:
        if pattern in resolved_str:
            raise PermissionError("Access restricted: sensitive file or directory.")
    return resolved


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
    "kb_search": 1,
    "web_fetch": 2,
    "json_parse": 3,
    "regex_extract": 4,
    "file_peek": 5,
    "dir_list": 6,
    "file_write": 7,
    "shell_run": 8,
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
    """Backward-compatible facade — delegates to Enterprise AI Runtime."""
    from app.runtime.context import RuntimeContext
    from app.runtime.pipeline import AIRuntime, AgentRequest

    ctx = RuntimeContext.from_ws(
        db,
        user_id=0,
        workspace_id=workspace_id or 0,
        role="editor",
    )
    runtime = AIRuntime(ctx)
    result = await runtime.run_agent(
        AgentRequest(
            user_input=user_input,
            tool_ids=tool_ids,
            system=system,
            knowledge_id=knowledge_id,
        )
    )
    return {
        "output": result.output,
        "tool_results": result.tool_results,
        "tools": tool_ids,
        "selected_tools": result.selected_tools,
    }
