import json
import re
import time
import asyncio
from typing import Any, Awaitable, Callable

import httpx
from sqlalchemy.orm import Session

from app.database import KnowledgeBase, UsageEvent, Workflow, WorkflowPendingRun, WorkflowRun, WorkflowVersion
from app.services.integrations import send_notification
from app.services.knowledge import search_chunks_semantic
from app.services.llm import stream_chat, stream_chat_sync

EmitFn = Callable[[dict], Awaitable[None]] | None


FLOW_TYPE_WORKFLOW = 10

# WorkflowRun.status: 1 = completed, 2 = error (step failure)
RUN_STATUS_OK = 1
RUN_STATUS_ERROR = 2


def _run_status_from_steps(steps: list) -> int:
    for step in steps or []:
        if isinstance(step, dict) and step.get("status") == "error":
            return RUN_STATUS_ERROR
    return RUN_STATUS_OK


DEFAULT_LLM_PROMPT = (
    "You are a precise NovaFlow assistant. Answer clearly in well-structured prose. "
    "Prefer short paragraphs and bullet lists when helpful. If context is missing, say what is unknown."
)

DEFAULT_RAG_GRAPH = {
    "nodes": [
        {"id": "trigger", "type": "trigger", "x": 60, "y": 140, "data": {"label": "User input"}},
        {"id": "retrieve", "type": "retrieve", "x": 260, "y": 140, "data": {"knowledge_id": None, "limit": 6}},
        {
            "id": "llm",
            "type": "llm",
            "x": 460,
            "y": 140,
            "data": {
                "prompt": (
                    "Answer the question using ONLY the retrieved context when available. "
                    "Structure the reply as: 1) Direct answer 2) Supporting bullets 3) Sources cited as [n]. "
                    "If context is empty or insufficient, say so and give the best cautious answer."
                )
            },
        },
        {"id": "output", "type": "output", "x": 660, "y": 140, "data": {"label": "Response"}},
    ],
    "edges": [
        {"from": "trigger", "to": "retrieve"},
        {"from": "retrieve", "to": "llm"},
        {"from": "llm", "to": "output"},
    ],
}

