"""Enterprise Intelligence & Autonomy Platform tests."""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from app.database import SessionLocal, User, init_db
from app.eiap import agent_intel, connectivity_intel, finops, governance, knowledge_intel, model_intel, workflow_intel
from app.eiap.observability import unified_health
from app.eiap.optimization import run_optimization_scan
from app.eiap.prediction import forecast
from app.eiap.recommendations import (
    create_recommendation,
    get_recommendation,
    list_recommendations,
    set_status,
)
from app.eiap.reporting import generate_report, list_reports


@pytest.fixture(scope="module")
def db() -> Session:
    init_db()
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def user_id(db: Session) -> int:
    u = db.query(User).first()
    if not u:
        u = User(
            user_name="admin",
            email="admin@example.com",
            password="x",
            role="editor",
        )
        db.add(u)
        db.commit()
        db.refresh(u)
    return u.user_id


def test_unified_health(db: Session):
    health = unified_health(db, workspace_id=1)
    assert "overall_health_score" in health
    assert health["status"] in ("healthy", "degraded", "unhealthy")
    assert "workflow" in health["layers"]
    assert "agent_os" in health["layers"]
    assert "connectivity" in health["layers"]


def test_recommendation_lifecycle(db: Session, user_id: int):
    rec = create_recommendation(
        db,
        workspace_id=1,
        domain="workflow",
        title="Test recommendation",
        detail="Testing approval flow",
        severity="medium",
    )
    assert rec.status == "open"
    # dedupe returns same open rec
    rec2 = create_recommendation(db, workspace_id=1, domain="workflow", title="Test recommendation")
    assert rec2.id == rec.id
    # tenant isolation
    assert get_recommendation(db, rec.id, workspace_id=99999) is None
    # approval workflow
    approved = set_status(db, rec, status="approved", reviewed_by=user_id)
    assert approved.status == "approved"


def test_recommendations_never_auto_applied(db: Session):
    """New recommendations must default to 'open' — never auto-applied."""
    rec = create_recommendation(db, workspace_id=1, domain="finops", title="Cost check", dedupe=False)
    assert rec.status == "open"
    assert rec.reviewed_at is None


def test_optimization_scan(db: Session):
    result = run_optimization_scan(db, workspace_id=1)
    assert "recommendations_created" in result
    assert "note" in result
    assert "approval" in result["note"].lower()


def test_domain_analysis(db: Session):
    assert "workflows" in workflow_intel.analyze_workflows(db, workspace_id=1)
    assert "leaderboard" in agent_intel.agent_scorecards(db, workspace_id=1)
    assert "collection_health" in knowledge_intel.analyze_knowledge(db, workspace_id=1)
    assert "connection_health" in connectivity_intel.analyze_connectivity(db, workspace_id=1)


def test_model_benchmark(db: Session):
    bench = model_intel.benchmark_models(db, workspace_id=1)
    assert "benchmarks" in bench
    rec = model_intel.recommend_provider(db, workspace_id=1, priority="cost")
    assert "recommendation" in rec


def test_prediction(db: Session):
    result = forecast(db, workspace_id=1)
    assert "growth" in result
    assert "cost" in result
    assert "capacity" in result


def test_finops(db: Session):
    analysis = finops.cost_analysis(db, workspace_id=1)
    assert "summary" in analysis
    assert "forecast" in analysis


def test_governance(db: Session):
    health = governance.workspace_health_report(db, workspace_id=1)
    assert "posture" in health
    compliance = governance.compliance_report(db, workspace_id=1)
    assert compliance["tenant_isolation"] == "enforced"
    security = governance.security_posture(db, workspace_id=1)
    assert security["controls"]["rbac"] == "active"


def test_reporting(db: Session):
    report = generate_report(db, workspace_id=1, report_type="daily")
    assert report["id"]
    assert report["summary"]
    reports = list_reports(db, workspace_id=1)
    assert len(reports) >= 1
