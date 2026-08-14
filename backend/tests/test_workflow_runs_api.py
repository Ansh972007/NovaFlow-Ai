"""Workflow run history and pending approval API tests."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from tests.test_smoke import _auth_headers, client as test_client


@pytest.fixture
def auth_headers(test_client: TestClient):
    return _auth_headers(test_client)


def _create_workflow(client: TestClient, headers: dict) -> str:
    res = client.post(
        "/api/v1/workflow",
        headers=headers,
        json={"name": "Runs API Test", "template_id": "rag"},
    )
    assert res.status_code == 200, res.text
    return res.json()["data"]["id"]


def test_list_workspace_runs_returns_created_run(test_client: TestClient, auth_headers: dict):
    from app.database import SessionLocal, WorkflowRun

    wf_id = _create_workflow(test_client, auth_headers)
    db = SessionLocal()
    try:
        row = WorkflowRun(
            workflow_id=wf_id,
            user_id=1,
            workspace_id=1,
            input_text="hello runs test",
            output_text="done",
            status=1,
            duration_ms=42,
            steps_json=json.dumps([{"type": "trigger", "status": "ok", "output": "hello"}]),
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        run_id = row.id
    finally:
        db.close()

    res = test_client.get("/api/v1/workflow/runs", headers=auth_headers)
    assert res.status_code == 200
    rows = res.json()["data"]
    assert isinstance(rows, list)
    match = [r for r in rows if r["id"] == run_id]
    assert match
    assert match[0]["workflow_id"] == wf_id
    assert "hello" in match[0]["input"]


def test_list_pending_runs_and_reject(test_client: TestClient, auth_headers: dict):
    from app.database import SessionLocal, WorkflowPendingRun

    wf_id = _create_workflow(test_client, auth_headers)
    db = SessionLocal()
    try:
        pending = WorkflowPendingRun(
            workflow_id=wf_id,
            user_id=1,
            workspace_id=1,
            context_json=json.dumps({"input": "needs approval"}),
            graph_json=json.dumps({"nodes": [], "edges": []}),
            pause_after_node="human_1",
            steps_json=json.dumps([{"type": "trigger", "status": "ok"}]),
            status=0,
        )
        db.add(pending)
        db.commit()
        db.refresh(pending)
        pending_id = pending.id
    finally:
        db.close()

    list_res = test_client.get("/api/v1/workflow/pending-runs", headers=auth_headers)
    assert list_res.status_code == 200
    items = list_res.json()["data"]
    assert any(p["id"] == pending_id for p in items)

    reject_res = test_client.post(
        "/api/v1/workflow/resume",
        headers=auth_headers,
        json={"pending_run_id": pending_id, "approved": False},
    )
    assert reject_res.status_code == 200
    body = reject_res.json()["data"]
    assert body.get("status") == "rejected"

    list_after = test_client.get("/api/v1/workflow/pending-runs", headers=auth_headers)
    ids = [p["id"] for p in list_after.json()["data"]]
    assert pending_id not in ids


def test_get_workflow_run_detail(test_client: TestClient, auth_headers: dict):
    from app.database import SessionLocal, WorkflowRun

    wf_id = _create_workflow(test_client, auth_headers)
    db = SessionLocal()
    try:
        row = WorkflowRun(
            workflow_id=wf_id,
            user_id=1,
            workspace_id=1,
            input_text="detail test",
            output_text="out",
            status=1,
            duration_ms=10,
            steps_json=json.dumps([{"type": "llm", "status": "ok", "output": "x"}]),
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        run_id = row.id
    finally:
        db.close()

    res = test_client.get(f"/api/v1/workflow/runs/{run_id}", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["id"] == run_id
    assert len(data.get("steps") or []) == 1