TEMPLATES = {
    "rag": {"name": "RAG Q&A pipeline", "desc": "Retrieve docs then answer with LLM", "graph": DEFAULT_RAG_GRAPH},
    "support": {
        "name": "Support triage",
        "desc": "Classify and draft support replies",
        "graph": {
            "nodes": [
                {"id": "trigger", "type": "trigger", "x": 60, "y": 140, "data": {"label": "Ticket"}},
                {
                    "id": "llm",
                    "type": "llm",
                    "x": 320,
                    "y": 140,
                    "data": {
                        "prompt": (
                            "You are a senior support agent. From the ticket, output exactly:\n"
                            "## Classification\nPriority (P1–P4) · Category · Sentiment\n"
                            "## Customer reply\nA clear, empathetic reply ready to send (3–6 sentences).\n"
                            "## Internal notes\n1–3 bullets for the team (root cause ideas / next step)."
                        )
                    },
                },
                {"id": "output", "type": "output", "x": 580, "y": 140, "data": {"label": "Draft"}},
            ],
            "edges": [{"from": "trigger", "to": "llm"}, {"from": "llm", "to": "output"}],
        },
    },
    "research": {
        "name": "Research brief",
        "desc": "Retrieve sources and synthesize a brief",
        "graph": {
            "nodes": [
                {"id": "trigger", "type": "trigger", "x": 40, "y": 140, "data": {"label": "Topic"}},
                {"id": "retrieve", "type": "retrieve", "x": 240, "y": 140, "data": {"knowledge_id": None, "limit": 8}},
                {
                    "id": "llm",
                    "type": "llm",
                    "x": 440,
                    "y": 140,
                    "data": {
                        "prompt": (
                            "Create a research brief from the retrieved sources. Use this structure:\n"
                            "## Executive summary\n2–3 sentences.\n"
                            "## Key findings\n3–6 bullets with source tags [n].\n"
                            "## Implications\nWhat to do next.\n"
                            "## Gaps\nWhat is still unknown."
                        )
                    },
                },
                {"id": "output", "type": "output", "x": 640, "y": 140, "data": {"label": "Brief"}},
            ],
            "edges": [
                {"from": "trigger", "to": "retrieve"},
                {"from": "retrieve", "to": "llm"},
                {"from": "llm", "to": "output"},
            ],
        },
    },
    "enrich": {
        "name": "Transform + LLM",
        "desc": "Format input with a template then run LLM",
        "graph": {
            "nodes": [
                {"id": "trigger", "type": "trigger", "x": 40, "y": 140, "data": {"label": "Raw input"}},
                {
                    "id": "transform",
                    "type": "transform",
                    "x": 240,
                    "y": 140,
                    "data": {"template": "User message:\n{{input}}\n\nRespond helpfully and specifically."},
                },
                {
                    "id": "llm",
                    "type": "llm",
                    "x": 440,
                    "y": 140,
                    "data": {
                        "prompt": (
                            "Turn the formatted message into a polished, actionable reply. "
                            "Lead with the answer, then add short supporting detail. Avoid filler."
                        )
                    },
                },
                {"id": "output", "type": "output", "x": 640, "y": 140, "data": {"label": "Reply"}},
            ],
            "edges": [
                {"from": "trigger", "to": "transform"},
                {"from": "transform", "to": "llm"},
                {"from": "llm", "to": "output"},
            ],
        },
    },
    "agent_loop": {
        "name": "Agent + review",
        "desc": "Tool agent with human review gate",
        "graph": {
            "nodes": [
                {"id": "trigger", "type": "trigger", "x": 40, "y": 140, "data": {"label": "Task"}},
                {
                    "id": "agent",
                    "type": "agent",
                    "x": 240,
                    "y": 140,
                    "data": {
                        "tools": ["summarize", "kb_search"],
                        "prompt": (
                            "You are a capable agent. Use tool results as evidence. "
                            "Return a final answer with: Summary · Details · Confidence (high/med/low)."
                        ),
                    },
                },
                {
                    "id": "human",
                    "type": "human",
                    "x": 440,
                    "y": 140,
                    "data": {"message": "Review and approve before finalize:\n\n{{output}}", "require_approval": True},
                },
                {"id": "output", "type": "output", "x": 640, "y": 140, "data": {"label": "Final"}},
            ],
            "edges": [
                {"from": "trigger", "to": "agent"},
                {"from": "agent", "to": "human"},
                {"from": "human", "to": "output"},
            ],
        },
    },
    "batch": {
        "name": "Batch loop",
        "desc": "Process each line of input in parallel tasks",
        "graph": {
            "nodes": [
                {"id": "trigger", "type": "trigger", "x": 40, "y": 140, "data": {"label": "Lines"}},
                {
                    "id": "loop",
                    "type": "loop",
                    "x": 260,
                    "y": 140,
                    "data": {
                        "max": 5,
                        "prompt": (
                            "For this item, return one compact line: "
                            "RESULT: <outcome> | WHY: <short reason>\nItem: {{item}}"
                        ),
                    },
                },
                {"id": "output", "type": "output", "x": 480, "y": 140, "data": {"label": "Results"}},
            ],
            "edges": [{"from": "trigger", "to": "loop"}, {"from": "loop", "to": "output"}],
        },
    },
    "telegram_qa": {
        "name": "Telegram Q&A bot",
        "desc": "Answer questions and reply via Telegram",
        "graph": {
            "nodes": [
                {"id": "trigger", "type": "trigger", "x": 40, "y": 140, "data": {"label": "Telegram message"}},
                {
                    "id": "llm",
                    "type": "llm",
                    "x": 260,
                    "y": 140,
                    "data": {
                        "prompt": (
                            "You are a project assistant on Telegram. Reply in under 800 characters, "
                            "plain text (no markdown tables). Lead with the answer, then one short tip if useful."
                        )
                    },
                },
                {
                    "id": "notify",
                    "type": "notify",
                    "x": 460,
                    "y": 140,
                    "data": {"channel": "telegram", "to": "{{chat_id}}", "message": "{{output}}"},
                },
                {"id": "output", "type": "output", "x": 660, "y": 140, "data": {"label": "Sent"}},
            ],
            "edges": [
                {"from": "trigger", "to": "llm"},
                {"from": "llm", "to": "notify"},
                {"from": "notify", "to": "output"},
            ],
        },
    },
    "daily_digest": {
        "name": "Daily digest email",
        "desc": "Retrieve knowledge and email a summary",
        "graph": {
            "nodes": [
                {"id": "trigger", "type": "trigger", "x": 40, "y": 140, "data": {"label": "Schedule"}},
                {"id": "retrieve", "type": "retrieve", "x": 220, "y": 140, "data": {"knowledge_id": None, "limit": 6}},
                {
                    "id": "llm",
                    "type": "llm",
                    "x": 400,
                    "y": 140,
                    "data": {
                        "prompt": (
                            "Write a daily digest email body for the team from the retrieved notes. Structure:\n"
                            "Subject line suggestion (one line)\n"
                            "## Highlights\n3–5 bullets\n"
                            "## Risks / blockers\nbullets or 'None'\n"
                            "## Asks\nclear next actions with owners if mentioned.\n"
                            "Tone: crisp, no fluff."
                        )
                    },
                },
                {
                    "id": "notify",
                    "type": "notify",
                    "x": 580,
                    "y": 140,
                    "data": {
                        "channel": "email",
                        "to": "team@example.com",
                        "subject": "Daily digest — {{input}}",
                        "message": "{{output}}",
                    },
                },
                {"id": "output", "type": "output", "x": 760, "y": 140, "data": {"label": "Emailed"}},
            ],
            "edges": [
                {"from": "trigger", "to": "retrieve"},
                {"from": "retrieve", "to": "llm"},
                {"from": "llm", "to": "notify"},
                {"from": "notify", "to": "output"},
            ],
        },
    },
    "eval_alert": {
        "name": "Eval alert webhook",
        "desc": "Format eval results and notify via webhook",
        "graph": {
            "nodes": [
                {"id": "trigger", "type": "trigger", "x": 40, "y": 140, "data": {"label": "Eval payload"}},
                {"id": "transform", "type": "transform", "x": 240, "y": 140, "data": {"template": "Eval alert:\n{{input}}"}},
                {"id": "notify", "type": "notify", "x": 440, "y": 140, "data": {"channel": "webhook", "to": "https://hooks.example.com/eval", "subject": "Eval regression", "message": "{{output}}"}},
                {"id": "output", "type": "output", "x": 640, "y": 140, "data": {"label": "Notified"}},
            ],
            "edges": [
                {"from": "trigger", "to": "transform"},
                {"from": "transform", "to": "notify"},
                {"from": "notify", "to": "output"},
            ],
        },
    },
    "jira_ticket": {
        "name": "Jira ticket from input",
        "desc": "Create a Jira issue from workflow output",
        "graph": {
            "nodes": [
                {"id": "trigger", "type": "trigger", "x": 40, "y": 140, "data": {"label": "Bug report"}},
                {"id": "llm", "type": "llm", "x": 240, "y": 140, "data": {
                    "prompt": (
                        "Convert the input into a Jira-ready ticket. Output ONLY:\n"
                        "TITLE: <one clear line under 80 chars>\n"
                        "DESCRIPTION:\n"
                        "- Context\n- Steps / evidence\n- Expected vs actual (if a bug)\n"
                        "Keep TITLE usable as the issue summary."
                    )
                }},
                {
                    "id": "jira",
                    "type": "jira",
                    "x": 460,
                    "y": 140,
                    "data": {
                        "action": "create",
                        "project_key": "NF",
                        "issue_type": "Task",
                        "summary": "{{output}}",
                        "description": "{{input}}",
                        "set_output": True,
                    },
                },
                {"id": "output", "type": "output", "x": 680, "y": 140, "data": {"label": "Ticket"}},
            ],
            "edges": [
                {"from": "trigger", "to": "llm"},
                {"from": "llm", "to": "jira"},
                {"from": "jira", "to": "output"},
            ],
        },
    },
    "slack_alert": {
        "name": "Slack alert",
        "desc": "Summarize input and post to Slack",
        "graph": {
            "nodes": [
                {"id": "trigger", "type": "trigger", "x": 40, "y": 140, "data": {"label": "Alert"}},
                {
                    "id": "llm",
                    "type": "llm",
                    "x": 240,
                    "y": 140,
                    "data": {
                        "prompt": (
                            "Write a Slack alert from the input. Format:\n"
                            "*What happened* — one sentence\n"
                            "*Impact* — one sentence\n"
                            "*Action* — one concrete next step\n"
                            "Keep under 500 characters. No hashtags."
                        )
                    },
                },
                {
                    "id": "notify",
                    "type": "notify",
                    "x": 460,
                    "y": 140,
                    "data": {
                        "channel": "slack",
                        "to": "",
                        "subject": "NovaFlow alert",
                        "message": "{{output}}",
                    },
                },
                {"id": "output", "type": "output", "x": 680, "y": 140, "data": {"label": "Posted"}},
            ],
            "edges": [
                {"from": "trigger", "to": "llm"},
                {"from": "llm", "to": "notify"},
                {"from": "notify", "to": "output"},
            ],
        },
    },
    "github_issue": {
        "name": "GitHub issue from input",
        "desc": "Create a GitHub issue from workflow output",
        "graph": {
            "nodes": [
                {"id": "trigger", "type": "trigger", "x": 40, "y": 140, "data": {"label": "Report"}},
                {
                    "id": "llm",
                    "type": "llm",
                    "x": 240,
                    "y": 140,
                    "data": {
                        "prompt": (
                            "Rewrite as a GitHub issue. Output ONLY:\n"
                            "TITLE: <imperative, under 70 chars>\n"
                            "BODY:\n"
                            "## Summary\n## Steps to reproduce\n## Expected\n## Actual\n"
                        )
                    },
                },
                {
                    "id": "github",
                    "type": "github",
                    "x": 460,
                    "y": 140,
                    "data": {
                        "action": "create",
                        "repo": "",
                        "title": "{{output}}",
                        "body": "{{input}}",
                        "labels": "bug",
                        "set_output": True,
                    },
                },
                {"id": "output", "type": "output", "x": 680, "y": 140, "data": {"label": "Issue"}},
            ],
            "edges": [
                {"from": "trigger", "to": "llm"},
                {"from": "llm", "to": "github"},
                {"from": "github", "to": "output"},
            ],
        },
    },
    "discord_alert": {
        "name": "Discord alert",
        "desc": "Summarize input and post to Discord",
        "graph": {
            "nodes": [
                {"id": "trigger", "type": "trigger", "x": 40, "y": 140, "data": {"label": "Alert"}},
                {
                    "id": "llm",
                    "type": "llm",
                    "x": 240,
                    "y": 140,
                    "data": {
                        "prompt": (
                            "Write a Discord alert. Use plain text with **bold** sparingly. "
                            "3 short lines: What · Impact · Next step. Under 400 characters."
                        )
                    },
                },
                {
                    "id": "notify",
                    "type": "notify",
                    "x": 460,
                    "y": 140,
                    "data": {
                        "channel": "discord",
                        "to": "",
                        "subject": "NovaFlow alert",
                        "message": "{{output}}",
                    },
                },
                {"id": "output", "type": "output", "x": 680, "y": 140, "data": {"label": "Posted"}},
            ],
            "edges": [
                {"from": "trigger", "to": "llm"},
                {"from": "llm", "to": "notify"},
                {"from": "notify", "to": "output"},
            ],
        },
    },
    "linear_issue": {
        "name": "Linear issue from input",
        "desc": "Create a Linear issue from workflow output",
        "graph": {
            "nodes": [
                {"id": "trigger", "type": "trigger", "x": 40, "y": 140, "data": {"label": "Ticket"}},
                {
                    "id": "llm",
                    "type": "llm",
                    "x": 240,
                    "y": 140,
                    "data": {
                        "prompt": (
                            "Rewrite as a Linear issue. Output ONLY:\n"
                            "TITLE: <clear under 80 chars>\n"
                            "DESCRIPTION:\n"
                            "Problem, acceptance criteria (bullets), and any links mentioned."
                        )
                    },
                },
                {
                    "id": "linear",
                    "type": "linear",
                    "x": 460,
                    "y": 140,
                    "data": {
                        "action": "create",
                        "team_id": "",
                        "title": "{{output}}",
                        "description": "{{input}}",
                        "set_output": True,
                    },
                },
                {"id": "output", "type": "output", "x": 680, "y": 140, "data": {"label": "Issue"}},
            ],
            "edges": [
                {"from": "trigger", "to": "llm"},
                {"from": "llm", "to": "linear"},
                {"from": "linear", "to": "output"},
            ],
        },
    },
}


