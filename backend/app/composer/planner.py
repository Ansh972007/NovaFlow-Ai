import json
import uuid
from sqlalchemy.orm import Session
from app.database import ProjectGraph, SolutionGraph, HierarchicalMemory
from app.composer.reuse import match_reusable_asset
from app.composer.gap_analysis import analyze_solution_gaps
from app.composer.registry import get_all_capabilities

def parse_goal_intent(goal: str) -> list[str]:
    """Identify required system capabilities based on natural language goal keywords."""
    goal_lower = goal.lower()
    required = []
    
    if "voice" in goal_lower or "audio" in goal_lower:
        required.append("cap_voice")
    if "workflow" in goal_lower or "automate" in goal_lower:
        required.append("cap_workflow")
    if "knowledge" in goal_lower or "docs" in goal_lower or "rag" in goal_lower:
        required.append("cap_knowledge")
    if "ocr" in goal_lower or "image" in goal_lower:
        required.append("cap_ocr")
    if "telegram" in goal_lower or "bot" in goal_lower:
        required.append("cap_telegram")
        
    return required


def compile_solution_blueprint(db: Session, workspace_id: int, goal: str) -> dict:
    """Design the solution blueprint, matching reuse options and running gap checks."""
    # 1. Run Component Reuse Check
    reused = match_reusable_asset(db, workspace_id, goal)
    if reused:
        return {
            "project_id": None,
            "solution_id": reused["id"],
            "status": "reused",
            "type": reused.get("type"),
            "graph": reused.get("graph", {}),
            "missing_credentials": [],
        }

    # 2. Capability Extraction
    required_caps = parse_goal_intent(goal)
    
    # 3. Gap Analysis
    missing_creds = analyze_solution_gaps(db, workspace_id, required_caps)
    
    # 4. Generate Solution Graph Structure
    nodes = {}
    edges = []
    
    for cap_id in required_caps:
        nodes[cap_id] = {
            "type": "capability",
            "id": cap_id,
            "status": "ready" if cap_id not in missing_creds else "pending_credentials"
        }
    
    # Create database target node if ordering or storing is mentioned
    if "store" in goal.lower() or "menu" in goal.lower() or "database" in goal.lower():
        nodes["db_orders"] = {
            "type": "database",
            "schema_name": "orders",
            "fields": ["id", "customer_name", "items", "total_price"]
        }
        for cap_id in required_caps:
            edges.append({"source": cap_id, "target": "db_orders"})

    graph_payload = {
        "nodes": nodes,
        "edges": edges,
        "required_capabilities": required_caps
    }

    # 5. Insert Database Records
    project = ProjectGraph(
        workspace_id=workspace_id,
        name=f"Project: {goal[:30]}...",
        business_goal=goal,
        status="compiled_draft" if missing_creds else "active",
        solution_payload=json.dumps(graph_payload),
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    solution = SolutionGraph(
        project_id=project.id,
        graph_payload=json.dumps(graph_payload),
        status="compiled_draft" if missing_creds else "compiled",
    )
    db.add(solution)
    db.commit()
    db.refresh(solution)

    # 6. Initialize Hierarchical Memory Partition
    memory = HierarchicalMemory(
        workspace_id=workspace_id,
        scope="solution",
        scope_ref=solution.id,
        content=f"Initial compilation memory context for goal: {goal}",
    )
    db.add(memory)
    db.commit()

    return {
        "project_id": project.id,
        "solution_id": solution.id,
        "status": project.status,
        "graph": graph_payload,
        "missing_credentials": missing_creds,
    }
