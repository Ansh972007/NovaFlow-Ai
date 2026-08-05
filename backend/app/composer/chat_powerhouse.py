"""Chat Powerhouse — 12 mega Peak Chat capabilities wired to platform backends."""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.config import UPLOAD_DIR
from app.database import (
    Conversation,
    ConversationAttachment,
    EvalRun,
    EvalSuite,
    KnowledgeBase,
    Workflow,
    WorkflowRun,
    WorkflowSchedule,
)
from app.sandbox.enterprise_suite import run_simulation_matrix
from app.services.receipt import estimate_cost_usd
from app.services.workflow import list_workflow_versions, restore_workflow_version
from app.services.workflow_diff import diff_workflow_graphs, format_diff_markdown

logger = logging.getLogger(__name__)

POWER_INTENTS = frozenset(
    {
        "powerhouse_catalog",
        "workflow_diff",
        "version_time_machine",
        "restore_version",
        "eval_command",
        "cost_receipt",
        "run_debugger",
        "knowledge_graph",
        "collab_war_room",
        "incident_kill_switch",
        "simulate_lab",
        "sla_brief",
        "change_request",
        "apply_change_request",
        "action_digest",
    }
)

POWERHOUSE_CATALOG = [
    {"id": "workflow_diff", "title": "Workflow Diff Studio", "chip": "Diff my workflow", "card": "aios_diff"},
    {"id": "version_time_machine", "title": "Version Time Machine", "chip": "Show workflow versions", "card": "aios_versions"},
    {"id": "eval_command", "title": "Eval Command Center", "chip": "Eval scorecard", "card": "aios_eval"},
    {"id": "cost_receipt", "title": "Cost Receipt & Budget", "chip": "Show cost receipt", "card": "aios_receipt"},
    {"id": "run_debugger", "title": "Live Run Debugger", "chip": "Debug last run", "card": "aios_debug"},
    {"id": "knowledge_graph", "title": "Knowledge Graph Explorer", "chip": "Explore knowledge graph", "card": "aios_kg"},
    {"id": "collab_war_room", "title": "Collaboration War Room", "chip": "Open collab war room", "card": "aios_collab"},
    {"id": "incident_kill_switch", "title": "Incident Kill Switch", "chip": "Confirm kill switch", "card": "aios_incident"},
    {"id": "simulate_lab", "title": "What-If Simulation Lab", "chip": "Run simulation lab", "card": "aios_simulate"},
    {"id": "sla_brief", "title": "SLA Reliability Brief", "chip": "SLA reliability brief", "card": "aios_sla"},
    {"id": "change_request", "title": "Change Request Review", "chip": "Propose change: add Slack notify", "card": "aios_change_request"},
    {"id": "action_digest", "title": "Action Digest → Workflows", "chip": "Digest attachments to workflows", "card": "aios_digest"},
]

_POWERHOUSE_REGISTERED = False


def register_powerhouse_ops() -> None:
    """Register Powerhouse intents into the durable chat ops registry."""
    global _POWERHOUSE_REGISTERED
    if _POWERHOUSE_REGISTERED:
        return
    from app.composer.chat_ops_registry import OpSpec, register_op

    specs = [
        OpSpec(
            "powerhouse_catalog",
            (r"\b(show )?powerhouse\b", r"\bbig chat tools\b", r"\bmega (chat )?tools\b", r"\bchat powerhouse\b"),
            "aios_powerhouse",
            "powerhouse",
            title="Chat Powerhouse",
            chip="Show powerhouse",
            priority=20,
        ),
        OpSpec(
            "apply_change_request",
            (r"\bapply (the )?change( request)?\b", r"\bapprove (the )?change( request)?\b", r"\bconfirm apply change\b"),
            "aios_change_request",
            "powerhouse",
            title="Apply Change Request",
            chip="Apply change request",
            priority=15,
        ),
        OpSpec(
            "restore_version",
            (r"\bconfirm restore (workflow )?version\b", r"\brestore (workflow )?version\b", r"\brestore version\s*#?\d+"),
            "aios_versions",
            "powerhouse",
            title="Restore Version",
            chip="Restore version #1",
            priority=15,
        ),
        OpSpec(
            "incident_kill_switch",
            (r"\b(confirm )?(kill switch|incident (lockdown|kill)|emergency stop all)\b",),
            "aios_incident",
            "powerhouse",
            title="Incident Kill Switch",
            chip="Confirm kill switch",
            priority=15,
        ),
        OpSpec(
            "workflow_diff",
            (r"\bdiff (my |the )?workflow\b", r"\bworkflow diff\b", r"\bcompare (workflow )?versions?\b", r"\bdiff studio\b"),
            "aios_diff",
            "powerhouse",
            title="Workflow Diff Studio",
            chip="Diff my workflow",
            priority=40,
        ),
        OpSpec(
            "version_time_machine",
            (r"\b(show |list )?workflow versions?\b", r"\bversion time machine\b", r"\btime machine\b"),
            "aios_versions",
            "powerhouse",
            title="Version Time Machine",
            chip="Show workflow versions",
            priority=40,
        ),
        OpSpec(
            "eval_command",
            (r"\beval (scorecard|suite|command)\b", r"\brun (quick )?eval\b", r"\beval center\b"),
            "aios_eval",
            "powerhouse",
            title="Eval Command Center",
            chip="Eval scorecard",
            priority=40,
        ),
        OpSpec(
            "cost_receipt",
            (r"\b(show |cost )?receipt\b", r"\bbudget guard\b", r"\bchat cost\b", r"\bsession cost\b"),
            "aios_receipt",
            "powerhouse",
            title="Cost Receipt & Budget",
            chip="Show cost receipt",
            priority=40,
        ),
        OpSpec(
            "run_debugger",
            (r"\bdebug (last |the )?run\b", r"\brun debugger\b", r"\blive debugger\b", r"\breplay (last )?run\b"),
            "aios_debug",
            "powerhouse",
            title="Live Run Debugger",
            chip="Debug last run",
            priority=40,
        ),
        OpSpec(
            "knowledge_graph",
            (r"\b(explore )?knowledge graph\b", r"\bkg explorer\b", r"\bsearch knowledge graph\b"),
            "aios_kg",
            "powerhouse",
            title="Knowledge Graph Explorer",
            chip="Explore knowledge graph",
            priority=40,
        ),
        OpSpec(
            "collab_war_room",
            (r"\b(collab|collaboration) war room\b", r"\bhand off (this )?plan\b", r"\bwar room\b"),
            "aios_collab",
            "powerhouse",
            title="Collaboration War Room",
            chip="Open collab war room",
            priority=40,
        ),
        OpSpec(
            "simulate_lab",
            (r"\b(run )?simulation lab\b", r"\bwhat[- ]?if simulation\b", r"\bsimulate (fixtures|matrix)\b"),
            "aios_simulate",
            "powerhouse",
            title="What-If Simulation Lab",
            chip="Run simulation lab",
            priority=40,
        ),
        OpSpec(
            "sla_brief",
            (r"\bsla (reliability )?brief\b", r"\breliability brief\b", r"\bsuccess rate (report|brief)\b"),
            "aios_sla",
            "powerhouse",
            title="SLA Reliability Brief",
            chip="SLA reliability brief",
            priority=40,
        ),
        OpSpec(
            "change_request",
            (r"\bpropose change\b", r"\bchange request\b", r"\badd (slack|telegram|email) notify\b"),
            "aios_change_request",
            "powerhouse",
            title="Change Request Review",
            chip="Propose change: add Slack notify",
            priority=45,
        ),
        OpSpec(
            "action_digest",
            (r"\bdigest (attachments?|transcript)\b", r"\baction digest\b", r"\bactions? from (attachments?|files?)\b"),
            "aios_digest",
            "powerhouse",
            title="Action Digest → Workflows",
            chip="Digest attachments to workflows",
            priority=40,
        ),
    ]
    for spec in specs:
        register_op(spec, None)
    _POWERHOUSE_REGISTERED = True


