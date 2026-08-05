"""Chat Forge — 12 mega Peak Chat capabilities on unused platform backends."""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.config import UPLOAD_DIR
from app.database import AbModelRoute, ConversationAttachment, DevProject, FineTuneDataset, FineTuneJob, Workflow

logger = logging.getLogger(__name__)

FORGE_INTENTS = frozenset(
    {
        "forge_catalog",
        "prompt_drift",
        "ab_router",
        "webhook_studio",
        "project_packs",
        "publish_scan",
        "template_reuse",
        "model_lab_desk",
        "ocr_to_workflow",
        "issue_bridge",
        "csv_import_chat",
        "solution_docs",
        "solution_assert",
    }
)

FORGE_CATALOG = [
    {"id": "prompt_drift", "title": "Prompt/Config Drift Radar", "chip": "Show prompt drift", "card": "aios_drift"},
    {"id": "ab_router", "title": "A/B Model Router Desk", "chip": "Show A/B routes", "card": "aios_ab"},
    {"id": "webhook_studio", "title": "Webhook Studio", "chip": "Open webhook studio", "card": "aios_webhook"},
    {"id": "project_packs", "title": "Project Packs", "chip": "List project packs", "card": "aios_project"},
    {"id": "publish_scan", "title": "Marketplace Publish Scan", "chip": "Scan for publish", "card": "aios_publish_scan"},
    {"id": "template_reuse", "title": "Template Reuse Finder", "chip": "Find reusable template", "card": "aios_reuse"},
    {"id": "model_lab_desk", "title": "Model Lab Cost Desk", "chip": "Model lab costs", "card": "aios_model_lab"},
    {"id": "ocr_to_workflow", "title": "OCR / Doc → Workflow", "chip": "OCR attachments to workflow", "card": "aios_ocr"},
    {"id": "issue_bridge", "title": "Issue Bridge (GitHub)", "chip": "GitHub issue bridge", "card": "aios_issue"},
    {"id": "csv_import_chat", "title": "CSV → Eval/Workflow", "chip": "Import CSV from chat", "card": "aios_csv"},
    {"id": "solution_docs", "title": "Solution Doc Generator", "chip": "Generate solution docs", "card": "aios_docs"},
    {"id": "solution_assert", "title": "Solution Test Assertions", "chip": "Run solution assertions", "card": "aios_assert"},
]

_FORGE_REGISTERED = False