def workflow_dict(w: Workflow) -> dict:
    try:
        graph = json.loads(w.graph_json or "{}")
    except json.JSONDecodeError:
        graph = {"nodes": [], "edges": []}
    return {
        "id": w.id,
        "name": w.name,
        "desc": w.desc or "",
        "description": w.desc or "",
        "status": w.status,
        "flow_type": FLOW_TYPE_WORKFLOW,
        "graph": graph,
        "user_id": w.user_id,
        "write": True,
        "create_time": w.create_time.isoformat() if w.create_time else None,
        "update_time": w.update_time.isoformat() if w.update_time else None,
        "webhook_token": getattr(w, "webhook_token", "") or "",
        "is_public": int(getattr(w, "is_public", 0) or 0),
        "run_webhook_url": getattr(w, "run_webhook_url", "") or "",
    }


MAX_WORKFLOW_VERSIONS = 25


def snapshot_workflow_version(db: Session, w: Workflow, user_id: int) -> None:
    last = (
        db.query(WorkflowVersion)
        .filter(WorkflowVersion.workflow_id == w.id)
        .order_by(WorkflowVersion.version_no.desc())
        .first()
    )
    version_no = (last.version_no + 1) if last else 1
    row = WorkflowVersion(
        workflow_id=w.id,
        version_no=version_no,
        name=w.name,
        desc=w.desc or "",
        graph_json=w.graph_json or "{}",
        user_id=user_id,
    )
    db.add(row)
    db.flush()
    excess = (
        db.query(WorkflowVersion)
        .filter(WorkflowVersion.workflow_id == w.id)
        .order_by(WorkflowVersion.version_no.desc())
        .offset(MAX_WORKFLOW_VERSIONS)
        .all()
    )
    for old in excess:
        db.delete(old)


