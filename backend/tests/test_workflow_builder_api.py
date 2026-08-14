"""Workflow builder API smoke tests."""

from __future__ import annotations

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
        json={"name": "Builder API Test", "template_id": "rag"},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["status_code"] == 200
    return body["data"]["id"]


def test_nodes_library_returns_builtin(test_client: TestClient, auth_headers: dict):
    res = test_client.get("/api/v1/nodes/library", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()["data"]
    assert "builtin" in data
    assert len(data["builtin"]) >= 5
    types = {s["type"] for s in data["builtin"]}
    assert "trigger" in types
    assert "llm" in types


def test_workflow_sandbox_test(test_client: TestClient, auth_headers: dict):
    wf_id = _create_workflow(test_client, auth_headers)
    res = test_client.post(
        f"/api/v1/workflow/info/{wf_id}/test",
        headers=auth_headers,
        json={"live_credential_probe": False},
    )
    assert res.status_code == 200
    body = res.json()["data"]
    assert body["workflow_id"] == wf_id
    report = body.get("report") or {}
    assert "status" in report
    assert "checks" in report


def test_publish_gate_in_error_response(test_client: TestClient, auth_headers: dict):
    res = test_client.post(
        "/api/v1/workflow",
        headers=auth_headers,
        json={"name": "Empty Publish Test", "template_id": "rag"},
    )
    wf_id = res.json()["data"]["id"]
    test_client.put(
        "/api/v1/workflow",
        headers=auth_headers,
        json={
            "id": wf_id,
            "name": "Empty Publish Test",
            "desc": "",
            "graph": {"nodes": [], "edges": []},
        },
    )
    pub = test_client.post(
        "/api/v1/workflow/status",
        headers=auth_headers,
        json={"id": wf_id, "status": 1},
    )
    assert pub.status_code == 200
    body = pub.json()
    if body["status_code"] != 200:
        assert "publish_gate" in (body.get("data") or {})
