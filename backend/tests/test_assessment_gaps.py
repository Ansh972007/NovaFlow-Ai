"""Tests for project-gap assessment fixes (chat ops, workflow test API)."""

from app.composer.chat_actions import classify_ops_intent, OPS_INTENTS


def test_classify_test_workflow_intent():
    assert classify_ops_intent("test workflow") == "test_workflow"
    assert classify_ops_intent("sandbox test my workflow") == "test_workflow"
    assert "test_workflow" in OPS_INTENTS


def test_classify_parallel_run_intent():
    assert classify_ops_intent("run workflow 1 and 3") == "run_workflows_parallel"
    assert classify_ops_intent("run workflows 2 and 5") == "run_workflows_parallel"
    assert "run_workflows_parallel" in OPS_INTENTS


def test_workflow_test_endpoint(client):
    listed = client.get("/api/v1/workflow", params={"page": 1, "limit": 1})
    assert listed.status_code == 200
    rows = listed.json().get("data") or []
    if not rows:
        return
    wf_id = rows[0]["id"]
    res = client.post(f"/api/v1/workflow/info/{wf_id}/test", json={})
    assert res.status_code == 200
    body = res.json()
    assert body.get("status_code") == 200
    report = (body.get("data") or {}).get("report") or {}
    assert "status" in report
