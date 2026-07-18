"""
NovaFlow Enterprise Platform Intelligence Layer.

Unified observability, tracing, FinOps, policy, events, self-healing,
reliability, capacity planning, and admin intelligence.

Extends — does not replace — platform/, runtime/, workflow_intelligence/, data/.
"""

from app.platform_intelligence.tracing.context import get_trace_id, new_trace_id
from app.platform_intelligence.events.emitter import emit_platform_event
from app.platform_intelligence.policy.engine import evaluate_policy, PolicyDecision

__all__ = [
    "get_trace_id",
    "new_trace_id",
    "emit_platform_event",
    "evaluate_policy",
    "PolicyDecision",
]
