"""Universal utterance router — any message → ops | work | agent | qa | boundary | pending."""

from __future__ import annotations

import re
from typing import Any

# Work verbs / field nouns that should become workflows, not plain chat
_WORK_VERBS = re.compile(
    r"\b("
    r"automate|automation|build|create|compose|deploy|process|triage|onboard|recruit|"
    r"invoice|expense|report|digest|notify|schedule|pipeline|workflow|bot|agent|"
    r"summarize\s+my|email\s+me|send\s+(a\s+)?(weekly|daily)|track|approve\s+(expense|invoice)|"
    r"lead\s+capture|intake|checklist|welcome\s+email|status\s+report|draft\s+(a\s+)?(blog|post|content)|"
    r"remind|reminder|escalate|handoff|ticket|"
    r"send\s+emails?|want\s+to\s+send|mail\s+to|email\s+my|"
    r"sync\s+drive|update\s+sheet|calendar\s+event"
    r")\b",
    re.I,
)

_QA_HINT = re.compile(
    r"^\s*(what\s+is|what\s+are|who\s+is|how\s+does|how\s+do\s+i|explain|define|why\s+is|"
    r"tell\s+me\s+about|can\s+you\s+explain)\b",
    re.I,
)

_PENDING_ACTIONS = frozenset(
    {
        "approve",
        "test",
        "deploy",
        "heal",
        "cancel",
        "refine",
        "hitl_approve",
        "hitl_reject",
        "credential",
    }
)


def has_work_signal(text: str) -> bool:
    return bool(_WORK_VERBS.search(text or ""))


def universal_route(
    text: str,
    *,
    has_pending: bool = False,
    last_field: str | None = None,
) -> dict[str, Any]:
    """
    Classify utterance for Peak Chat.
    Returns {route, intent_hint, work_signal, suggest_workflow_chips}.
    """
    from app.composer.chat_actions import OPS_INTENTS, classify_ops_intent
    from app.composer.chat_advanced import is_complex_agent_goal, is_host_control_request
    from app.composer.chat_bridge import classify_intent

    t = (text or "").strip()
    if not t:
        return {
            "route": "qa",
            "intent_hint": "chat",
            "work_signal": False,
            "suggest_workflow_chips": False,
            "ops_intent": None,
        }

    if is_host_control_request(t):
        return {
            "route": "boundary",
            "intent_hint": "boundary",
            "work_signal": False,
            "suggest_workflow_chips": False,
            "ops_intent": None,
        }

    ops_intent = classify_ops_intent(t)
    if ops_intent and ops_intent in OPS_INTENTS:
        return {
            "route": "ops",
            "intent_hint": ops_intent,
            "work_signal": False,
            "suggest_workflow_chips": False,
            "ops_intent": ops_intent,
        }

    intent = classify_intent(t, has_pending=has_pending)
    if has_pending and intent in _PENDING_ACTIONS:
        return {
            "route": "pending_action",
            "intent_hint": intent,
            "work_signal": False,
            "suggest_workflow_chips": False,
            "ops_intent": None,
        }

    if intent == "agent_run" or is_complex_agent_goal(t):
        return {
            "route": "agent",
            "intent_hint": "agent_run",
            "work_signal": True,
            "suggest_workflow_chips": False,
            "ops_intent": None,
        }

    if intent in ("compose", "refine"):
        return {
            "route": "work_compose",
            "intent_hint": intent,
            "work_signal": True,
            "suggest_workflow_chips": False,
            "ops_intent": None,
            "last_field": last_field,
        }

    work = has_work_signal(t)
    # Follow-up like "same for invoices" with remembered field
    if last_field and re.search(r"\b(same|similar|another|also|again)\b", t, re.I) and len(t.split()) <= 12:
        work = True

    if work and not _QA_HINT.match(t):
        return {
            "route": "work_compose",
            "intent_hint": "compose",
            "work_signal": True,
            "suggest_workflow_chips": False,
            "ops_intent": None,
            "last_field": last_field,
        }

    return {
        "route": "qa",
        "intent_hint": "chat",
        "work_signal": work,
        "suggest_workflow_chips": work or bool(_WORK_VERBS.search(t)),
        "ops_intent": None,
    }


def infer_field(goal: str, last_field: str | None = None) -> str:
    g = (goal or "").lower()
    if re.search(r"\b(invoice|expense|finance|payroll|payment)\b", g):
        return "finance"
    if re.search(r"\b(hire|onboard|hr|recruit|employee|welcome email)\b", g):
        return "hr"
    if re.search(r"\b(lead|sales|crm|prospect|pipeline)\b", g):
        return "sales"
    if re.search(r"\b(support|ticket|customer|intake|helpdesk)\b", g):
        return "support"
    if re.search(r"\b(blog|content|copy|draft|newsletter|write)\b", g):
        return "content"
    if re.search(r"\b(ops|status report|incident|monitor|sla)\b", g):
        return "ops"
    if last_field:
        return last_field
    return "generic"
