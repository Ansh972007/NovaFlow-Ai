"""NovaFlow final verification suite — unit + API smoke tests."""

from __future__ import annotations

import asyncio
import base64
import json
import os
import tempfile
from pathlib import Path

import pytest
import rsa
from fastapi.testclient import TestClient

# Isolate tests from the developer's local SQLite so we never mutate production-ish data.
_TEST_DIR = Path(tempfile.mkdtemp(prefix="novaflow-test-"))
os.environ["DATA_DIR"] = str(_TEST_DIR)
os.environ["DATABASE_URL"] = f"sqlite:///{(_TEST_DIR / 'test.db').as_posix()}"
os.environ["JWT_SECRET"] = "novaflow-test-secret"
os.environ["NOVAFLOW_DEMO_SEED"] = "0"
os.environ["MILVUS_URI"] = ""
os.environ["NOVAFLOW_ADMIN_USER"] = "admin"
os.environ["NOVAFLOW_ADMIN_PASSWORD"] = "admin123"

from app.crypto import get_rsa_keys, md5_hash  # noqa: E402
from app.main import app  # noqa: E402
from app.services.agent_tools import BUILTIN_TOOLS, DEFAULT_AGENT_SYSTEM, _safe_calc  # noqa: E402
from app.services.workflow import (  # noqa: E402
    DEFAULT_LLM_PROMPT,
    TEMPLATES,
    _extract_titled_fields,
    _format_notify_body,
    _run_status_from_steps,
)
from app.services.knowledge import _rrf_fuse  # noqa: E402
from app.services.receipt import build_chat_receipt, estimate_cost_usd  # noqa: E402


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def _encrypt(password: str) -> str:
    pub, _ = get_rsa_keys()
    return base64.b64encode(rsa.encrypt(password.encode("utf-8"), pub)).decode("utf-8")


def _auth_headers(client: TestClient) -> dict:
    pk = client.get("/api/v1/user/public_key")
    assert pk.status_code == 200
    login = client.post(
        "/api/v1/user/login",
        json={"user_name": "admin", "password": _encrypt("admin123")},
    )
    assert login.status_code == 200, login.text
    body = login.json()
    assert body["status_code"] == 200, body
    token = body["data"]["access_token"]
    assert token
    return {"Authorization": f"Bearer {token}"}


# ---------- unit: prompts / helpers ----------


def test_templates_cover_core_pipelines():
    required = {
        "rag",
        "support",
        "research",
        "enrich",
        "agent_loop",
        "batch",
        "daily_digest",
        "jira_ticket",
        "slack_alert",
        "github_issue",
        "discord_alert",
        "linear_issue",
    }
    assert required.issubset(set(TEMPLATES.keys()))
    for tid, tpl in TEMPLATES.items():
        assert tpl.get("name") and tpl.get("graph"), tid
        nodes = tpl["graph"].get("nodes") or []
        assert nodes, tid


def test_default_prompts_are_structured():
    assert "structured" in DEFAULT_LLM_PROMPT.lower() or "precise" in DEFAULT_LLM_PROMPT.lower()
    assert "evidence" in DEFAULT_AGENT_SYSTEM.lower() or "tool" in DEFAULT_AGENT_SYSTEM.lower()
    assert set(BUILTIN_TOOLS) >= {"summarize", "kb_search", "calculator", "word_count"}


def test_extract_titled_fields():
    title, body = _extract_titled_fields("TITLE: Fix auth\nDESCRIPTION: Users cannot log in")
    assert title == "Fix auth"
    assert "cannot log in" in body
    title2, body2 = _extract_titled_fields("TITLE: Hello\nBODY: World details")
    assert title2 == "Hello"
    assert "World" in body2


def test_format_notify_body_limits():
    long = "x" * 5000
    assert len(_format_notify_body("discord", "subj", long)) <= 1900
    assert len(_format_notify_body("telegram", "subj", long)) <= 3500


def test_run_status_from_steps():
    assert _run_status_from_steps([{"status": "ok"}, {"status": "ok"}]) == 1
    assert _run_status_from_steps([{"status": "ok"}, {"status": "error"}]) == 2


def test_safe_calc():
    assert _safe_calc("2+2") == "4"
    assert "Error" in _safe_calc("__import__('os')") or _safe_calc("__import__('os')") == "0"


# ---------- API smoke ----------


def test_health(client):
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status_code"] == 200
    assert data["data"]["status"] == "ok"
    assert data["data"]["version"] == "9.7.0"


def test_root(client):
    res = client.get("/")
    assert res.status_code == 200
    assert res.json()["data"]["version"] == "9.7.0"


def test_login_and_user_info(client):
    headers = _auth_headers(client)
    info = client.get("/api/v1/user/info", headers=headers)
    assert info.status_code == 200
    body = info.json()
    assert body["status_code"] == 200
    assert body["data"]["user_name"] == "admin"


def test_unauthorized_blocked(client):
    res = client.get("/api/v1/workflow")
    assert res.status_code in (401, 403)


