"""User-model-driven chat orchestrator — routes QA vs compose/modify/ops/credential."""

from __future__ import annotations

import json
import re
from typing import Any

from sqlalchemy.orm import Session

from app.composer.chat_actions import classify_ops_intent, OPS_INTENTS
from app.composer.chat_advanced import is_conversational_message, is_explicit_workflow_request
from app.composer.chat_router import is_qa_message, universal_route


_ORCH_SYSTEM = (
    "You are NovaFlow Chat Orchestrator. Classify the user message and return ONLY JSON:\n"
    "{"
    '"mode": "qa|compose|modify|ops|credential|agent",'
    '"answer": "optional short answer for qa mode",'
    '"ops_intent": "optional ops intent id",'
    '"requirements_patch": {optional structured fields},'
    '"workflow_action": "create|modify|reuse|null"'
    "}\n"
    "modes:\n"
    "- qa: general questions, greetings, explanations (NOT workflow building)\n"
    "- compose: build new workflow/automation\n"
    "- modify: change pending or existing workflow plan\n"
    "- ops: list/run/deploy workflows, store knowledge, switch model\n"
    "- credential: user pasted secrets\n"
    "- agent: complex multi-step automation needing agent runtime\n"
    "If user asks to list workflows, run workflow, store in knowledge — use ops with ops_intent.\n"
    "requirements_patch keys when compose/modify: integrations[], input_channels[], "
    "output_channels[], trigger, email_plan, goal.\n"
)


def _parse_json_object(raw: str) -> dict[str, Any] | None:
    if not raw:
        return None
    match = re.search(r"\{[\s\S]*\}", raw)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        return None


def _heuristic_orchestrate(text: str, *, has_pending: bool, aios: dict[str, Any]) -> dict[str, Any] | None:
    t = (text or "").strip()
    if not t:
        return {"mode": "qa", "allow_normal_reply": True}

    ops = classify_ops_intent(t)
    if ops and ops in OPS_INTENTS:
        return {"mode": "ops", "ops_intent": ops, "allow_normal_reply": True}

    route = universal_route(t, has_pending=has_pending, last_field=aios.get("last_field"))
    if route.get("route") == "ops":
        return {
            "mode": "ops",
            "ops_intent": route.get("ops_intent"),
            "allow_normal_reply": True,
        }

    if route.get("route") == "pending_action":
        # Let chat_bridge handle approve / test / deploy / refine directly
        return None

    if is_conversational_message(t) and not is_explicit_workflow_request(t):
        from app.composer.chat_bridge import classify_intent
        from app.composer.chat_router import PENDING_ACTIONS

        if has_pending and classify_intent(t, has_pending=True) in PENDING_ACTIONS:
            return None
        return {"mode": "qa", "allow_normal_reply": True}

    if route.get("route") in ("work_compose", "agent"):
        mode = "agent" if route.get("route") == "agent" else "compose"
        if has_pending and route.get("intent_hint") == "refine":
            mode = "modify"
        return {"mode": mode, "workflow_action": "modify" if mode == "modify" else "create"}

    if is_qa_message(t) and not route.get("work_signal"):
        return {"mode": "qa", "allow_normal_reply": True}

    return None


def orchestrate_turn(
    db: Session,
    *,
    workspace_id: int,
    user_id: int,
    user_message: str,
    aios: dict[str, Any],
    has_pending: bool,
) -> dict[str, Any] | None:
    """
    Classify user turn via user-selected planning model.
    Returns orchestration dict or None to fall back to keyword routing.
    """
    from app.composer.llm_resolve import resolve_chat_llm_config

    text = (user_message or "").strip()
    heuristic = _heuristic_orchestrate(text, has_pending=has_pending, aios=aios)
    if heuristic is None:
        return None
    if db is None:
        return heuristic

    llm_cfg = resolve_chat_llm_config(db, workspace_id, user_id, aios)
    if not llm_cfg.get("api_key"):
        return heuristic

    snapshot = {
        "compose_phase": aios.get("compose_phase"),
        "status": aios.get("status"),
        "workflow_id": aios.get("workflow_id"),
        "goal": (aios.get("goal") or "")[:300],
        "has_pending": has_pending,
    }
    try:
        from app.services.llm import complete_text

        raw = complete_text(
            system=_ORCH_SYSTEM,
            user=f"Snapshot: {json.dumps(snapshot)}\nUser: {text[:1200]}",
            cfg=llm_cfg,
            db=db,
        )
        parsed = _parse_json_object(raw)
        if not parsed or not parsed.get("mode"):
            return heuristic
        mode = str(parsed.get("mode") or "").lower()
        out: dict[str, Any] = {
            "mode": mode,
            "answer": (parsed.get("answer") or "").strip(),
            "requirements_patch": parsed.get("requirements_patch") or {},
            "workflow_action": parsed.get("workflow_action"),
            "ops_intent": parsed.get("ops_intent"),
        }
        if mode == "qa":
            out["allow_normal_reply"] = True
        elif mode == "ops":
            out["allow_normal_reply"] = True
            if not out.get("ops_intent"):
                out["ops_intent"] = classify_ops_intent(text)
        elif mode in ("compose", "modify", "agent"):
            out["allow_normal_reply"] = True
        elif mode == "credential":
            out["allow_normal_reply"] = True
        return out
    except Exception:
        return heuristic


def apply_orchestrator_patch(aios: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    """Merge orchestrator requirements_patch into aios requirements."""
    if not patch:
        return aios
    req = dict(aios.get("requirements") or {})
    for key, val in patch.items():
        if val is None:
            continue
        if key in ("integrations", "input_channels", "output_channels") and isinstance(val, list):
            existing = list(req.get(key) or [])
            for item in val:
                if item not in existing:
                    existing.append(item)
            req[key] = existing
        elif key == "email_plan" and isinstance(val, dict):
            req["email_plan"] = {**(req.get("email_plan") or {}), **val}
        else:
            req[key] = val
    aios["requirements"] = req
    if patch.get("goal"):
        aios["goal"] = str(patch["goal"])[:1000]
    return aios
