"""AgentOS supervisor engine — goal breakdown, assignment, merge."""

from __future__ import annotations

import json
from typing import Any

from app.agent_os.planning import decompose_goal
from app.runtime.agents import AGENT_ROLES


def supervise_plan(goal: str, *, agent_type: str = "supervisor") -> dict[str, Any]:
    """Break goal into subtasks and assign roles."""
    plan = decompose_goal(goal)
    assignments = []
    role_cycle = ["research", "developer", "reviewer", "writer"]
    for i, task in enumerate(plan.get("tasks") or []):
        role = role_cycle[i % len(role_cycle)]
        assignments.append(
            {
                "task_id": task["id"],
                "title": task["title"],
                "assigned_role": role,
                "role_prompt": AGENT_ROLES.get(role, AGENT_ROLES["writer"]),
                "status": "pending",
            }
        )
    return {
        "goal": goal,
        "plan": plan,
        "assignments": assignments,
        "supervisor_prompt": AGENT_ROLES["coordinator"],
        "agent_type": agent_type,
    }


def merge_outputs(transcripts: list[str], *, confidence: float = 0.0) -> dict[str, Any]:
    merged = "\n\n".join(t for t in transcripts if t.strip())
    return {
        "output": merged,
        "source_count": len(transcripts),
        "confidence": confidence,
    }


def evaluate_progress(assignments: list[dict]) -> dict[str, Any]:
    total = len(assignments)
    done = sum(1 for a in assignments if a.get("status") == "completed")
    failed = sum(1 for a in assignments if a.get("status") == "failed")
    return {
        "total": total,
        "completed": done,
        "failed": failed,
        "progress": round(done / max(total, 1), 2),
        "needs_retry": failed > 0,
        "needs_escalation": failed > 1,
    }


def supervisor_session_dict(plan: dict, assignments: list[dict], progress: dict) -> dict[str, Any]:
    return {
        "plan": plan,
        "assignments": assignments,
        "progress": progress,
    }