def get_workflow_version(db: Session, workflow_id: str, version_id: int) -> dict | None:
    row = db.get(WorkflowVersion, version_id)
    if not row or row.workflow_id != workflow_id:
        return None
    try:
        graph = json.loads(row.graph_json or "{}")
    except json.JSONDecodeError:
        graph = {"nodes": [], "edges": []}
    return {
        "id": row.id,
        "version_no": row.version_no,
        "name": row.name,
        "desc": row.desc or "",
        "graph": graph,
        "create_time": row.create_time.isoformat() if row.create_time else None,
    }


def list_workflow_versions(db: Session, workflow_id: str) -> list[dict]:
    rows = (
        db.query(WorkflowVersion)
        .filter(WorkflowVersion.workflow_id == workflow_id)
        .order_by(WorkflowVersion.version_no.desc())
        .limit(MAX_WORKFLOW_VERSIONS)
        .all()
    )
    return [
        {
            "id": r.id,
            "version_no": r.version_no,
            "name": r.name,
            "desc": r.desc or "",
            "create_time": r.create_time.isoformat() if r.create_time else None,
        }
        for r in rows
    ]


def restore_workflow_version(db: Session, w: Workflow, version_id: int, user_id: int) -> dict | None:
    row = db.get(WorkflowVersion, version_id)
    if not row or row.workflow_id != w.id:
        return None
    snapshot_workflow_version(db, w, user_id)
    w.name = row.name
    w.desc = row.desc or ""
    w.graph_json = row.graph_json or "{}"
    from datetime import datetime

    w.update_time = datetime.utcnow()
    db.commit()
    db.refresh(w)
    return workflow_dict(w)


def _node_map(graph: dict) -> dict[str, dict]:
    return {n["id"]: n for n in graph.get("nodes", []) if n.get("id")}


def _next_nodes(graph: dict, node_id: str) -> list[str]:
    return [e["to"] for e in graph.get("edges", []) if e.get("from") == node_id]


def _topo_order(graph: dict) -> list[dict]:
    nodes = graph.get("nodes", [])
    if not nodes:
        return []
    edges = graph.get("edges", [])
    incoming = {n["id"]: 0 for n in nodes}
    for e in edges:
        if e.get("to") in incoming:
            incoming[e["to"]] += 1
    queue = [nid for nid, c in incoming.items() if c == 0]
    order = []
    nmap = _node_map(graph)
    while queue:
        nid = queue.pop(0)
        if nid in nmap:
            order.append(nmap[nid])
        for e in edges:
            if e.get("from") == nid:
                incoming[e["to"]] -= 1
                if incoming[e["to"]] == 0:
                    queue.append(e["to"])
    if len(order) < len(nodes):
        order = nodes
    return order


def _apply_template(template: str, context: dict) -> str:
    text = template or ""
    # Prefer longer / known keys first so nested names don't partial-clash
    keys = sorted(
        (
            "retrieved",
            "transform",
            "linear_issue",
            "github_issue",
            "jira_key",
            "github_url",
            "linear_url",
            "slack_channel",
            "slack_user",
            "agent_tools",
            "output",
            "input",
            "http",
            "chat_id",
        ),
        key=len,
        reverse=True,
    )
    for key in keys:
        if key in context or key in (
            "input",
            "retrieved",
            "output",
            "http",
            "transform",
            "chat_id",
        ):
            val = context.get(key)
            if isinstance(val, (dict, list)):
                try:
                    val = json.dumps(val, ensure_ascii=False)[:4000]
                except Exception:
                    val = str(val)[:4000]
            text = text.replace(f"{{{{{key}}}}}", str(val or ""))
    return text


def _extract_titled_fields(text: str) -> tuple[str, str]:
    """Parse TITLE:/DESCRIPTION: or TITLE:/BODY: blocks from LLM issue drafts."""
    raw = (text or "").strip()
    if not raw:
        return "", ""
    title = ""
    body = raw
    m = re.search(r"(?im)^\s*TITLE:\s*(.+)$", raw)
    if m:
        title = m.group(1).strip()
        rest = raw[m.end() :].strip()
        for marker in ("DESCRIPTION:", "BODY:"):
            idx = rest.upper().find(marker)
            if idx >= 0:
                body = rest[idx + len(marker) :].strip()
                break
        else:
            body = rest
    else:
        # First non-empty line as title, rest as body
        lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
        if lines:
            title = lines[0][:255]
            body = "\n".join(lines[1:]) if len(lines) > 1 else raw
    return title[:255], body


def _format_notify_body(channel: str, subject: str, body: str) -> str:
    """Light channel-aware cleanup so digests/alerts stay readable."""
    text = (body or "").strip()
    ch = (channel or "").lower()
    if ch == "telegram":
        text = re.sub(r"[#*_`]{2,}", "", text)
        return text[:3500]
    if ch == "slack":
        return text[:3500]
    if ch == "discord":
        return text[:1900]
    if ch == "email" and subject and subject not in text[:120]:
        return text
    return text


async def _fetch_http(url: str, method: str = "GET", body: str = "") -> str:
    method = (method or "GET").upper()
    timeout = httpx.Timeout(15.0)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        if method == "POST":
            resp = await client.post(url, content=body or None)
        else:
            resp = await client.get(url)
        resp.raise_for_status()
        content_type = resp.headers.get("content-type", "")
        if "json" in content_type:
            return json.dumps(resp.json())[:8000]
        return (resp.text or "")[:8000]


