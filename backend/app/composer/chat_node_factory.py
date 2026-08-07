"""Chat ops: API node factory (probe/test/publish) and navigation."""

from __future__ import annotations

import json
import re
import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.database import Conversation, Workflow
from app.services.node_library import (
    check_probe_rate,
    create_definition,
    get_definition,
    node_def_dict,
    probe_http,
    publish_definition,
    test_definition,
)

NODE_FACTORY_INTENTS = frozenset(
    {
        "node_probe",
        "node_create",
        "node_test",
        "node_publish",
        "node_attach_to_workflow",
        "openapi_import",
    }
)

NAV_INTENTS = frozenset(
    {
        "open_marketplace",
        "open_settings",
        "open_model_lab",
        "open_credentials",
    }
)


def classify_node_factory_intent(text: str) -> str | None:
    t = (text or "").lower().strip()
    if not t:
        return None
    if re.search(r"\bimport openapi\b|\bopenapi import\b|\bimport swagger\b|\bfrom openapi\b", t):
        return "openapi_import"
    if re.search(
        r"\bprobe api\b|\bprobe (the )?api\b|\btest api call\b|\bprobe first\b|\bprobe first operation\b",
        t,
    ):
        return "node_probe"
    if re.search(r"\btest node\b|\brun node test\b|\btest api node\b", t):
        return "node_test"
    if re.search(r"\bpublish node\b|\bpublish api node\b", t):
        return "node_publish"
    if re.search(r"\buse in workflow\b|\battach.*node\b|\battach to workflow\b", t):
        return "node_attach_to_workflow"
    if re.search(r"\bsave (api )?node\b|\bcreate (api )?node\b|\bsave draft node\b", t):
        return "node_create"
    return None


def classify_nav_intent(text: str) -> str | None:
    t = (text or "").lower().strip()
    if not t:
        return None
    if re.search(r"\bopen marketplace\b|\bbrowse templates\b|\bworkflow marketplace\b", t):
        return "open_marketplace"
    if re.search(r"\bopen (the )?model lab\b|\bstart fine-?tune\b|\bopen fine-?tune\b", t):
        return "open_model_lab"
    if re.search(r"\bopen credentials\b|\bopen (the )?vault\b|\bcredential vault\b", t):
        return "open_credentials"
    if re.search(
        r"\bopen settings\b|\bsettings (security|team|integrations)\b|\bapi keys? settings\b|\bopen api keys?\b",
        t,
    ):
        return "open_settings"
    return None


def _load_aios(db: Session, conversation_id: str | None) -> tuple[Conversation | None, dict[str, Any]]:
    if not conversation_id:
        return None, {}
    conv = db.get(Conversation, conversation_id)
    if not conv:
        return None, {}
    try:
        meta = json.loads(conv.meta_json or "{}")
    except json.JSONDecodeError:
        meta = {}
    if not isinstance(meta, dict):
        meta = {}
    aios = meta.get("aios") if isinstance(meta.get("aios"), dict) else {}
    return conv, aios


def _save_aios(db: Session, conv: Conversation | None, aios: dict[str, Any]) -> None:
    if not conv:
        return
    try:
        meta = json.loads(conv.meta_json or "{}")
    except json.JSONDecodeError:
        meta = {}
    if not isinstance(meta, dict):
        meta = {}
    meta["aios"] = aios
    conv.meta_json = json.dumps(meta)
    db.commit()


def _node_factory_state(aios: dict[str, Any]) -> dict[str, Any]:
    nf = aios.get("node_factory")
    if not isinstance(nf, dict):
        nf = {}
        aios["node_factory"] = nf
    return nf


