"""Enterprise Knowledge OS API."""

from __future__ import annotations

import json
import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.orm import Session

from app.config import UPLOAD_DIR
from app.database import KnowledgeBase, KnowledgeFile, KnowledgeSyncJob, get_db
from app.deps import get_workspace_ctx, require_permission, require_workspace_editor
from app.knowledge_os.curator import analyze_collection, workspace_analytics
from app.knowledge_os.export import export_collection, import_collection_metadata
from app.knowledge_os.graph import build_graph_for_file, get_entity_graph, search_entities
from app.knowledge_os.indexing import detect_duplicates, index_document, reindex_collection
from app.knowledge_os.ingestion import create_sync_job, ingest_uploaded_file, ingest_url_content, run_sync_job
from app.knowledge_os.retrieval import enterprise_retrieve
from app.knowledge_os.search import enterprise_search
from app.knowledge_os.security import scan_document_content
from app.knowledge_os.service import (
    add_tag,
    archive_collection,
    collection_dict,
    create_collection,
    create_folder,
    document_dict,
    folder_dict,
    get_collection,
    list_collections,
    list_documents,
    list_folders,
    restore_collection,
)
from app.knowledge_os.versioning import compare_versions, create_document_version, list_versions, restore_version
from app.schemas import fail, ok
from app.security.rbac import Permission
from app.services.knowledge import kb_upload_dir

router = APIRouter(tags=["Knowledge OS"])


@router.post("/kos/collections")
def api_create_collection(body: dict, db: Session = Depends(get_db), ctx=Depends(require_workspace_editor)):
    kb = create_collection(
        db,
        workspace_id=ctx.workspace_id,
        user_id=ctx.user.user_id,
        organization_id=ctx.organization_id,
        name=(body.get("name") or "Collection").strip(),
        description=body.get("description") or "",
        model=body.get("model") or "text-embedding-3-small",
        classification=body.get("classification") or "internal",
        tags=body.get("tags"),
        labels=body.get("labels"),
    )
    kb_upload_dir(kb.id)
    ctx.audit("kos.collection.create", resource_type="knowledge", resource_id=str(kb.id))
    return ok(collection_dict(kb))


@router.get("/kos/collections")
def api_list_collections(
    name: str = Query(""),
    status: str = Query(""),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    ctx=Depends(require_permission(Permission.ASSISTANT_READ)),
):
    rows, total = list_collections(db, workspace_id=ctx.workspace_id, name=name, status=status, limit=limit, offset=offset)
    data = []
    for kb in rows:
        file_count = db.query(KnowledgeFile).filter(KnowledgeFile.knowledge_id == kb.id).count()
        data.append(collection_dict(kb, file_count=file_count))
    return ok({"data": data, "total": total})


@router.get("/kos/collections/{collection_id}")
def api_get_collection(collection_id: int, db: Session = Depends(get_db), ctx=Depends(require_permission(Permission.ASSISTANT_READ))):
    kb = get_collection(db, collection_id, workspace_id=ctx.workspace_id)
    if not kb:
        return fail(404, "Collection not found")
    file_count = db.query(KnowledgeFile).filter(KnowledgeFile.knowledge_id == kb.id).count()
    return ok(collection_dict(kb, file_count=file_count))


@router.post("/kos/collections/{collection_id}/archive")
def api_archive_collection(collection_id: int, db: Session = Depends(get_db), ctx=Depends(require_workspace_editor)):
    kb = get_collection(db, collection_id, workspace_id=ctx.workspace_id)
    if not kb:
        return fail(404, "Collection not found")
    try:
        archive_collection(db, kb)
    except ValueError as exc:
        return fail(400, str(exc))
    ctx.audit("kos.collection.archive", resource_type="knowledge", resource_id=str(kb.id))
    return ok({"archived": collection_id})


@router.post("/kos/collections/{collection_id}/restore")
def api_restore_collection(collection_id: int, db: Session = Depends(get_db), ctx=Depends(require_workspace_editor)):
    kb = get_collection(db, collection_id, workspace_id=ctx.workspace_id)
    if not kb:
        return fail(404, "Collection not found")
    restore_collection(db, kb)
    return ok({"restored": collection_id})


@router.post("/kos/collections/{collection_id}/folders")
def api_create_folder(collection_id: int, body: dict, db: Session = Depends(get_db), ctx=Depends(require_workspace_editor)):
    kb = get_collection(db, collection_id, workspace_id=ctx.workspace_id)
    if not kb:
        return fail(404, "Collection not found")
    folder = create_folder(
        db,
        knowledge_id=collection_id,
        workspace_id=ctx.workspace_id,
        name=(body.get("name") or "Folder").strip(),
        parent_folder_id=body.get("parent_folder_id"),
        organization_id=ctx.organization_id,
        labels=body.get("labels"),
    )
    return ok(folder_dict(folder))


@router.get("/kos/collections/{collection_id}/folders")
def api_list_folders(collection_id: int, db: Session = Depends(get_db), ctx=Depends(require_permission(Permission.ASSISTANT_READ))):
    kb = get_collection(db, collection_id, workspace_id=ctx.workspace_id)
    if not kb:
        return fail(404, "Collection not found")
    return ok([folder_dict(f) for f in list_folders(db, knowledge_id=collection_id, workspace_id=ctx.workspace_id)])