def classify_power_intent(text: str) -> str | None:
    """Classify Powerhouse intents (legacy ordered matcher; registry mirrors these phrases)."""
    register_powerhouse_ops()
    t = (text or "").lower().strip()
    if not t:
        return None
    if re.search(r"\b(show )?powerhouse\b|\bbig chat tools\b|\bmega (chat )?tools\b|\bchat powerhouse\b", t):
        return "powerhouse_catalog"
    if re.search(r"\bapply (the )?change( request)?\b|\bapprove (the )?change( request)?\b|\bconfirm apply change\b", t):
        return "apply_change_request"
    if re.search(r"\b(confirm )?restore (workflow )?version\b|\brestore version\s*#?\d+", t):
        return "restore_version"
    if re.search(r"\b(confirm )?(kill switch|incident (lockdown|kill)|emergency stop all)\b", t):
        return "incident_kill_switch"
    if re.search(r"\bdiff (my |the )?workflow\b|\bworkflow diff\b|\bcompare (workflow )?versions?\b|\bdiff studio\b", t):
        return "workflow_diff"
    if re.search(r"\b(show |list )?workflow versions?\b|\bversion time machine\b|\btime machine\b", t):
        return "version_time_machine"
    if re.search(r"\beval (scorecard|suite|command)\b|\brun (quick )?eval\b|\beval center\b", t):
        return "eval_command"
    if re.search(r"\b(show |cost )?receipt\b|\bbudget guard\b|\bchat cost\b|\bsession cost\b", t):
        return "cost_receipt"
    if re.search(r"\bdebug (last |the )?run\b|\brun debugger\b|\blive debugger\b|\breplay (last )?run\b", t):
        return "run_debugger"
    if re.search(r"\b(explore )?knowledge graph\b|\bkg explorer\b|\bsearch knowledge graph\b", t):
        return "knowledge_graph"
    if re.search(r"\b(collab|collaboration) war room\b|\bhand off (this )?plan\b|\bwar room\b", t):
        return "collab_war_room"
    if re.search(r"\b(run )?simulation lab\b|\bwhat[- ]?if simulation\b|\bsimulate (fixtures|matrix)\b", t):
        return "simulate_lab"
    if re.search(r"\bsla (reliability )?brief\b|\breliability brief\b|\bsuccess rate (report|brief)\b", t):
        return "sla_brief"
    if re.search(r"\bpropose change\b|\bchange request\b|\badd (slack|telegram|email) notify\b", t):
        return "change_request"
    if re.search(r"\bdigest (attachments?|transcript)\b|\baction digest\b|\bactions? from (attachments?|files?)\b", t):
        return "action_digest"
    return None


def _helpers():
    from app.composer import chat_actions as ca

    return ca


def _normalize_graph(graph: Any) -> dict[str, Any]:
    if not isinstance(graph, dict):
        return {"nodes": [], "edges": []}
    nodes = graph.get("nodes")
    edges = graph.get("edges") or []
    if isinstance(nodes, dict):
        node_list = []
        for nid, data in nodes.items():
            if isinstance(data, dict):
                row = dict(data)
                row.setdefault("id", str(nid))
                node_list.append(row)
            else:
                node_list.append({"id": str(nid), "type": "unknown"})
        return {"nodes": node_list, "edges": edges if isinstance(edges, list) else [], "meta": graph.get("meta") or {}}
    if isinstance(nodes, list):
        return {"nodes": nodes, "edges": edges if isinstance(edges, list) else [], "meta": graph.get("meta") or {}}
    return {"nodes": [], "edges": edges if isinstance(edges, list) else [], "meta": graph.get("meta") or {}}


def _find_workflow(db: Session, workspace_id: int, aios: dict[str, Any], text: str = "") -> Workflow | None:
    ca = _helpers()
    return ca._find_workflow(db, workspace_id, text or "", aios)


def _workflow_graph(wf: Workflow | None) -> dict[str, Any]:
    if not wf:
        return {"nodes": [], "edges": []}
    try:
        return _normalize_graph(json.loads(wf.graph_json or "{}"))
    except json.JSONDecodeError:
        return {"nodes": [], "edges": []}


