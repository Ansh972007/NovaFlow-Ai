import json
from sqlalchemy.orm import Session
from app.database import UniversalAsset, WorkflowFragment
from app.services.workflow import TEMPLATES

def find_reusable_template(goal: str) -> dict | None:
    """Scan built-in templates for an intentional match (not bare substring of tid)."""
    goal_lower = (goal or "").lower()
    for tid, tpl in TEMPLATES.items():
        name = (tpl.get("name") or "").lower()
        # Require whole-word / phrase match on template name or explicit "use template X"
        if name and name in goal_lower:
            return {
                "id": tid,
                "name": tpl.get("name"),
                "desc": tpl.get("desc"),
                "graph": tpl.get("graph"),
                "type": "system_template",
            }
        if f"template {tid}" in goal_lower or f"use {tid}" in goal_lower:
            return {
                "id": tid,
                "name": tpl.get("name"),
                "desc": tpl.get("desc"),
                "graph": tpl.get("graph"),
                "type": "system_template",
            }
    return None


def match_reusable_asset(db: Session, workspace_id: int, goal: str) -> dict | None:
    """Find workspace-specific or system templates that match the user goal to prevent rebuilding."""
    # 1. Check system templates first
    sys_match = find_reusable_template(goal)
    if sys_match:
        return sys_match

    # 2. Check workspace assets (custom workflows, agent templates)
    goal_lower = goal.lower()
    assets = db.query(UniversalAsset).filter(UniversalAsset.workspace_id == workspace_id).all()
    for asset in assets:
        if asset.name.lower() in goal_lower or goal_lower in asset.name.lower():
            return {
                "id": asset.id,
                "name": asset.name,
                "type": asset.asset_type,
                "config": json.loads(asset.config_json),
            }

    # 3. Check workflow fragments
    fragments = db.query(WorkflowFragment).filter(WorkflowFragment.workspace_id == workspace_id).all()
    for frag in fragments:
        if frag.name.lower() in goal_lower:
            return {
                "id": frag.id,
                "name": frag.name,
                "type": "workflow_fragment",
                "graph": json.loads(frag.graph_json),
            }

    return None
