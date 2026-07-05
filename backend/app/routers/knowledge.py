import shutil
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.orm import Session

from app.config import EMBEDDING_MODELS
from app.database import KnowledgeBase, KnowledgeFile, get_db
from app.deps import get_workspace_ctx, require_workspace_editor
from app.schemas import KnowledgeCreate, ProcessFiles, fail, ok
from app.services.knowledge import kb_upload_dir, process_file_record, search_chunks

router = APIRouter(tags=["Knowledge"])


def kb_dict(kb: KnowledgeBase) -> dict:
    return {
        "id": kb.id,
        "name": kb.name,
        "description": kb.description or "",
        "model": kb.model,
        "type": kb.type,
        "create_time": kb.create_time.isoformat() if kb.create_time else None,
        "update_time": kb.update_time.isoformat() if kb.update_time else None,
    }


@router.get("/knowledge")
def list_knowledge(
    page_num: int = Query(1, alias="page_num"),
    page_size: int = Query(50, alias="page_size"),
    name: str = Query(""),
    db: Session = Depends(get_db),
    ctx=Depends(get_workspace_ctx),
):
    q = db.query(KnowledgeBase).filter(KnowledgeBase.workspace_id == ctx.workspace_id)
    if name:
        q = q.filter(KnowledgeBase.name.contains(name))
    total = q.count()
    rows = q.order_by(KnowledgeBase.update_time.desc()).offset((page_num - 1) * page_size).limit(page_size).all()
    return ok({"data": [kb_dict(k) for k in rows], "total": total})


@router.get("/knowledge/embedding_param")
def embedding_param():
    return ok({"models": EMBEDDING_MODELS})


@router.post("/knowledge/create")
def create_knowledge(body: KnowledgeCreate, db: Session = Depends(get_db), ctx=Depends(require_workspace_editor)):
    kb = KnowledgeBase(
        name=body.name.strip(),
        description=body.description or "",
        model=body.model or EMBEDDING_MODELS[0],
        type=body.type,
        user_id=ctx.user.user_id,
        workspace_id=ctx.workspace_id,
    )
    db.add(kb)
    db.commit()
    db.refresh(kb)
    kb_upload_dir(kb.id)
    return ok(kb_dict(kb))


@router.get("/knowledge/file_list/{knowledge_id}")
def file_list(
    knowledge_id: int,
    page_num: int = Query(1),
    page_size: int = Query(50),
    db: Session = Depends(get_db),
    ctx=Depends(get_workspace_ctx),
):
    kb = db.get(KnowledgeBase, knowledge_id)
    if not kb or kb.workspace_id != ctx.workspace_id:
        return fail(404, "Knowledge base not found")
    rows = (
        db.query(KnowledgeFile)
        .filter(KnowledgeFile.knowledge_id == knowledge_id)
        .order_by(KnowledgeFile.update_time.desc())
        .offset((page_num - 1) * page_size)
        .limit(page_size)
        .all()
    )
    data = [
        {
            "id": f.id,
            "file_name": f.file_name,
            "status": f.status,
            "update_time": f.update_time.isoformat() if f.update_time else None,
        }
        for f in rows
    ]
    return ok({"data": data, "writeable": ctx.role != "viewer", "total": len(data)})


@router.post("/knowledge/upload/{knowledge_id}")
async def upload_file(
    knowledge_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    ctx=Depends(require_workspace_editor),
):
    kb = db.get(KnowledgeBase, knowledge_id)
    if not kb or kb.workspace_id != ctx.workspace_id:
        return fail(404, "Knowledge base not found")
    dest_dir = kb_upload_dir(knowledge_id)
    safe_name = file.filename or "upload.bin"
    dest = dest_dir / f"{uuid.uuid4().hex}_{safe_name}"
    with dest.open("wb") as out:
        shutil.copyfileobj(file.file, out)
    rel = f"{knowledge_id}/{dest.name}"
    record = KnowledgeFile(
        knowledge_id=knowledge_id,
        file_name=safe_name,
        file_path=rel,
        status=5,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return ok({"file_path": rel, "file_name": safe_name, "id": record.id})


@router.post("/knowledge/process")
def process_files(body: ProcessFiles, db: Session = Depends(get_db), ctx=Depends(require_workspace_editor)):
    kb = db.get(KnowledgeBase, body.knowledge_id)
    if not kb or kb.workspace_id != ctx.workspace_id:
        return fail(404, "Knowledge base not found")
    for item in body.file_list:
        fp = item.get("file_path")
        record = (
            db.query(KnowledgeFile)
            .filter(KnowledgeFile.knowledge_id == body.knowledge_id, KnowledgeFile.file_path == fp)
            .first()
        )
        if record:
            process_file_record(db, record, body.chunk_size, body.chunk_overlap)
    return ok(None)


@router.get("/knowledge/chunk")
def get_chunks(
    knowledge_id: int = Query(...),
    keyword: str = Query(""),
    page: int = Query(1),
    limit: int = Query(10),
    db: Session = Depends(get_db),
    ctx=Depends(get_workspace_ctx),
):
    kb = db.get(KnowledgeBase, knowledge_id)
    if not kb or kb.workspace_id != ctx.workspace_id:
        return fail(404, "Knowledge base not found")
    data, total = search_chunks(db, knowledge_id, keyword, page, limit)
    return ok({"data": data, "total": total})


@router.post("/knowledge/retry")
def retry_file():
    return ok(None)
