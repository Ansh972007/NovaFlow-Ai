import re
import shutil
import uuid
from datetime import datetime
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, Depends, File, Query, UploadFile, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import EMBEDDING_MODELS, UPLOAD_DIR
from app.database import KnowledgeBase, KnowledgeFile, get_db
from app.deps import get_workspace_ctx, require_workspace_editor
from app.schemas import KnowledgeCreate, KnowledgeUrlIngest, ProcessFiles, fail, ok
from app.services.knowledge import (
    _embedding_ready,
    _llm_answer_enabled,
    _parse_file_meta,
    build_citations,
    build_extractive_digest,
    delete_knowledge_file,
    kb_file_stats,
    kb_status_from_stats,
    kb_upload_dir,
    mask_sensitive_text,
    process_file_record,
    retrieve_knowledge,
    search_chunks,
    search_chunks_semantic,
    should_mask_kb_content,
)
from app.services.doc_parse import is_supported_suffix, UNSUPPORTED_OFFICE

router = APIRouter(tags=["Knowledge"])

_VALID_CLASSIFICATIONS = {"public", "internal", "confidential", "restricted", "secret"}


def kb_dict(kb: KnowledgeBase, stats: dict | None = None) -> dict:
    status_label, state = kb_status_from_stats(stats)
    classification = (getattr(kb, "classification", None) or "internal").lower()
    return {
        "id": kb.id,
        "name": kb.name,
        "description": kb.description or "",
        "model": kb.model,
        "type": kb.type,
        "classification": classification,
        "create_time": kb.create_time.isoformat() if kb.create_time else None,
        "update_time": kb.update_time.isoformat() if kb.update_time else None,
        "file_count": int((stats or {}).get("total") or 0),
        "ready_count": int((stats or {}).get("ready") or 0),
        "status": status_label,
        "state": state,
    }


def file_dict(f: KnowledgeFile) -> dict:
    meta = _parse_file_meta(f)
    return {
        "id": f.id,
        "file_name": f.file_name,
        "file_path": f.file_path,
        "status": f.status,
        "error_message": getattr(f, "error_message", "") or "",
        "pii_count": int(meta.get("pii_count") or 0),
        "update_time": f.update_time.isoformat() if f.update_time else None,
    }


@router.get("/knowledge")
def list_knowledge(
    page_num: int = Query(1, alias="page_num"),
    page_size: int = Query(50, alias="page_size"),
    name: str = Query(""),
    db: Session = Depends(get_db),
    ctx=Depends(get_workspace_ctx),
):
    q = ctx.query(KnowledgeBase)
    if name:
        q = q.filter(KnowledgeBase.name.contains(name))
    total = q.count()
    rows = q.order_by(KnowledgeBase.update_time.desc()).offset((page_num - 1) * page_size).limit(page_size).all()
    stats_map = kb_file_stats(db, [k.id for k in rows])
    return ok({"data": [kb_dict(k, stats_map.get(k.id)) for k in rows], "total": total})


@router.get("/knowledge/embedding_param")
def embedding_param():
    return ok({"models": EMBEDDING_MODELS})


@router.post("/knowledge/create")
def create_knowledge(body: KnowledgeCreate, db: Session = Depends(get_db), ctx=Depends(require_workspace_editor)):
    classification = (body.classification or "internal").strip().lower()
    if classification not in _VALID_CLASSIFICATIONS:
        classification = "internal"
    kb = KnowledgeBase(
        name=body.name.strip(),
        description=body.description or "",
        model=body.model or EMBEDDING_MODELS[0],
        type=body.type,
        classification=classification,
    )
    ctx.attach(kb)
    db.add(kb)
    db.commit()
    db.refresh(kb)
    kb_upload_dir(kb.id)
    ctx.audit("knowledge.created", resource_type="knowledge", resource_id=str(kb.id))
    return ok(kb_dict(kb))


