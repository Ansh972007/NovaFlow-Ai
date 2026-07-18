"""ECP policy engine — connector access control."""

from __future__ import annotations

from typing import Any

BLOCKED_CONNECTORS_DEFAULT: set[str] = set()
BLOCKED_DOMAINS_DEFAULT = {"localhost", "127.0.0.1", "0.0.0.0"}


def evaluate_connector_policy(
    *,
    connector_type: str,
    workspace_policies: dict | None = None,
    organization_policies: dict | None = None,
) -> dict[str, Any]:
    policies = {**(organization_policies or {}), **(workspace_policies or {})}
    allowed = policies.get("allowed_connectors")
    blocked = set(policies.get("blocked_connectors") or []) | BLOCKED_CONNECTORS_DEFAULT
    if connector_type in blocked:
        return {"allowed": False, "reason": "connector_blocked"}
    if allowed and connector_type not in allowed:
        return {"allowed": False, "reason": "connector_not_allowed"}
    return {"allowed": True, "reason": "ok"}


def evaluate_domain_policy(url: str, *, policies: dict | None = None) -> dict[str, Any]:
    policies = policies or {}
    blocked = set(policies.get("blocked_domains") or []) | BLOCKED_DOMAINS_DEFAULT
    lower = (url or "").lower()
    for domain in blocked:
        if domain in lower:
            return {"allowed": False, "reason": f"domain_blocked:{domain}"}
    return {"allowed": True, "reason": "ok"}


def requires_approval(connector_type: str, action: str, *, policies: dict | None = None) -> bool:
    policies = policies or {}
    rules = policies.get("approval_rules") or []
    for rule in rules:
        if rule.get("connector") == connector_type and action in (rule.get("actions") or []):
            return True
    return connector_type in (policies.get("approval_connectors") or [])
