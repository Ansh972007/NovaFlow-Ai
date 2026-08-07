"""Tests for in-chat API node factory, navigation ops, and OpenAPI import."""

from __future__ import annotations

import json

import pytest
from sqlalchemy.orm import Session

from app.composer.chat_node_factory import (
    attach_api_node_to_graph,
    classify_nav_intent,
    classify_node_factory_intent,
    dispatch_nav_action,
)
from app.composer.chat_router import universal_route
from app.services.openapi_import import draft_definitions_from_openapi, summarize_openapi


SAMPLE_OPENAPI = json.dumps(
    {
        "openapi": "3.0.0",
        "info": {"title": "Petstore", "version": "1.0"},
        "servers": [{"url": "https://api.example.com"}],
        "paths": {
            "/pets": {
                "get": {"operationId": "listPets", "summary": "List pets"},
                "post": {"operationId": "createPet", "summary": "Create a pet"},
            }
        },
    }
)


def test_classify_node_factory_intents():
    assert classify_node_factory_intent("Probe API") == "node_probe"
    assert classify_node_factory_intent("Save node") == "node_create"
    assert classify_node_factory_intent("Test node") == "node_test"
    assert classify_node_factory_intent("Publish node") == "node_publish"
    assert classify_node_factory_intent("Use in workflow") == "node_attach_to_workflow"
    assert classify_node_factory_intent("Import OpenAPI") == "openapi_import"


def test_classify_nav_intents():
    assert classify_nav_intent("open marketplace") == "open_marketplace"
    assert classify_nav_intent("open model lab") == "open_model_lab"
    assert classify_nav_intent("open credentials") == "open_credentials"
    assert classify_nav_intent("open settings security") == "open_settings"


def test_openapi_summarize_and_draft():
    summary = summarize_openapi(SAMPLE_OPENAPI)
    assert summary["title"] == "Petstore"
    assert summary["operation_count"] >= 2
    drafts = draft_definitions_from_openapi(SAMPLE_OPENAPI)
    assert len(drafts) >= 2
    assert drafts[0]["definition"]["http"]["url"].startswith("https://api.example.com")


def test_attach_api_node_replaces_http():
    graph = {
        "nodes": [
            {"id": "trigger", "type": "trigger"},
            {"id": "http1", "type": "http", "data": {"url": "{{base_url}}"}},
            {"id": "llm", "type": "llm"},
        ],
        "edges": [
            {"from": "trigger", "to": "http1"},
            {"from": "http1", "to": "llm"},
        ],
    }
    patched = attach_api_node_to_graph(graph, "def123abc", "My API")
    types = [n["type"] for n in patched["nodes"]]
    assert "api_node" in types
    assert "http" not in types
    api = next(n for n in patched["nodes"] if n["type"] == "api_node")
    assert api["data"]["node_def_id"] == "def123abc"


def test_marketplace_routes_ops_not_compose():
    route = universal_route("open marketplace", has_pending=False)
    assert route["route"] == "ops"
    assert route["ops_intent"] == "open_marketplace"


def test_nav_dispatch_href():
    out = dispatch_nav_action("open_marketplace", "open marketplace")
    ev = out["events"][0]
    assert ev["type"] == "aios_navigate"
    assert ev["data"]["href"] == "/marketplace"


@pytest.fixture
def api_client():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as c:
        yield c


def test_node_probe_from_chat_dispatch(api_client):
    from app.composer.chat_actions import dispatch_ops_action
    from app.database import SessionLocal

    headers = __import__("tests.test_smoke", fromlist=["_auth_headers"])._auth_headers(api_client)
    conv = api_client.post(
        "/api/v1/conversations",
        headers=headers,
        json={"title": "node factory", "conversation_type": "assistant"},
    ).json()["data"]

    db = SessionLocal()
    try:
        import asyncio

        out = asyncio.run(
            dispatch_ops_action(
                db,
                workspace_id=1,
                user_id=1,
                conversation_id=conv["id"],
                user_message="Probe API",
                intent="node_probe",
            )
        )
        assert out is not None
        assert any(e["type"] == "aios_node_factory" for e in out.get("events") or [])
    finally:
        db.close()


def test_publish_node_blocked_without_test(api_client, db: Session):
    from app.composer.chat_actions import dispatch_ops_action
    from app.services.node_library import create_definition

    headers = __import__("tests.test_smoke", fromlist=["_auth_headers"])._auth_headers(api_client)
    conv = api_client.post(
        "/api/v1/conversations",
        headers=headers,
        json={"title": "publish block", "conversation_type": "assistant"},
    ).json()["data"]

    row = create_definition(
        db,
        1,
        1,
        {
            "display_name": "Untested",
            "definition": {
                "display_name": "Untested",
                "runtime": "http_declarative",
                "http": {"url": "https://example.com", "method": "GET", "auth": "custom"},
            },
        },
    )

    import asyncio

    conv_row = db.get(__import__("app.database", fromlist=["Conversation"]).Conversation, conv["id"])
    meta = json.loads(conv_row.meta_json or "{}")
    meta["aios"] = {"node_factory": {"pending_node_def_id": row.id}}
    conv_row.meta_json = json.dumps(meta)
    db.commit()

    out = asyncio.run(
        dispatch_ops_action(
            db,
            workspace_id=1,
            user_id=1,
            conversation_id=conv["id"],
            user_message="Publish node",
            intent="node_publish",
        )
    )
    types = [e["type"] for e in out.get("events") or []]
    assert "aios_error" in types
