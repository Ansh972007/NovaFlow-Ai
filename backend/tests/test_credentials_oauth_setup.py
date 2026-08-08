"""Credentials OAuth setup and placeholder rejection."""

import pytest

# Import test_smoke first so isolated test DB env is configured before app loads.
from tests.test_smoke import _auth_headers, client as test_client


def test_oauth_setup_returns_google_redirect_uris(test_client):
    headers = _auth_headers(test_client)
    res = test_client.get("/api/v1/credentials/oauth-setup", headers=headers)
    assert res.status_code == 200
    data = res.json()["data"]
    assert "google" in data
    uris = data["google"].get("redirect_uris") or []
    assert len(uris) >= 2
    labels = {u["id"] for u in uris}
    assert "login" in labels
    assert "gmail_send" in labels
    for u in uris:
        assert u["uri"].startswith("http")
        assert "/callback" in u["uri"]


def test_create_credential_rejects_placeholder_email(test_client):
    headers = _auth_headers(test_client)
    res = test_client.post(
        "/api/v1/credentials",
        headers=headers,
        json={
            "category": "email",
            "kind": "gmail_smtp",
            "label": "reject-placeholder-test",
            "fields": {
                "smtp_host": "smtp.gmail.com",
                "smtp_user": "you@gmail.com",
                "smtp_password": "xxxx xxxx xxxx xxxx",
            },
            "is_default": False,
        },
    )
    body = res.json()
    assert body.get("status_code") == 400 or res.status_code == 400


def test_verify_returns_error_status_on_bad_llm_key(test_client):
    headers = _auth_headers(test_client)
    create = test_client.post(
        "/api/v1/credentials",
        headers=headers,
        json={
            "category": "llm",
            "kind": "openai",
            "label": "verify-fail-test",
            "fields": {"api_key": "sk-invalid-test-key-for-verify"},
            "is_default": False,
        },
    )
    assert create.status_code == 200
    entry_id = create.json()["data"]["id"]
    verify = test_client.post(f"/api/v1/credentials/{entry_id}/verify", headers=headers)
    assert verify.status_code == 200
    data = verify.json()["data"]
    assert data.get("status") == "error"
    assert "credential" in data
    assert data["credential"].get("status") == "error"


def test_vault_create_rejects_placeholder_email():
    from app.database import SessionLocal
    from app.services import credential_vault as vault

    db = SessionLocal()
    try:
        with pytest.raises(ValueError, match="smtp_user"):
            vault.create_entry(
                db,
                workspace_id=1,
                user_id=1,
                category="email",
                kind="gmail_smtp",
                label="vault-placeholder-reject",
                fields={
                    "smtp_host": "smtp.gmail.com",
                    "smtp_user": "you@gmail.com",
                    "smtp_password": "xxxx xxxx xxxx xxxx",
                },
            )
    finally:
        db.close()


def test_integration_specific_graph_shapes():
    from app.composer.workflow_composer import build_executable_graph

    jira = build_executable_graph(
        required_caps=["cap_jira", "cap_workflow"],
        goal="create Jira tickets from support emails",
        requirements={"jira_project_key": "SUP"},
    )
    assert any(n.get("type") == "jira" for n in jira["nodes"])

    cal = build_executable_graph(
        required_caps=["cap_google", "cap_workflow"],
        goal="summarize my calendar meetings every morning",
    )
    assert any(n.get("type") == "http" for n in cal["nodes"])

    tg = build_executable_graph(
        required_caps=["cap_telegram", "cap_workflow"],
        goal="build a telegram support bot that answers questions",
    )
    assert any(n.get("type") == "trigger" for n in tg["nodes"])
    assert any(
        n.get("type") == "notify" and (n.get("data") or {}).get("channel") == "telegram"
        for n in tg["nodes"]
    )


def test_gather_not_ready_with_missing_credentials():
    from app.composer.chat_bridge import process_chat_goal
    from app.database import SessionLocal

    db = SessionLocal()
    conv = __import__("app.database", fromlist=["Conversation"]).Conversation(
        title="missing creds",
        conversation_type="assistant",
        workspace_id=1,
        user_id=1,
        meta_json="{}",
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)
    out = process_chat_goal(
        db,
        workspace_id=1,
        user_id=1,
        conversation_id=conv.id,
        user_message="build a telegram bot workflow to answer customer questions",
    )
    ui = out.get("ui_events") or []
    primary = out.get("primary_event") or (ui[0] if ui else {})
    if primary.get("type") == "aios_solution":
        data = primary.get("data") or {}
        assert data.get("phase") != "ready" or data.get("missing_credentials")
    db.close()


    from app.composer.workflow_composer import build_executable_graph

    graph = build_executable_graph(
        required_caps=["cap_workflow"],
        goal="make a workflow to add reels on instagram",
    )
    meta = graph.get("meta") or {}
    assert meta.get("unsupported") is True
    assert "Instagram" in (meta.get("message") or "")


# Manual transcript checklist (run after API restart):
# - Gmail workflow compose shows gather slots, not fake "Everything looks ready"
# - Jira / calendar / telegram goals use integration-specific nodes
# - Approve deploys; hello does not hijack compose
# - how many workflows / store knowledge / run it route to ops
# - Credentials page blocks you@gmail.com and xxxx passwords
# - Google OAuth setup shows redirect URIs + Connect with Google
# - Workflow builder shows Delete on selected node (mobile rail + sticky bar)
