import json
from sqlalchemy.orm import Session
from app.database import SolutionGraph, Workflow

def assemble_executable_workflow(db: Session, workspace_id: int, user_id: int, solution_id: str) -> Workflow:
    """Assembles a compiled Solution Graph blueprint into an executable Workflow database record."""
    solution = db.query(SolutionGraph).filter(SolutionGraph.id == solution_id).first()
    if not solution:
        raise ValueError("Solution graph not found.")
        
    graph_payload = json.loads(solution.graph_payload)
    nodes = graph_payload.get("nodes", {})
    
    # Translate Solution Graph nodes into a standard workspace workflow structure
    wf_nodes = []
    for node_id, node_data in nodes.items():
        wf_nodes.append({
            "id": node_id,
            "name": node_data.get("type", "node"),
            "type": node_data.get("type", "capability"),
            "config": node_data,
        })
        
    graph_json = {
        "nodes": wf_nodes,
        "edges": graph_payload.get("edges", [])
    }
    
    workflow = Workflow(
        name=f"Compiled Workflow: {solution_id[:8]}",
        desc="Compiled autonomously by NovaFlow Composer Engine",
        graph_json=json.dumps(graph_json),
        user_id=user_id,
        workspace_id=workspace_id,
        status=1, # Active
    )
    db.add(workflow)
    db.commit()
    db.refresh(workflow)
    return workflow