def register_forge_ops() -> None:
    global _FORGE_REGISTERED
    if _FORGE_REGISTERED:
        return
    from app.composer.chat_ops_registry import OpSpec, register_op

    specs = [
        OpSpec(
            "forge_catalog",
            (r"\b(show )?forge\b", r"\bchat forge\b", r"\bforge tools\b", r"\bshow forge\b"),
            "aios_forge",
            "forge",
            title="Chat Forge",
            chip="Show forge",
            priority=20,
        ),
        OpSpec("prompt_drift", (r"\b(show )?prompt drift\b", r"\bconfig drift\b", r"\bdrift radar\b"), "aios_drift", "forge", title="Prompt Drift Radar", chip="Show prompt drift", priority=40),
        OpSpec("ab_router", (r"\b(show )?a/?b routes?\b", r"\bab model\b", r"\bmodel router\b"), "aios_ab", "forge", title="A/B Model Router", chip="Show A/B routes", priority=40),
        OpSpec("webhook_studio", (r"\bwebhook studio\b", r"\b(open |list )?webhooks?\b", r"\bprovision webhook\b"), "aios_webhook", "forge", title="Webhook Studio", chip="Open webhook studio", priority=40),
        OpSpec("project_packs", (r"\b(list )?project packs?\b", r"\bcreate project pack\b", r"\bdev projects?\b"), "aios_project", "forge", title="Project Packs", chip="List project packs", priority=40),
        OpSpec("publish_scan", (r"\bscan (for )?publish\b", r"\bmarketplace (publish )?scan\b", r"\bpublish scan\b"), "aios_publish_scan", "forge", title="Publish Scan", chip="Scan for publish", priority=40),
        OpSpec("template_reuse", (r"\bfind reusable template\b", r"\btemplate reuse\b", r"\breuse template\b"), "aios_reuse", "forge", title="Template Reuse", chip="Find reusable template", priority=40),
        OpSpec("model_lab_desk", (r"\bmodel lab( costs?)?\b", r"\bfinetune cost\b", r"\btraining cost\b"), "aios_model_lab", "forge", title="Model Lab Costs", chip="Model lab costs", priority=40),
        OpSpec("ocr_to_workflow", (r"\bocr (attachments? )?to workflow\b", r"\bdoc(ument)? to workflow\b", r"\bextract (text|ocr) from attachments?\b"), "aios_ocr", "forge", title="OCR → Workflow", chip="OCR attachments to workflow", priority=40),
        OpSpec("issue_bridge", (r"\bgithub issue bridge\b", r"\b(create|open) github issue\b", r"\bissue bridge\b"), "aios_issue", "forge", title="Issue Bridge", chip="GitHub issue bridge", priority=40),
        OpSpec("csv_import_chat", (r"\bimport csv( from chat)?\b", r"\bcsv (to )?(eval|workflow)\b", r"\bparse csv attachment\b"), "aios_csv", "forge", title="CSV Import", chip="Import CSV from chat", priority=40),
        OpSpec("solution_docs", (r"\bgenerate solution docs?\b", r"\bsolution documentation\b", r"\bdocument (this )?solution\b"), "aios_docs", "forge", title="Solution Docs", chip="Generate solution docs", priority=40),
        OpSpec("solution_assert", (r"\brun solution assertions?\b", r"\bsolution (test )?assertions?\b", r"\bassert (the )?solution\b"), "aios_assert", "forge", title="Solution Assertions", chip="Run solution assertions", priority=40),
    ]
    for spec in specs:
        register_op(spec, None)
    _FORGE_REGISTERED = True


def classify_forge_intent(text: str) -> str | None:
    register_forge_ops()
    t = (text or "").lower().strip()
    if not t:
        return None
    ordered = [
        ("forge_catalog", r"\b(show )?forge\b|\bchat forge\b|\bforge tools\b"),
        ("prompt_drift", r"\b(show )?prompt drift\b|\bconfig drift\b|\bdrift radar\b"),
        ("ab_router", r"\b(show )?a/?b routes?\b|\bab model\b|\bmodel router\b"),
        ("webhook_studio", r"\bwebhook studio\b|\b(open |list )?webhooks?\b|\bprovision webhook\b"),
        ("project_packs", r"\b(list )?project packs?\b|\bcreate project pack\b|\bdev projects?\b"),
        ("publish_scan", r"\bscan (for )?publish\b|\bmarketplace (publish )?scan\b|\bpublish scan\b"),
        ("template_reuse", r"\bfind reusable template\b|\btemplate reuse\b|\breuse template\b"),
        ("model_lab_desk", r"\bmodel lab( costs?)?\b|\bfinetune cost\b|\btraining cost\b"),
        ("ocr_to_workflow", r"\bocr (attachments? )?to workflow\b|\bdoc(ument)? to workflow\b|\bextract (text|ocr) from attachments?\b"),
        ("issue_bridge", r"\bgithub issue bridge\b|\b(create|open) github issue\b|\bissue bridge\b"),
        ("csv_import_chat", r"\bimport csv( from chat)?\b|\bcsv (to )?(eval|workflow)\b|\bparse csv attachment\b"),
        ("solution_docs", r"\bgenerate solution docs?\b|\bsolution documentation\b|\bdocument (this )?solution\b"),
        ("solution_assert", r"\brun solution assertions?\b|\bsolution (test )?assertions?\b|\bassert (the )?solution\b"),
    ]
    for intent, pat in ordered:
        if re.search(pat, t):
            return intent
    return None


def _helpers():
    from app.composer import chat_actions as ca

    return ca