@router.get("/knowledge/file_list/{knowledge_id}")
def file_list(
    knowledge_id: int,
    page_num: int = Query(1),
    page_size: int = Query(50),
    db: Session = Depends(get_db),
    ctx=Depends(get_workspace_ctx),
):
    kb = ctx.fetch(KnowledgeBase, knowledge_id)
    if not kb:
        return fail(404, "Knowledge base not found")
    base_q = db.query(KnowledgeFile).filter(KnowledgeFile.knowledge_id == knowledge_id)
    total = base_q.count()
    rows = (
        base_q.order_by(KnowledgeFile.update_time.desc())
        .offset((page_num - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return ok({"data": [file_dict(f) for f in rows], "writeable": ctx.role != "viewer", "total": total})


@router.post("/knowledge/upload/{knowledge_id}")
async def upload_file(
    knowledge_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    ctx=Depends(require_workspace_editor),
):
    from app.security.files import FileSecurityError, validate_upload

    kb = ctx.fetch(KnowledgeBase, knowledge_id)
    if not kb:
        return fail(404, "Knowledge base not found")
    raw_name = file.filename or "upload.bin"
    suffix = ("." + raw_name.rsplit(".", 1)[-1].lower()) if "." in raw_name else ""
    if suffix in UNSUPPORTED_OFFICE:
        return fail(
            400,
            f"Legacy Office format {suffix} is not supported. Convert to .docx / .xlsx / .pptx and upload again.",
        )
    if suffix and not is_supported_suffix(suffix):
        return fail(
            400,
            f"Unsupported file type {suffix}. Accepted: pdf, docx, txt, md, csv, tsv, xlsx, pptx, html, json, images.",
        )
    content = await file.read()
    try:
        meta = validate_upload(filename=raw_name, content=content, content_type=file.content_type)
    except FileSecurityError as exc:
        return fail(400, str(exc))
    dest_dir = kb_upload_dir(knowledge_id)
    dest = dest_dir / meta["storage_name"]
    dest.write_bytes(content)
    rel = f"{knowledge_id}/{dest.name}"
    record = KnowledgeFile(
        knowledge_id=knowledge_id,
        file_name=meta["safe_name"],
        file_path=rel,
        status=5,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    ctx.audit(
        "knowledge.file.uploaded",
        resource_type="knowledge_file",
        resource_id=str(record.id),
        detail={"knowledge_id": knowledge_id, "file_name": meta["safe_name"]},
    )
    return ok({"file_path": rel, "file_name": meta["safe_name"], "id": record.id})


@router.delete("/knowledge/file/{file_id}")
def delete_file(
    file_id: int,
    db: Session = Depends(get_db),
    ctx=Depends(require_workspace_editor),
):
    record = db.get(KnowledgeFile, file_id)
    if not record:
        return fail(404, "File not found")
    kb = ctx.fetch(KnowledgeBase, record.knowledge_id)
    if not kb:
        return fail(404, "File not found")
    delete_knowledge_file(db, record)
    ctx.audit(
        "knowledge.file.deleted",
        resource_type="knowledge_file",
        resource_id=str(file_id),
        detail={"knowledge_id": kb.id, "file_name": record.file_name},
    )
    return ok({"deleted": True, "id": file_id})


@router.post("/knowledge/process")
def process_files(body: ProcessFiles, background_tasks: BackgroundTasks, db: Session = Depends(get_db), ctx=Depends(require_workspace_editor)):
    kb = ctx.fetch(KnowledgeBase, body.knowledge_id)
    if not kb:
        return fail(404, "Knowledge base not found")

    record_ids = []
    for item in body.file_list:
        fp = item.get("file_path")
        record = (
            db.query(KnowledgeFile)
            .filter(KnowledgeFile.knowledge_id == body.knowledge_id, KnowledgeFile.file_path == fp)
            .first()
        )
        if record:
            record_ids.append(record.id)

    if record_ids:
        from app.services.knowledge import process_file_records_bg

        background_tasks.add_task(process_file_records_bg, record_ids, body.chunk_size, body.chunk_overlap)

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
    kb = ctx.fetch(KnowledgeBase, knowledge_id)
    if not kb:
        return fail(404, "Knowledge base not found")
    data, total = search_chunks(db, knowledge_id, keyword, page, limit)
    return ok({"data": data, "total": total})


@router.get("/knowledge/search")
def semantic_search(
    knowledge_id: int = Query(...),
    q: str = Query(""),
    limit: int = Query(6, ge=1, le=20),
    db: Session = Depends(get_db),
    ctx=Depends(get_workspace_ctx),
):
    """Semantic (vector) search with keyword fallback — used by Knowledge Q&A preview."""
    kb = ctx.fetch(KnowledgeBase, knowledge_id)
    if not kb:
        return fail(404, "Knowledge base not found")
    query = (q or "").strip()
    if not query:
        return ok(
            {
                "data": [],
                "total": 0,
                "method": "none",
                "embedding_available": _embedding_ready(db),
                "llm_answer_available": _llm_answer_enabled(db),
            }
        )
    hits = search_chunks_semantic(db, knowledge_id, query, limit)
    method = hits[0].get("method") if hits else "none"
    mask = should_mask_kb_content(kb)
    if mask:
        for hit in hits:
            hit["text"] = mask_sensitive_text(hit.get("text") or "")
    return ok(
        {
            "data": hits,
            "total": len(hits),
            "method": method,
            "embedding_available": _embedding_ready(db),
            "llm_answer_available": _llm_answer_enabled(db),
        }
    )


@router.post("/knowledge/retrieve")
def knowledge_retrieve(
    body: dict,
    db: Session = Depends(get_db),
    ctx=Depends(get_workspace_ctx),
):
    knowledge_id = body.get("knowledge_id") or body.get("id")
    query = (body.get("q") or body.get("question") or body.get("query") or "").strip()
    limit = min(max(int(body.get("limit") or 5), 1), 10)
    if not knowledge_id:
        return fail(400, "knowledge_id required")
    if not query:
        return fail(400, "question required")

    kb = ctx.fetch(KnowledgeBase, int(knowledge_id))
    if not kb:
        return fail(404, "Knowledge base not found")

    result = retrieve_knowledge(db, int(knowledge_id), query, limit)
    if not result["data"]:
        result["extractive_digest"] = (
            "No matching passages found in this library. Try different keywords or upload more documents."
        )
    return ok(result)


@router.post("/knowledge/answer")
async def knowledge_answer(
    body: dict,
    db: Session = Depends(get_db),
    ctx=Depends(get_workspace_ctx),
):
    """Grounded Q&A over one knowledge base (retrieve + short cited answer)."""
    from app.runtime.context import runtime_from_platform
    from app.runtime.pipeline import AIRuntime

    knowledge_id = body.get("knowledge_id") or body.get("id")
    query = (body.get("q") or body.get("question") or body.get("query") or "").strip()
    limit = min(max(int(body.get("limit") or 5), 1), 10)
    if not knowledge_id:
        return fail(400, "knowledge_id required")
    if not query:
        return fail(400, "question required")

    kb = ctx.fetch(KnowledgeBase, int(knowledge_id))
    if not kb:
        return fail(404, "Knowledge base not found")

    hits = search_chunks_semantic(db, int(knowledge_id), query, limit)
    method = hits[0].get("method") if hits else "none"
    mask = should_mask_kb_content(kb)
    if mask:
        for hit in hits:
            hit["text"] = mask_sensitive_text(hit.get("text") or "")

    if not hits:
        return ok(
            {
                "answer": "No matching passages found in this library. Try different keywords or upload more documents.",
                "data": [],
                "total": 0,
                "method": method,
                "citations": [],
                "embedding_available": _embedding_ready(db),
                "llm_answer_available": _llm_answer_enabled(db),
                "extractive": True,
            }
        )

    citations = build_citations(hits, mask=mask)
    digest = build_extractive_digest(hits, query)
    if mask:
        digest = mask_sensitive_text(digest)

    if not _llm_answer_enabled(db):
        return ok(
            {
                "answer": digest,
                "data": hits,
                "total": len(hits),
                "method": method,
                "citations": citations,
                "embedding_available": _embedding_ready(db),
                "llm_answer_available": False,
                "extractive": True,
            }
        )

    system = (
        f"You answer questions using only the retrieved passages from knowledge base «{kb.name}». "
        "Lead with a direct answer, then 2–4 short supporting bullets. "
        "Cite sources as [n] when you rely on a passage. "
        "If the passages do not contain the answer, say what is missing — do not invent facts."
    )
    try:
        runtime = AIRuntime(runtime_from_platform(ctx))
        result = await runtime.knowledge_answer(
            int(knowledge_id),
            query,
            system_override=system,
            limit=limit,
        )
        answer = result.content
    except Exception:
        return ok(
            {
                "answer": digest,
                "data": hits,
                "total": len(hits),
                "method": method,
                "citations": citations,
                "embedding_available": _embedding_ready(db),
                "llm_answer_available": False,
                "extractive": True,
            }
        )

    return ok(
        {
            "answer": (answer or "").strip(),
            "data": hits,
            "total": len(hits),
            "method": method,
            "citations": citations,
            "metrics": result.metrics.to_dict(),
            "embedding_available": _embedding_ready(db),
            "llm_answer_available": True,
            "extractive": False,
        }
    )


@router.post("/knowledge/retry")
def retry_file(body: dict, background_tasks: BackgroundTasks, db: Session = Depends(get_db), ctx=Depends(require_workspace_editor)):
    file_id = body.get("file_id") or body.get("id")
    if not file_id:
        return fail(400, "file_id required")
    record = db.get(KnowledgeFile, int(file_id))
    if not record:
        return fail(404, "File not found")
    kb = ctx.fetch(KnowledgeBase, record.knowledge_id)
    if not kb:
        return fail(404, "File not found")

    from app.services.knowledge import process_file_records_bg

    background_tasks.add_task(
        process_file_records_bg,
        [record.id],
        int(body.get("chunk_size") or 1000),
        int(body.get("chunk_overlap") or 100),
    )
    return ok(
        {
            "id": record.id,
            "file_name": record.file_name,
            "status": record.status,
            "error_message": getattr(record, "error_message", "") or "",
        }
    )


def _url_to_filename(url: str) -> str:
    parsed = urlparse(url)
    path = (parsed.path or "").rstrip("/").split("/")[-1]
    if path and "." in path:
        return path[:120]
    host = (parsed.netloc or "page").replace(":", "_")
    return f"{host}.txt"[:120]


@router.post("/knowledge/ingest-url/{knowledge_id}")
async def ingest_url(
    knowledge_id: int,
    body: KnowledgeUrlIngest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    ctx=Depends(require_workspace_editor),
):
    kb = ctx.fetch(KnowledgeBase, knowledge_id)
    if not kb:
        return fail(404, "Knowledge base not found")
    from app.security.ssrf import SafeUrlError, assert_safe_url

    url = body.url.strip()
    try:
        url = assert_safe_url(url, allow_http=True)
    except SafeUrlError as exc:
        return fail(400, f"URL blocked by security policy: {exc}")
    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=False) as client:
            res = await client.get(url, headers={"User-Agent": "NovaFlow-KB-Ingest/1.0"})
            if res.is_redirect:
                return fail(400, "Redirects are blocked for security")
            res.raise_for_status()
            content_type = (res.headers.get("content-type") or "").lower()
            if "html" in content_type or "<html" in (res.text or "")[:200].lower():
                text = re.sub(r"<script[^>]*>[\s\S]*?</script>", " ", res.text or "", flags=re.I)
                text = re.sub(r"<style[^>]*>[\s\S]*?</style>", " ", text, flags=re.I)
                text = re.sub(r"<[^>]+>", " ", text)
                text = re.sub(r"\s+", " ", text).strip()
            else:
                text = (res.text or "").strip()
    except httpx.HTTPStatusError as exc:
        return fail(400, f"Fetch failed: HTTP {exc.response.status_code}")
    except Exception as exc:
        return fail(400, f"Fetch failed: {exc}")
    if not text:
        return fail(400, "No text content found at URL")
    text = text[:500_000]
    safe_name = _url_to_filename(url)
    dest_dir = kb_upload_dir(knowledge_id)
    dest = dest_dir / f"{uuid.uuid4().hex}_{safe_name}"
    header = f"Source: {url}\nFetched: {datetime.utcnow().isoformat()}Z\n\n"
    dest.write_text(header + text, encoding="utf-8")
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
    from app.services.knowledge import process_file_records_bg

    background_tasks.add_task(process_file_records_bg, [record.id], body.chunk_size, body.chunk_overlap)
    return ok({"id": record.id, "file_name": safe_name, "file_path": rel, "url": url})


@router.get("/knowledge/{knowledge_id}")
def get_knowledge(
    knowledge_id: int,
    db: Session = Depends(get_db),
    ctx=Depends(get_workspace_ctx),
):
    kb = ctx.fetch(KnowledgeBase, knowledge_id)
    if not kb:
        return fail(404, "Knowledge base not found")
    stats_map = kb_file_stats(db, [kb.id])
    return ok(kb_dict(kb, stats_map.get(kb.id)))


class ChunkInitBody(BaseModel):
    file_name: str
    file_size: int
    chunk_size: int
    total_chunks: int


@router.post("/knowledge/upload-chunk/init/{knowledge_id}")
def init_chunked_upload(
    knowledge_id: int,
    body: ChunkInitBody,
    db: Session = Depends(get_db),
    ctx=Depends(require_workspace_editor),
):
    kb = ctx.fetch(KnowledgeBase, knowledge_id)
    if not kb:
        return fail(404, "Knowledge base not found")

    from app.security.files import validate_upload_metadata, FileSecurityError

    try:
        meta = validate_upload_metadata(
            filename=body.file_name,
            size=body.file_size,
            head=b"",
            bypass_max_size=True,
        )
    except FileSecurityError as exc:
        return fail(400, str(exc))

    from app.security.files import safe_subdir, safe_upload_id

    upload_id = safe_upload_id(uuid.uuid4().hex)
    temp_dir = safe_subdir(UPLOAD_DIR, "temp", upload_id)
    temp_dir.mkdir(parents=True, exist_ok=True)

    import json

    meta_path = temp_dir / "meta.json"
    meta_path.write_text(
        json.dumps(
            {
                "knowledge_id": knowledge_id,
                "file_name": body.file_name,
                "file_size": body.file_size,
                "chunk_size": body.chunk_size,
                "total_chunks": body.total_chunks,
                "safe_name": meta["safe_name"],
                "storage_name": meta["storage_name"],
            }
        )
    )

    return ok({"upload_id": upload_id, "uploaded_chunks": []})


@router.post("/knowledge/upload-chunk/complete/{upload_id}")
def complete_chunked_upload(
    upload_id: str,
    db: Session = Depends(get_db),
    ctx=Depends(require_workspace_editor),
):
    from app.security.files import FileSecurityError, safe_subdir, safe_upload_id

    try:
        uid = safe_upload_id(upload_id)
        temp_dir = safe_subdir(UPLOAD_DIR, "temp", uid)
    except FileSecurityError as exc:
        return fail(400, str(exc))
    if not temp_dir.exists():
        return fail(404, "Upload session not found")

    import json

    meta_path = temp_dir / "meta.json"
    if not meta_path.exists():
        return fail(400, "Upload session metadata missing")

    meta = json.loads(meta_path.read_text())
    knowledge_id = meta["knowledge_id"]
    total_chunks = meta["total_chunks"]
    safe_name = meta["safe_name"]
    storage_name = meta["storage_name"]

    kb = ctx.fetch(KnowledgeBase, knowledge_id)
    if not kb:
        return fail(404, "Knowledge base not found")

    for idx in range(total_chunks):
        if not (temp_dir / f"chunk_{idx}").exists():
            return fail(400, f"Missing chunk index {idx}")

    dest_dir = kb_upload_dir(knowledge_id)
    dest = dest_dir / storage_name

    try:
        with open(dest, "wb") as outfile:
            for idx in range(total_chunks):
                chunk_file = temp_dir / f"chunk_{idx}"
                with open(chunk_file, "rb") as infile:
                    outfile.write(infile.read())
    except Exception as exc:
        if dest.exists():
            dest.unlink()
        return fail(500, f"Merge failed: {exc}")

    from app.security.files import validate_upload_metadata, FileSecurityError

    try:
        with open(dest, "rb") as infile:
            head = infile.read(16)
        validate_upload_metadata(
            filename=meta["file_name"],
            size=meta["file_size"],
            head=head,
            bypass_max_size=True,
        )
    except FileSecurityError as exc:
        if dest.exists():
            dest.unlink()
        return fail(400, f"Security check failed: {exc}")

    shutil.rmtree(temp_dir, ignore_errors=True)

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


@router.post("/knowledge/upload-chunk/{upload_id}/{chunk_index}")
async def upload_chunk(
    upload_id: str,
    chunk_index: int,
    file: UploadFile = File(...),
    ctx=Depends(require_workspace_editor),
):
    from app.security.files import FileSecurityError, safe_subdir, safe_upload_id

    try:
        uid = safe_upload_id(upload_id)
        temp_dir = safe_subdir(UPLOAD_DIR, "temp", uid)
    except FileSecurityError as exc:
        return fail(400, str(exc))
    if not temp_dir.exists():
        return fail(404, "Upload session not found")

    chunk_path = temp_dir / f"chunk_{int(chunk_index)}"
    content = await file.read()
    chunk_path.write_bytes(content)

    return ok({"chunk_index": chunk_index, "uploaded": True})
