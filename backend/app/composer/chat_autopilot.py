"""Chat Autopilot — multi-step playbook runner against the real ops bus."""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.composer.chat_playbooks import PLAYBOOKS, match_playbook

logger = logging.getLogger(__name__)

AUTOPILOT_INTENTS = frozenset(
    {
        "autopilot_start",
        "autopilot_confirm",
        "autopilot_status",
        "autopilot_cancel",
        "autopilot_next",
        "autopilot_skip",
    }
)

# Steps whose chips map to destructive / mutating ops — pause for Confirm autopilot
DANGEROUS_STEP_CHIPS = frozenset(
    {
        "deploy",
        "confirm kill switch",
        "schedule my last workflow daily at 9am",
        "share conversation",
        "export this chat as markdown",
    }
)

# Map playbook chip text → ops intent (best-effort)
CHIP_TO_INTENT: dict[str, str] = {
    "run status": "workflow_status",
    "heal": "monitor",  # heal handled via bridge keywords; status/monitor as safe probe
    "run test": "simulate_lab",
    "send a test notification": "test_notification",
    "monitor the run": "monitor",
    "workspace health": "workspace_health",
    "finops summary": "finops_summary",
    "list schedules": "list_schedules",
    "show recommendations": "list_recommendations",
    "export this chat as markdown": "export_conversation",
    "what credentials are missing?": "list_credentials_needed",
    "list vault categories": "vault_posture",
    "approve": "capabilities",  # approve is bridge compose path; status card only
    "deploy": "list_workflows",
    "schedule my last workflow daily at 9am": "schedule_create",
    "confirm kill switch": "incident_kill_switch",
}

_AUTOPILOT_REGISTERED = False


def register_autopilot_ops() -> None:
    global _AUTOPILOT_REGISTERED
    if _AUTOPILOT_REGISTERED:
        return
    from app.composer.chat_ops_registry import OpSpec, register_op

    specs = [
        OpSpec(
            "autopilot_confirm",
            (r"\bconfirm autopilot\b", r"\bcontinue autopilot\b"),
            "aios_autopilot",
            "autopilot",
            title="Confirm Autopilot",
            chip="Confirm autopilot",
            priority=12,
        ),
        OpSpec(
            "autopilot_cancel",
            (r"\bcancel autopilot\b", r"\bstop autopilot\b"),
            "aios_autopilot",
            "autopilot",
            title="Cancel Autopilot",
            chip="Cancel autopilot",
            priority=12,
        ),
        OpSpec(
            "autopilot_skip",
            (r"\bskip autopilot( step)?\b", r"\bskip (this )?step\b"),
            "aios_autopilot",
            "autopilot",
            title="Skip Autopilot Step",
            chip="Skip autopilot step",
            priority=12,
        ),
        OpSpec(
            "autopilot_status",
            (r"\bautopilot status\b", r"\bautopilot progress\b"),
            "aios_autopilot",
            "autopilot",
            title="Autopilot Status",
            chip="Autopilot status",
            priority=18,
        ),
        OpSpec(
            "autopilot_next",
            (r"\bnext autopilot( step)?\b", r"\bautopilot next\b"),
            "aios_autopilot",
            "autopilot",
            title="Next Autopilot Step",
            chip="Next autopilot step",
            priority=18,
        ),
        OpSpec(
            "autopilot_start",
            (
                r"\brun (incident |weekly |onboard )?autopilot\b",
                r"\bstart (incident |weekly |onboard )?autopilot\b",
                r"\bautopilot (incident|weekly|onboard)\b",
                r"\brun incident autopilot\b",
            ),
            "aios_autopilot",
            "autopilot",
            title="Chat Autopilot",
            chip="Run incident autopilot",
            priority=22,
        ),
    ]
    for spec in specs:
        register_op(spec, None)
    _AUTOPILOT_REGISTERED = True