def forge_catalog_action() -> dict[str, Any]:
    return {
        "events": [
            {
                "type": "aios_forge",
                "data": {
                    "title": "Chat Forge — 12 platform tools",
                    "tools": FORGE_CATALOG,
                    "chips": [t["chip"] for t in FORGE_CATALOG],
                    "message": "Forge tools for drift, A/B, webhooks, projects, publish scan, reuse, model lab, OCR, issues, CSV, docs, and assertions.",
                },
            }
        ],
        "blocked_normal_reply": True,
        "summary": "Chat Forge: 12 tools ready.",
    }


def prompt_drift_action(db: Session, *, workspace_id: int) -> dict[str, Any]:
    from app.services.drift import compute_prompt_drift

    report = compute_prompt_drift(db, workspace_id)
    radar = report.get("radar") or report.get("suites") or []
    if isinstance(report, dict) and not radar and report.get("items"):
        radar = report["items"]
    return {
        "events": [
            {
                "type": "aios_drift",
                "data": {
                    "status": "ok" if radar else "empty",
                    "radar": radar[:12] if isinstance(radar, list) else [],
                    "report": {k: v for k, v in (report or {}).items() if k != "radar"},
                    "message": (
                        f"Drift radar: {len(radar)} suite(s) with enough eval history."
                        if radar
                        else "No drift signal yet — run eval suites twice to compare pass rates."
                    ),
                    "chips": ["Eval scorecard", "Show forge", "Model lab costs"],
                    "links": {"evals": "/developer?tab=evals"},
                },
            }
        ],
        "blocked_normal_reply": True,
        "summary": "Prompt drift radar ready." if radar else "No drift data yet.",
    }


def ab_router_action(db: Session, *, workspace_id: int) -> dict[str, Any]:
    rows = (
        db.query(AbModelRoute)
        .filter(AbModelRoute.workspace_id == workspace_id)
        .order_by(AbModelRoute.update_time.desc())
        .limit(12)
        .all()
    )
    from app.services.ab_routing import pick_ab_model, route_dict

    routes = [route_dict(r) for r in rows]
    picked = pick_ab_model(db, workspace_id, default_model="gpt-4o-mini")
    return {
        "events": [
            {
                "type": "aios_ab",
                "data": {
                    "status": "ok" if routes else "empty",
                    "routes": routes,
                    "picked": picked,
                    "message": (
                        f"{len(routes)} A/B route(s). Live pick: "
                        + (f"`{picked.get('model')}` ({picked.get('variant')})" if picked else "none enabled")
                        if routes
                        else "No A/B routes configured. Add one in Developer → Model lab."
                    ),
                    "chips": ["Model lab costs", "Show forge", "Eval scorecard"],
                    "links": {"model_lab": "/developer?tab=models"},
                },
            }
        ],
        "blocked_normal_reply": True,
        "summary": f"A/B routes: {len(routes)}.",
    }