def test_workflow_templates_and_run(client):
    headers = _auth_headers(client)
    tpl = client.get("/api/v1/workflow/templates", headers=headers)
    assert tpl.status_code == 200
    templates = tpl.json()["data"]
    assert len(templates) >= 8
    ids = {t["id"] for t in templates}
    assert "support" in ids

    created = client.post(
        "/api/v1/workflow",
        headers=headers,
        json={"name": "Smoke Support", "desc": "final verification", "template_id": "support"},
    )
    assert created.status_code == 200, created.text
    wf = created.json()["data"]
    assert wf["id"]

    run = client.post(
        "/api/v1/workflow/run",
        headers=headers,
        json={"workflow_id": wf["id"], "input": "User cannot reset password after email change."},
    )
    assert run.status_code == 200, run.text
    result = run.json()
    assert result["status_code"] == 200
    data = result["data"]
    assert data.get("output")
    assert isinstance(data.get("steps"), list) and len(data["steps"]) >= 2
    assert data.get("run_id")

    runs = client.get("/api/v1/workflow/runs?limit=10", headers=headers)
    assert runs.status_code == 200
    rows = runs.json()["data"]
    assert any(r["id"] == data["run_id"] for r in rows)
    detail = client.get(f"/api/v1/workflow/runs/{data['run_id']}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["data"]["status_label"] in ("completed", "error")


def test_knowledge_create_list(client):
    headers = _auth_headers(client)
    created = client.post(
        "/api/v1/knowledge/create",
        headers=headers,
        json={"name": "Smoke KB", "description": "final verification", "type": 0},
    )
    assert created.status_code == 200, created.text
    kb = created.json()["data"]
    assert kb["id"]
    listed = client.get("/api/v1/knowledge?page_num=1&page_size=20", headers=headers)
    assert listed.status_code == 200
    payload = listed.json()["data"]
    rows = payload.get("data") if isinstance(payload, dict) else payload
    assert any(r["id"] == kb["id"] for r in rows)


def test_agents_tools_and_run(client):
    headers = _auth_headers(client)
    tools = client.get("/api/v1/agents/tools", headers=headers)
    assert tools.status_code == 200
    tool_ids = {t["id"] for t in tools.json()["data"]}
    assert "summarize" in tool_ids
    assert "word_count" in tool_ids

    run = client.post(
        "/api/v1/agents/run",
        headers=headers,
        json={
            "input": "Count words in: NovaFlow final verification pipeline.",
            "tools": ["word_count", "calculator"],
            "system": DEFAULT_AGENT_SYSTEM,
        },
    )
    assert run.status_code == 200, run.text
    data = run.json()["data"]
    assert data.get("output")
    assert data.get("tool_results")

    saved = client.post(
        "/api/v1/agents",
        headers=headers,
        json={"name": "Smoke Agent", "tools": ["word_count"], "system_prompt": DEFAULT_AGENT_SYSTEM},
    )
    assert saved.status_code == 200
    agent_id = saved.json()["data"]["id"]
    listed = client.get("/api/v1/agents", headers=headers)
    assert any(a["id"] == agent_id for a in listed.json()["data"])


def test_integrations_health_settings(client):
    headers = _auth_headers(client)
    health = client.get("/api/v1/integrations/health", headers=headers)
    assert health.status_code == 200
    flags = health.json()["data"]
    assert isinstance(flags, dict)
    settings = client.get("/api/v1/integrations/settings", headers=headers)
    assert settings.status_code == 200


def test_schedules_list(client):
    headers = _auth_headers(client)
    res = client.get("/api/v1/workflow/schedules", headers=headers)
    assert res.status_code == 200
    assert isinstance(res.json()["data"], list)


def test_model_lab_and_eval_surface(client):
    headers = _auth_headers(client)
    pipes = client.get("/api/v1/model-lab/pipelines", headers=headers)
    assert pipes.status_code == 200
    drift = client.get("/api/v1/model-lab/drift", headers=headers)
    assert drift.status_code == 200
    suites = client.get("/api/v1/eval/suites", headers=headers)
    assert suites.status_code == 200, suites.text
    assert isinstance(suites.json()["data"], list)


def test_batch_template_run(client):
    headers = _auth_headers(client)
    created = client.post(
        "/api/v1/workflow",
        headers=headers,
        json={"name": "Smoke Batch", "template_id": "batch"},
    )
    assert created.status_code == 200
    wf_id = created.json()["data"]["id"]
    run = client.post(
        "/api/v1/workflow/run",
        headers=headers,
        json={"workflow_id": wf_id, "input": "alpha\nbeta\ngamma"},
    )
    assert run.status_code == 200
    data = run.json()["data"]
    assert data.get("output")
    assert "alpha" in data["output"] or "RESULT" in data["output"]


def test_md5_hash_stable():
    assert md5_hash("admin123") == md5_hash("admin123")
    assert len(md5_hash("x")) == 32


def test_rrf_hybrid_fuse():
    a = [{"file_id": 1, "chunk_index": 0, "score": 0.9, "method": "vector", "text": "a", "file_name": "a.txt"}]
    b = [
        {"file_id": 2, "chunk_index": 0, "score": 0.5, "method": "keyword", "text": "b", "file_name": "b.txt"},
        {"file_id": 1, "chunk_index": 0, "score": 0.4, "method": "keyword", "text": "a2", "file_name": "a.txt"},
    ]
    fused = _rrf_fuse([a, b], limit=2)
    assert fused
    assert fused[0]["file_id"] == 1
    assert fused[0]["method"] == "hybrid"


def test_receipt_usage_and_cost():
    r = build_chat_receipt(
        model="openai/gpt-4o-mini",
        rag_hits=[{"file_name": "policy.pdf", "text": "hello", "score": 0.8, "method": "hybrid"}],
        chars=12,
        usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
    )
    assert r["source_count"] == 1
    assert r["total_tokens"] == 150
    assert r["est_cost_usd"] is not None
    assert estimate_cost_usd("gpt-4o-mini", 1_000_000, 0) == 0.15
