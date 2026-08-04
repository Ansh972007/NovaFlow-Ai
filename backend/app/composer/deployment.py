from sqlalchemy.orm import Session
from app.database import SolutionGraph

def deploy_solution_graph(db: Session, workspace_id: int, solution_id: str) -> dict:
    """Updates status to deployed for compiled Solution Graphs."""
    solution = db.query(SolutionGraph).filter(SolutionGraph.id == solution_id).first()
    if not solution:
        raise ValueError("Solution graph not found.")
        
    solution.status = "deployed"
    db.commit()
    
    return {
        "solution_id": solution_id,
        "status": "deployed",
        "timestamp": "now"
    }
