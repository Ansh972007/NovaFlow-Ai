"""Tests for Capability Horizon plan features."""

from __future__ import annotations

from app.composer.chat_actions import capabilities_event, classify_ops_intent
from app.composer.chat_bridge import _ui_events_from
from app.composer.chat_requirements import oauth_assist_url
from app.composer.graph_planner import _validate_graph, is_llm_graph_compose_enabled


def test_capabilities_event_has_workflow_types():
    ev = capabilities_event()
    data = ev["data"]
    assert data.get("can_build")
    assert data.get("cannot")
    assert len(data.get("workflow_types") or []) >= 5


def test_ui_events_from_returns_primary():
    events = [
        {"type": "aios_solution", "data": {"message": "a"}},
        {"type": "aios_progress", "data": {"message": "b"}},
        {"type": "aios_suggest", "data": {"message": "c"}},
    ]
    ui = _ui_events_from(events)
    assert len(ui) == 1
    assert ui[0]["type"] == "aios_solution"


def test_oauth_assist_urls():
    assert "google" in oauth_assist_url("google_calendar")
    assert oauth_assist_url("unknown") == "/credentials?return=chat"


def test_graph_validate_accepts_minimal():
    graph, err = _validate_graph(
        {
            "nodes": [
                {"id": "trigger", "type": "trigger", "data": {"label": "Start"}},
                {"id": "output", "type": "output", "data": {"label": "Done"}},
            ],
            "edges": [{"source": "trigger", "target": "output"}],
        }
    )
    assert graph is not None
    assert not err


def test_create_component_ops_intent():
    assert classify_ops_intent("create component email_parser") == "create_component"


def test_llm_graph_compose_enabled_default():
    assert is_llm_graph_compose_enabled(None, 1) is True
