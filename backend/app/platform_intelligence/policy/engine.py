"""Centralized policy engine — organization, workspace, execution policies."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

DEFAULT_POLICIES: list[dict] = [
    {
        "policy_type": "rate_limit",
        "scope": "workspace",
        "rule_key": "ai.requests_per_minute",
        "rule_value": "120",
        "severity": "enforce",
    },
    {
        "policy_type": "prompt",
        "scope": "workspace",
        "rule_key": "block_prompt_injection",
        "rule_value": "true",
        "severity": "enforce",
    },
    {
        "policy_type": "retention",
        "scope": "organization",
        "rule_key": "audit_log_days",
        "rule_value": "365",
        "severity": "advisory",
    },
    {
        "policy_type": "provider",
        "scope": "workspace",
        "rule_key": "allow_external_http",
        "rule_value": "true",
        "severity": "enforce",
    },
    {
        "policy_type": "workflow",
        "scope": "workspace",
        "rule_key": "require_publish_validation",
        "rule_value": "true",
        "severity": "enforce",
    },
]


@dataclass
class PolicyDecision:
    allowed: bool
    reason: str = ""
    policy_id: int | None = None
    severity: str = "enforce"
    matched_rules: list[str] = field(default_factory=list)


def _load_policies(db: Session, workspace_id: int | None, organization_id: int | None) -> list[dict]:
    from app.database import PlatformPolicy

    q = db.query(PlatformPolicy).filter(PlatformPolicy.enabled == 1)
    if workspace_id:
        q = q.filter(
            (PlatformPolicy.workspace_id == workspace_id)
            | (PlatformPolicy.workspace_id.is_(None))
        )
    if organization_id:
        q = q.filter(
            (PlatformPolicy.organization_id == organization_id)
            | (PlatformPolicy.organization_id.is_(None))
        )
    rows = q.all()
    if rows:
        return [
            {
                "id": r.id,
                "policy_type": r.policy_type,
                "scope": r.scope,
                "rule_key": r.rule_key,
                "rule_value": r.rule_value,
                "severity": r.severity,
            }
            for r in rows
        ]
    return DEFAULT_POLICIES


def evaluate_policy(
    db: Session,
    policy_type: str,
    context: dict[str, Any],
    *,
    workspace_id: int | None = None,
    organization_id: int | None = None,
) -> PolicyDecision:
    """Evaluate policies for a given type and context."""
    policies = _load_policies(db, workspace_id, organization_id)
    matched: list[str] = []
    blocking: PolicyDecision | None = None

    for p in policies:
        if p.get("policy_type") != policy_type and policy_type != "*":
            continue
        key = p.get("rule_key") or ""
        val = p.get("rule_value") or ""
        severity = p.get("severity") or "enforce"

        if policy_type == "quota" and key == "monthly_cost_usd":
            budget = float(val or 0)
            current = float(context.get("current_cost_usd") or 0)
            if budget > 0 and current > budget:
                dec = PolicyDecision(
                    allowed=False,
                    reason=f"Monthly budget exceeded (${current:.2f} > ${budget:.2f})",
                    policy_id=p.get("id"),
                    severity=severity,
                    matched_rules=[key],
                )
                if severity == "enforce":
                    return dec
                blocking = dec
            matched.append(key)

        if policy_type == "provider" and key == "allowed_models":
            allowed = [m.strip() for m in val.split(",") if m.strip()]
            model = (context.get("model") or "").strip()
            if allowed and model and model not in allowed:
                dec = PolicyDecision(
                    allowed=False,
                    reason=f"Model {model!r} not in allowlist",
                    policy_id=p.get("id"),
                    severity=severity,
                    matched_rules=[key],
                )
                if severity == "enforce":
                    return dec
                blocking = dec

        if policy_type == "workflow" and key == "require_publish_validation":
            if val.lower() == "true" and context.get("skip_validation"):
                return PolicyDecision(
                    allowed=False,
                    reason="Publish validation required by policy",
                    policy_id=p.get("id"),
                    severity=severity,
                    matched_rules=[key],
                )

        if policy_type == "execution" and key == "max_concurrent_runs":
            limit = int(val or 0)
            current = int(context.get("concurrent_runs") or 0)
            if limit > 0 and current >= limit:
                return PolicyDecision(
                    allowed=False,
                    reason=f"Concurrent run limit ({limit}) reached",
                    policy_id=p.get("id"),
                    severity=severity,
                    matched_rules=[key],
                )

    if blocking:
        return blocking
    return PolicyDecision(allowed=True, matched_rules=matched)


def seed_default_policies(db: Session, workspace_id: int) -> int:
    from app.database import PlatformPolicy

    count = 0
    for p in DEFAULT_POLICIES:
        exists = (
            db.query(PlatformPolicy)
            .filter(
                PlatformPolicy.workspace_id == workspace_id,
                PlatformPolicy.rule_key == p["rule_key"],
            )
            .first()
        )
        if exists:
            continue
        db.add(
            PlatformPolicy(
                workspace_id=workspace_id,
                policy_type=p["policy_type"],
                scope=p["scope"],
                rule_key=p["rule_key"],
                rule_value=p["rule_value"],
                severity=p["severity"],
                enabled=1,
            )
        )
        count += 1
    if count:
        db.commit()
    return count