def powerhouse_catalog_action() -> dict[str, Any]:
    return {
        "events": [
            {
                "type": "aios_powerhouse",
                "data": {
                    "title": "Chat Powerhouse — 12 mega tools",
                    "tools": POWERHOUSE_CATALOG,
                    "chips": [t["chip"] for t in POWERHOUSE_CATALOG],
                    "message": "Senior-dev tools inside Peak Chat. Tap a chip to run one.",
                },
            }
        ],
        "blocked_normal_reply": True,
        "summary": "Chat Powerhouse: 12 mega tools ready.",
    }


def workflow_diff_action(
    db: Session,
    *,
    workspace_id: int,
    conversation_id: str | None,
    text: str,
) -> dict[str, Any]:
    ca = _helpers()
    conv, aios = ca._load_aios(db, conversation_id)
    wf = _find_workflow(db, workspace_id, aios, text)
    pending = _normalize_graph(aios.get("executable_preview") or aios.get("graph") or {})
    deployed = _workflow_graph(wf)
    if not deployed.get("nodes") and not pending.get("nodes"):
        return {
            "events": [
                {
                    "type": "aios_diff",
                    "data": {
                        "status": "empty",
                        "message": (
                            "No deployed vs pending pair to compare. "
                            "Compose a plan (or deploy a workflow), then try again."
                        ),
                        "chips": [
                            "Build a telegram support bot that answers from knowledge",
                            "List my workflows",
                            "Show powerhouse",
                        ],
                    },
                }
            ],
            "blocked_normal_reply": True,
            "summary": "No graphs to diff.",
        }
    # Prefer pending vs deployed; else last two versions
    left, right, left_label, right_label = deployed, pending, "deployed", "pending compose"
    if not pending.get("nodes"):
        versions = list_workflow_versions(db, wf.id) if wf else []
        if wf and len(versions) >= 2:
            from app.services.workflow import get_workflow_version

            older = get_workflow_version(db, wf.id, versions[1]["id"])
            newer = get_workflow_version(db, wf.id, versions[0]["id"])
            left = _normalize_graph((older or {}).get("graph") or {})
            right = _normalize_graph((newer or {}).get("graph") or {})
            left_label = f"v{versions[1].get('version_no')}"
            right_label = f"v{versions[0].get('version_no')}"
        else:
            right = deployed
            right_label = "current"
    diff = diff_workflow_graphs(left, right)
    md = format_diff_markdown(
        diff,
        workflow_name=(wf.name if wf else "pending"),
        from_label=left_label,
        to_label=right_label,
    )
    return {
        "events": [
            {
                "type": "aios_diff",
                "data": {
                    "status": "ok",
                    "workflow_id": wf.id if wf else None,
                    "workflow_name": wf.name if wf else "pending",
                    "from_label": left_label,
                    "to_label": right_label,
                    "summary": diff.get("summary") or {},
                    "markdown": md[:6000],
                    "nodes_added": (diff.get("nodes_added") or [])[:12],
                    "nodes_removed": (diff.get("nodes_removed") or [])[:12],
                    "nodes_changed": (diff.get("nodes_changed") or [])[:12],
                    "chips": ["Show workflow versions", "Run simulation lab", "Propose change: add Slack notify"],
                },
            }
        ],
        "blocked_normal_reply": True,
        "summary": f"Diff {left_label} → {right_label}: {diff.get('summary')}",
    }


def versions_action(
    db: Session,
    *,
    workspace_id: int,
    conversation_id: str | None,
    text: str,
    user_id: int,
    restore: bool = False,
) -> dict[str, Any]:
    ca = _helpers()
    _, aios = ca._load_aios(db, conversation_id)
    wf = _find_workflow(db, workspace_id, aios, text)
    if not wf:
        return {
            "events": [
                {
                    "type": "aios_versions",
                    "data": {
                        "status": "empty",
                        "message": "No workflow found. Deploy one from chat first.",
                        "chips": ["List my workflows", "Show powerhouse"],
                    },
                }
            ],
            "blocked_normal_reply": True,
            "summary": "No workflow for versions.",
        }
    if restore:
        m = re.search(r"version\s*#?(\d+)", text or "", re.I)
        version_id = int(m.group(1)) if m else None
        # Also allow version_no lookup
        versions = list_workflow_versions(db, wf.id)
        target = None
        if version_id:
            target = next((v for v in versions if v["id"] == version_id or v["version_no"] == version_id), None)
        if not target and versions:
            target = versions[0]
        if not target:
            return {
                "events": [
                    {
                        "type": "aios_versions",
                        "data": {
                            "status": "error",
                            "message": "No version to restore.",
                            "versions": versions,
                            "chips": ["Show workflow versions", "List my workflows"],
                        },
                    }
                ],
                "blocked_normal_reply": True,
                "summary": "Restore failed.",
            }
        confirmed = bool(re.search(r"\bconfirm restore\b", text or "", re.I))
        preview_snip = f"version #{target.get('version_no')}"
        try:
            from app.services.workflow import get_workflow_version

            snap = get_workflow_version(db, wf.id, target["id"]) or {}
            g = snap.get("graph") or {}
            nodes = g.get("nodes") if isinstance(g, dict) else []
            ncount = len(nodes) if isinstance(nodes, (list, dict)) else 0
            preview_snip = f"{ncount} node(s) in snapshot #{target.get('version_no')}"
        except Exception:  # noqa: BLE001
            pass
        if not confirmed:
            chip = f"Confirm restore version #{target.get('version_no')}"
            return {
                "events": [
                    {
                        "type": "aios_versions",
                        "data": {
                            "status": "confirm_required",
                            "workflow_id": wf.id,
                            "workflow_name": wf.name,
                            "versions": versions,
                            "pending_restore": target,
                            "preview": preview_snip,
                            "message": (
                                f"Restore `{wf.name}` to **version #{target.get('version_no')}** "
                                f"({preview_snip})? Say **{chip}** to proceed."
                            ),
                            "chips": [chip, "Show workflow versions", "Diff my workflow"],
                        },
                    }
                ],
                "blocked_normal_reply": True,
                "summary": "Confirm restore to proceed.",
            }
        restored = restore_workflow_version(db, wf, target["id"], user_id)
        db.commit()
        ca.audit_chat_action(
            db,
            action="restore_version",
            user_id=user_id,
            workspace_id=workspace_id,
            resource_type="workflow",
            resource_id=str(wf.id),
            detail={"version_id": target["id"]},
        )
        return {
            "events": [
                {
                    "type": "aios_versions",
                    "data": {
                        "status": "restored",
                        "workflow_id": wf.id,
                        "workflow_name": wf.name,
                        "restored": restored or target,
                        "message": f"Restored `{wf.name}` to version #{target.get('version_no')}.",
                        "versions": list_workflow_versions(db, wf.id),
                        "chips": ["Diff my workflow", "Run simulation lab"],
                    },
                }
            ],
            "blocked_normal_reply": True,
            "summary": f"Restored version #{target.get('version_no')}.",
        }
    versions = list_workflow_versions(db, wf.id)
    return {
        "events": [
            {
                "type": "aios_versions",
                "data": {
                    "status": "ok" if versions else "empty",
                    "workflow_id": wf.id,
                    "workflow_name": wf.name,
                    "versions": versions,
                    "count": len(versions),
                    "message": (
                        f"{len(versions)} snapshot(s) for `{wf.name}`. "
                        "Say **restore version #N**, then **confirm restore version #N**."
                        if versions
                        else f"No snapshots yet for `{wf.name}`. Deploy edits to create versions."
                    ),
                    "chips": (
                        [f"Restore version #{versions[0]['version_no']}", "Diff my workflow"]
                        if versions
                        else ["List my workflows", "Show powerhouse"]
                    ),
                },
            }
        ],
        "blocked_normal_reply": True,
        "summary": f"{len(versions)} version(s) for {wf.name}.",
    }


