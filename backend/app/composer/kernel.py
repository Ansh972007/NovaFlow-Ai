from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import AIOSKernelConfig, ProjectGraph, SolutionGraph, get_db
from app.deps import require_permission
from app.schemas import ok, fail
from app.security.rbac import Permission
from app.composer.registry import get_all_capabilities
from app.composer.planner import compile_solution_blueprint

router = APIRouter(tags=["AIOS Kernel"])


class GoalRequest(BaseModel):
    goal: str


@router.get("/aios/kernel/status")
def get_kernel_status(
    db: Session = Depends(get_db),
    ctx=Depends(require_permission(Permission.WORKSPACE_READ)),
):
    """Retrieve the core AIOS Kernel configuration and operational heartbeat state."""
    config = db.query(AIOSKernelConfig).first()
    if not config:
        config = AIOSKernelConfig(active_provider_id=None, heartbeat_interval=30)
        db.add(config)
        db.commit()
        db.refresh(config)

    return ok(
        {
            "kernel_version": "12.2.0",
            "status": "active",
            "registered_capabilities_count": 22,
            "active_workers_count": 12,
            "active_provider_id": config.active_provider_id,
            "heartbeat_interval": config.heartbeat_interval,
            "updated_at": config.updated_at.isoformat() if config.updated_at else None,
        }
    )


@router.get("/aios/capabilities")
def list_capabilities(
    db: Session = Depends(get_db),
    ctx=Depends(require_permission(Permission.WORKSPACE_READ)),
):
    """List all registered capability DNAs within the active workspace."""
    caps = get_all_capabilities(db, ctx.workspace_id)
    return ok(caps)


@router.post("/aios/project")
def create_project_goal(
    body: GoalRequest,
    db: Session = Depends(get_db),
    ctx=Depends(require_permission(Permission.WORKSPACE_READ)),
):
    """Submit a business goal to compose a new project and solution graph blueprint."""
    if not body.goal.strip():
        return fail("Goal cannot be empty.")
    
    result = compile_solution_blueprint(db, ctx.workspace_id, body.goal)
    return ok(result)


@router.get("/aios/project/{project_id}")
def get_project_status(
    project_id: str,
    db: Session = Depends(get_db),
    ctx=Depends(require_permission(Permission.WORKSPACE_READ)),
):
    """Retrieve solution compilation status, requirements, and missing credentials JIT logs."""
    project = db.query(ProjectGraph).filter(
        ProjectGraph.id == project_id,
        ProjectGraph.workspace_id == ctx.workspace_id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    solution = db.query(SolutionGraph).filter(
        SolutionGraph.project_id == project.id
    ).first()
    
    import json
    graph_payload = json.loads(project.solution_payload)
    required_caps = graph_payload.get("required_capabilities", [])
    
    from app.composer.gap_analysis import analyze_solution_gaps
    missing_creds = analyze_solution_gaps(db, ctx.workspace_id, required_caps)

    return ok(
        {
            "project_id": project.id,
            "name": project.name,
            "business_goal": project.business_goal,
            "status": project.status,
            "version_tag": project.version_tag,
            "solution_id": solution.id if solution else None,
            "solution_status": solution.status if solution else "none",
            "graph": graph_payload,
            "missing_credentials": missing_creds,
        }
    )