def log_usage(
    db: Session,
    user_id: int,
    event_type: str,
    resource_id: str,
    meta: dict | None = None,
    workspace_id: int | None = None,
):
    db.add(
        UsageEvent(
            user_id=user_id,
            workspace_id=workspace_id,
            event_type=event_type,
            resource_id=resource_id,
            meta=json.dumps(meta or {}),
        )
    )
    db.commit()


async def run_workflow(
    db: Session,
    workflow: Workflow,
    user_id: int,
    user_input: str,
    workspace_id: int | None = None,
    extra_context: dict | None = None,
) -> dict[str, Any]:
    start = time.perf_counter()
    try:
        graph = json.loads(workflow.graph_json or "{}")
    except json.JSONDecodeError:
        graph = {"nodes": [], "edges": []}

    initial_context = {"input": user_input, "retrieved": "", "output": ""}
    if extra_context:
        initial_context.update(extra_context)
    context, steps, pause_node = await _execute_graph(
        db, user_id, graph, user_input.strip(), workspace_id=workspace_id, initial_context=initial_context
    )
    if pause_node:
        pending = WorkflowPendingRun(
            workflow_id=workflow.id,
            user_id=user_id,
            workspace_id=workspace_id or workflow.workspace_id,
            context_json=json.dumps(context),
            graph_json=json.dumps(graph),
            pause_after_node=pause_node,
            steps_json=json.dumps(steps),
            status=0,
        )
        db.add(pending)
        db.commit()
        db.refresh(pending)
        return {
            "workflow_id": workflow.id,
            "output": context.get("output") or "",
            "steps": steps,
            "duration_ms": int((time.perf_counter() - start) * 1000),
            "pending_run_id": pending.id,
            "status": "pending_human",
        }

    duration_ms = int((time.perf_counter() - start) * 1000)
    final_output = context["output"] or context["input"]
    run_status = _run_status_from_steps(steps)

    run = WorkflowRun(
        workflow_id=workflow.id,
        user_id=user_id,
        workspace_id=workspace_id or workflow.workspace_id,
        input_text=user_input[:4000],
        output_text=final_output[:8000],
        status=run_status,
        duration_ms=duration_ms,
        steps_json=json.dumps(steps),
    )
    db.add(run)
    log_usage(db, user_id, "workflow_run", workflow.id, {"duration_ms": duration_ms}, workspace_id or workflow.workspace_id)
    db.commit()

    webhook_url = getattr(workflow, "run_webhook_url", "") or ""
    if webhook_url.strip():
        from app.services.webhooks import post_webhook

        await post_webhook(
            webhook_url,
            {
                "workflow_id": workflow.id,
                "run_id": run.id,
                "output": final_output[:2000],
                "duration_ms": duration_ms,
                "status": "completed" if run_status == RUN_STATUS_OK else "error",
            },
            event="workflow.run.completed",
        )

    return {
        "workflow_id": workflow.id,
        "output": final_output,
        "steps": steps,
        "duration_ms": duration_ms,
        "run_id": run.id,
        "status": "completed" if run_status == RUN_STATUS_OK else "error",
    }


async def run_workflow_with_progress(
    db: Session,
    workflow: Workflow,
    user_id: int,
    user_input: str,
    emit: EmitFn,
    workspace_id: int | None = None,
) -> dict[str, Any]:
    start = time.perf_counter()
    try:
        graph = json.loads(workflow.graph_json or "{}")
    except json.JSONDecodeError:
        graph = {"nodes": [], "edges": []}

    async def _emit(event: dict):
        if emit:
            await emit(event)

    context, steps, pause_node = await _execute_graph(
        db, user_id, graph, user_input.strip(), emit=_emit, stream_llm=bool(emit), workspace_id=workspace_id
    )

    if pause_node:
        pending = WorkflowPendingRun(
            workflow_id=workflow.id,
            user_id=user_id,
            workspace_id=workspace_id or workflow.workspace_id,
            context_json=json.dumps(context),
            graph_json=json.dumps(graph),
            pause_after_node=pause_node,
            steps_json=json.dumps(steps),
            status=0,
        )
        db.add(pending)
        db.commit()
        db.refresh(pending)
        duration_ms = int((time.perf_counter() - start) * 1000)
        result = {
            "workflow_id": workflow.id,
            "output": context.get("output") or "",
            "steps": steps,
            "duration_ms": duration_ms,
            "pending_run_id": pending.id,
            "status": "pending_human",
        }
        await _emit({"type": "human_review", "pending_run_id": pending.id, "node_id": pause_node})
        await _emit({"type": "complete", **result})
        return result

    duration_ms = int((time.perf_counter() - start) * 1000)
    final_output = context["output"] or context["input"]
    run_status = _run_status_from_steps(steps)

    run = WorkflowRun(
        workflow_id=workflow.id,
        user_id=user_id,
        workspace_id=workspace_id or workflow.workspace_id,
        input_text=user_input[:4000],
        output_text=final_output[:8000],
        status=run_status,
        duration_ms=duration_ms,
        steps_json=json.dumps(steps),
    )
    db.add(run)
    log_usage(db, user_id, "workflow_run", workflow.id, {"duration_ms": duration_ms}, workspace_id or workflow.workspace_id)
    db.commit()

    result = {
        "workflow_id": workflow.id,
        "output": final_output,
        "steps": steps,
        "duration_ms": duration_ms,
        "run_id": run.id,
        "status": "completed" if run_status == RUN_STATUS_OK else "error",
    }
    await _emit({"type": "complete", **result})
    return result


