"""Workflow Intelligence Platform tests."""

from __future__ import annotations

import asyncio

import pytest
from sqlalchemy.orm import Session

from app.database import SessionLocal, Workflow, init_db
from app.workflow_intelligence.graph.model import WorkflowGraph, WorkflowNode, WorkflowEdge
from app.workflow_intelligence.graph.parser import parse_graph
from app.workflow_intelligence.graph.validator import validate_graph
from app.workflow_intelligence.optimizer import optimize_graph
from app.workflow_intelligence.security import validate_workflow_security
from app.workflow_intelligence.publish_gate import check_publish_ready
from app.workflow_intelligence.planner import _heuristic_plan
from app.workflow_intelligence.debugger import build_debug_session, replay_steps
from app.workflow_intelligence.observability import analyze_run


@pytest.fixture(scope="module")
def db() -> Session:
    init_db()
    session = SessionLocal()
    yield session
    session.close()


def _sample_graph() -> WorkflowGraph:
    return WorkflowGraph(
        nodes=[
            WorkflowNode("trigger", "trigger"),
            WorkflowNode("retrieve", "retrieve", {"knowledge_id": None}),
            WorkflowNode("llm", "llm", {"prompt": "Answer"}),
            WorkflowNode("output", "output"),
        ],
        edges=[
            WorkflowEdge("trigger", "retrieve"),
            WorkflowEdge("retrieve", "llm"),
            WorkflowEdge("llm", "output"),
        ],
    )


def test_parse_graph():
    g = parse_graph({"nodes": [{"id": "a", "type": "trigger"}], "edges": []})
    assert len(g.nodes) == 1


def test_validate_valid_graph():
    report = validate_graph(_sample_graph())
    assert report.ok
    assert report.score > 50


def test_validate_cycle_detected():
    g = WorkflowGraph(
        nodes=[WorkflowNode("a", "trigger"), WorkflowNode("b", "llm")],
        edges=[WorkflowEdge("a", "b"), WorkflowEdge("b", "a")],
    )
    report = validate_graph(g)
    assert not report.ok
    assert any(i.code == "cycle_detected" for i in report.issues)


def test_validate_dangling_edge():
    g = WorkflowGraph(
        nodes=[WorkflowNode("a", "trigger")],
        edges=[WorkflowEdge("a", "missing")],
    )
    report = validate_graph(g)
    assert any(i.code == "dangling_edge" for i in report.issues)


def test_security_ssrf():
    g = WorkflowGraph(
        nodes=[WorkflowNode("http1", "http", {"url": "http://127.0.0.1/admin"})],
        edges=[],
    )
    sec = validate_workflow_security(g)
    assert not sec.ok


def test_optimizer_suggestions():
    report = optimize_graph(_sample_graph())
    assert report.estimated_llm_calls >= 1


def test_publish_gate():
    gate = check_publish_ready(_sample_graph())
    assert "ready" in gate
    assert "validation" in gate


def test_heuristic_planner():
    plan = _heuristic_plan("When customer uploads invoice, extract and notify finance")
    assert plan.graph.get("nodes")
    assert any(n["type"] == "trigger" for n in plan.graph["nodes"])


def test_debugger_replay():
    from app.database import WorkflowRun

    run = WorkflowRun(
        id=1,
        workflow_id="test",
        user_id=1,
        workspace_id=1,
        input_text="hi",
        output_text="bye",
        steps_json='[{"node_id":"trigger","type":"trigger","status":"ok","output":"hi"}]',
        status=1,
        duration_ms=100,
    )
    session = build_debug_session(None, run, {"nodes": [], "edges": []})
    assert len(session.timeline) == 1
    steps = replay_steps([{"status": "ok"}, {"status": "error"}])
    assert len(steps) == 2


def test_analyze_run():
    from app.database import WorkflowRun

    run = WorkflowRun(
        id=2,
        workflow_id="w1",
        user_id=1,
        workspace_id=1,
        steps_json='[{"type":"llm","status":"ok"},{"type":"retrieve","status":"ok"}]',
        duration_ms=250,
        status=1,
    )
    m = analyze_run(run)
    assert m.llm_steps == 1
    assert m.retrieve_steps == 1


def test_plugin_registry():
    from app.workflow_intelligence.plugin_sdk import WorkflowPluginRegistry, PluginManifest

    async def _handler(**kwargs):
        return {"ok": True}

    reg = WorkflowPluginRegistry()
    reg.register_node("custom", _handler, manifest=PluginManifest("p1", "Test"))
    assert reg.get_node_handler("custom") is not None
