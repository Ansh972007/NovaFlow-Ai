"""Tests for workflow node registry and library API."""

import pytest

from app.workflow_intelligence.node_registry import (
    default_data_for_type,
    get_builtin_palette_with_schemas,
    get_known_node_types,
    list_dynamic_components,
    validate_node_data,
)
from app.services.node_library import list_library


def test_known_node_types_include_subgraph_and_component():
    types = get_known_node_types()
    assert "subgraph" in types
    assert "component_node" in types
    assert "api_node" in types
    assert len(types) >= 17


def test_builtin_palette_has_schemas():
    palette = get_builtin_palette_with_schemas()
    assert len(palette) >= 16
    trigger = next(p for p in palette if p["type"] == "trigger")
    assert trigger.get("fields")
    assert trigger.get("defaults")


def test_default_data_for_http_has_credential_id():
    data = default_data_for_type("http")
    assert "url" in data
    assert "credential_id" in data


def test_validate_node_data_http_requires_url():
    issues = validate_node_data("http", {"url": ""})
    assert any(i["field"] == "url" for i in issues)


def test_validate_node_data_jira_create_requires_project_key():
    issues = validate_node_data("jira", {"action": "create", "project_key": ""})
    assert any(i["field"] == "project_key" for i in issues)


def test_notify_email_fields_are_channel_specific():
    from app.workflow_intelligence.node_registry import get_schema

    schema = get_schema("notify")
    fields = schema.get("fields") or []
    email_to = [f for f in fields if f.get("key") == "to" and (f.get("show_when") or {}).get("channel") == "email"]
    telegram_to = [f for f in fields if f.get("key") == "to" and (f.get("show_when") or {}).get("channel") == "telegram"]
    email_from = [f for f in fields if f.get("key") == "from"]
    assert email_to and email_from
    assert telegram_to
    assert email_to[0].get("label") != telegram_to[0].get("label")


def test_merge_node_data_fills_defaults():
    from app.workflow_intelligence.node_registry import merge_node_data_with_defaults

    merged = merge_node_data_with_defaults("notify", {"channel": "email", "to": "a@b.com"})
    assert merged.get("channel") == "email"
    assert merged.get("to") == "a@b.com"
    assert "message" in merged
    assert "subject" in merged


    rows = list_dynamic_components()
    assert isinstance(rows, list)


def test_list_library_returns_dynamic_section():
    from app.database import SessionLocal
    from app.services.tenancy import ensure_personal_workspace
    from app.database import User

    db = SessionLocal()
    try:
        user = db.query(User).first()
        if not user:
            pytest.skip("no user in test db")
        ws = ensure_personal_workspace(db, user)
        out = list_library(db, ws.id, include_drafts=False)
        assert "builtin" in out
        assert "custom" in out
        assert "dynamic" in out
        assert isinstance(out["builtin"][0], dict)
        assert "fields" in out["builtin"][0]
    finally:
        db.close()
