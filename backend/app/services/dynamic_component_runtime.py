"""Runtime execution for AI-generated disk components."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.workflow_intelligence.node_registry import get_component_discovery


def _apply_template(text: str, context: dict[str, Any]) -> str:
    out = str(text or "")
    for key, val in context.items():
        if isinstance(val, (str, int, float)):
            out = out.replace(f"{{{{{key}}}}}", str(val))
    return out


async def execute_dynamic_component(
    db: Session,
    workspace_id: int,
    component_name: str,
    node_data: dict[str, Any],
    context: dict[str, Any],
    *,
    rt_ctx: Any = None,
) -> dict[str, Any]:
    """
    Execute a disk component by name.
    HTTP-config components use api_node_runtime; others use bounded LLM fallback.
    """
    name = str(component_name or node_data.get("component_name") or "").strip()
    if not name:
        raise ValueError("component_name is required")

    discovery = get_component_discovery()
    component = discovery.find_component(name)
    if not component:
        raise ValueError(f"Component not found: {name}")

    merged_ctx = {**context, **{k: v for k, v in node_data.items() if not k.startswith("_")}}
    config = component.get("configuration") or {}

    # HTTP path
    url = str(config.get("url") or "").strip()
    if url:
        from app.services.api_node_runtime import execute_http_probe

        http_cfg = {
            "url": _apply_template(url, merged_ctx),
            "method": str(config.get("method") or "GET").upper(),
            "body": _apply_template(str(config.get("body") or ""), merged_ctx),
            "auth": config.get("auth") or "custom",
            "credential_id": node_data.get("credential_id") or config.get("credential_id"),
            "headers": config.get("headers") or {},
        }
        probe = await execute_http_probe(db, workspace_id, http_cfg, merged_ctx)
        if not probe.get("ok"):
            raise ValueError(probe.get("error") or f"HTTP {probe.get('status_code')}")
        body = probe.get("body_preview") or probe.get("body") or ""
        return {"output": body, "http": probe}

    # LLM fallback — no arbitrary code execution
    description = str(component.get("description") or f"Run component {name}")
    purpose = str(component.get("type") or "custom")
    input_text = merged_ctx.get("input") or merged_ctx.get("output") or ""
    for inp in component.get("inputs") or []:
        if isinstance(inp, dict):
            k = inp.get("key") or inp.get("name")
            if k and node_data.get(k):
                input_text = f"{k}: {node_data.get(k)}\n{input_text}"

    if not rt_ctx:
        raise ValueError("Component requires LLM runtime context (no HTTP configuration)")

    from app.services.workflow import workflow_llm_sync

    sys_msg = (
        f"You are executing workflow component '{name}' ({purpose}). "
        f"Description: {description}. "
        "Respond with the component result only — no preamble."
    )
    reply = await workflow_llm_sync(rt_ctx, sys_msg, str(input_text)[:8000])
    return {"output": (reply or "").strip(), "mode": "llm_fallback"}