def webhook_studio_action(
    db: Session,
    *,
    workspace_id: int,
    user_id: int,
    text: str,
) -> dict[str, Any]:
    from app.database import ConnectorWebhook
    from app.composer.connector_composer import provision_connector_webhook

    rows = (
        db.query(ConnectorWebhook)
        .filter(ConnectorWebhook.workspace_id == workspace_id)
        .order_by(ConnectorWebhook.id.desc())
        .limit(12)
        .all()
    )
    items = [
        {
            "id": r.id,
            "direction": r.direction,
            "url": (r.url or "")[:80],
            "status": r.status,
        }
        for r in rows
    ]
    provisioned = None
    m = re.search(r"https?://\S+", text or "")
    if m and re.search(r"\bprovision\b", text or "", re.I):
        url = m.group(0).rstrip(").,")
        direction = "outbound" if "out" in (text or "").lower() else "inbound"
        try:
            wh = provision_connector_webhook(db, workspace_id, direction, url)
            provisioned = {"id": wh.id, "url": wh.url, "direction": wh.direction}
            ca = _helpers()
            ca.audit_chat_action(
                db,
                action="webhook_provision",
                user_id=user_id,
                workspace_id=workspace_id,
                resource_type="webhook",
                resource_id=str(wh.id),
            )
            items = [
                {"id": wh.id, "direction": wh.direction, "url": (wh.url or "")[:80], "status": wh.status}
            ] + items
        except Exception as exc:  # noqa: BLE001
            logger.warning("webhook provision failed: %s", exc)
            return {
                "events": [
                    {
                        "type": "aios_webhook",
                        "data": {
                            "status": "error",
                            "message": f"Could not provision webhook: {exc}",
                            "webhooks": items,
                            "chips": ["Open webhook studio", "Show forge"],
                        },
                    }
                ],
                "blocked_normal_reply": True,
                "summary": "Webhook provision failed.",
            }
    return {
        "events": [
            {
                "type": "aios_webhook",
                "data": {
                    "status": "ok" if items else "empty",
                    "webhooks": items,
                    "provisioned": provisioned,
                    "message": (
                        f"{len(items)} webhook(s). "
                        + ("Provisioned new endpoint." if provisioned else "Say **provision webhook https://…** to add one.")
                    ),
                    "chips": ["Show forge", "Integrations health", "Workspace health"],
                },
            }
        ],
        "blocked_normal_reply": True,
        "summary": f"Webhooks: {len(items)}.",
    }


def project_packs_action(
    db: Session,
    *,
    workspace_id: int,
    user_id: int,
    text: str,
) -> dict[str, Any]:
    from app.services.projects import create_project, project_dict

    rows = (
        db.query(DevProject)
        .filter(DevProject.workspace_id == workspace_id)
        .order_by(DevProject.update_time.desc())
        .limit(12)
        .all()
    )
    created = None
    if re.search(r"\bcreate project( pack)?\b", text or "", re.I):
        name_m = re.search(r"create project(?: pack)?(?: named| called)?\s+[\"']?([^\"'\n]{2,80})", text or "", re.I)
        name = (name_m.group(1).strip() if name_m else "Chat project pack")[:120]
        try:
            row = create_project(
                db,
                user_id=user_id,
                workspace_id=workspace_id,
                name=name,
                description="Created from Peak Chat Forge",
            )
            db.commit()
            created = project_dict(row)
            rows = [row] + list(rows)
        except Exception as exc:  # noqa: BLE001
            logger.warning("create project failed: %s", exc)
    items = [project_dict(r) for r in rows[:12]]
    return {
        "events": [
            {
                "type": "aios_project",
                "data": {
                    "status": "ok" if items else "empty",
                    "projects": items,
                    "created": created,
                    "message": (
                        f"{len(items)} project pack(s)."
                        + (" Created new pack." if created else " Say **create project pack named Ops** to add one.")
                    ),
                    "chips": ["Create project pack named Ops", "List my workflows", "Show forge"],
                    "links": {"projects": "/developer?tab=projects"},
                },
            }
        ],
        "blocked_normal_reply": True,
        "summary": f"Projects: {len(items)}.",
    }


def publish_scan_action(db: Session, *, conversation_id: str | None) -> dict[str, Any]:
    from app.composer.governance import scan_marketplace_asset

    ca = _helpers()
    _, aios = ca._load_aios(db, conversation_id)
    graph = aios.get("executable_preview") or aios.get("graph") or {}
    if not isinstance(graph, dict) or not (graph.get("nodes") or graph.get("meta")):
        return {
            "events": [
                {
                    "type": "aios_publish_scan",
                    "data": {
                        "status": "empty",
                        "message": "No pending graph to scan. Compose a plan first.",
                        "chips": ["Show forge", "Show powerhouse"],
                        "vulnerabilities": [],
                    },
                }
            ],
            "blocked_normal_reply": True,
            "summary": "Nothing to scan for publish.",
        }
    vulns = scan_marketplace_asset(graph)
    return {
        "events": [
            {
                "type": "aios_publish_scan",
                "data": {
                    "status": "warn" if vulns else "ok",
                    "vulnerabilities": vulns,
                    "count": len(vulns),
                    "message": (
                        f"Publish scan found {len(vulns)} issue(s)."
                        if vulns
                        else "Publish scan clean — no hardcoded secrets detected in the pending graph."
                    ),
                    "chips": ["Diff my workflow", "Generate solution docs", "Show forge"],
                },
            }
        ],
        "blocked_normal_reply": True,
        "summary": f"Publish scan: {len(vulns)} finding(s).",
    }


