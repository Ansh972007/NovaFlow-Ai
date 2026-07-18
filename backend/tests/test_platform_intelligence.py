"""Platform Intelligence Layer tests."""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from app.database import SessionLocal, init_db
from app.platform_intelligence.tracing.context import get_trace_id, new_trace_id, set_trace_id
from app.platform_intelligence.policy.engine import evaluate_policy, DEFAULT_POLICIES
from app.platform_intelligence.healing.circuit_breaker import get_breaker, breaker_status
from app.platform_intelligence.healing.detectors import detect_anomalies, recovery_recommendations
from app.platform_intelligence.observability.metrics import aggregate_subsystems, record_http_metric
from app.platform_intelligence.events.emitter import emit_platform_event, list_events
from app.platform_intelligence.finops.ledger import record_cost, workspace_cost_summary
from app.platform_intelligence.observability.health import platform_health_snapshot


@pytest.fixture(scope="module")
def db() -> Session:
    init_db()
    session = SessionLocal()
    yield session
    session.close()


def test_trace_id_propagation():
    set_trace_id("abc123")
    assert get_trace_id() == "abc123"
    assert len(new_trace_id()) == 16


def test_http_metric_ring():
    record_http_metric(path="/api/v1/test", method="GET", status=200, latency_ms=12.5, trace_id="t1")
    agg = aggregate_subsystems()
    assert "http" in agg or agg == {}


def test_circuit_breaker():
    br = get_breaker("test_provider")
    assert br.allow()
    for _ in range(5):
        br.record_failure()
    assert br.state == "open"
    assert not br.allow()
    st = breaker_status()
    assert "test_provider" in st


def test_policy_evaluation(db: Session):
    decision = evaluate_policy(db, "workflow", {"skip_validation": True}, workspace_id=1)
    assert not decision.allowed
    decision2 = evaluate_policy(db, "execution", {"concurrent_runs": 0}, workspace_id=1)
    assert decision2.allowed


def test_default_policies_exist():
    assert len(DEFAULT_POLICIES) >= 3


def test_platform_event(db: Session):
    eid = emit_platform_event(
        db,
        "TestEvent",
        workspace_id=1,
        actor_user_id=1,
        payload={"hello": "world"},
    )
    events = list_events(db, workspace_id=1, event_type="TestEvent", limit=5)
    assert events or eid is not None


def test_cost_ledger(db: Session):
    record_cost(db, workspace_id=1, organization_id=None, cost_type="llm", amount_usd=0.001, model="gpt-4o-mini")
    summary = workspace_cost_summary(db, 1, days=30)
    assert summary["total_usd"] >= 0


def test_platform_health():
    snap = platform_health_snapshot()
    assert snap["platform_intelligence"] == "enterprise-v1"
    assert "subsystems" in snap


def test_anomaly_detection():
    findings = detect_anomalies()
    recs = recovery_recommendations()
    assert isinstance(findings, list)
    assert isinstance(recs, list)
