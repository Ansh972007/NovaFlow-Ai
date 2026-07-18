"""AgentOS plugin registry."""

from __future__ import annotations

from typing import Any, Callable

_CUSTOM_AGENTS: dict[str, Callable] = {}
_CUSTOM_PLANNERS: dict[str, Callable] = {}
_CUSTOM_VERIFIERS: dict[str, Callable] = {}


def register_custom_agent(name: str, handler: Callable) -> None:
    _CUSTOM_AGENTS[name.lower()] = handler


def register_custom_planner(name: str, handler: Callable) -> None:
    _CUSTOM_PLANNERS[name.lower()] = handler


def register_custom_verifier(name: str, handler: Callable) -> None:
    _CUSTOM_VERIFIERS[name.lower()] = handler


def get_custom_agent(name: str) -> Callable | None:
    return _CUSTOM_AGENTS.get(name.lower())


def list_plugins() -> dict[str, list[str]]:
    return {
        "agents": list(_CUSTOM_AGENTS.keys()),
        "planners": list(_CUSTOM_PLANNERS.keys()),
        "verifiers": list(_CUSTOM_VERIFIERS.keys()),
    }