async def resume_workflow_pending(
    db: Session,
    pending_id: int,
    user_id: int,
    *,
    approved: bool = True,
    note: str = "",
    workspace_id: int | None = None,
    emit: EmitFn = None,
) -> dict[str, Any]:
    pending = db.get(WorkflowPendingRun, pending_id)
    if not pending or pending.user_id != user_id or pending.status != 0:
        return {"status": "error", "message": "Pending run not found"}
    workflow = db.get(Workflow, pending.workflow_id)
    if not workflow:
        return {"status": "error", "message": "Workflow not found"}

    if not approved:
        pending.status = 2
        db.commit()
        return {"status": "rejected", "pending_run_id": pending_id}

    start = time.perf_counter()
    context = json.loads(pending.context_json or "{}")
    if note.strip():
        context["output"] = note.strip()
    graph = json.loads(pending.graph_json or "{}")
    steps = json.loads(pending.steps_json or "[]")

    async def _emit(event: dict):
        if emit:
            await emit(event)

    context, steps, pause_node = await _execute_graph(
        db,
        user_id,
        graph,
        context.get("input") or "",
        emit=_emit,
        stream_llm=bool(emit),
        workspace_id=workspace_id or pending.workspace_id,
        initial_context=context,
        skip_until_after=pending.pause_after_node,
        initial_steps=steps,
    )

    if pause_node:
        pending.context_json = json.dumps(context)
        pending.steps_json = json.dumps(steps)
        pending.pause_after_node = pause_node
        db.commit()
        return {
            "status": "pending_human",
            "pending_run_id": pending.id,
            "steps": steps,
            "output": context.get("output") or "",
        }

    duration_ms = int((time.perf_counter() - start) * 1000)
    final_output = context["output"] or context.get("input") or ""
    pending.status = 1
    run_status = _run_status_from_steps(steps)
    run = WorkflowRun(
        workflow_id=workflow.id,
        user_id=user_id,
        workspace_id=workspace_id or pending.workspace_id,
        input_text=(context.get("input") or "")[:4000],
        output_text=final_output[:8000],
        status=run_status,
        duration_ms=duration_ms,
        steps_json=json.dumps(steps),
    )
    db.add(run)
    db.commit()
    return {
        "status": "completed" if run_status == RUN_STATUS_OK else "error",
        "workflow_id": workflow.id,
        "output": final_output,
        "steps": steps,
        "duration_ms": duration_ms,
        "run_id": run.id,
    }


