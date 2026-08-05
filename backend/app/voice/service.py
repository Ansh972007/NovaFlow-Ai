"""Voice Intent Processor and Command Registry."""

from __future__ import annotations

import re
from typing import Any, NamedTuple


class VoiceIntent(NamedTuple):
    action: str
    target: str
    params: dict[str, Any]


# Routes Peak Chat may navigate to via voice
NAV_ALIASES: dict[str, str] = {
    "workflows": "/workflows",
    "workflow": "/workflows",
    "credentials": "/credentials",
    "credential": "/credentials",
    "vault": "/credentials",
    "chat": "/chat",
    "projects": "/projects",
    "project": "/projects",
    "marketplace": "/marketplace",
    "developer": "/developer",
    "agents": "/developer",
    "schedules": "/workflows?tab=schedules",
}


class VoiceService:
    """Enterprise Voice Intelligence Service."""

    def __init__(self):
        self._nav_pattern = re.compile(
            r"\b(?:go\s+to|navigate\s+to|open|show)\s+([a-z0-9_\-\s]+)\b",
            re.IGNORECASE,
        )
        self._workflow_pattern = re.compile(
            r"\b(run|execute|pause|stop|resume|approve)\s+workflow\s+([a-z0-9_\-\s]+)\b",
            re.IGNORECASE,
        )

    def classify_intent(self, text: str) -> VoiceIntent:
        """Parse transcription and classify the command intent."""
        cleaned = (text or "").strip().lower()
        if not cleaned:
            return VoiceIntent(action="chat", target="", params={"query": text or ""})

        # Short composer / HITL commands (Peak Chat)
        if re.fullmatch(r"(please\s+)?(approve|yes|confirm)(\s+it|\s+the\s+plan)?", cleaned):
            return VoiceIntent(action="suggest", target="approve", params={"phrase": "approve"})
        if re.fullmatch(r"(please\s+)?(deploy|ship)(\s+it|\s+this)?", cleaned):
            return VoiceIntent(action="suggest", target="deploy", params={"phrase": "deploy"})
        if re.fullmatch(r"(please\s+)?(continue|proceed)", cleaned):
            return VoiceIntent(action="suggest", target="continue", params={"phrase": "continue"})
        if re.fullmatch(r"(please\s+)?(cancel|reject)(\s+it)?", cleaned):
            return VoiceIntent(action="suggest", target="cancel", params={"phrase": "cancel"})
        if re.fullmatch(r"(run\s+)?(my\s+)?last\s+workflow|run\s+my\s+workflow", cleaned):
            return VoiceIntent(
                action="suggest",
                target="run_workflow",
                params={"phrase": "Run my last workflow"},
            )
        if re.fullmatch(r"heal(\s+again)?", cleaned):
            phrase = "heal again" if "again" in cleaned else "heal"
            return VoiceIntent(action="suggest", target="heal", params={"phrase": phrase})
        if re.fullmatch(r"what can you do(\?)?", cleaned) or cleaned in ("capabilities", "help"):
            return VoiceIntent(
                action="suggest",
                target="capabilities",
                params={"phrase": "What can you do?"},
            )
        if re.fullmatch(r"workspace health|health report", cleaned):
            return VoiceIntent(action="suggest", target="health", params={"phrase": "Workspace health"})
        if re.fullmatch(r"list schedules|show schedules", cleaned):
            return VoiceIntent(action="suggest", target="schedules", params={"phrase": "List schedules"})
        if re.fullmatch(r"export (this )?(chat|conversation)( as markdown)?", cleaned):
            return VoiceIntent(
                action="suggest",
                target="export",
                params={"phrase": "Export this chat as markdown"},
            )
        if re.fullmatch(r"finops( summary)?|show (ai )?costs", cleaned):
            return VoiceIntent(action="suggest", target="finops", params={"phrase": "FinOps summary"})
        if re.fullmatch(r"enterprise playbooks?|list playbooks", cleaned):
            return VoiceIntent(
                action="suggest",
                target="playbook",
                params={"phrase": "Enterprise playbooks"},
            )

        # Named workflow controls (legacy + WS)
        wf_match = self._workflow_pattern.search(cleaned)
        if wf_match:
            action, target = wf_match.groups()
            action_l = action.lower()
            if action_l == "execute":
                action_l = "run"
            return VoiceIntent(
                action=f"workflow.{action_l}",
                target=target.strip(),
                params={},
            )

        # Navigation — Peak aliases first, else underscore target (legacy)
        nav_match = self._nav_pattern.search(cleaned)
        if nav_match:
            target = nav_match.group(1).strip()
            key = target.replace(" ", "_").replace("-", "_")
            first = key.split("_")[0]
            path = NAV_ALIASES.get(key) or NAV_ALIASES.get(first) or NAV_ALIASES.get(target)
            if path:
                return VoiceIntent(
                    action="navigate",
                    target=path,
                    params={"original_target": target, "route": path},
                )
            return VoiceIntent(
                action="navigate",
                target=key,
                params={"original_target": target},
            )

        return VoiceIntent(action="chat", target="", params={"query": text})


voice_service = VoiceService()


def polish_transcript(text: str) -> str:
    """Server-side STT cleanup aligned with frontend voicePolish."""
    t = re.sub(r"\s+", " ", (text or "").strip())
    if not t:
        return ""
    t = re.sub(r"\b(um+|uh+|erm+|ah+|like|you know)\b", " ", t, flags=re.I)
    t = re.sub(r"\s+", " ", t).strip()
    fixes = [
        (r"\bimpliment(ing|ed|s)?\b", r"implement\1"),
        (r"\bfor mr\b", "for me"),
        (r"\bcan you do this for mr\b", "can you do this for me"),
        (r"\bon this subjects\b", "on this subject"),
        (r"\be-?\s*mail\b", "email"),
        (r"\bdaly\b", "daily"),
    ]
    for pat, rep in fixes:
        t = re.sub(pat, rep, t, flags=re.I)
    t = re.sub(
        r"\b([a-z0-9._%+\-]+)\s+at\s+([a-z0-9\-]+)\s+dot\s+([a-z]{2,})\b",
        r"\1@\2.\3",
        t,
        flags=re.I,
    )
    if t and t[0].islower():
        t = t[0].upper() + t[1:]
    return t.strip()