def _factory_event(
    nf: dict[str, Any],
    *,
    message: str,
    status: str = "active",
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    chips = list(nf.get("chips") or ["Probe API", "Save node", "Test node", "Publish node", "Use in workflow"])
    data: dict[str, Any] = {
        "message": message,
        "status": status,
        "suggested": nf.get("suggested") or {},
        "pending_node_def_id": nf.get("pending_node_def_id"),
        "workflow_id": nf.get("workflow_id"),
        "probe_result": nf.get("last_probe"),
        "test_result": nf.get("last_test"),
        "node_def": nf.get("node_def"),
        "chips": chips,
    }
    if extra:
        data.update(extra)
    return {"type": "aios_node_factory", "data": data}


def _navigate_event(title: str, message: str, href: str, chips: list[str] | None = None) -> dict[str, Any]:
    return {
        "type": "aios_navigate",
        "data": {
            "title": title,
            "message": message,
            "href": href,
            "chips": chips or [],
        },
    }


def _http_config_from_nf(nf: dict[str, Any]) -> dict[str, Any]:
    suggested = nf.get("suggested") or {}
    return {
        "url": suggested.get("url") or "{{base_url}}/v1/resource",
        "method": suggested.get("method") or "GET",
        "body": suggested.get("body") or "",
        "auth": suggested.get("auth") or "custom",
        "credential_id": suggested.get("credential_id"),
        "headers": suggested.get("headers") or {},
    }


def attach_api_node_to_graph(
    graph: dict[str, Any],
    node_def_id: str,
    display_name: str,
) -> dict[str, Any]:
    nodes = [dict(n) for n in (graph.get("nodes") or []) if isinstance(n, dict)]
    edges = [dict(e) for e in (graph.get("edges") or []) if isinstance(e, dict)]
    api_id = f"api_{node_def_id[:10]}"
    api_node = {
        "id": api_id,
        "type": "api_node",
        "data": {
            "node_def_id": node_def_id,
            "label": display_name,
            "set_output": True,
        },
    }
    replace_idx = None
    for i, node in enumerate(nodes):
        if str(node.get("type") or "").lower() in ("http", "api_node"):
            replace_idx = i
            break
    if replace_idx is not None:
        old_id = nodes[replace_idx].get("id")
        nodes[replace_idx] = api_node
        if old_id:
            for edge in edges:
                if edge.get("from") == old_id:
                    edge["from"] = api_id
                if edge.get("to") == old_id:
                    edge["to"] = api_id
    else:
        nodes.append(api_node)
        trigger = next((n for n in nodes if str(n.get("type")).lower() == "trigger"), None)
        llm = next((n for n in nodes if str(n.get("type")).lower() == "llm"), None)
        if trigger and llm:
            edges.append({"from": trigger.get("id"), "to": api_id})
            edges.append({"from": api_id, "to": llm.get("id")})
    return {"nodes": nodes, "edges": edges}


async def dispatch_node_factory_action(
    db: Session,
    *,
    workspace_id: int,
    user_id: int,
    conversation_id: str | None,
    user_message: str,
    intent: str,
) -> dict[str, Any]:
    conv, aios = _load_aios(db, conversation_id)
    nf = _node_factory_state(aios)
    nf["workflow_id"] = nf.get("workflow_id") or aios.get("workflow_id")
    nf.setdefault(
        "chips",
        ["Probe API", "Save node", "Test node", "Publish node", "Use in workflow"],
    )

    if intent == "node_probe":
        if not check_probe_rate(workspace_id, user_id):
            return {
                "events": [
                    {
                        "type": "aios_error",
                        "data": {
                            "message": "Probe rate limit exceeded — try again in a minute.",
                            "detail": "node_probe",
                        },
                    }
                ],
                "blocked_normal_reply": True,
                "summary": "Probe rate limited.",
            }
        http_cfg = _http_config_from_nf(nf)
        result = await probe_http(
            db,
            workspace_id,
            {"http": http_cfg, "context": {"input": "probe", "output": ""}},
        )
        nf["last_probe"] = result
        nf["suggested"] = {**(nf.get("suggested") or {}), **http_cfg}
        if result.get("ok"):
            nf["chips"] = ["Save node", "Test node", "Probe API", "Use in workflow"]
            msg = f"Probe OK (HTTP {result.get('status_code') or '—'})."
        else:
            nf["chips"] = ["Probe API", "Open workflow builder"]
            msg = f"Probe failed: {result.get('error') or 'check URL and credentials'}"
        _save_aios(db, conv, aios)
        ev = _factory_event(nf, message=msg, status="probed" if result.get("ok") else "probe_failed")
        return {
            "events": [ev],
            "blocked_normal_reply": True,
            "summary": msg,
        }

    if intent == "node_create":
        http_cfg = _http_config_from_nf(nf)
        display = str(nf.get("display_name") or nf.get("suggested", {}).get("label") or "Custom API")
        try:
            row = create_definition(
                db,
                workspace_id,
                user_id,
                {
                    "display_name": display,
                    "definition": {
                        "display_name": display,
                        "runtime": "http_declarative",
                        "http": http_cfg,
                    },
                },
            )
        except ValueError as exc:
            return {
                "events": [
                    {
                        "type": "aios_error",
                        "data": {"message": str(exc), "detail": "node_create"},
                    }
                ],
                "blocked_normal_reply": True,
                "summary": str(exc),
            }
        nf["pending_node_def_id"] = row.id
        nf["node_def"] = node_def_dict(row)
        nf["chips"] = ["Test node", "Publish node", "Use in workflow", "Probe API"]
        _save_aios(db, conv, aios)
        msg = f"Saved draft node **{row.display_name}** (`{row.slug}`)."
        return {
            "events": [_factory_event(nf, message=msg, status="draft")],
            "blocked_normal_reply": True,
            "summary": msg,
        }

    if intent == "node_test":
        def_id = nf.get("pending_node_def_id")
        if not def_id:
            return {
                "events": [
                    _factory_event(
                        nf,
                        message="Save a draft node first (Probe API → Save node).",
                        status="needs_draft",
                    )
                ],
                "blocked_normal_reply": True,
                "summary": "No draft node to test.",
            }
        result = await test_definition(db, workspace_id, def_id)
        nf["last_test"] = result
        row = get_definition(db, workspace_id, def_id)
        if row:
            nf["node_def"] = node_def_dict(row)
        nf["chips"] = (
            ["Publish node", "Use in workflow", "Test node"]
            if result.get("ok")
            else ["Probe API", "Test node", "Save node"]
        )
        _save_aios(db, conv, aios)
        msg = (
            f"Node test passed (HTTP {result.get('status_code') or '—'})."
            if result.get("ok")
            else f"Node test failed: {result.get('error') or 'probe error'}"
        )
        return {
            "events": [_factory_event(nf, message=msg, status="tested" if result.get("ok") else "test_failed")],
            "blocked_normal_reply": True,
            "summary": msg,
        }

    if intent == "node_publish":
        def_id = nf.get("pending_node_def_id")
        if not def_id:
            return {
                "events": [
                    _factory_event(nf, message="Create and test a node before publishing.", status="needs_draft")
                ],
                "blocked_normal_reply": True,
                "summary": "No node to publish.",
            }
        try:
            row = publish_definition(db, workspace_id, user_id, def_id, require_test=True)
        except ValueError as exc:
            return {
                "events": [
                    {
                        "type": "aios_error",
                        "data": {"message": str(exc), "detail": "node_publish"},
                    },
                    _factory_event(nf, message=str(exc), status="publish_blocked"),
                ],
                "blocked_normal_reply": True,
                "summary": str(exc),
            }
        nf["node_def"] = node_def_dict(row)
        nf["chips"] = ["Use in workflow", "Run now", "Probe API"]
        _save_aios(db, conv, aios)
        msg = f"Published node **{row.display_name}** — ready for workflows."
        return {
            "events": [_factory_event(nf, message=msg, status="published")],
            "blocked_normal_reply": True,
            "summary": msg,
        }

    if intent == "node_attach_to_workflow":
        def_id = nf.get("pending_node_def_id")
        row = get_definition(db, workspace_id, def_id) if def_id else None
        if not row or row.status != "published":
            return {
                "events": [
                    _factory_event(
                        nf,
                        message="Publish the API node first, then attach it to your workflow.",
                        status="needs_publish",
                    )
                ],
                "blocked_normal_reply": True,
                "summary": "Publish node before attach.",
            }
        preview = dict(aios.get("executable_preview") or {})
        if not preview.get("nodes"):
            preview = {"nodes": [], "edges": []}
        patched = attach_api_node_to_graph(preview, row.id, row.display_name)
        aios["executable_preview"] = patched
        wf_id = nf.get("workflow_id") or aios.get("workflow_id")
        if wf_id:
            wf = db.get(Workflow, wf_id)
            if wf and int(wf.workspace_id or 0) == workspace_id:
                wf.graph_json = json.dumps(patched)
                db.commit()
        _save_aios(db, conv, aios)
        msg = f"Attached **{row.display_name}** to the workflow graph."
        return {
            "events": [
                _factory_event(nf, message=msg, status="attached"),
                {
                    "type": "aios_suggest",
                    "data": {
                        "message": "Graph updated with your API node.",
                        "chips": ["Run test", "Approve", "Deploy", "Run now"],
                    },
                },
            ],
            "blocked_normal_reply": True,
            "summary": msg,
        }

    if intent == "openapi_import":
        from app.services.openapi_import import draft_definitions_from_openapi, summarize_openapi

        raw = nf.get("openapi_raw") or user_message
        if user_message.strip().startswith("{") or "openapi" in user_message.lower():
            nf["openapi_raw"] = user_message
            raw = user_message
        try:
            summary = summarize_openapi(raw)
            drafts = draft_definitions_from_openapi(raw)
        except ValueError as exc:
            return {
                "events": [
                    {
                        "type": "aios_error",
                        "data": {"message": str(exc), "detail": "openapi_import"},
                    }
                ],
                "blocked_normal_reply": True,
                "summary": str(exc),
            }
        created: list[dict[str, Any]] = []
        for draft in drafts[:12]:
            try:
                row = create_definition(db, workspace_id, user_id, draft)
                created.append(node_def_dict(row, include_definition=False))
            except ValueError:
                continue
        nf["openapi_imported"] = [c["id"] for c in created]
        if created:
            nf["pending_node_def_id"] = created[0]["id"]
        _save_aios(db, conv, aios)
        ev = {
            "type": "aios_openapi_import",
            "data": {
                "title": summary.get("title"),
                "message": f"Imported {len(created)} draft node(s) from OpenAPI ({summary.get('operation_count')} ops found).",
                "operations": summary.get("operations") or [],
                "created": created,
                "chips": ["Publish node", "Test node", "Probe first operation", "Use in workflow"],
            },
        }
        return {
            "events": [ev],
            "blocked_normal_reply": True,
            "summary": ev["data"]["message"],
        }

    return {
        "events": [{"type": "aios_error", "data": {"message": "Unknown node factory action."}}],
        "blocked_normal_reply": True,
        "summary": "Unknown node factory action.",
    }


def dispatch_nav_action(intent: str, user_message: str) -> dict[str, Any]:
    t = (user_message or "").lower()
    if intent == "open_marketplace":
        ev = _navigate_event(
            "Marketplace",
            "Browse community workflow templates and clone them into your workspace.",
            "/marketplace",
            ["Build a workflow", "What can you do?"],
        )
    elif intent == "open_model_lab":
        ev = _navigate_event(
            "Model Lab",
            "Fine-tune models, compare evals, and manage training jobs in Model Lab.",
            "/developer?tab=models",
            ["Model lab costs", "Show forge"],
        )
    elif intent == "open_credentials":
        ev = _navigate_event(
            "Credentials",
            "Manage integration secrets and OAuth connections for workflows.",
            "/credentials",
            ["List vault", "Open Credentials"],
        )
    elif intent == "open_settings":
        tab = "overview"
        if "security" in t:
            tab = "security"
        elif "team" in t:
            tab = "team"
        elif "integration" in t:
            tab = "integrations"
        elif re.search(r"\bapi\b|\bmodel", t):
            tab = "integrations"
        ev = _navigate_event(
            "Settings",
            f"Open workspace settings ({tab} tab). For API keys, use Credentials or Integrations.",
            f"/settings?tab={tab}",
            ["Open Credentials", "Integrations health"],
        )
    else:
        ev = _navigate_event("Navigate", "Pick a destination.", "/")
    return {
        "events": [ev],
        "blocked_normal_reply": True,
        "summary": ev["data"]["message"],
    }