async def _execute_graph(
    db: Session,
    user_id: int,
    graph: dict,
    user_input: str,
    *,
    skip_llm: bool = False,
    stream_llm: bool = False,
    emit: EmitFn = None,
    workspace_id: int | None = None,
    initial_context: dict | None = None,
    skip_until_after: str | None = None,
    initial_steps: list | None = None,
) -> tuple[dict, list[dict], str | None]:
    context = dict(initial_context) if initial_context else {"input": user_input, "retrieved": "", "output": ""}
    if user_input:
        context["input"] = user_input
    steps: list[dict] = list(initial_steps or [])
    llm_messages: tuple[str, str] | None = None
    passed_pause = not skip_until_after

    async def _emit(event: dict):
        if emit:
            await emit(event)

    for node in _topo_order(graph):
        if not passed_pause:
            if node.get("id") == skip_until_after:
                passed_pause = True
            continue
        ntype = node.get("type")
        data = node.get("data") or {}
        step = {"node_id": node.get("id"), "type": ntype, "status": "running"}
        await _emit({"type": "step", "phase": "start", "step": {**step}})

        if ntype == "trigger":
            step["output"] = context["input"]
            step["status"] = "ok"
        elif ntype == "retrieve":
            kid = data.get("knowledge_id")
            limit = int(data.get("limit") or 5)
            hits = []
            if kid:
                kb = db.get(KnowledgeBase, kid)
                if kb and (not workspace_id or kb.workspace_id == workspace_id):
                    hits = search_chunks_semantic(db, kid, context["input"], limit)
            parts = []
            for i, hit in enumerate(hits, 1):
                source = hit.get("file_name") or "document"
                score = hit.get("score")
                score_bit = f" · score {score:.3f}" if isinstance(score, (int, float)) else ""
                text = (hit.get("text") or "").strip()[:1400]
                parts.append(f"[{i}] Source: {source}{score_bit}\n{text}")
            context["retrieved"] = "\n\n".join(parts)
            if not parts:
                context["retrieved"] = (
                    "(no knowledge matches — answer carefully and state that no documents were found)"
                )
            step["output"] = context["retrieved"][:800] + ("…" if len(context["retrieved"]) > 800 else "")
            step["hits"] = len(hits)
            step["status"] = "ok"
        elif ntype == "transform":
            template = data.get("template") or "{{input}}"
            rendered = _apply_template(template, context)
            context["transform"] = rendered
            context["output"] = rendered
            step["output"] = rendered[:500] + ("…" if len(rendered) > 500 else "")
            step["status"] = "ok"
        elif ntype == "condition":
            keyword = (data.get("keyword") or "").strip()
            haystack = context.get("input") or ""
            matched = bool(keyword and re.search(re.escape(keyword), haystack, re.I))
            branch = data.get("then_text") if matched else data.get("else_text")
            branch = _apply_template(branch or "", context) if branch else haystack
            context["output"] = branch
            step["matched"] = matched
            step["output"] = branch[:500] + ("…" if len(branch) > 500 else "")
            step["status"] = "ok"
        elif ntype == "http":
            url = _apply_template(data.get("url") or "", context).strip()
            method = (data.get("method") or "GET").upper()
            body = _apply_template(data.get("body") or "", context)
            if not url:
                step["output"] = "(no url)"
                step["status"] = "error"
            else:
                try:
                    result = await _fetch_http(url, method, body)
                    context["http"] = result
                    if data.get("set_output", True):
                        context["output"] = result
                    step["output"] = result[:500] + ("…" if len(result) > 500 else "")
                    step["status"] = "ok"
                except Exception as exc:
                    step["output"] = str(exc)[:500]
                    step["status"] = "error"
        elif ntype == "notify":
            channel = (data.get("channel") or "telegram").strip().lower()
            to_addr = _apply_template(data.get("to") or "", context).strip()
            subject = _apply_template(data.get("subject") or "NovaFlow notification", context)
            body_text = _apply_template(data.get("message") or "{{output}}", context)
            body_text = _format_notify_body(channel, subject, body_text)
            bot_token = (data.get("bot_token") or "").strip()
            prior_output = context.get("output") or body_text
            result = await send_notification(
                channel,
                to_addr,
                subject,
                body_text,
                bot_token=bot_token,
                db=db,
                workspace_id=workspace_id,
            )
            detail = result.get("detail") or ("sent" if result.get("ok") else "failed")
            if result.get("ok"):
                # Keep the user-facing content as output; delivery note goes on the step only
                context["output"] = prior_output
                context["notify_status"] = detail
                step["output"] = f"{detail}\n---\n{(prior_output or '')[:400]}"
                step["status"] = "ok"
            else:
                step["output"] = detail
                step["status"] = "error"
        elif ntype == "jira":
            from app.services.gmail_jira import jira_create_issue, jira_update_issue

            action = (data.get("action") or "create").strip().lower()
            project_key = _apply_template(data.get("project_key") or "", context).strip()
            issue_type = _apply_template(data.get("issue_type") or "Task", context).strip() or "Task"
            issue_key = _apply_template(data.get("issue_key") or "", context).strip()
            summary = _apply_template(data.get("summary") or "{{output}}", context).strip()
            description = _apply_template(data.get("description") or "{{input}}", context).strip()
            titled, body_from_llm = _extract_titled_fields(summary)
            if titled:
                summary = titled
                if body_from_llm and description == (context.get("input") or ""):
                    description = body_from_llm
            try:
                if action == "update":
                    if not issue_key:
                        raise ValueError("issue_key required for Jira update")
                    result = await jira_update_issue(
                        db,
                        workspace_id,
                        issue_key=issue_key,
                        summary=summary,
                        description=description,
                    )
                    key = result.get("key") or issue_key
                else:
                    if not project_key:
                        raise ValueError("project_key required for Jira create")
                    result = await jira_create_issue(
                        db,
                        workspace_id,
                        project_key=project_key,
                        summary=summary or "NovaFlow issue",
                        description=description,
                        issue_type=issue_type,
                    )
                    key = result.get("key") or ""
                context["jira"] = result
                context["jira_key"] = key
                detail = f"Jira {action}: {key}" if key else f"Jira {action} ok"
                if data.get("set_output", True):
                    context["output"] = detail
                step["output"] = detail
                step["status"] = "ok"
            except Exception as exc:
                step["output"] = str(exc)[:500]
                step["status"] = "error"
        elif ntype == "github":
            from app.services.github_issues import github_create_issue, github_update_issue

            action = (data.get("action") or "create").strip().lower()
            repo = _apply_template(data.get("repo") or "", context).strip()
            title = _apply_template(data.get("title") or "{{output}}", context).strip()
            body_md = _apply_template(data.get("body") or "{{input}}", context).strip()
            titled, body_from_llm = _extract_titled_fields(title)
            if titled:
                title = titled
                if body_from_llm and body_md == (context.get("input") or ""):
                    body_md = body_from_llm
            issue_number = _apply_template(data.get("issue_number") or "", context).strip()
            labels_raw = _apply_template(data.get("labels") or "", context).strip()
            labels = [x.strip() for x in labels_raw.replace(";", ",").split(",") if x.strip()] if labels_raw else []
            try:
                if action == "update":
                    if not issue_number:
                        raise ValueError("issue_number required for GitHub update")
                    result = await github_update_issue(
                        db,
                        workspace_id,
                        repo=repo,
                        issue_number=issue_number,
                        title=title,
                        body=body_md,
                    )
                else:
                    result = await github_create_issue(
                        db,
                        workspace_id,
                        repo=repo,
                        title=title or "NovaFlow issue",
                        body=body_md,
                        labels=labels or None,
                    )
                num = result.get("number")
                html_url = result.get("html_url") or ""
                context["github"] = result
                context["github_issue"] = str(num or "")
                context["github_url"] = html_url
                detail = f"GitHub #{num}" if num else f"GitHub {action} ok"
                if html_url:
                    detail = f"{detail} · {html_url}"
                if data.get("set_output", True):
                    context["output"] = detail
                step["output"] = detail[:500]
                step["status"] = "ok"
            except Exception as exc:
                step["output"] = str(exc)[:500]
                step["status"] = "error"
        elif ntype == "linear":
            from app.services.linear_issues import linear_create_issue, linear_update_issue

            action = (data.get("action") or "create").strip().lower()
            team_id = _apply_template(data.get("team_id") or "", context).strip()
            title = _apply_template(data.get("title") or "{{output}}", context).strip()
            description = _apply_template(data.get("description") or "{{input}}", context).strip()
            titled, body_from_llm = _extract_titled_fields(title)
            if titled:
                title = titled
                if body_from_llm and description == (context.get("input") or ""):
                    description = body_from_llm
            issue_id = _apply_template(data.get("issue_id") or "", context).strip()
            try:
                if action == "update":
                    if not issue_id:
                        raise ValueError("issue_id required for Linear update")
                    result = await linear_update_issue(
                        db,
                        workspace_id,
                        issue_id=issue_id,
                        title=title,
                        description=description,
                    )
                else:
                    result = await linear_create_issue(
                        db,
                        workspace_id,
                        title=title or "NovaFlow issue",
                        description=description,
                        team_id=team_id,
                    )
                ident = result.get("identifier") or result.get("id") or ""
                url = result.get("url") or ""
                context["linear"] = result
                context["linear_issue"] = str(ident)
                context["linear_url"] = url
                detail = f"Linear {ident}" if ident else f"Linear {action} ok"
                if url:
                    detail = f"{detail} · {url}"
                if data.get("set_output", True):
                    context["output"] = detail
                step["output"] = detail[:500]
                step["status"] = "ok"
            except Exception as exc:
                step["output"] = str(exc)[:500]
                step["status"] = "error"
        elif ntype == "llm":
            prompt = (data.get("prompt") or DEFAULT_LLM_PROMPT).strip() or DEFAULT_LLM_PROMPT
            user_msg = context.get("transform") or context["input"]
            if context.get("retrieved"):
                user_msg = (
                    f"## Question\n{user_msg}\n\n"
                    f"## Retrieved context\n{context['retrieved']}\n\n"
                    f"## Instructions\nUse the context above. Cite sources as [n] when you rely on them."
                )
            llm_messages = (prompt, user_msg)
            if skip_llm:
                step["output"] = "(streaming)"
                step["status"] = "ok"
            elif stream_llm and emit:
                await _emit({"type": "llm_start"})
                reply = ""
                async for token in stream_chat(prompt, user_msg, db=db, workspace_id=workspace_id):
                    reply += token
                    await _emit({"type": "stream", "message": {"content": token}})
                context["output"] = reply
                step["output"] = reply[:500] + ("…" if len(reply) > 500 else "")
                step["status"] = "ok"
                await _emit({"type": "llm_end"})
            else:
                reply = await stream_chat_sync(prompt, user_msg, db=db, workspace_id=workspace_id)
                context["output"] = reply
                step["output"] = reply[:500] + ("…" if len(reply) > 500 else "")
                step["status"] = "ok"
        elif ntype == "output":
            step["output"] = context["output"] or context["input"]
            step["status"] = "ok"
        elif ntype == "loop":
            sep = data.get("separator") or "\n"
            max_iter = int(data.get("max") or 5)
            items = [x.strip() for x in (context.get("input") or "").split(sep) if x.strip()][:max_iter]
            prompt_tpl = data.get("prompt") or "Process: {{item}}"
            outputs = []
            for item in items:
                msg = prompt_tpl.replace("{{item}}", item)
                reply = await stream_chat_sync(
                    "Produce compact, consistent results. No preamble — only the requested format.",
                    msg,
                    db=db,
                    workspace_id=workspace_id,
                )
                outputs.append(f"• {item}\n  → {(reply or '').strip()}")
            merged = "\n\n".join(outputs) if outputs else context.get("input", "")
            context["output"] = merged
            step["output"] = merged[:500] + ("…" if len(merged) > 500 else "")
            step["iterations"] = len(items)
            step["status"] = "ok"
        elif ntype == "parallel":
            branches = data.get("branches") or ["Summary", "Key points", "Action items"]
            branches = [str(b) for b in branches][:5]
            tasks = [
                stream_chat_sync(
                    (
                        f"You are contributing one section of a multi-perspective analysis. "
                        f"Focus ONLY on: {b}. Be specific and concise (5–10 lines max)."
                    ),
                    context.get("input") or "",
                    db=db,
                    workspace_id=workspace_id,
                )
                for b in branches
            ]
            results = await asyncio.gather(*tasks)
            merged = "\n\n".join(f"## {b}\n{(r or '').strip()}" for b, r in zip(branches, results))
            context["output"] = merged
            step["output"] = merged[:500] + ("…" if len(merged) > 500 else "")
            step["status"] = "ok"
        elif ntype == "human":
            message = _apply_template(data.get("message") or "Review: {{output}}", context)
            if data.get("require_approval"):
                await _emit({"type": "human_review", "message": message, "node_id": node.get("id")})
                step["output"] = message
                step["status"] = "pending_human"
                steps.append(step)
                await _emit({"type": "step", "phase": "done", "step": step})
                context["human_pending"] = True
                return context, steps, node.get("id")
            context["output"] = context.get("output") or context.get("input") or message
            step["output"] = message[:500]
            step["status"] = "ok"
        elif ntype == "agent":
            from app.services.agent_tools import run_agent

            tools = data.get("tools") or ["summarize"]
            kid = data.get("knowledge_id")
            reply = await run_agent(
                db,
                context.get("input") or "",
                tools if isinstance(tools, list) else [tools],
                knowledge_id=kid,
                workspace_id=workspace_id,
                system=data.get("prompt")
                or (
                    "You are a capable NovaFlow agent. Use tool results as evidence. "
                    "Answer with: Summary · Details · Confidence (high/med/low). Avoid inventing facts."
                ),
            )
            text = reply.get("output") if isinstance(reply, dict) else str(reply or "")
            context["output"] = text
            if isinstance(reply, dict) and reply.get("tool_results"):
                context["agent_tools"] = reply["tool_results"]
            step["output"] = text[:500] + ("…" if len(text) > 500 else "")
            step["status"] = "ok"
        elif ntype == "subgraph":
            sub_id = data.get("workflow_id")
            sub = db.get(Workflow, sub_id) if sub_id else None
            if not sub or (workspace_id and sub.workspace_id != workspace_id):
                step["output"] = "(subgraph not found)"
                step["status"] = "error"
            else:
                try:
                    sub_graph = json.loads(sub.graph_json or "{}")
                except json.JSONDecodeError:
                    sub_graph = {"nodes": [], "edges": []}
                sub_ctx, sub_steps, _ = await _execute_graph(
                    db,
                    user_id,
                    sub_graph,
                    context.get("input") or "",
                    workspace_id=workspace_id,
                )
                context["output"] = sub_ctx.get("output") or ""
                step["output"] = (context["output"] or "")[:500]
                step["sub_steps"] = len(sub_steps)
                step["status"] = "ok"
        else:
            step["status"] = "skipped"

        steps.append(step)
        await _emit({"type": "step", "phase": "done", "step": step})

    if skip_llm and llm_messages:
        context["_llm_system"] = llm_messages[0]
        context["_llm_user"] = llm_messages[1]

    return context, steps, None


async def resolve_workflow_llm_messages(
    db: Session, workflow: Workflow, user_id: int, user_input: str
) -> tuple[str, str]:
    try:
        graph = json.loads(workflow.graph_json or "{}")
    except json.JSONDecodeError:
        graph = {"nodes": [], "edges": []}
    context, _, _ = await _execute_graph(db, user_id, graph, user_input.strip(), skip_llm=True)
    system = context.get("_llm_system") or DEFAULT_LLM_PROMPT
    user_msg = context.get("_llm_user") or user_input.strip()
    return system, user_msg