@router.get("/kos/collections/{collection_id}/documents")
def api_list_documents(
    collection_id: int,
    folder_id: str | None = Query(None),
    db: Session = Depends(get_db),
    ctx=Depends(require_permission(Permission.ASSISTANT_READ)),
):
    kb = get_collection(db, collection_id, workspace_id=ctx.workspace_id)
    if not kb:
        return fail(404, "Collection not found")
    return ok([document_dict(f) for f in list_documents(db, knowledge_id=collection_id, folder_id=folder_id)])


@router.post("/kos/collections/{collection_id}/upload")
async def api_upload_document(
    collection_id: int,
    file: UploadFile = File(...),
    folder_id: str | None = Query(None),
    db: Session = Depends(get_db),
    ctx=Depends(require_workspace_editor),
):
    kb = get_collection(db, collection_id, workspace_id=ctx.workspace_id)
    if not kb:
        return fail(404, "Collection not found")
    kb_dir = UPLOAD_DIR / str(kb.id)
    kb_dir.mkdir(parents=True, exist_ok=True)
    safe_name = (file.filename or "upload.bin").replace("/", "_").replace("\\", "_")[:200]
    rel = f"{kb.id}/{uuid.uuid4().hex}_{safe_name}"
    dest = UPLOAD_DIR / rel
    with dest.open("wb") as out:
        shutil.copyfileobj(file.file, out)

    record = KnowledgeFile(knowledge_id=kb.id, file_name=safe_name, file_path=rel, status=5)
    db.add(record)
    db.commit()
    db.refresh(record)
    create_document_version(db, record, created_by=ctx.user.user_id, change_summary="Upload")
    result = ingest_uploaded_file(db, kb=kb, record=record, folder_id=folder_id)
    ctx.audit("kos.document.upload", resource_type="knowledge_file", resource_id=str(record.id))
    return ok({"document": document_dict(record), **result})


@router.post("/kos/collections/{collection_id}/reindex")
def api_reindex(collection_id: int, body: dict, db: Session = Depends(get_db), ctx=Depends(require_workspace_editor)):
    kb = get_collection(db, collection_id, workspace_id=ctx.workspace_id)
    if not kb:
        return fail(404, "Collection not found")
    result = reindex_collection(db, kb, partial=bool(body.get("partial")), file_ids=body.get("file_ids"))
    return ok(result)


@router.post("/kos/search")
def api_search(body: dict, db: Session = Depends(get_db), ctx=Depends(require_permission(Permission.ASSISTANT_READ))):
    result = enterprise_search(
        db,
        workspace_id=ctx.workspace_id,
        query=body.get("q") or body.get("query") or "",
        collection_id=body.get("collection_id"),
        collection_ids=body.get("collection_ids"),
        folder_id=body.get("folder_id"),
        owner_id=body.get("owner_id"),
        classification=body.get("classification"),
        document_type=body.get("document_type"),
        tag=body.get("tag"),
        date_from=body.get("date_from"),
        date_to=body.get("date_to"),
        limit=min(int(body.get("limit") or 20), 100),
    )
    return ok(result)


@router.post("/kos/retrieve")
def api_retrieve(body: dict, db: Session = Depends(get_db), ctx=Depends(require_permission(Permission.ASSISTANT_READ))):
    query = (body.get("q") or body.get("query") or "").strip()
    if not query:
        return fail(400, "query required")
    result = enterprise_retrieve(
        db,
        workspace_id=ctx.workspace_id,
        query=query,
        knowledge_id=body.get("collection_id") or body.get("knowledge_id"),
        assistant_id=body.get("assistant_id"),
        limit=min(int(body.get("limit") or 5), 20),
        trace_id=getattr(ctx, "trace_id", "") or "",
    )
    return ok(result)


@router.get("/kos/documents/{file_id}/versions")
def api_list_versions(file_id: int, db: Session = Depends(get_db), ctx=Depends(require_permission(Permission.ASSISTANT_READ))):
    record = db.get(KnowledgeFile, file_id)
    if not record:
        return fail(404, "Document not found")
    kb = get_collection(db, record.knowledge_id, workspace_id=ctx.workspace_id)
    if not kb:
        return fail(404, "Document not found")
    return ok(list_versions(db, file_id))


@router.post("/kos/versions/compare")
def api_compare_versions(body: dict, db: Session = Depends(get_db), ctx=Depends(require_permission(Permission.ASSISTANT_READ))):
    return ok(compare_versions(db, body.get("version_a_id"), body.get("version_b_id")))


@router.post("/kos/documents/{file_id}/restore-version")
def api_restore_version(file_id: int, body: dict, db: Session = Depends(get_db), ctx=Depends(require_workspace_editor)):
    record = db.get(KnowledgeFile, file_id)
    if not record:
        return fail(404, "Document not found")
    kb = get_collection(db, record.knowledge_id, workspace_id=ctx.workspace_id)
    if not kb:
        return fail(404, "Document not found")
    try:
        ver = restore_version(db, record, body.get("version_id"))
    except ValueError as exc:
        return fail(400, str(exc))
    index_document(db, record)
    return ok({"restored_version": ver.version_no})


