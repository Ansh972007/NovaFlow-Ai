"""Workspace node library — CRUD, probe, test, and publish for API node definitions."""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.database import NodeDefinition
from app.security.audit import audit_log
from app.security.rate_limit import rate_limiter
from app.services.api_node_runtime import (
    execute_http_probe,
    execute_api_node_definition,
    normalize_slug,
)

SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,78}[a-z0-9]$|^[a-z0-9]{1,2}$")

BUILTIN_PALETTE: list[dict[str, str]] = [
    {"type": "trigger", "label": "Trigger", "category": "builtin"},
    {"type": "retrieve", "label": "Retrieve", "category": "builtin"},
    {"type": "llm", "label": "LLM", "category": "builtin"},
    {"type": "output", "label": "Output", "category": "builtin"},
    {"type": "transform", "label": "Transform", "category": "builtin"},
    {"type": "condition", "label": "Condition", "category": "builtin"},
    {"type": "http", "label": "HTTP", "category": "builtin"},
    {"type": "notify", "label": "Notify", "category": "builtin"},
    {"type": "jira", "label": "Jira", "category": "builtin"},
    {"type": "github", "label": "GitHub", "category": "builtin"},
    {"type": "linear", "label": "Linear", "category": "builtin"},
    {"type": "loop", "label": "Loop", "category": "builtin"},
    {"type": "parallel", "label": "Parallel", "category": "builtin"},
    {"type": "human", "label": "Human", "category": "builtin"},
    {"type": "agent", "label": "Agent", "category": "builtin"},
    {"type": "subgraph", "label": "Subgraph", "category": "builtin"},
]


def node_def_dict(row: NodeDefinition, *, include_definition: bool = True) -> dict[str, Any]:
    try:
        defn = json.loads(row.definition_json or "{}")
    except json.JSONDecodeError:
        defn = {}
    out: dict[str, Any] = {
        "id": row.id,
        "workspace_id": row.workspace_id,
        "slug": row.slug,
        "display_name": row.display_name,
        "status": row.status,
        "version": row.version,
        "test_status": row.test_status,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        "category": defn.get("category") or "api",
        "icon": defn.get("icon") or "api",
        "tags": defn.get("tags") or [],
        "type": "api_node",
    }
    if include_definition:
        out["definition"] = defn
        try:
            out["test_result"] = json.loads(row.test_result_json or "{}")
        except json.JSONDecodeError:
            out["test_result"] = {}
    return out


def list_library(
    db: Session,
    workspace_id: int,
    *,
    include_drafts: bool = True,
    status: str | None = None,
) -> dict[str, Any]:
    q = db.query(NodeDefinition).filter(NodeDefinition.workspace_id == workspace_id)
    if status:
        q = q.filter(NodeDefinition.status == status)
    elif not include_drafts:
        q = q.filter(NodeDefinition.status == "published")
    rows = q.order_by(NodeDefinition.updated_at.desc()).all()
    custom = [node_def_dict(r, include_definition=False) for r in rows]
    return {"builtin": BUILTIN_PALETTE, "custom": custom}


def get_definition(db: Session, workspace_id: int, def_id: str) -> NodeDefinition | None:
    row = db.get(NodeDefinition, def_id)
    if not row or row.workspace_id != workspace_id:
        return None
    return row


def _validate_definition_payload(defn: dict[str, Any]) -> None:
    http = defn.get("http") or {}
    url = str(http.get("url") or "").strip()
    if not url:
        raise ValueError("definition.http.url is required")
    slug = normalize_slug(defn.get("slug") or defn.get("display_name") or "api_node")
    if not SLUG_RE.match(slug):
        raise ValueError("Invalid slug — use lowercase letters, numbers, hyphens, underscores")