def eval_command_action(
    db: Session,
    *,
    workspace_id: int,
    conversation_id: str | None,
) -> dict[str, Any]:
    ca = _helpers()
    _, aios = ca._load_aios(db, conversation_id)
    suites = (
        db.query(EvalSuite)
        .filter(EvalSuite.workspace_id == workspace_id)
        .order_by(EvalSuite.update_time.desc())
        .limit(8)
        .all()
    )
    suite_items = []
    last_run = None
    for s in suites:
        case_count = len(s.cases or [])
        suite_items.append({"id": s.id, "name": s.name, "case_count": case_count, "assistant_id": s.assistant_id})
        run = (
            db.query(EvalRun)
            .filter(EvalRun.suite_id == s.id)
            .order_by(EvalRun.create_time.desc())
            .first()
        )
        if run and (last_run is None or (run.create_time and last_run.create_time and run.create_time > last_run.create_time)):
            last_run = run
    # Quick structural eval via simulation matrix on pending graph
    preview = aios.get("executable_preview") or {}
    quick = None
    if isinstance(preview, dict) and (preview.get("nodes") or (preview.get("meta") or {}).get("node_types")):
        quick = run_simulation_matrix(
            preview,
            fields=["finance", "hr", "support", "generic"],
            missing_credentials=aios.get("missing_credentials") or [],
        )
    scorecard = None
    if last_run:
        total = last_run.total_count or 0
        scorecard = {
            "run_id": last_run.id,
            "suite_id": last_run.suite_id,
            "pass_count": last_run.pass_count,
            "fail_count": last_run.fail_count,
            "total_count": total,
            "pass_rate": round((last_run.pass_count / total) * 100, 1) if total else 0,
            "avg_latency_ms": last_run.avg_latency_ms,
        }
    return {
        "events": [
            {
                "type": "aios_eval",
                "data": {
                    "status": "ok",
                    "suites": suite_items,
                    "suite_count": len(suite_items),
                    "last_run": scorecard,
                    "quick_matrix": quick,
                    "message": (
                        f"{len(suite_items)} eval suite(s). "
                        + (
                            f"Last run pass rate {scorecard['pass_rate']}%."
                            if scorecard
                            else "No eval runs yet — quick matrix shown if a plan is pending."
                        )
                    ),
                    "chips": ["Run simulation lab", "Show powerhouse", "SLA reliability brief"],
                    "links": {"evals": "/developer?tab=evals"},
                },
            }
        ],
        "blocked_normal_reply": True,
        "summary": f"Eval center: {len(suite_items)} suite(s).",
    }


def cost_receipt_action(
    db: Session,
    *,
    conversation_id: str | None,
    workspace_id: int,
) -> dict[str, Any]:
    ca = _helpers()
    _, aios = ca._load_aios(db, conversation_id)
    session_cost = float(aios.get("cost_usd") or 0)
    turns = int(aios.get("cost_turns") or 0)
    budget = float(aios.get("budget_usd") or 25.0)
    over = session_cost > budget
    return {
        "events": [
            {
                "type": "aios_receipt",
                "data": {
                    "status": "warn" if over else "ok",
                    "session_cost_usd": round(session_cost, 6),
                    "budget_usd": budget,
                    "turns": turns,
                    "over_budget": over,
                    "last_receipt": aios.get("last_receipt") or {},
                    "message": (
                        f"Session estimate **${session_cost:.4f}** across {turns} billed turn(s). "
                        f"Budget guard: ${budget:.2f}."
                        + (" **Over budget.**" if over else "")
                    ),
                    "chips": ["Show powerhouse", "FinOps", "Workspace health"],
                },
            }
        ],
        "blocked_normal_reply": True,
        "summary": f"Session cost ~${session_cost:.4f} ({turns} turns).",
    }


