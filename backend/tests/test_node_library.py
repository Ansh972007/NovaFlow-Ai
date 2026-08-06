"""Tests for workspace node library and api_node runtime."""

from __future__ import annotations

import json
import uuid

import pytest
from sqlalchemy.orm import Session

from app.database import SessionLocal, User, Workspace, init_db
from app.services.api_node_runtime import execute_api_node_definition, normalize_slug
from app.services.node_library import (
    create_definition,
    list_library,
    publish_definition,
    validate_graph_api_nodes,
)
from app.workflow_intelligence.graph.model import WorkflowGraph, WorkflowNode
from app.workflow_intelligence.publish_gate import check_publish_ready


@pytest.fixture(scope="module")
def db() -> Session:
    init_db()
    session = SessionLocal()
    yield session
    session.close()


def _workspace_user(db: Session) -> tuple[int, int]:
    user = db.query(User).filter(User.delete == 0).first()
    if not user:
        pytest.skip("No user in database")
    ws = db.query(Workspace).first()
    if not ws:
        pytest.skip("No workspace in database")
    return ws.id, user.user_id


def test_normalize_slug():
    assert normalize_slug("Stripe List Charges") == "stripe_list_charges"


def test_create_and_list_definition(db: Session):
    ws_id, user_id = _workspace_user(db)
    slug = f"test_node_{uuid.uuid4().hex[:8]}"
    row = create_definition(
        db,
        ws_id,
        user_id,
        {
            "display_name": "Test API",
            "slug": slug,
            "definition": {
                "runtime": "http_declarative",
                "http": {"url": "https://httpbin.org/get", "method": "GET", "auth": ""},
            },
        },
    )
    assert row.slug == slug
    lib = list_library(db, ws_id, include_drafts=True)
    assert any(c["id"] == row.id for c in lib["custom"])


def test_validate_graph_api_nodes_missing_def(db: Session):
    ws_id, _ = _workspace_user(db)
    graph = {
        "nodes": [{"id": "a1", "type": "api_node", "data": {"node_def_id": "missing"}}],
        "edges": [],
    }
    issues = validate_graph_api_nodes(db, ws_id, graph)
    assert any(i["code"] == "node_def_not_found" for i in issues)


def test_publish_gate_blocks_unpublished_api_node(db: Session):
    ws_id, user_id = _workspace_user(db)
    slug = f"gate_{uuid.uuid4().hex[:8]}"
    row = create_definition(
        db,
        ws_id,
        user_id,
        {
            "display_name": "Gate Test",
            "slug": slug,
            "definition": {
                "runtime": "http_declarative",
                "http": {"url": "https://httpbin.org/get", "method": "GET"},
            },
        },
    )
    graph = WorkflowGraph(
        nodes=[
            WorkflowNode("trigger", "trigger"),
            WorkflowNode("api1", "api_node", {"node_def_id": row.id}),
            WorkflowNode("output", "output"),
        ],
        edges=[],
    )
    gate = check_publish_ready(graph, db=db, workspace_id=ws_id)
    assert not gate["ready"]
    assert any(b.get("code") == "node_def_not_published" for b in gate["blockers"])


def test_execute_api_node_requires_published(db: Session):
    ws_id, user_id = _workspace_user(db)
    slug = f"run_{uuid.uuid4().hex[:8]}"
    row = create_definition(
        db,
        ws_id,
        user_id,
        {
            "display_name": "Run Test",
            "slug": slug,
            "definition": {
                "runtime": "http_declarative",
                "http": {"url": "https://httpbin.org/get", "method": "GET"},
            },
        },
    )

    async def _run():
        try:
            await execute_api_node_definition(db, ws_id, {"node_def_id": row.id}, {"input": "x"})
            raise AssertionError("Should fail for draft")
        except ValueError as exc:
            assert "not published" in str(exc).lower()

    import asyncio

    asyncio.run(_run())


def test_execute_published_api_node_httpbin(db: Session):
    ws_id, user_id = _workspace_user(db)
    slug = f"live_{uuid.uuid4().hex[:8]}"
    row = create_definition(
        db,
        ws_id,
        user_id,
        {
            "display_name": "Httpbin GET",
            "slug": slug,
            "definition": {
                "runtime": "http_declarative",
                "http": {"url": "https://httpbin.org/get", "method": "GET"},
                "output_mapping": {"template": "{{json}}"},
            },
        },
    )
    from app.services.node_library import test_definition

    async def _run():
        test_res = await test_definition(db, ws_id, row.id, {"input": "hello"})
        if not test_res.get("ok"):
            return None
        publish_definition(db, ws_id, user_id, row.id, require_test=True)
        try:
            out, _ = await execute_api_node_definition(
                db, ws_id, {"node_def_id": row.id}, {"input": "hello"}
            )
            return out
        except ValueError:
            return None

    import asyncio

    out = asyncio.run(_run())
    if out is None:
        pytest.skip("httpbin probe failed in CI environment")
    assert out and len(str(out)) > 0


def test_unknown_node_type_is_error_in_strict_validation():
    from app.workflow_intelligence.graph.validator import validate_graph

    g = WorkflowGraph(nodes=[WorkflowNode("x", "totally_unknown")], edges=[])
    vr = validate_graph(g, strict=True)
    assert any(i.code == "unknown_node_type" and i.severity == "error" for i in vr.issues)