def create_definition(
    db: Session,
    workspace_id: int,
    user_id: int,
    payload: dict[str, Any],
) -> NodeDefinition:
    defn = dict(payload.get("definition") or payload)
    display_name = str(payload.get("display_name") or defn.get("display_name") or "API Node").strip()
    slug = normalize_slug(payload.get("slug") or defn.get("slug") or display_name)
    defn.setdefault("slug", slug)
    defn.setdefault("display_name", display_name)
    defn.setdefault("runtime", "http_declarative")
    _validate_definition_payload(defn)

    existing = (
        db.query(NodeDefinition)
        .filter(NodeDefinition.workspace_id == workspace_id, NodeDefinition.slug == slug)
        .first()
    )
    if existing:
        raise ValueError(f"Node slug already exists: {slug}")

    row = NodeDefinition(
        id=uuid.uuid4().hex,
        workspace_id=workspace_id,
        created_by=user_id,
        slug=slug,
        display_name=display_name,
        definition_json=json.dumps(defn, ensure_ascii=False),
        status="draft",
        version=str(payload.get("version") or defn.get("version") or "1.0.0"),
        test_status="untested",
        test_result_json="{}",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_definition(
    db: Session,
    workspace_id: int,
    def_id: str,
    payload: dict[str, Any],
) -> NodeDefinition:
    row = get_definition(db, workspace_id, def_id)
    if not row:
        raise ValueError("Node definition not found")
    if row.status == "deprecated":
        raise ValueError("Deprecated definitions cannot be edited")

    if payload.get("display_name"):
        row.display_name = str(payload["display_name"]).strip()
    if payload.get("definition"):
        defn = dict(payload["definition"])
        defn.setdefault("slug", row.slug)
        defn.setdefault("display_name", row.display_name)
        _validate_definition_payload(defn)
        row.definition_json = json.dumps(defn, ensure_ascii=False)
    if payload.get("version"):
        row.version = str(payload["version"])
    if row.status == "published":
        row.status = "draft"
        row.test_status = "untested"
    row.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return row


def check_probe_rate(workspace_id: int, user_id: int) -> bool:
    key = f"ws:{workspace_id}:user:{user_id}"
    return rate_limiter.allow("node_probe", key, limit=20, window_seconds=60)


async def probe_http(
    db: Session,
    workspace_id: int,
    payload: dict[str, Any],
) -> dict[str, Any]:
    http_cfg = dict(payload.get("http") or payload)
    context = dict(payload.get("context") or {})
    context.setdefault("input", context.get("input") or "probe")
    return await execute_http_probe(db, workspace_id, http_cfg, context)


async def test_definition(
    db: Session,
    workspace_id: int,
    def_id: str,
    sample_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    row = get_definition(db, workspace_id, def_id)
    if not row:
        raise ValueError("Node definition not found")

    ctx = dict(sample_context or {})
    ctx.setdefault("input", ctx.get("input") or "test")
    ctx.setdefault("output", ctx.get("output") or "")

    try:
        defn = json.loads(row.definition_json or "{}")
    except json.JSONDecodeError:
        defn = {}
    http_cfg = dict(defn.get("http") or {})
    probe = await execute_http_probe(db, workspace_id, http_cfg, ctx)
    result = {
        "ok": probe.get("ok"),
        "status_code": probe.get("status_code"),
        "body_preview": probe.get("body_preview"),
        "error": probe.get("error"),
        "tested_at": datetime.utcnow().isoformat(),
    }
    row.test_result_json = json.dumps(result, ensure_ascii=False)
    row.test_status = "passed" if probe.get("ok") else "failed"
    row.updated_at = datetime.utcnow()
    db.commit()
    return result


def publish_definition(
    db: Session,
    workspace_id: int,
    user_id: int,
    def_id: str,
    *,
    require_test: bool = True,
) -> NodeDefinition:
    row = get_definition(db, workspace_id, def_id)
    if not row:
        raise ValueError("Node definition not found")
    if require_test and row.test_status != "passed":
        raise ValueError("Run a successful test before publishing")
    row.status = "published"
    row.updated_at = datetime.utcnow()
    db.commit()
    audit_log(
        db,
        action="node_library.publish",
        actor_user_id=user_id,
        workspace_id=workspace_id,
        resource_type="node_definition",
        resource_id=row.id,
        detail={"slug": row.slug, "version": row.version},
        success=True,
    )
    db.refresh(row)
    return row


def deprecate_definition(db: Session, workspace_id: int, user_id: int, def_id: str) -> NodeDefinition:
    row = get_definition(db, workspace_id, def_id)
    if not row:
        raise ValueError("Node definition not found")
    row.status = "deprecated"
    row.updated_at = datetime.utcnow()
    db.commit()
    audit_log(
        db,
        action="node_library.deprecate",
        actor_user_id=user_id,
        workspace_id=workspace_id,
        resource_type="node_definition",
        resource_id=row.id,
        detail={"slug": row.slug},
        success=True,
    )
    db.refresh(row)
    return row


def search_published(db: Session, workspace_id: int, keywords: list[str]) -> list[NodeDefinition]:
    if not keywords:
        return []
    rows = (
        db.query(NodeDefinition)
        .filter(NodeDefinition.workspace_id == workspace_id, NodeDefinition.status == "published")
        .all()
    )
    kw = [k.lower() for k in keywords if k]
    scored: list[tuple[int, NodeDefinition]] = []
    for row in rows:
        try:
            defn = json.loads(row.definition_json or "{}")
        except json.JSONDecodeError:
            defn = {}
        text = " ".join(
            [
                row.slug,
                row.display_name,
                str(defn.get("category") or ""),
                " ".join(defn.get("tags") or []),
            ]
        ).lower()
        score = sum(1 for k in kw if k in text)
        if score:
            scored.append((score, row))
    scored.sort(key=lambda x: -x[0])
    return [r for _, r in scored]


def find_best_library_match(db: Session, workspace_id: int, goal: str) -> NodeDefinition | None:
    goal_l = (goal or "").lower()
    tokens = re.findall(r"[a-z0-9]{3,}", goal_l)
    matches = search_published(db, workspace_id, tokens[:12])
    return matches[0] if matches else None


def get_published_def_ids(db: Session, workspace_id: int) -> set[str]:
    rows = (
        db.query(NodeDefinition.id)
        .filter(NodeDefinition.workspace_id == workspace_id, NodeDefinition.status == "published")
        .all()
    )
    return {r[0] for r in rows}


def validate_graph_api_nodes(db: Session, workspace_id: int, graph: dict[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    published = get_published_def_ids(db, workspace_id)
    for node in graph.get("nodes") or []:
        if not isinstance(node, dict):
            continue
        if str(node.get("type") or "").lower() != "api_node":
            continue
        nid = str(node.get("id") or "")
        data = node.get("data") or {}
        def_id = str(data.get("node_def_id") or "").strip()
        if not def_id:
            issues.append(
                {
                    "code": "missing_node_def_id",
                    "severity": "error",
                    "message": "api_node missing node_def_id",
                    "node_id": nid,
                }
            )
            continue
        row = db.get(NodeDefinition, def_id)
        if not row or row.workspace_id != workspace_id:
            issues.append(
                {
                    "code": "node_def_not_found",
                    "severity": "error",
                    "message": f"Node definition not found: {def_id}",
                    "node_id": nid,
                }
            )
        elif row.status != "published":
            issues.append(
                {
                    "code": "node_def_not_published",
                    "severity": "error",
                    "message": f"Node '{row.slug}' is not published (status={row.status})",
                    "node_id": nid,
                }
            )
        elif def_id not in published:
            issues.append(
                {
                    "code": "node_def_unavailable",
                    "severity": "error",
                    "message": f"Node '{row.slug}' is not available for execution",
                    "node_id": nid,
                }
            )
    return issues