def template_reuse_action(
    db: Session,
    *,
    workspace_id: int,
    conversation_id: str | None,
    text: str,
) -> dict[str, Any]:
    from app.composer.reuse import find_reusable_template, match_reusable_asset

    ca = _helpers()
    _, aios = ca._load_aios(db, conversation_id)
    goal = text or aios.get("goal") or aios.get("friendly_title") or ""
    # Strip command words for better match
    goal_clean = re.sub(
        r"\b(find reusable template|template reuse|reuse template)\b",
        " ",
        goal,
        flags=re.I,
    ).strip() or str(aios.get("goal") or "support bot")
    match = match_reusable_asset(db, workspace_id, goal_clean) or find_reusable_template(goal_clean)
    if not match:
        return {
            "events": [
                {
                    "type": "aios_reuse",
                    "data": {
                        "status": "empty",
                        "goal": goal_clean,
                        "message": "No reusable template matched. Compose from scratch or refine the goal.",
                        "chips": ["Show forge", "Show powerhouse", "What can you do?"],
                    },
                }
            ],
            "blocked_normal_reply": True,
            "summary": "No reusable template found.",
        }
    chip = f"Build {match.get('name') or match.get('id')}"
    return {
        "events": [
            {
                "type": "aios_reuse",
                "data": {
                    "status": "ok",
                    "match": {
                        "id": match.get("id"),
                        "name": match.get("name"),
                        "desc": match.get("desc"),
                        "type": match.get("type"),
                    },
                    "message": f"Reusable match: **{match.get('name') or match.get('id')}**. Tap compose chip to continue.",
                    "chips": [chip, "Diff my workflow", "Show forge"],
                },
            }
        ],
        "blocked_normal_reply": True,
        "summary": f"Reuse: {match.get('name') or match.get('id')}.",
    }


def model_lab_desk_action(db: Session, *, workspace_id: int) -> dict[str, Any]:
    from app.services.finetune_cost import estimate_finetune_cost

    datasets = (
        db.query(FineTuneDataset)
        .filter(FineTuneDataset.workspace_id == workspace_id)
        .order_by(FineTuneDataset.id.desc())
        .limit(8)
        .all()
    )
    jobs = (
        db.query(FineTuneJob)
        .filter(FineTuneJob.workspace_id == workspace_id)
        .order_by(FineTuneJob.id.desc())
        .limit(8)
        .all()
    )
    estimates = []
    for ds in datasets[:5]:
        try:
            est = estimate_finetune_cost(ds, getattr(ds, "base_model", None) or "gpt-4o-mini")
        except Exception:  # noqa: BLE001
            est = None
        estimates.append(
            {
                "dataset_id": ds.id,
                "name": getattr(ds, "name", None) or f"dataset-{ds.id}",
                "estimate": est if isinstance(est, dict) else {"raw": str(est) if est else None},
            }
        )
    return {
        "events": [
            {
                "type": "aios_model_lab",
                "data": {
                    "status": "ok" if datasets or jobs else "empty",
                    "datasets": estimates,
                    "jobs": [
                        {
                            "id": j.id,
                            "status": getattr(j, "status", None),
                            "base_model": getattr(j, "base_model", None),
                        }
                        for j in jobs
                    ],
                    "message": (
                        f"{len(datasets)} dataset(s), {len(jobs)} fine-tune job(s)."
                        if datasets or jobs
                        else "No model-lab datasets yet. Create one from Knowledge in Developer."
                    ),
                    "chips": ["Show A/B routes", "Show forge", "Eval scorecard"],
                    "links": {"model_lab": "/developer?tab=models"},
                },
            }
        ],
        "blocked_normal_reply": True,
        "summary": f"Model lab: {len(datasets)} dataset(s).",
    }


