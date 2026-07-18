"""AgentOS planning engine — hierarchical task decomposition."""

from __future__ import annotations

import json
import re
import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.database import AgentPlanSession


def decompose_goal(goal: str, *, max_tasks: int = 6) -> dict[str, Any]:
    """Rule-based goal decomposition into subtasks with dependencies."""
    goal = (goal or "").strip()
    if not goal:
        return {"goal": "", "tasks": [], "dependencies": []}

    sentences = [s.strip() for s in re.split(r"[.!?\n]+", goal) if s.strip()]
    if len(sentences) <= 1:
        keywords = re.findall(r"[a-zA-Z]{4,}", goal)
        chunks = keywords[:max_tasks] or [goal[:80]]
        tasks = [{"id": f"t{i+1}", "title": c, "priority": i + 1} for i, c in enumerate(chunks)]
    else:
        tasks = [{"id": f"t{i+1}", "title": s[:200], "priority": i + 1} for i, s in enumerate(sentences[:max_tasks])]

    dependencies = []
    for i in range(1, len(tasks)):
        dependencies.append({"from": tasks[i - 1]["id"], "to": tasks[i]["id"], "type": "sequential"})

    return {
        "goal": goal,
        "tasks": tasks,
        "dependencies": dependencies,
        "execution_order": [t["id"] for t in tasks],
    }


def create_plan_session(
    db: Session,
    *,
    workspace_id: int,
    goal: str,
    run_id: str | None = None,
) -> AgentPlanSession:
    plan = decompose_goal(goal)
    session = AgentPlanSession(
        id=uuid.uuid4().hex,
        run_id=run_id,
        workspace_id=workspace_id,
        goal=goal[:2000],
        plan_json=json.dumps(plan),
        dependencies_json=json.dumps(plan.get("dependencies") or []),
        status="active",
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def replan(db: Session, session: AgentPlanSession, *, new_goal: str = "") -> dict[str, Any]:
    goal = new_goal or session.goal
    plan = decompose_goal(goal)
    session.goal = goal[:2000]
    session.plan_json = json.dumps(plan)
    session.dependencies_json = json.dumps(plan.get("dependencies") or [])
    db.commit()
    return plan


def plan_dict(session: AgentPlanSession) -> dict[str, Any]:
    try:
        plan = json.loads(session.plan_json or "{}")
    except json.JSONDecodeError:
        plan = {}
    return {
        "id": session.id,
        "run_id": session.run_id,
        "goal": session.goal,
        "plan": plan,
        "status": session.status,
        "create_time": session.create_time.isoformat() if session.create_time else None,
    }
