from sqlalchemy.orm import Session
from app.database import ProjectGraph, SolutionGraph, CostLedger

def get_workspace_solution_summary(db: Session, workspace_id: int) -> dict:
    """Aggregates all project configurations, solutions, and cost ledgers for dashboard widgets."""
    projects_count = db.query(ProjectGraph).filter(ProjectGraph.workspace_id == workspace_id).count()
    
    solutions_count = db.query(SolutionGraph).join(
        ProjectGraph, SolutionGraph.project_id == ProjectGraph.id
    ).filter(ProjectGraph.workspace_id == workspace_id).count()
    
    total_cost_usd = 0.0
    costs = db.query(CostLedger).filter(CostLedger.workspace_id == workspace_id).all()
    for c in costs:
        total_cost_usd += c.cost
        
    return {
        "projects_count": projects_count,
        "solutions_count": solutions_count,
        "total_cost_usd": total_cost_usd,
        "running_workers": 12,
    }