def _read_attachment_text(path: Path) -> str:
    try:
        from app.services.doc_parse import extract_document, is_supported_suffix
        from app.services.ocr import extract_image_text, is_image_path

        if is_image_path(path):
            return extract_image_text(path) or ""
        if is_supported_suffix(path.suffix):
            return extract_document(path) or ""
        if path.suffix.lower() in {".txt", ".md", ".csv", ".json"}:
            return path.read_text(encoding="utf-8", errors="ignore")[:20000]
    except Exception as exc:  # noqa: BLE001
        logger.warning("attachment extract failed: %s", exc)
    return ""


def ocr_to_workflow_action(
    db: Session,
    *,
    workspace_id: int,
    conversation_id: str | None,
) -> dict[str, Any]:
    if not conversation_id:
        return {
            "events": [
                {
                    "type": "aios_ocr",
                    "data": {"status": "error", "message": "Open a chat and attach files first.", "chips": ["Show forge"]},
                }
            ],
            "blocked_normal_reply": True,
            "summary": "No conversation.",
        }
    rows = (
        db.query(ConversationAttachment)
        .filter(
            ConversationAttachment.conversation_id == conversation_id,
            ConversationAttachment.workspace_id == workspace_id,
            ConversationAttachment.deleted_at.is_(None),
        )
        .all()
    )
    extracts: list[dict[str, Any]] = []
    blob_parts: list[str] = []
    for r in rows[:8]:
        key = r.storage_key or ""
        path = UPLOAD_DIR / key
        text = ""
        if path.exists():
            text = _read_attachment_text(path)[:6000]
        if text:
            extracts.append({"file": r.filename or key, "chars": len(text), "preview": text[:240]})
            blob_parts.append(text)
    actions: list[str] = []
    for line in "\n".join(blob_parts).splitlines():
        line = line.strip(" -\t*")
        if 12 <= len(line) <= 180 and re.search(
            r"\b(todo|action|automate|email|schedule|invoice|onboard|notify)\b", line, re.I
        ):
            actions.append(line)
        if len(actions) >= 6:
            break
    chips = [f"Build workflow: {a[:60]}" for a in actions[:3]] or ["Digest attachments to workflows", "Show forge"]
    return {
        "events": [
            {
                "type": "aios_ocr",
                "data": {
                    "status": "ok" if extracts else "empty",
                    "extracts": extracts,
                    "actions": actions,
                    "message": (
                        f"Extracted text from {len(extracts)} file(s); {len(actions)} action-like line(s)."
                        if extracts
                        else "No readable attachments. Upload an image/PDF/DOCX, then retry."
                    ),
                    "chips": chips + ["Digest attachments to workflows"],
                },
            }
        ],
        "blocked_normal_reply": True,
        "summary": f"OCR/doc extract: {len(extracts)} file(s).",
    }


