"""Advanced chat helpers: clarify, boundary, Agent OS plan/HITL, heal."""

from __future__ import annotations

import re
from typing import Any

from sqlalchemy.orm import Session

from app.agent_os.hitl import request_approval, submit_feedback
from app.agent_os.planning import create_plan_session, decompose_goal
from app.agent_os.tasks import create_run
from app.composer.recipes import progress_steps
from app.composer.workflow_composer import heal_executable_graph
from app.database import AgentRun
from app.sandbox.twin import run_sandbox_trial

_VAGUE = re.compile(
    r"^(automate(\s+my)?\s+work|do\s+something|help\s+me|make\s+it\s+work|"
    r"build\s+(an?\s+)?automation|create\s+(an?\s+)?automation)\.?$",
    re.I,
)

_HOST_CONTROL = re.compile(
    r"\b(control\s+my\s+(pc|computer|laptop)|open\s+(chrome|firefox|browser)|"
    r"run\s+shell|execute\s+bash|cmd\.exe|powershell\s+script|"
    r"click\s+on\s+my\s+screen|take\s+over\s+my\s+(desktop|mouse))\b",
    re.I,
)

_COMPLEX = re.compile(
    r"\b(multi[- ]?agent|supervisor|research|figure\s+out|plan\s+and\s+execute|"
    r"team\s+of\s+agents|investigate|break\s+down|step\s+by\s+step\s+plan)\b",
    re.I,
)


def is_vague_goal(text: str) -> bool:
    t = (text or "").strip()
    if len(t) < 12:
        return bool(re.search(r"\b(automate|build|create|workflow|bot|agent)\b", t, re.I)) and len(t.split()) < 4
    if _VAGUE.match(t):
        return True
    # Named channel / SaaS from universal registry → specific enough to compose
    try:
        from app.composer.chat_channels import detect_channels

        if detect_channels(t):
            return False
    except Exception:  # noqa: BLE001
        pass
    # Work verb but no field, channel, data, or output signal
    if re.search(r"\b(automate|build|create|process)\b", t, re.I) and not re.search(
        r"\b(telegram|slack|discord|email|digest|github|jira|linear|csv|webhook|"
        r"http|knowledge|bot|agent|workflow|support|invoice|expense|hire|onboard|"
        r"hr|sales|lead|crm|finance|content|blog|document|docs|report|ticket|"
        r"schedule|monday|weekly|daily|from my|"
        r"shopify|outlook|whatsapp|youtube|google|hubspot|stripe|notion|"
        r"salesforce|microsoft|oauth|api)\b",
        t,
        re.I,
    ):
        return True
    return False


def is_host_control_request(text: str) -> bool:
    return bool(_HOST_CONTROL.search(text or ""))


def is_complex_agent_goal(text: str) -> bool:
    return bool(_COMPLEX.search(text or ""))


def clarify_event(goal: str = "") -> dict[str, Any]:
    return {
        "type": "aios_clarify",
        "data": {
            "message": (
                "I can turn this into a NovaFlow workflow. Pick a field, trigger, data source, and output — "
                "or use a starter chip."
            ),
            "questions": [
                "Field: ops, support, sales, HR, finance, or content?",
                "Trigger: manual, schedule, webhook, or chat?",
                "Data: Knowledge base, upload, or API?",
                "Output: email, Slack, Telegram, docs/workflow only?",
            ],
            "chips": [
                "Automate invoice reminders from my documents every Monday",
                "Onboard new hires with a welcome email",
                "Build a telegram support bot that answers from knowledge",
                "Create a weekly email digest from my documents",
                "Build a GitHub issue triage workflow",
                "Draft a status report from my docs and notify Slack",
                "Capture sales leads and post to a webhook",
            ],
            "goal_hint": goal,
            "progress": progress_steps(mode="workflow"),
            "next_action": "clarify",
            "clarify_kind": "field",
        },
    }


def boundary_event() -> dict[str, Any]:
    return {
        "type": "aios_clarify",
        "data": {
            "message": (
                "I stay inside NovaFlow (workflows, agents, knowledge, credentials, notify). "
                "I can’t control your PC, browser, or shell."
            ),
            "questions": ["What NovaFlow automation should we build instead?"],
            "chips": [
                "Build a telegram support bot that answers from knowledge",
                "Create a weekly email digest from my documents",
                "Build a GitHub issue triage workflow",
            ],
            "boundary": True,
            "next_action": "clarify",
        },
    }


def start_agent_os_plan(
    db: Session,
    *,
    workspace_id: int,
    user_id: int,
    goal: str,
) -> dict[str, Any]:
    """Create Agent OS plan session (+ optional run) without full LLM execute."""
    plan = decompose_goal(goal)
    session = create_plan_session(db, workspace_id=workspace_id, goal=goal, run_id=None)
    run = create_run(
        db,
        workspace_id=workspace_id,
        user_id=user_id,
        input_text=goal,
        agent_id=None,
        mode="supervisor",
    )
    wants_hitl = bool(
        re.search(r"\b(ask(?:s)? me|approve|human|hitl|confirm before|before acting)\b", goal or "", re.I)
    )
    hitl = None
    if wants_hitl:
        hitl = request_approval(db, run, reason="Human approval requested before agent execution", action="continue")
    return {
        "mode": "agent",
        "plan_session_id": session.id,
        "run_id": run.id,
        "plan": plan,
        "tasks": plan.get("tasks") or [],
        "hitl": hitl,
        "status": "paused" if hitl else "planning",
        "progress": progress_steps(mode="agent"),
        "next_action": "hitl" if hitl else "approve",
    }


def resolve_hitl(
    db: Session,
    *,
    run_id: str,
    approved: bool,
    feedback: str = "",
) -> dict[str, Any]:
    run = db.get(AgentRun, run_id)
    if not run:
        return {"status": "error", "message": "Agent run not found"}
    return submit_feedback(db, run, approved=approved, feedback=feedback)


def heal_and_retest(
    preview: dict[str, Any],
    *,
    knowledge_id: int | None = None,
    missing_credentials: list[str] | None = None,
    field: str | None = None,
    max_rounds: int = 2,
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    from app.sandbox.enterprise_suite import run_enterprise_suite

    drop_notify = bool(missing_credentials) and any(
        "telegram" in m or "slack" in m or "discord" in m or "smtp" in m or "webhook" in m
        for m in (missing_credentials or [])
    )
    all_fixes: list[str] = []
    healed = preview if isinstance(preview, dict) else {}
    report: dict[str, Any] = {}
    rounds = max(1, min(int(max_rounds or 2), 3))
    for _ in range(rounds):
        healed, fixes = heal_executable_graph(
            healed,
            knowledge_id=knowledge_id,
            drop_notify_without_creds=drop_notify,
        )
        if not fixes and not all_fixes:
            healed, fixes = heal_executable_graph(healed, knowledge_id=knowledge_id)
        all_fixes.extend(fixes or [])
        report = run_enterprise_suite(
            healed,
            missing_credentials=missing_credentials,
            field=field,
        )
        if report.get("status") == "success":
            break
    report["healed"] = True
    report["heal_fixes"] = all_fixes
    # Keep twin-compatible fields for older UI paths
    if "total_latency_ms" not in report:
        twin = run_sandbox_trial(healed)
        report["total_latency_ms"] = twin.get("total_latency_ms")
        report["nodes"] = twin.get("nodes")
    return healed, report, all_fixes
