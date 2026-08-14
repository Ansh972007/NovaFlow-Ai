"""Marketplace API tests — list, public listing, clone, rate, comments."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from tests.test_smoke import _auth_headers, client as test_client


@pytest.fixture
def auth_headers(test_client: TestClient):
    return _auth_headers(test_client)


def _create_workflow(client: TestClient, headers: dict, name: str = "Marketplace Test WF") -> str:
    res = client.post(
        "/api/v1/workflow",
        headers=headers,
        json={"name": name, "template_id": "rag"},
    )
    assert res.status_code == 200, res.text
    return res.json()["data"]["id"]


def test_list_marketplace_returns_items_and_templates(test_client: TestClient, auth_headers: dict):
    res = test_client.get("/api/v1/marketplace/workflows", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()["data"]
    assert "items" in data
    assert "templates" in data
    assert isinstance(data["items"], list)
    assert isinstance(data["templates"], list)
    assert len(data["templates"]) >= 1


def test_public_workflow_appears_in_marketplace(test_client: TestClient, auth_headers: dict):
    from app.database import SessionLocal, Workflow

    wf_id = _create_workflow(test_client, auth_headers, "Public Marketplace Listing")
    db = SessionLocal()
    try:
        row = db.get(Workflow, wf_id)
        row.status = 1
        row.is_public = 1
        row.graph_json = json.dumps({"nodes": [{"id": "n1", "type": "trigger"}], "edges": []})
        db.commit()
    finally:
        db.close()

    res = test_client.get("/api/v1/marketplace/workflows", headers=auth_headers)
    ids = [w["id"] for w in res.json()["data"]["items"]]
    assert wf_id in ids


def test_clone_marketplace_workflow(test_client: TestClient, auth_headers: dict):
    from app.database import SessionLocal, Workflow

    wf_id = _create_workflow(test_client, auth_headers, "Clone Source WF")
    db = SessionLocal()
    try:
        row = db.get(Workflow, wf_id)
        row.status = 1
        row.is_public = 1
        db.commit()
    finally:
        db.close()

    res = test_client.post(f"/api/v1/marketplace/workflows/{wf_id}/clone", headers=auth_headers)
    assert res.status_code == 200
    clone = res.json()["data"]
    assert clone["id"] != wf_id
    assert "copy" in clone.get("name", "").lower() or clone.get("name")


def test_rate_workflow_and_invalid_score(test_client: TestClient, auth_headers: dict):
    from app.database import SessionLocal, Workflow

    wf_id = _create_workflow(test_client, auth_headers, "Rate Test WF")
    db = SessionLocal()
    try:
        row = db.get(Workflow, wf_id)
        row.status = 1
        row.is_public = 1
        db.commit()
    finally:
        db.close()

    ok = test_client.post(
        f"/api/v1/marketplace/workflows/{wf_id}/rate",
        headers=auth_headers,
        json={"score": 4},
    )
    assert ok.status_code == 200
    body = ok.json()["data"]
    assert body.get("score") == 4
    assert body.get("avg_rating") is not None

    bad = test_client.post(
        f"/api/v1/marketplace/workflows/{wf_id}/rate",
        headers=auth_headers,
        json={"score": 9},
    )
    assert bad.status_code == 200
    assert bad.json().get("status_code") == 400 or bad.status_code == 400


def test_workflow_comments_post_and_list(test_client: TestClient, auth_headers: dict):
    from app.database import SessionLocal, Workflow

    wf_id = _create_workflow(test_client, auth_headers, "Comment Test WF")
    db = SessionLocal()
    try:
        row = db.get(Workflow, wf_id)
        row.status = 1
        row.is_public = 1
        db.commit()
    finally:
        db.close()

    post = test_client.post(
        f"/api/v1/marketplace/workflows/{wf_id}/comments",
        headers=auth_headers,
        json={"body": "Great workflow for demos"},
    )
    assert post.status_code == 200
    comment = post.json()["data"]
    assert comment.get("body") == "Great workflow for demos"

    list_res = test_client.get(f"/api/v1/marketplace/workflows/{wf_id}/comments", headers=auth_headers)
    assert list_res.status_code == 200
    rows = list_res.json()["data"]
    assert any(c.get("body") == "Great workflow for demos" for c in rows)
