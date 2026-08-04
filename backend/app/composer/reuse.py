import json
from sqlalchemy.orm import Session
from app.database import UniversalAsset, WorkflowFragment
from app.services.workflow import TEMPLATES

def find_reusable_template(goal: str) -> dict | None:
    """Scan the built-in system templates to see if the goal matches a pre-designed pattern."""
    goal_lower = goal.lower()
    for tid, tpl in TEMPLATES.items():
        # Check title, description, or keys
        if tid in goal_lower or tpl.get("name", "").lower() in goal_lower:
            return {
                "id": tid,
                "name": tpl.get("name"),
                "desc": tpl.get("desc"),
                "graph": tpl.get("graph"),
                "type": "system_template"
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
