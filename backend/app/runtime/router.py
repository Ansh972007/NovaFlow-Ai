"""Model router — configurable routing policies over AB routes + defaults."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from sqlalchemy.orm import Session

from app.runtime.providers import ProviderConfig, resolve_provider


class RoutingPolicy(str, Enum):
    DEFAULT = "default"
    LOW_LATENCY = "low_latency"
    LOW_COST = "low_cost"
    LARGE_CONTEXT = "large_context"


@dataclass
class RouteDecision:
    model: str
    provider_type: str
    variant: str = "base"
    route_id: int | None = None
    policy: str = "default"
    reason: str = ""


# Heuristic model hints per policy when AB route does not override
_POLICY_MODEL_HINTS: dict[str, list[str]] = {
    RoutingPolicy.LOW_LATENCY.value: ["gpt-4o-mini", "claude-3-5-haiku", "gemini-2.0-flash"],
    RoutingPolicy.LOW_COST.value: ["gpt-4o-mini", "openai/gpt-4o-mini", "llama3"],
    RoutingPolicy.LARGE_CONTEXT.value: ["gpt-4o", "claude-sonnet-4", "openai/gpt-4o"],
}


def route_model(
    db: Session,
    workspace_id: int | None,
    provider: ProviderConfig,
    *,
    policy: str | RoutingPolicy = RoutingPolicy.DEFAULT,
) -> RouteDecision:
    """Choose model: workspace AB split first, then policy hints, then provider default."""
    policy_s = policy.value if isinstance(policy, RoutingPolicy) else str(policy or "default")
    base_model = provider.model or ""

    if db is not None and workspace_id:
        from app.services.ab_routing import pick_ab_model

        ab = pick_ab_model(db, workspace_id, base_model)
        if ab and ab.get("model"):
            return RouteDecision(
                model=ab["model"],
                provider_type=provider.provider_type,
                variant=ab.get("variant") or "base",
                route_id=ab.get("route_id"),
                policy=policy_s,
                reason="ab_route",
            )

    if policy_s != RoutingPolicy.DEFAULT.value:
        hints = _POLICY_MODEL_HINTS.get(policy_s, [])
        for hint in hints:
            if hint:
                return RouteDecision(
                    model=hint,
                    provider_type=provider.provider_type,
                    policy=policy_s,
                    reason=f"policy:{policy_s}",
                )

    return RouteDecision(
        model=base_model,
        provider_type=provider.provider_type,
        policy=policy_s,
        reason="provider_default",
    )
