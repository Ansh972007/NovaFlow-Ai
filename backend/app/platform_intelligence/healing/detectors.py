"""Self-healing detectors and recovery actions."""

from __future__ import annotations

from typing import Any

from app.platform_intelligence.healing.circuit_breaker import breaker_status, get_breaker
from app.platform_intelligence.observability.metrics import aggregate_subsystems


def detect_anomalies() -> list[dict[str, Any]]:
    findings: list[dict] = []
    subs = aggregate_subsystems()

    for name, stats in subs.items():
        if stats.get("error_rate", 0) > 0.2:
            findings.append(
                {
                    "code": "high_error_rate",
                    "subsystem": name,
                    "severity": "critical",
                    "message": f"{name} error rate {stats['error_rate']:.0%}",
                    "action": "circuit_breaker",
                }
            )
            get_breaker(name).record_failure()

        if stats.get("avg_latency_ms", 0) > 5000:
            findings.append(
                {
                    "code": "high_latency",
                    "subsystem": name,
                    "severity": "warning",
                    "message": f"{name} avg latency {stats['avg_latency_ms']:.0f}ms",
                    "action": "graceful_degradation",
                }
            )

    for name, st in breaker_status().items():
        if st.get("state") == "open":
            findings.append(
                {
                    "code": "circuit_open",
                    "subsystem": name,
                    "severity": "critical",
                    "message": f"Circuit breaker open for {name}",
                    "action": "provider_failover",
                }
            )

    return findings


def recovery_recommendations() -> list[str]:
    recs = []
    for name, st in breaker_status().items():
        if st.get("state") == "open":
            recs.append(f"Reset or wait for recovery on breaker: {name}")
    subs = aggregate_subsystems()
    if subs.get("http", {}).get("error_rate", 0) > 0.1:
        recs.append("Review recent API errors and rate limits")
    if not recs:
        recs.append("All subsystems within normal parameters")
    return recs