@router.get("/kos/graph/entities")
def api_search_entities(
    q: str = Query(""),
    entity_type: str = Query(""),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    ctx=Depends(require_permission(Permission.ASSISTANT_READ)),
):
    return ok(search_entities(db, workspace_id=ctx.workspace_id, query=q, entity_type=entity_type, limit=limit))


@router.get("/kos/graph/entities/{entity_id}")
def api_entity_graph(entity_id: str, db: Session = Depends(get_db), ctx=Depends(require_permission(Permission.ASSISTANT_READ))):
    return ok(get_entity_graph(db, workspace_id=ctx.workspace_id, entity_id=entity_id))


@router.post("/kos/documents/{file_id}/build-graph")
def api_build_graph(file_id: int, db: Session = Depends(get_db), ctx=Depends(require_workspace_editor)):
    from app.services.knowledge import extract_text

    record = db.get(KnowledgeFile, file_id)
    if not record:
        return fail(404, "Document not found")
    kb = get_collection(db, record.knowledge_id, workspace_id=ctx.workspace_id)
    if not kb:
        return fail(404, "Document not found")
    path = UPLOAD_DIR / record.file_path
    text = extract_text(path, db)[:50000] if path.exists() else ""
    result = build_graph_for_file(db, file=record, workspace_id=ctx.workspace_id, text=text, organization_id=ctx.organization_id)
    return ok(result)


@router.get("/kos/collections/{collection_id}/curator")
def api_curator(collection_id: int, db: Session = Depends(get_db), ctx=Depends(require_permission(Permission.ASSISTANT_READ))):
    kb = get_collection(db, collection_id, workspace_id=ctx.workspace_id)
    if not kb:
        return fail(404, "Collection not found")
    return ok(analyze_collection(db, kb))


@router.get("/kos/analytics")
def api_analytics(db: Session = Depends(get_db), ctx=Depends(require_permission(Permission.ASSISTANT_READ))):
    return ok(workspace_analytics(db, workspace_id=ctx.workspace_id))


@router.post("/kos/collections/{collection_id}/sync")
def api_create_sync(collection_id: int, body: dict, db: Session = Depends(get_db), ctx=Depends(require_workspace_editor)):
    kb = get_collection(db, collection_id, workspace_id=ctx.workspace_id)
    if not kb:
        return fail(404, "Collection not found")
    job = create_sync_job(
        db,
        knowledge_id=collection_id,
        workspace_id=ctx.workspace_id,
        connector_type=body.get("connector_type") or "manual",
        config=body.get("config"),
    )
    return ok({"job_id": job.id, "status": job.status, "connector_type": job.connector_type})


@router.post("/kos/sync/{job_id}/run")
def api_run_sync(job_id: str, db: Session = Depends(get_db), ctx=Depends(require_workspace_editor)):
    job = db.get(KnowledgeSyncJob, job_id)
    if not job or job.workspace_id != ctx.workspace_id:
        return fail(404, "Sync job not found")
    try:
        result = run_sync_job(db, job)
    except Exception as exc:
        return fail(400, str(exc))
    return ok(result)


@router.post("/kos/collections/{collection_id}/tags")
def api_add_tag(collection_id: int, body: dict, db: Session = Depends(get_db), ctx=Depends(require_workspace_editor)):
    kb = get_collection(db, collection_id, workspace_id=ctx.workspace_id)
    if not kb:
        return fail(404, "Collection not found")
    tag = add_tag(db, workspace_id=ctx.workspace_id, label=body.get("label") or "untagged", knowledge_id=collection_id)
    return ok({"id": tag.id, "label": tag.label})


@router.get("/kos/collections/{collection_id}/export")
def api_export(
    collection_id: int,
    fmt: str = Query("json"),
    include_chunks: bool = Query(False),
    db: Session = Depends(get_db),
    ctx=Depends(require_permission(Permission.ASSISTANT_READ)),
):
    kb = get_collection(db, collection_id, workspace_id=ctx.workspace_id)
    if not kb:
        return fail(404, "Collection not found")
    return ok(export_collection(db, kb, fmt=fmt, include_chunks=include_chunks))


@router.post("/kos/collections/{collection_id}/import")
def api_import(collection_id: int, body: dict, db: Session = Depends(get_db), ctx=Depends(require_workspace_editor)):
    kb = get_collection(db, collection_id, workspace_id=ctx.workspace_id)
    if not kb:
        return fail(404, "Collection not found")
    return ok(import_collection_metadata(db, kb, body))


@router.post("/kos/scan")
def api_scan(body: dict, db: Session = Depends(get_db), ctx=Depends(require_workspace_editor)):
    text = body.get("text") or ""
    return ok(scan_document_content(text, classification=body.get("classification") or "internal"))


@router.get("/kos/connectors")
def api_connectors(ctx=Depends(get_workspace_ctx)):
    from app.knowledge_os.plugins import list_connectors

    return ok(list_connectors())
