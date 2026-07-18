"""Plugin SDK — extensibility hooks for custom nodes, triggers, and validators."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable

NodeHandler = Callable[..., Awaitable[dict[str, Any]]]
ValidatorHook = Callable[[dict], list[dict]]


@dataclass
class PluginManifest:
    id: str
    name: str
    version: str = "1.0.0"
    node_types: list[str] = field(default_factory=list)
    description: str = ""


class WorkflowPluginRegistry:
    """Register custom node handlers and validators without modifying core engine."""

    def __init__(self) -> None:
        self._nodes: dict[str, NodeHandler] = {}
        self._validators: list[ValidatorHook] = []
        self._manifests: dict[str, PluginManifest] = {}

    def register_node(self, node_type: str, handler: NodeHandler, *, manifest: PluginManifest | None = None) -> None:
        self._nodes[node_type] = handler
        if manifest:
            self._manifests[manifest.id] = manifest

    def register_validator(self, hook: ValidatorHook) -> None:
        self._validators.append(hook)

    def get_node_handler(self, node_type: str) -> NodeHandler | None:
        return self._nodes.get(node_type)

    def run_validators(self, graph: dict) -> list[dict]:
        issues: list[dict] = []
        for hook in self._validators:
            try:
                issues.extend(hook(graph) or [])
            except Exception as exc:
                issues.append({"code": "plugin_validator_error", "severity": "warning", "message": str(exc)})
        return issues

    def list_plugins(self) -> list[dict]:
        return [
            {"id": m.id, "name": m.name, "version": m.version, "node_types": m.node_types}
            for m in self._manifests.values()
        ]


plugin_registry = WorkflowPluginRegistry()