def accumulate_receipt(
    db: Session,
    *,
    conversation_id: str | None,
    usage: dict[str, Any] | None,
    model: str = "",
) -> None:
    """Roll estimated cost into conversation aios meta."""
    if not conversation_id or not usage:
        return
    ca = _helpers()
    conv, aios = ca._load_aios(db, conversation_id)
    if not conv:
        return
    cost = estimate_cost_usd(
        model or str(usage.get("model") or ""),
        usage.get("prompt_tokens"),
        usage.get("completion_tokens"),
    )
    if cost is None:
        # char-based fallback when tokens missing
        total = int(usage.get("total_tokens") or 0)
        if total <= 0:
            return
        cost = estimate_cost_usd(model or "gpt-4o-mini", total // 2, total - total // 2) or 0.0
    aios["cost_usd"] = round(float(aios.get("cost_usd") or 0) + float(cost or 0), 6)
    aios["cost_turns"] = int(aios.get("cost_turns") or 0) + 1
    aios["last_receipt"] = {
        "est_cost_usd": cost,
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "total_tokens": usage.get("total_tokens"),
        "model": model or usage.get("model"),
        "at": datetime.utcnow().isoformat(),
    }
    ca._save_aios(db, conv, aios)


def debug_action(
    db: Session,
    *,
    workspace_id: int,
    conversation_id: str | None,
    text: str,
) -> dict[str, Any]:
    ca = _helpers()
    _, aios = ca._load_aios(db, conversation_id)
    wf = _find_workflow(db, workspace_id, aios, text)
    run = None
    if aios.get("active_run_id"):
        run = db.get(WorkflowRun, aios["active_run_id"])
    if not run and wf:
        run = (
            db.query(WorkflowRun)
            .filter(WorkflowRun.workflow_id == wf.id)
            .order_by(WorkflowRun.id.desc())
            .first()
        )
    if not run:
        run = (
            db.query(WorkflowRun)
            .join(Workflow, Workflow.id == WorkflowRun.workflow_id)
            .filter(Workflow.workspace_id == workspace_id)
            .order_by(WorkflowRun.id.desc())
            .first()
        )
    if not run:
        return {
            "events": [
                {
                    "type": "aios_debug",
                    "data": {
                        "status": "empty",
                        "message": "No workflow runs yet. Run a workflow, then debug.",
                        "chips": ["Run my last workflow", "List my workflows"],
                    },
                }
            ],
            "blocked_normal_reply": True,
            "summary": "No runs to debug.",
        }
    from app.workflow_intelligence.debugger import build_debug_session, replay_steps

    graph = None
    if wf:
        graph = _workflow_graph(wf)
    session = build_debug_session(db, run, graph)
    try:
        steps = json.loads(run.steps_json or "[]")
    except json.JSONDecodeError:
        steps = []
    replay = replay_steps(steps if isinstance(steps, list) else [])
    failed = next((t for t in session.timeline if t.status in ("error", "failed")), None)
    data = session.to_dict()
    data.update(
        {
            "status": "ok",
            "failed_node": failed.node_id if failed else None,
            "failed_type": failed.node_type if failed else None,
            "replay_steps": len(replay),
            "run_status": run.status,
            "input_preview": (run.input_text or "")[:400],
            "output_preview": (run.output_text or "")[:400],
            "message": (
                f"Run `{run.id}` — {len(session.timeline)} step(s)."
                + (f" Failed at `{failed.node_id}` ({failed.node_type})." if failed else " No hard failure in timeline.")
            ),
            "chips": [
                "Run my last workflow",
                "Heal",
                "Run simulation lab",
                "SLA reliability brief",
            ]
            + ([f"Replay from {failed.node_id}"] if failed and failed.node_id else []),
        }
    )
    return {
        "events": [{"type": "aios_debug", "data": data}],
        "blocked_normal_reply": True,
        "summary": f"Debug run {run.id}.",
    }


def knowledge_graph_action(
    db: Session,
    *,
    workspace_id: int,
    conversation_id: str | None,
    text: str,
) -> dict[str, Any]:
    ca = _helpers()
    _, aios = ca._load_aios(db, conversation_id)
    kid = aios.get("knowledge_id")
    q = re.sub(
        r"\b(explore|knowledge|graph|kg|search|explorer)\b",
        " ",
        text or "",
        flags=re.I,
    ).strip() or "policy"
    collections = (
        db.query(KnowledgeBase)
        .filter(KnowledgeBase.workspace_id == workspace_id)
        .order_by(KnowledgeBase.id.desc())
        .limit(8)
        .all()
    )
    chunks: list[dict[str, Any]] = []
    try:
        from app.knowledge_os.search import enterprise_search

        result = enterprise_search(
            db,
            workspace_id=workspace_id,
            query=q,
            collection_id=int(kid) if kid else None,
            limit=8,
        )
        chunks = result.get("chunks") or []
    except Exception as exc:  # noqa: BLE001
        logger.warning("kg search failed: %s", exc)
    items = [
        {
            "preview": (c.get("text") or c.get("preview") or "")[:220],
            "file_name": c.get("file_name") or c.get("source") or "doc",
            "score": c.get("score"),
        }
        for c in chunks[:8]
    ]
    return {
        "events": [
            {
                "type": "aios_kg",
                "data": {
                    "status": "ok" if items or collections else "empty",
                    "query": q,
                    "knowledge_id": kid,
                    "collections": [{"id": c.id, "name": c.name} for c in collections],
                    "hits": items,
                    "hit_count": len(items),
                    "message": (
                        f"Knowledge explorer for “{q}”: {len(items)} hit(s), {len(collections)} collection(s)."
                        if collections or items
                        else "No knowledge collections yet. Index attachments or open Knowledge."
                    ),
                    "chips": [
                        "Index attachments",
                        "Build a weekly email digest from my documents",
                        "Show powerhouse",
                    ],
                    "links": {"knowledge": "/knowledge"},
                },
            }
        ],
        "blocked_normal_reply": True,
        "summary": f"KG search “{q}”: {len(items)} hit(s).",
    }


def collab_war_room_action(
    db: Session,
    *,
    workspace_id: int,
    user_id: int,
    conversation_id: str | None,
    text: str,
) -> dict[str, Any]:
    ca = _helpers()
    conv, aios = ca._load_aios(db, conversation_id)
    if not conv:
        return {
            "events": [
                {
                    "type": "aios_collab",
                    "data": {"status": "error", "message": "Open a conversation first."},
                }
            ],
            "blocked_normal_reply": True,
            "summary": "No conversation.",
        }
    from app.conversation.collaboration import create_share_link

    share = create_share_link(db, conv, created_by=user_id, permission="read", expires_hours=72)
    handoff = ""
    m = re.search(r"hand\s*off[:\s]+(.+)$", text or "", re.I)
    if m:
        handoff = m.group(1).strip()[:500]
    aios["collab"] = {
        "share_token": share.get("share_token"),
        "permission": share.get("permission"),
        "expires_at": share.get("expires_at"),
        "handoff_note": handoff or aios.get("goal") or "",
        "reviewers_suggested": ["editor", "admin"],
    }
    ca._save_aios(db, conv, aios)
    ca.audit_chat_action(
        db,
        action="collab_war_room",
        user_id=user_id,
        workspace_id=workspace_id,
        resource_type="conversation",
        resource_id=str(conversation_id or ""),
    )
    token = share.get("share_token") or ""
    return {
        "events": [
            {
                "type": "aios_collab",
                "data": {
                    "status": "ok",
                    "share_token": token,
                    "permission": share.get("permission"),
                    "expires_at": share.get("expires_at"),
                    "handoff_note": aios["collab"].get("handoff_note"),
                    "reviewers_suggested": aios["collab"]["reviewers_suggested"],
                    "share_path": f"/share/{token}" if token else None,
                    "message": "War room opened — share link created (72h). Hand off note saved on the plan.",
                    "chips": ["Export conversation", "Show requirements", "Diff my workflow"],
                },
            }
        ],
        "blocked_normal_reply": True,
        "summary": "Collaboration war room ready.",
    }


def incident_kill_switch_action(
    db: Session,
    *,
    workspace_id: int,
    user_id: int,
    text: str,
) -> dict[str, Any]:
    t = (text or "").lower()
    confirmed = bool(re.search(r"\bconfirm (kill switch|incident|lockdown)\b|\bconfirm kill switch\b", t))
    if not confirmed:
        return {
            "events": [
                {
                    "type": "aios_incident",
                    "data": {
                        "status": "confirm_required",
                        "message": (
                            "This pauses **all schedules** and flags active runs to stop. "
                            "Say **confirm kill switch** to proceed."
                        ),
                        "chips": ["Confirm kill switch", "List schedules", "Workspace health"],
                    },
                }
            ],
            "blocked_normal_reply": True,
            "summary": "Kill switch needs confirmation.",
        }
    ca = _helpers()
    schedules = (
        db.query(WorkflowSchedule)
        .filter(WorkflowSchedule.workspace_id == workspace_id, WorkflowSchedule.enabled == 1)
        .all()
    )
    paused = 0
    for row in schedules:
        row.enabled = 0
        paused += 1
    runs = (
        db.query(WorkflowRun)
        .join(Workflow, Workflow.id == WorkflowRun.workflow_id)
        .filter(Workflow.workspace_id == workspace_id, WorkflowRun.status.in_([0, 1]))
        .limit(50)
        .all()
    )
    stopped = 0
    for run in runs:
        # status conventions vary; mark as stopped-ish if attribute exists
        try:
            run.status = 3
            stopped += 1
        except Exception:  # noqa: BLE001
            pass
    db.commit()
    ca.audit_chat_action(
        db,
        action="incident_kill_switch",
        user_id=user_id,
        workspace_id=workspace_id,
        resource_type="workspace",
        resource_id=str(workspace_id),
        detail={"paused_schedules": paused, "stopped_runs": stopped},
    )
    return {
        "events": [
            {
                "type": "aios_incident",
                "data": {
                    "status": "executed",
                    "paused_schedules": paused,
                    "stopped_runs": stopped,
                    "message": f"Incident lockdown: paused {paused} schedule(s), flagged {stopped} run(s).",
                    "chips": ["List schedules", "Workspace health", "SLA reliability brief"],
                },
            }
        ],
        "blocked_normal_reply": True,
        "summary": f"Kill switch: paused {paused}, stopped {stopped}.",
    }


def simulate_lab_action(
    db: Session,
    *,
    conversation_id: str | None,
) -> dict[str, Any]:
    ca = _helpers()
    _, aios = ca._load_aios(db, conversation_id)
    preview = aios.get("executable_preview") or aios.get("graph") or {}
    if not isinstance(preview, dict) or not (
        preview.get("nodes") or (preview.get("meta") or {}).get("node_types")
    ):
        return {
            "events": [
                {
                    "type": "aios_simulate",
                    "data": {
                        "status": "empty",
                        "message": "Compose a workflow first, then run the simulation lab.",
                        "chips": [
                            "Automate invoice reminders from my documents every Monday",
                            "Show powerhouse",
                        ],
                    },
                }
            ],
            "blocked_normal_reply": True,
            "summary": "Nothing to simulate.",
        }
    matrix = run_simulation_matrix(
        preview,
        missing_credentials=aios.get("missing_credentials") or [],
        fields=["finance", "hr", "support", "sales", "ops", "generic"],
    )
    return {
        "events": [
            {
                "type": "aios_simulate",
                "data": {
                    **matrix,
                    "message": (
                        f"Simulation matrix: {matrix.get('passed_fields')}/{matrix.get('field_count')} fields passed "
                        f"in {matrix.get('total_ms')}ms."
                    ),
                    "chips": (
                        ["Approve", "Deploy", "Eval scorecard"]
                        if matrix.get("status") == "success"
                        else ["Heal", "Fix & retest", "Diff my workflow"]
                    ),
                },
            }
        ],
        "blocked_normal_reply": True,
        "summary": f"Simulation: {matrix.get('passed_fields')}/{matrix.get('field_count')} passed.",
    }


def sla_brief_action(db: Session, *, workspace_id: int) -> dict[str, Any]:
    since = datetime.utcnow() - timedelta(days=7)
    rows = (
        db.query(WorkflowRun)
        .join(Workflow, Workflow.id == WorkflowRun.workflow_id)
        .filter(Workflow.workspace_id == workspace_id, WorkflowRun.create_time >= since)
        .order_by(WorkflowRun.id.desc())
        .limit(200)
        .all()
    )
    total = len(rows)
    # Heuristic: status 2 = success in many codepaths; also accept string
    success = 0
    latencies: list[float] = []
    fail_nodes: dict[str, int] = {}
    for r in rows:
        st = r.status
        ok = st == 2 or str(st).lower() in ("success", "completed", "ok", "2")
        if ok:
            success += 1
        try:
            steps = json.loads(r.steps_json or "[]")
        except json.JSONDecodeError:
            steps = []
        if isinstance(steps, list):
            dur = 0.0
            for step in steps:
                if not isinstance(step, dict):
                    continue
                dur += float(step.get("latency_ms") or step.get("duration_ms") or 0)
                if step.get("status") in ("error", "failed"):
                    nid = str(step.get("node_id") or step.get("type") or "unknown")
                    fail_nodes[nid] = fail_nodes.get(nid, 0) + 1
            if dur:
                latencies.append(dur)
    rate = round((success / total) * 100, 1) if total else 0.0
    p95 = 0.0
    if latencies:
        latencies.sort()
        idx = min(len(latencies) - 1, max(0, int(0.95 * (len(latencies) - 1))))
        p95 = round(latencies[idx], 1)
    top_fail = sorted(fail_nodes.items(), key=lambda x: -x[1])[:5]
    return {
        "events": [
            {
                "type": "aios_sla",
                "data": {
                    "status": "ok",
                    "window_days": 7,
                    "run_count": total,
                    "success_count": success,
                    "success_rate": rate,
                    "p95_latency_ms": p95,
                    "top_failing_nodes": [{"node": n, "count": c} for n, c in top_fail],
                    "message": (
                        f"Last 7d: {total} run(s), success rate **{rate}%**, p95 ~{p95}ms."
                        if total
                        else "No workflow runs in the last 7 days."
                    ),
                    "chips": ["Debug last run", "Eval scorecard", "Workspace health"],
                },
            }
        ],
        "blocked_normal_reply": True,
        "summary": f"SLA: {rate}% success over {total} runs (7d).",
    }


def _propose_notify_change(preview: dict[str, Any], channel: str) -> tuple[dict[str, Any], list[str]]:
    from app.composer.workflow_composer import heal_executable_graph

    g = dict(preview) if isinstance(preview, dict) else {}
    nodes = g.get("nodes")
    node_list: list[dict[str, Any]]
    if isinstance(nodes, dict):
        node_list = []
        for nid, data in nodes.items():
            row = dict(data) if isinstance(data, dict) else {"raw": data}
            row.setdefault("id", str(nid))
            node_list.append(row)
    elif isinstance(nodes, list):
        node_list = [dict(n) for n in nodes if isinstance(n, dict)]
    else:
        node_list = []
    edges = list(g.get("edges") or []) if isinstance(g.get("edges"), list) else []
    notes: list[str] = []
    notify_id = f"notify_{channel}"
    if not any(str(n.get("id")) == notify_id or str(n.get("type")) == "notify" for n in node_list):
        node_list.append(
            {
                "id": notify_id,
                "type": "notify",
                "data": {"channel": channel, "message": "{{output}}"},
            }
        )
        notes.append(f"Add {channel} notify node")
        out = next((n.get("id") for n in node_list if n.get("type") == "output"), None)
        src = next(
            (n.get("id") for n in reversed(node_list) if n.get("type") not in ("notify", "output")),
            None,
        )
        if src and out:
            edges.append({"from": src, "to": notify_id})
            edges.append({"from": notify_id, "to": out})
            notes.append(f"Wire {src} → {notify_id} → {out}")
        elif src:
            edges.append({"from": src, "to": notify_id})
            notes.append(f"Wire {src} → {notify_id}")
    proposed = {"nodes": node_list, "edges": edges, "meta": dict(g.get("meta") or {})}
    healed, fixes = heal_executable_graph(proposed)
    notes.extend(fixes or [])
    return healed, notes


def change_request_action(
    db: Session,
    *,
    conversation_id: str | None,
    text: str,
    apply: bool = False,
) -> dict[str, Any]:
    ca = _helpers()
    conv, aios = ca._load_aios(db, conversation_id)
    if apply:
        cr = aios.get("change_request") or {}
        proposed = cr.get("proposed")
        if not proposed:
            return {
                "events": [
                    {
                        "type": "aios_change_request",
                        "data": {
                            "status": "error",
                            "message": "No pending change request. Propose one first.",
                            "chips": ["Propose change: add Slack notify"],
                        },
                    }
                ],
                "blocked_normal_reply": True,
                "summary": "No change request.",
            }
        # Require explicit apply/confirm phrasing (chip "Apply change request" counts)
        confirmed = bool(
            re.search(
                r"\b(apply (the )?change( request)?|confirm apply change|approve (the )?change( request)?)\b",
                text or "",
                re.I,
            )
        )
        if not confirmed:
            return {
                "events": [
                    {
                        "type": "aios_change_request",
                        "data": {
                            "status": "confirm_required",
                            "notes": cr.get("notes") or [],
                            "diff_summary": cr.get("diff_summary"),
                            "message": "Pending change ready. Say **Apply change request** to write it into the plan.",
                            "chips": ["Apply change request", "Diff my workflow", "Cancel"],
                        },
                    }
                ],
                "blocked_normal_reply": True,
                "summary": "Confirm apply change request.",
            }
        aios["executable_preview"] = proposed
        aios["node_types"] = (proposed.get("meta") or {}).get("node_types") or aios.get("node_types")
        aios["change_request"] = {**cr, "status": "applied", "applied_at": datetime.utcnow().isoformat()}
        aios["tested"] = False
        aios["next_action"] = "test"
        ca._save_aios(db, conv, aios)
        return {
            "events": [
                {
                    "type": "aios_change_request",
                    "data": {
                        "status": "applied",
                        "notes": cr.get("notes") or [],
                        "message": "Change applied to pending executable. Run test / simulation next.",
                        "chips": ["Run simulation lab", "Diff my workflow", "Approve"],
                    },
                }
            ],
            "blocked_normal_reply": True,
            "summary": "Change request applied.",
        }

    t = (text or "").lower()
    channel = "slack"
    if "telegram" in t:
        channel = "telegram"
    elif "email" in t or "smtp" in t:
        channel = "email"
    elif "discord" in t:
        channel = "discord"
    preview = aios.get("executable_preview") or {}
    if not isinstance(preview, dict) or not preview.get("nodes"):
        return {
            "events": [
                {
                    "type": "aios_change_request",
                    "data": {
                        "status": "empty",
                        "message": "Compose a plan first, then propose a change.",
                        "chips": ["Show powerhouse"],
                    },
                }
            ],
            "blocked_normal_reply": True,
            "summary": "No plan for change request.",
        }
    before = _normalize_graph(preview)
    proposed, notes = _propose_notify_change(preview, channel)
    after = _normalize_graph(proposed)
    diff = diff_workflow_graphs(before, after)
    aios["change_request"] = {
        "status": "pending",
        "channel": channel,
        "notes": notes,
        "proposed": proposed,
        "diff_summary": diff.get("summary"),
    }
    ca._save_aios(db, conv, aios)
    return {
        "events": [
            {
                "type": "aios_change_request",
                "data": {
                    "status": "pending",
                    "channel": channel,
                    "notes": notes,
                    "diff_summary": diff.get("summary"),
                    "nodes_added": diff.get("nodes_added") or [],
                    "message": f"Change request: add **{channel}** notify. Review diff, then **apply change request**.",
                    "chips": ["Apply change request", "Diff my workflow", "Cancel"],
                },
            }
        ],
        "blocked_normal_reply": True,
        "summary": f"Pending change: add {channel} notify.",
    }


def action_digest_action(
    db: Session,
    *,
    workspace_id: int,
    conversation_id: str | None,
) -> dict[str, Any]:
    if not conversation_id:
        return {
            "events": [
                {
                    "type": "aios_digest",
                    "data": {"status": "error", "message": "Open a chat and attach files first."},
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
    blob_parts: list[str] = []
    for r in rows[:12]:
        key = r.storage_key or ""
        path = UPLOAD_DIR / key
        sidecar = path.with_suffix(path.suffix + ".txt") if path.suffix else path.with_name(path.name + ".txt")
        text = ""
        try:
            if sidecar.exists():
                text = sidecar.read_text(encoding="utf-8", errors="ignore")[:8000]
            elif path.exists() and path.stat().st_size < 2_000_000:
                text = path.read_text(encoding="utf-8", errors="ignore")[:8000]
        except Exception:  # noqa: BLE001
            text = ""
        if text:
            blob_parts.append(text)
    blob = "\n".join(blob_parts)
    actions: list[str] = []
    for line in blob.splitlines():
        line = line.strip(" -\t*")
        if len(line) < 8 or len(line) > 200:
            continue
        if re.search(
            r"\b(todo|action|follow[- ]?up|please|need to|should|schedule|email|notify|automate|onboard|invoice)\b",
            line,
            re.I,
        ):
            actions.append(line)
        if len(actions) >= 8:
            break
    if not actions and blob:
        # fallback: first non-empty sentences
        for sent in re.split(r"[.\n]+", blob):
            s = sent.strip()
            if 20 <= len(s) <= 160:
                actions.append(s)
            if len(actions) >= 5:
                break
    chips = [f"Build a workflow: {a[:80]}" for a in actions[:5]] or [
        "Index attachments",
        "Capture requirements: process my uploaded documents",
    ]
    return {
        "events": [
            {
                "type": "aios_digest",
                "data": {
                    "status": "ok" if actions else "empty",
                    "attachment_count": len(rows),
                    "actions": actions,
                    "action_count": len(actions),
                    "message": (
                        f"Extracted {len(actions)} action item(s) from {len(rows)} attachment(s)."
                        if actions
                        else "No action-like lines found. Attach a transcript/notes file, or index knowledge."
                    ),
                    "chips": chips + ["Fulfill these requirements", "Show powerhouse"],
                },
            }
        ],
        "blocked_normal_reply": True,
        "summary": f"Digest: {len(actions)} action(s) from {len(rows)} file(s).",
    }


async def dispatch_power_action(
    db: Session,
    *,
    workspace_id: int,
    user_id: int,
    conversation_id: str | None,
    user_message: str,
    intent: str | None = None,
) -> dict[str, Any] | None:
    intent = intent or classify_power_intent(user_message)
    if not intent or intent not in POWER_INTENTS:
        return None

    if intent == "powerhouse_catalog":
        return powerhouse_catalog_action()
    if intent == "workflow_diff":
        return workflow_diff_action(
            db, workspace_id=workspace_id, conversation_id=conversation_id, text=user_message
        )
    if intent == "version_time_machine":
        return versions_action(
            db,
            workspace_id=workspace_id,
            conversation_id=conversation_id,
            text=user_message,
            user_id=user_id,
            restore=False,
        )
    if intent == "restore_version":
        return versions_action(
            db,
            workspace_id=workspace_id,
            conversation_id=conversation_id,
            text=user_message,
            user_id=user_id,
            restore=True,
        )
    if intent == "eval_command":
        return eval_command_action(db, workspace_id=workspace_id, conversation_id=conversation_id)
    if intent == "cost_receipt":
        return cost_receipt_action(db, conversation_id=conversation_id, workspace_id=workspace_id)
    if intent == "run_debugger":
        return debug_action(
            db, workspace_id=workspace_id, conversation_id=conversation_id, text=user_message
        )
    if intent == "knowledge_graph":
        return knowledge_graph_action(
            db, workspace_id=workspace_id, conversation_id=conversation_id, text=user_message
        )
    if intent == "collab_war_room":
        return collab_war_room_action(
            db,
            workspace_id=workspace_id,
            user_id=user_id,
            conversation_id=conversation_id,
            text=user_message,
        )
    if intent == "incident_kill_switch":
        return incident_kill_switch_action(
            db, workspace_id=workspace_id, user_id=user_id, text=user_message
        )
    if intent == "simulate_lab":
        return simulate_lab_action(db, conversation_id=conversation_id)
    if intent == "sla_brief":
        return sla_brief_action(db, workspace_id=workspace_id)
    if intent == "change_request":
        return change_request_action(db, conversation_id=conversation_id, text=user_message, apply=False)
    if intent == "apply_change_request":
        return change_request_action(db, conversation_id=conversation_id, text=user_message, apply=True)
    if intent == "action_digest":
        return action_digest_action(
            db, workspace_id=workspace_id, conversation_id=conversation_id
        )
    return None