def classify_autopilot_intent(text: str) -> str | None:
    register_autopilot_ops()
    t = (text or "").lower().strip()
    if not t:
        return None
    if re.search(r"\bconfirm autopilot\b|\bcontinue autopilot\b", t):
        return "autopilot_confirm"
    if re.search(r"\bcancel autopilot\b|\bstop autopilot\b", t):
        return "autopilot_cancel"
    if re.search(r"\bskip autopilot( step)?\b|\bskip (this )?step\b", t):
        return "autopilot_skip"
    if re.search(r"\bautopilot status\b|\bautopilot progress\b", t):
        return "autopilot_status"
    if re.search(r"\bnext autopilot( step)?\b|\bautopilot next\b", t):
        return "autopilot_next"
    if re.search(
        r"\b(run|start) (incident |weekly |onboard )?autopilot\b|\bautopilot (incident|weekly|onboard)\b",
        t,
    ):
        return "autopilot_start"
    return None


def _helpers():
    from app.composer import chat_actions as ca

    return ca


def _resolve_playbook(text: str) -> dict[str, Any]:
    t = (text or "").lower()
    if "weekly" in t:
        return PLAYBOOKS["weekly_ops"]
    if "onboard" in t:
        return PLAYBOOKS["onboard_bot"]
    pb = match_playbook(text) or PLAYBOOKS["incident"]
    return pb


def _step_chip(step: dict[str, Any]) -> str:
    return str(step.get("chip") or step.get("label") or "").strip()


def _is_dangerous_step(step: dict[str, Any]) -> bool:
    chip = _step_chip(step).lower()
    if chip in DANGEROUS_STEP_CHIPS:
        return True
    if any(k in chip for k in ("deploy", "kill switch", "schedule", "share", "export")):
        return True
    return False


def _intent_for_step(step: dict[str, Any]) -> str | None:
    chip = _step_chip(step).lower()
    if chip in CHIP_TO_INTENT:
        return CHIP_TO_INTENT[chip]
    # compose-like chips: leave for bridge by returning None and recording suggest
    if chip.startswith("build ") or "compose" in chip:
        return None
    return CHIP_TO_INTENT.get(chip)


