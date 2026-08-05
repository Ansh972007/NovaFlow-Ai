"""Enterprise chat playbooks — ordered chips, no separate orchestrator."""

from __future__ import annotations

from typing import Any


PLAYBOOKS: dict[str, dict[str, Any]] = {
    "incident": {
        "id": "incident",
        "title": "Incident response playbook",
        "summary": "Diagnose failing runs, heal the graph, retest, and notify the team.",
        "steps": [
            {"id": "status", "label": "Check last run status", "chip": "Run status"},
            {"id": "heal", "label": "Heal failed graph", "chip": "heal"},
            {"id": "retest", "label": "Retest sandbox", "chip": "run test"},
            {"id": "notify", "label": "Send test notification", "chip": "Send a test notification"},
            {"id": "monitor", "label": "Monitor timeline", "chip": "monitor the run"},
        ],
        "chips": ["Run status", "heal", "Send a test notification", "Workspace health"],
    },
    "weekly_ops": {
        "id": "weekly_ops",
        "title": "Weekly ops digest playbook",
        "summary": "Review health, costs, and schedules — then export a summary.",
        "steps": [
            {"id": "health", "label": "Workspace health", "chip": "Workspace health"},
            {"id": "finops", "label": "FinOps summary", "chip": "FinOps summary"},
            {"id": "schedules", "label": "List schedules", "chip": "List schedules"},
            {"id": "recs", "label": "Open recommendations", "chip": "Show recommendations"},
            {"id": "export", "label": "Export this chat", "chip": "Export this chat as markdown"},
        ],
        "chips": ["Workspace health", "FinOps summary", "List schedules", "Show recommendations"],
    },
    "onboard_bot": {
        "id": "onboard_bot",
        "title": "Onboard new bot playbook",
        "summary": "Compose a bot, fill credentials, approve, deploy, and schedule.",
        "steps": [
            {
                "id": "compose",
                "label": "Compose telegram support bot",
                "chip": "Build a telegram support bot that answers from knowledge",
            },
            {"id": "creds", "label": "Check missing credentials", "chip": "What credentials are missing?"},
            {"id": "vault", "label": "Review vault posture", "chip": "List vault categories"},
            {"id": "approve", "label": "Approve plan", "chip": "approve"},
            {"id": "deploy", "label": "Deploy", "chip": "deploy"},
            {"id": "schedule", "label": "Schedule daily", "chip": "Schedule my last workflow daily at 9am"},
        ],
        "chips": [
            "Build a telegram support bot that answers from knowledge",
            "What credentials are missing?",
            "approve",
            "Schedule my last workflow daily at 9am",
        ],
    },
}


def match_playbook(text: str) -> dict[str, Any] | None:
    t = (text or "").lower()
    if "incident" in t:
        return PLAYBOOKS["incident"]
    if "weekly" in t or "ops digest" in t:
        return PLAYBOOKS["weekly_ops"]
    if "onboard" in t or "new bot" in t:
        return PLAYBOOKS["onboard_bot"]
    if "playbook" in t and "list" in t:
        return None  # list all via handler
    if re_search_playbook_generic(t):
        # default incident if vague "run playbook"
        return PLAYBOOKS["incident"]
    return None


def re_search_playbook_generic(t: str) -> bool:
    return "playbook" in t and ("run" in t or "start" in t)


def list_playbooks_event() -> dict[str, Any]:
    items = [
        {"id": p["id"], "title": p["title"], "summary": p["summary"], "chip": f"Run {p['id']} playbook"}
        for p in PLAYBOOKS.values()
    ]
    return {
        "type": "aios_playbook",
        "data": {
            "status": "catalog",
            "title": "Enterprise playbooks",
            "playbooks": items,
            "chips": [i["chip"] for i in items],
        },
    }


def playbook_event(pb: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "aios_playbook",
        "data": {
            "status": "ready",
            "id": pb["id"],
            "title": pb["title"],
            "summary": pb["summary"],
            "steps": pb["steps"],
            "chips": pb["chips"],
        },
    }
