"""Smoke tests for integration credential_id resolution."""

import pytest

from app.database import SessionLocal, User
from app.services.gmail_jira import resolve_jira_config
from app.services.github_issues import resolve_github_config
from app.services.linear_issues import resolve_linear_config
from app.services.tenancy import ensure_personal_workspace


def test_resolve_jira_config_no_workspace():
    cfg = resolve_jira_config(None, None)
    assert cfg["configured"] is False


def test_resolve_github_config_no_workspace():
    cfg = resolve_github_config(None, None)
    assert cfg["configured"] is False


def test_resolve_linear_config_no_workspace():
    cfg = resolve_linear_config(None, None)
    assert cfg["configured"] is False


def test_dynamic_component_runtime_missing_name():
    import asyncio

    from app.services.dynamic_component_runtime import execute_dynamic_component

    db = SessionLocal()
    try:
        user = db.query(User).first()
        if not user:
            pytest.skip("no user")
        ws = ensure_personal_workspace(db, user)

        async def _run():
            with pytest.raises(ValueError, match="component_name"):
                await execute_dynamic_component(
                    db,
                    ws.id,
                    "",
                    {},
                    {"input": "test"},
                )

        asyncio.run(_run())
    finally:
        db.close()
