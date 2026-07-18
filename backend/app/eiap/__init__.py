"""
NovaFlow Enterprise Intelligence & Autonomy Platform (EIAP).

Strategic intelligence layer that observes, evaluates, predicts, optimizes,
governs, and recommends improvements across the entire NovaFlow ecosystem.

EIAP NEVER replaces AI Runtime, AgentOS, Workflow Intelligence, Knowledge OS,
Connectivity, or Platform Intelligence. It orchestrates intelligence across them
and NEVER applies changes automatically — all recommendations require approval.
"""

from app.eiap.observability import unified_health
from app.eiap.optimization import run_optimization_scan
from app.eiap.prediction import forecast

__all__ = [
    "unified_health",
    "run_optimization_scan",
    "forecast",
]