async def issue_bridge_action(
    db: Session,
    *,
    workspace_id: int,
    text: str,
) -> dict[str, Any]:
    from app.services.github_issues import github_create_issue, github_verify

    verify = await github_verify(db, workspace_id)
    create = re.search(r"\b(create|open) github issue\b", text or "", re.I)
    created = None
    if create and verify.get("ok"):
        title_m = re.search(r"issue[:\s]+(.+)$", text or "", re.I)
        title = (title_m.group(1).strip() if title_m else "Chat Forge issue")[:120]
        try:
            created = await github_create_issue(
                db,
                workspace_id,
                title=title,
                body=f"Created from NovaFlow Peak Chat.\n\nRequest: {text}",
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("github create failed: %s", exc)
            created = {"error": str(exc)}
    return {
        "events": [
            {
                "type": "aios_issue",
                "data": {
                    "status": "ok" if verify.get("ok") else "empty",
                    "verify": verify,
                    "created": created,
                    "message": (
                        "GitHub connected."
                        + (
                            f" Created issue: {created.get('html_url') or created.get('number') or created}."
                            if created and not created.get("error")
                            else " Say **create github issue: title** to open one."
                            if verify.get("ok")
                            else ""
                        )
                        if verify.get("ok")
                        else "GitHub not configured. Add a GitHub integration in Credentials / Integrations."
                    ),
                    "chips": ["Create github issue: follow up from chat", "Show forge", "Integrations health"],
                },
            }
        ],
        "blocked_normal_reply": True,
        "summary": "GitHub issue bridge.",
    }


def csv_import_action(
    db: Session,
    *,
    workspace_id: int,
    conversation_id: str | None,
) -> dict[str, Any]:
    from app.services.csv_import import parse_csv_text, parse_eval_cases_csv

    if not conversation_id:
        return {
            "events": [
                {
                    "type": "aios_csv",
                    "data": {"status": "empty", "message": "Attach a CSV in this chat first.", "chips": ["Show forge"]},
                }
            ],
            "blocked_normal_reply": True,
            "summary": "No CSV conversation.",
        }
    rows = (
        db.query(ConversationAttachment)
        .filter(
            ConversationAttachment.conversation_id == conversation_id,
            ConversationAttachment.workspace_id == workspace_id,
            ConversationAttachment.deleted_at.is_(None),
        )
        .all()
    )
    csv_text = ""
    fname = ""
    for r in rows:
        key = r.storage_key or ""
        path = UPLOAD_DIR / key
        name = (r.filename or key or "").lower()
        if name.endswith(".csv") and path.exists():
            csv_text = path.read_text(encoding="utf-8", errors="ignore")[:200000]
            fname = r.filename or key
            break
    if not csv_text:
        return {
            "events": [
                {
                    "type": "aios_csv",
                    "data": {
                        "status": "empty",
                        "message": "No CSV attachment found. Upload a `.csv` then say **Import CSV from chat**.",
                        "chips": ["Show forge", "Eval scorecard"],
                    },
                }
            ],
            "blocked_normal_reply": True,
            "summary": "No CSV attached.",
        }
    parsed = parse_csv_text(csv_text)
    cases = parse_eval_cases_csv(csv_text)
    return {
        "events": [
            {
                "type": "aios_csv",
                "data": {
                    "status": "ok",
                    "filename": fname,
                    "row_count": len(parsed),
                    "eval_case_count": len(cases),
                    "preview_rows": parsed[:5],
                    "preview_cases": cases[:5],
                    "message": f"Parsed `{fname}`: {len(parsed)} row(s), {len(cases)} eval-shaped case(s).",
                    "chips": ["Eval scorecard", "Show forge", "Run simulation lab"],
                },
            }
        ],
        "blocked_normal_reply": True,
        "summary": f"CSV import preview: {len(parsed)} rows.",
    }


def solution_docs_action(db: Session, *, conversation_id: str | None, workspace_id: int) -> dict[str, Any]:
    from app.composer.doc_generator import generate_solution_documentation

    ca = _helpers()
    _, aios = ca._load_aios(db, conversation_id)
    sid = aios.get("solution_id") or aios.get("friendly_title") or "pending"
    graph = aios.get("executable_preview") or aios.get("graph") or {}
    if not isinstance(graph, dict) or not graph.get("nodes"):
        # Fall back to last workflow
        wf = (
            db.query(Workflow)
            .filter(Workflow.workspace_id == workspace_id, Workflow.status == 1)
            .order_by(Workflow.update_time.desc())
            .first()
        )
        if wf and wf.graph_json:
            try:
                graph = json.loads(wf.graph_json)
            except json.JSONDecodeError:
                graph = {}
            sid = wf.name or str(wf.id)
    if not isinstance(graph, dict) or not graph.get("nodes"):
        return {
            "events": [
                {
                    "type": "aios_docs",
                    "data": {
                        "status": "empty",
                        "message": "No solution/workflow graph to document. Compose or deploy first.",
                        "chips": ["Show forge", "List my workflows"],
                    },
                }
            ],
            "blocked_normal_reply": True,
            "summary": "No graph for docs.",
        }
    # Normalize list nodes → dict for doc generator
    payload = graph
    nodes = graph.get("nodes")
    if isinstance(nodes, list):
        payload = {
            "nodes": {str(n.get("id") or i): n for i, n in enumerate(nodes) if isinstance(n, dict)},
            "edges": graph.get("edges") or [],
            "required_capabilities": (graph.get("meta") or {}).get("node_types") or [],
        }
    md = generate_solution_documentation(str(sid), payload)
    return {
        "events": [
            {
                "type": "aios_docs",
                "data": {
                    "status": "ok",
                    "solution_id": sid,
                    "markdown": md[:8000],
                    "message": f"Documentation ready for **{sid}**.",
                    "chips": ["Scan for publish", "Diff my workflow", "Show forge"],
                },
            }
        ],
        "blocked_normal_reply": True,
        "summary": f"Docs generated for {sid}.",
    }


def solution_assert_action(db: Session, *, conversation_id: str | None) -> dict[str, Any]:
    from app.composer.testing_engine import run_solution_test_assertions
    from app.sandbox.enterprise_suite import run_enterprise_suite

    ca = _helpers()
    _, aios = ca._load_aios(db, conversation_id)
    sid = str(aios.get("solution_id") or "pending")
    preview = aios.get("executable_preview") or {}
    assertions = run_solution_test_assertions(sid, {"goal": aios.get("goal") or "test"})
    suite = None
    if isinstance(preview, dict) and preview.get("nodes"):
        suite = run_enterprise_suite(preview, field="generic")
    status = "ok" if assertions.get("test_run_status") == "passed" else "failed"
    if suite and suite.get("status") == "failed":
        status = "failed"
    return {
        "events": [
            {
                "type": "aios_assert",
                "data": {
                    "status": status,
                    "assertions": assertions,
                    "suite": suite,
                    "message": (
                        "Assertions passed."
                        if status == "ok"
                        else "Assertions or enterprise suite reported failures — see card."
                    ),
                    "chips": ["Run simulation lab", "Heal", "Show forge"],
                },
            }
        ],
        "blocked_normal_reply": True,
        "summary": f"Solution assertions: {status}.",
    }


async def dispatch_forge_action(
    db: Session,
    *,
    workspace_id: int,
    user_id: int,
    conversation_id: str | None,
    user_message: str,
    intent: str | None = None,
) -> dict[str, Any] | None:
    intent = intent or classify_forge_intent(user_message)
    if not intent or intent not in FORGE_INTENTS:
        return None
    if intent == "forge_catalog":
        return forge_catalog_action()
    if intent == "prompt_drift":
        return prompt_drift_action(db, workspace_id=workspace_id)
    if intent == "ab_router":
        return ab_router_action(db, workspace_id=workspace_id)
    if intent == "webhook_studio":
        return webhook_studio_action(db, workspace_id=workspace_id, user_id=user_id, text=user_message)
    if intent == "project_packs":
        return project_packs_action(db, workspace_id=workspace_id, user_id=user_id, text=user_message)
    if intent == "publish_scan":
        return publish_scan_action(db, conversation_id=conversation_id)
    if intent == "template_reuse":
        return template_reuse_action(
            db, workspace_id=workspace_id, conversation_id=conversation_id, text=user_message
        )
    if intent == "model_lab_desk":
        return model_lab_desk_action(db, workspace_id=workspace_id)
    if intent == "ocr_to_workflow":
        return ocr_to_workflow_action(db, workspace_id=workspace_id, conversation_id=conversation_id)
    if intent == "issue_bridge":
        return await issue_bridge_action(db, workspace_id=workspace_id, text=user_message)
    if intent == "csv_import_chat":
        return csv_import_action(db, workspace_id=workspace_id, conversation_id=conversation_id)
    if intent == "solution_docs":
        return solution_docs_action(db, conversation_id=conversation_id, workspace_id=workspace_id)
    if intent == "solution_assert":
        return solution_assert_action(db, conversation_id=conversation_id)
    return None
