from datetime import datetime

from fastapi import APIRouter, Body, Depends, Query
from sqlalchemy.orm import Session

from app.database import Assistant, AssistantKnowledge, KnowledgeBase, get_db
from app.deps import get_current_user, get_workspace_ctx, require_workspace_editor
from app.schemas import AssistantCreate, AssistantKnowledgeUpdate, AssistantUpdate, fail, ok
from app.services.knowledge import get_assistant_knowledge_ids, set_assistant_knowledge

router = APIRouter(tags=["Assistant"])
FLOW_TYPE_ASSISTANT = 5


def assistant_dict(a: Assistant) -> dict:
    return {
        "id": a.id,
        "name": a.name,
        "desc": a.desc or "",
        "description": a.desc or "",
        "logo": a.logo or "",
        "user_id": a.user_id,
        "user_name": "",
        "status": a.status,
        "flow_type": FLOW_TYPE_ASSISTANT,
        "write": True,
        "create_time": a.create_time.isoformat() if a.create_time else None,
        "update_time": a.update_time.isoformat() if a.update_time else None,
    }


@router.get("/assistant")
def list_assistants(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    status: int | None = Query(None),
    name: str | None = Query(None),
    db: Session = Depends(get_db),
    ctx=Depends(get_workspace_ctx),
):
    q = db.query(Assistant).filter(Assistant.workspace_id == ctx.workspace_id)
    if status is not None:
        q = q.filter(Assistant.status == status)
    if name:
        q = q.filter(Assistant.name.contains(name))
    total = q.count()
    rows = q.order_by(Assistant.update_time.desc()).offset((page - 1) * limit).limit(limit).all()
    return ok({"data": [assistant_dict(a) for a in rows], "total": total})


@router.get("/assistant/info/{assistant_id}")
def assistant_info(assistant_id: str, db: Session = Depends(get_db), ctx=Depends(get_workspace_ctx)):
    a = db.get(Assistant, assistant_id)
    if not a or a.workspace_id != ctx.workspace_id:
        return fail(404, "Assistant not found")
    data = assistant_dict(a)
    data["prompt"] = a.prompt
    data["tool_list"] = []
    data["flow_list"] = []
    kid_list = get_assistant_knowledge_ids(db, assistant_id)
    kbs = (
        db.query(KnowledgeBase)
        .filter(KnowledgeBase.id.in_(kid_list), KnowledgeBase.workspace_id == ctx.workspace_id)
        .all()
        if kid_list
        else []
    )
    data["knowledge_list"] = [
        {"id": kb.id, "name": kb.name, "description": kb.description or ""} for kb in kbs
    ]
    data["knowledge_ids"] = [kb.id for kb in kbs]
    return ok(data)


@router.post("/assistant")
def create_assistant(body: AssistantCreate, db: Session = Depends(get_db), ctx=Depends(require_workspace_editor)):
    a = Assistant(
        name=body.name.strip(),
        prompt=body.prompt.strip(),
        logo=body.logo or "",
        user_id=ctx.user.user_id,
        workspace_id=ctx.workspace_id,
        status=0,
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    return ok(assistant_dict(a))


@router.put("/assistant")
def update_assistant(body: AssistantUpdate, db: Session = Depends(get_db), ctx=Depends(require_workspace_editor)):
    a = db.get(Assistant, body.id)
    if not a or a.workspace_id != ctx.workspace_id:
        return fail(404, "Assistant not found")
    if body.name:
        a.name = body.name.strip()
    if body.desc is not None:
        a.desc = body.desc
    if body.prompt:
        a.prompt = body.prompt.strip()
    a.update_time = datetime.utcnow()
    db.commit()
    db.refresh(a)
    return ok(assistant_dict(a))


@router.post("/assistant/status")
def set_status(
    id: str = Body(..., alias="id"),
    status: int = Body(...),
    db: Session = Depends(get_db),
    ctx=Depends(require_workspace_editor),
):
    a = db.get(Assistant, id)
    if not a or a.workspace_id != ctx.workspace_id:
        return fail(404, "Assistant not found")
    a.status = status
    a.update_time = datetime.utcnow()
    db.commit()
    return ok(None)


@router.post("/assistant/delete")
def delete_assistant(
    assistant_id: str = Body(...),
    db: Session = Depends(get_db),
    ctx=Depends(require_workspace_editor),
):
    a = db.get(Assistant, assistant_id)
    if not a or a.workspace_id != ctx.workspace_id:
        return fail(404, "Assistant not found")
    db.query(AssistantKnowledge).filter(AssistantKnowledge.assistant_id == assistant_id).delete()
    db.delete(a)
    db.commit()
    return ok(None)


@router.post("/assistant/knowledge")
def update_assistant_knowledge(
    body: AssistantKnowledgeUpdate,
    db: Session = Depends(get_db),
    ctx=Depends(require_workspace_editor),
):
    a = db.get(Assistant, body.assistant_id)
    if not a or a.workspace_id != ctx.workspace_id:
        return fail(404, "Assistant not found")
    valid_ids = []
    for kid in body.knowledge_ids:
        kb = db.get(KnowledgeBase, kid)
        if kb and kb.workspace_id == ctx.workspace_id:
            valid_ids.append(kid)
    set_assistant_knowledge(db, body.assistant_id, valid_ids)
    a.update_time = datetime.utcnow()
    db.commit()
    return ok({"knowledge_ids": valid_ids})


@router.get("/chat/online")
def online_chat(
    page: int = Query(1),
    limit: int = Query(50),
    db: Session = Depends(get_db),
    ctx=Depends(get_workspace_ctx),
):
    q = db.query(Assistant).filter(Assistant.workspace_id == ctx.workspace_id, Assistant.status == 1)
    rows = q.order_by(Assistant.update_time.desc()).limit(limit).all()
    return ok([assistant_dict(a) for a in rows])
