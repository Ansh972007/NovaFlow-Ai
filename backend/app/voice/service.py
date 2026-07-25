"""Voice Intent Processor and Command Registry."""

from __future__ import annotations

import re
from typing import Any, NamedTuple


class VoiceIntent(NamedTuple):
    action: str
    target: str
    params: dict[str, Any]


class VoiceService:
    """Enterprise Voice Intelligence Service."""

    def __init__(self):
        # Match navigation commands: "go to X", "navigate to X", "open X"
        self._nav_pattern = re.compile(
            r"\b(?:go\s+to|navigate\s+to|open|show)\s+([a-z0-9_\-\s]+)\b",
            re.IGNORECASE,
        )
        # Match workflow control commands: "run workflow X", "pause/stop workflow X", etc.
        self._workflow_pattern = re.compile(
            r"\b(run|execute|pause|stop|resume|approve)\s+workflow\s+([a-z0-9_\-\s]+)\b",
            re.IGNORECASE,
        )

    def classify_intent(self, text: str) -> VoiceIntent:
        """Parse transcription and classify the command intent."""
        cleaned = (text or "").strip().lower()

        # Check workflow commands first
        wf_match = self._workflow_pattern.search(cleaned)
        if wf_match:
            action, target = wf_match.groups()
            return VoiceIntent(
                action=f"workflow.{action.lower()}",
                target=target.strip(),
                params={},
            )

        # Check navigation commands next
        nav_match = self._nav_pattern.search(cleaned)
        if nav_match:
            target = nav_match.group(1).strip()
            # Normalize target names to system routes
            normalized = target.replace(" ", "_")
            return VoiceIntent(
                action="navigate",
                target=normalized,
                params={"original_target": target},
            )

        # Fallback to standard conversational query
        return VoiceIntent(action="chat", target="", params={"query": text})