def _state_event(
    *,
    status: str,
    playbook: dict[str, Any] | None,
    state: dict[str, Any],
    message: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    steps = (playbook or {}).get("steps") or state.get("steps") or []
    idx = int(state.get("step_index") or 0)
    step_rows = []
    for i, s in enumerate(steps):
        step_rows.append(
            {
                "id": s.get("id"),
                "label": s.get("label"),
                "chip": s.get("chip"),
                "state": (
                    "done"
                    if i < idx
                    else ("current" if i == idx and status in ("running", "paused", "plan") else "pending")
                ),
            }
        )
    data = {
        "status": status,
        "playbook_id": state.get("playbook_id") or (playbook or {}).get("id"),
        "title": (playbook or {}).get("title") or state.get("title") or "Autopilot",
        "step_index": idx,
        "step_count": len(steps),
        "steps": step_rows,
        "log": (state.get("log") or [])[-12:],
        "message": message,
        "chips": [],
    }
    if status == "paused":
        data["chips"] = ["Confirm autopilot", "Skip autopilot step", "Cancel autopilot"]
    elif status in ("running", "plan"):
        data["chips"] = ["Confirm autopilot", "Autopilot status", "Cancel autopilot"]
    elif status == "done":
        data["chips"] = ["Show powerhouse", "Show forge", "What can you do?"]
    else:
        data["chips"] = ["Run incident autopilot", "Cancel autopilot"]
    if extra:
        data.update(extra)
    return {"type": "aios_autopilot", "data": data}


async def _run_step_ops(
    db: Session,
    *,
    workspace_id: int,
    user_id: int,
    conversation_id: str | None,
    step: dict[str, Any],
    workspace_role: str | None,
) -> dict[str, Any]:
    """Execute one playbook step via ops bus; return merged result."""
    ca = _helpers()
    chip = _step_chip(step)
    intent = _intent_for_step(step)
    if not intent:
        return {
            "events": [],
            "summary": f"Suggested: {chip}",
            "suggest_chip": chip,
            "blocked_normal_reply": True,
        }
    # For kill switch confirm path, send confirm phrase
    msg = chip
    if intent == "incident_kill_switch":
        msg = "Confirm kill switch"
    if intent == "schedule_create":
        msg = chip
    result = await ca.dispatch_ops_action(
        db,
        workspace_id=workspace_id,
        user_id=user_id,
        conversation_id=conversation_id,
        user_message=msg,
        intent=intent,
        workspace_role=workspace_role,
    )
    return result or {
        "events": [],
        "summary": f"Step `{chip}` had no handler.",
        "blocked_normal_reply": True,
    }


async def _advance(
    db: Session,
    *,
    workspace_id: int,
    user_id: int,
    conversation_id: str | None,
    workspace_role: str | None,
    state: dict[str, Any],
    playbook: dict[str, Any],
    auto_chain: bool,
    confirmed: bool,
) -> dict[str, Any]:
    ca = _helpers()
    conv, aios = ca._load_aios(db, conversation_id)
    steps = playbook.get("steps") or []
    events: list[dict[str, Any]] = []
    summaries: list[str] = []
    idx = int(state.get("step_index") or 0)
    log = list(state.get("log") or [])

    # Cap auto-chain to avoid runaway turns
    max_auto = 4 if auto_chain else 1
    ran = 0

    while idx < len(steps) and ran < max_auto:
        step = steps[idx]
        dangerous = _is_dangerous_step(step)
        if dangerous and not confirmed and state.get("status") != "confirmed_once":
            state.update(
                {
                    "status": "paused",
                    "step_index": idx,
                    "paused_reason": "destructive_step",
                    "title": playbook.get("title"),
                    "steps": steps,
                    "log": log,
                    "updated_at": datetime.utcnow().isoformat(),
                }
            )
            aios["autopilot"] = state
            ca._save_aios(db, conv, aios)
            ev = _state_event(
                status="paused",
                playbook=playbook,
                state=state,
                message=(
                    f"Autopilot paused at step {idx + 1}/{len(steps)}: **{_step_chip(step)}**. "
                    "Say **Confirm autopilot** to continue, or **Skip autopilot step**."
                ),
            )
            events.append(ev)
            return {
                "events": events,
                "blocked_normal_reply": True,
                "summary": ev["data"]["message"],
            }

        # Run step
        step_result = await _run_step_ops(
            db,
            workspace_id=workspace_id,
            user_id=user_id,
            conversation_id=conversation_id,
            step=step,
            workspace_role=workspace_role,
        )
        step_events = step_result.get("events") or []
        events.extend(step_events)
        summaries.append(step_result.get("summary") or _step_chip(step))
        log.append(
            {
                "step_id": step.get("id"),
                "chip": _step_chip(step),
                "summary": step_result.get("summary"),
                "at": datetime.utcnow().isoformat(),
                "ok": not any(
                    (e.get("data") or {}).get("status") in ("error", "denied") for e in step_events
                ),
            }
        )
        if step_result.get("suggest_chip"):
            events.append(
                {
                    "type": "aios_suggest",
                    "data": {
                        "message": f"Next manual chip: {step_result['suggest_chip']}",
                        "chips": [step_result["suggest_chip"]],
                    },
                }
            )
        idx += 1
        ran += 1
        confirmed = False  # only one destructive confirm per confirm message
        state["status"] = "running"
        # Stop after dangerous step that just ran
        if dangerous:
            break
        # Reload aios after ops may have mutated it
        conv, aios = ca._load_aios(db, conversation_id)

    done = idx >= len(steps)
    state.update(
        {
            "status": "done" if done else "running",
            "step_index": idx,
            "title": playbook.get("title"),
            "playbook_id": playbook.get("id"),
            "steps": steps,
            "log": log,
            "updated_at": datetime.utcnow().isoformat(),
        }
    )
    if done:
        state["finished_at"] = datetime.utcnow().isoformat()
    aios["autopilot"] = state
    ca._save_aios(db, conv, aios)

    progress = _state_event(
        status="done" if done else "running",
        playbook=playbook,
        state=state,
        message=(
            f"Autopilot complete — {playbook.get('title')}."
            if done
            else f"Running autopilot — step {min(idx + 1, len(steps))}/{len(steps)}."
        ),
    )
    events.append(progress)
    summary = "; ".join(summaries[-3:]) if summaries else progress["data"]["message"]
    return {"events": events, "blocked_normal_reply": True, "summary": summary}


async def dispatch_autopilot_action(
    db: Session,
    *,
    workspace_id: int,
    user_id: int,
    conversation_id: str | None,
    user_message: str,
    intent: str | None = None,
    workspace_role: str | None = "editor",
) -> dict[str, Any] | None:
    intent = intent or classify_autopilot_intent(user_message)
    if not intent or intent not in AUTOPILOT_INTENTS:
        return None

    ca = _helpers()
    conv, aios = ca._load_aios(db, conversation_id)
    state = aios.get("autopilot") if isinstance(aios.get("autopilot"), dict) else {}

    if intent == "autopilot_cancel":
        aios["autopilot"] = {
            "status": "cancelled",
            "cancelled_at": datetime.utcnow().isoformat(),
            "playbook_id": state.get("playbook_id"),
            "step_index": state.get("step_index") or 0,
            "log": state.get("log") or [],
        }
        ca._save_aios(db, conv, aios)
        ev = _state_event(
            status="cancelled",
            playbook=None,
            state=aios["autopilot"],
            message="Autopilot cancelled.",
        )
        return {"events": [ev], "blocked_normal_reply": True, "summary": "Autopilot cancelled."}

    if intent == "autopilot_status":
        pb_id = state.get("playbook_id") or "incident"
        playbook = PLAYBOOKS.get(pb_id) or PLAYBOOKS["incident"]
        if not state:
            ev = _state_event(
                status="idle",
                playbook=None,
                state={},
                message="No autopilot running. Try **Run incident autopilot**.",
                extra={"chips": ["Run incident autopilot", "Show powerhouse"]},
            )
            return {"events": [ev], "blocked_normal_reply": True, "summary": ev["data"]["message"]}
        ev = _state_event(
            status=state.get("status") or "running",
            playbook=playbook,
            state=state,
            message=(
                f"Autopilot `{pb_id}` — step {int(state.get('step_index') or 0) + 1}/"
                f"{len(playbook.get('steps') or [])} ({state.get('status')})."
            ),
        )
        return {"events": [ev], "blocked_normal_reply": True, "summary": ev["data"]["message"]}

    if intent == "autopilot_start":
        playbook = _resolve_playbook(user_message)
        state = {
            "status": "plan",
            "playbook_id": playbook["id"],
            "title": playbook["title"],
            "step_index": 0,
            "steps": playbook.get("steps") or [],
            "log": [],
            "started_at": datetime.utcnow().isoformat(),
        }
        aios["autopilot"] = state
        ca._save_aios(db, conv, aios)
        # Kick off auto-chain until pause
        return await _advance(
            db,
            workspace_id=workspace_id,
            user_id=user_id,
            conversation_id=conversation_id,
            workspace_role=workspace_role,
            state=state,
            playbook=playbook,
            auto_chain=True,
            confirmed=False,
        )

    if intent in ("autopilot_confirm", "autopilot_next", "autopilot_skip"):
        if not state or state.get("status") in ("cancelled", "done", None) and not state.get("playbook_id"):
            return {
                "events": [
                    _state_event(
                        status="idle",
                        playbook=None,
                        state={},
                        message="No active autopilot. Say **Run incident autopilot**.",
                        extra={"chips": ["Run incident autopilot"]},
                    )
                ],
                "blocked_normal_reply": True,
                "summary": "No active autopilot.",
            }
        pb_id = state.get("playbook_id") or "incident"
        playbook = PLAYBOOKS.get(pb_id) or PLAYBOOKS["incident"]
        if intent == "autopilot_skip":
            state["step_index"] = int(state.get("step_index") or 0) + 1
            state["status"] = "running"
            log = list(state.get("log") or [])
            log.append({"step_id": "skipped", "at": datetime.utcnow().isoformat(), "ok": True})
            state["log"] = log
        confirmed = intent == "autopilot_confirm"
        if confirmed:
            state["status"] = "confirmed_once"
        return await _advance(
            db,
            workspace_id=workspace_id,
            user_id=user_id,
            conversation_id=conversation_id,
            workspace_role=workspace_role,
            state=state,
            playbook=playbook,
            auto_chain=True,
            confirmed=confirmed or intent == "autopilot_next",
        )

    return None
