import json
from datetime import datetime

from app.database import DevProject


def project_dict(row: DevProject) -> dict:
    try:
        integrations = json.loads(row.integrations_json or "{}")
    except json.JSONDecodeError:
        integrations = {}
    try:
        workflow_ids = json.loads(row.workflow_ids_json or "[]")
    except json.JSONDecodeError:
        workflow_ids = []
    return {
        "id": row.id,
        "name": row.name,
        "description": row.description or "",
        "status": row.status or "active",
        "integrations": integrations,
        "workflow_ids": workflow_ids,
        "create_time": row.create_time.isoformat() if row.create_time else None,
        "update_time": row.update_time.isoformat() if row.update_time else None,
    }


def create_project(
    db,
    *,
    user_id: int,
    workspace_id: int,
    name: str,
    description: str = "",
    integrations: dict | None = None,
    workflow_ids: list | None = None,
) -> DevProject:
    row = DevProject(
        name=name[:120],
        description=description[:2000],
        status="active",
        user_id=user_id,
        workspace_id=workspace_id,
        integrations_json=json.dumps(integrations or {}),
        workflow_ids_json=json.dumps(workflow_ids or []),
        update_time=datetime.utcnow(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_project(db, row: DevProject, body: dict) -> DevProject:
    if "name" in body and body["name"]:
        row.name = str(body["name"]).strip()[:120]
    if "description" in body:
        row.description = str(body["description"] or "").strip()[:2000]
    if "status" in body:
        row.status = str(body["status"] or "active").strip()[:24]
    if "integrations" in body and isinstance(body["integrations"], dict):
        row.integrations_json = json.dumps(body["integrations"])
    if "workflow_ids" in body and isinstance(body["workflow_ids"], list):
        row.workflow_ids_json = json.dumps(body["workflow_ids"])
    row.update_time = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return row
