"""Conversation attachment upload + extraction helpers."""

from __future__ import annotations

import json
import logging
import re
import threading
import uuid
from pathlib import Path

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config import UPLOAD_DIR
from app.conversation.service import get_conversation
from app.database import ConversationAttachment
from app.schemas import fail, ok
from app.security.config import MAX_CHAT_UPLOAD_BYTES, SYNC_EXTRACT_MAX_BYTES
from app.security.files import FileSecurityError, validate_upload, validate_upload_metadata
from app.services.knowledge import extract_text

logger = logging.getLogger(__name__)

# Image / binary types — skip full text extract
_SKIP_EXTRACT_EXT = {".png", ".jpg", ".jpeg", ".webp", ".gif"}


class ConversationChunkInitBody(BaseModel):
    file_name: str = Field(min_length=1, max_length=255)
    file_size: int = Field(gt=0)
    chunk_size: int = Field(gt=0)
    total_chunks: int = Field(gt=0)


def _conv_upload_root(conversation_id: str) -> Path:
    from app.security.files import safe_subdir, safe_upload_id

    cid = safe_upload_id(conversation_id) if re.fullmatch(r"[a-fA-F0-9\-]{8,64}", conversation_id or "") else None
    if not cid:
        # conversation ids are uuid hex — reject traversal
        from app.security.files import FileSecurityError

        raise FileSecurityError("Invalid conversation id")
    root = safe_subdir(UPLOAD_DIR, "conversations", cid)
    root.mkdir(parents=True, exist_ok=True)
    return root


def _attach_temp_root(upload_id: str) -> Path:
    from app.security.files import safe_subdir, safe_upload_id

    uid = safe_upload_id(upload_id)
    root = safe_subdir(UPLOAD_DIR, "conversations", "temp", uid)
    root.mkdir(parents=True, exist_ok=True)
    return root


def _save_attachment_record(
    db: Session,
    *,
    conversation_id: str,
    workspace_id: int,
    file_name: str,
    mime_type: str,
    size_bytes: int,
    storage_key: str,
) -> ConversationAttachment:
    row = ConversationAttachment(
        id=uuid.uuid4().hex,
        conversation_id=conversation_id,
        workspace_id=workspace_id,
        file_name=file_name,
        mime_type=(mime_type or "")[:120],
        size_bytes=int(size_bytes or 0),
        storage_key=storage_key,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _should_sync_extract(path: Path, size_bytes: int) -> bool:
    ext = path.suffix.lower()
    if ext in _SKIP_EXTRACT_EXT:
        return False
    return int(size_bytes or 0) <= int(SYNC_EXTRACT_MAX_BYTES)


def _extract_and_cache_text(path: Path, db: Session | None = None) -> str:
    try:
        text = (extract_text(path, db=db) or "").strip()
    except Exception:
        text = ""
    if text:
        sidecar = path.with_suffix(path.suffix + ".txt")
        try:
            sidecar.write_text(text[:200000], encoding="utf-8")
        except Exception:
            pass
    return text


def _extract_attachment_bg(storage_key: str) -> None:
    """Background text extract for large chat attachments (new DB session)."""
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        path = UPLOAD_DIR / storage_key
        if not path.exists():
            return
        _extract_and_cache_text(path, db)
    except Exception as exc:  # noqa: BLE001
        logger.warning("bg extract failed for %s: %s", storage_key, exc)
    finally:
        db.close()


def enqueue_attachment_extract(storage_key: str) -> None:
    t = threading.Thread(target=_extract_attachment_bg, args=(storage_key,), daemon=True)
    t.start()


def upload_single_attachment(
    *,
    db: Session,
    workspace_id: int,
    conversation_id: str,
    filename: str,
    content: bytes,
    content_type: str | None = None,
) -> dict:
    conv = get_conversation(db, conversation_id, workspace_id=workspace_id)
    if not conv:
        return fail(404, "Conversation not found")
    try:
        meta = validate_upload(filename=filename, content=content, content_type=content_type)
    except FileSecurityError as exc:
        return fail(400, str(exc))

    root = _conv_upload_root(conversation_id)
    dest = root / meta["storage_name"]
    dest.write_bytes(content)
    size = int(meta["size"])
    indexing_status = "ready"
    extracted = ""
    if _should_sync_extract(dest, size):
        extracted = _extract_and_cache_text(dest, db)
        indexing_status = "extracted" if extracted else "ready"
    else:
        indexing_status = "pending"
        enqueue_attachment_extract(str(dest.relative_to(UPLOAD_DIR)).replace("\\", "/"))

    row = _save_attachment_record(
        db,
        conversation_id=conversation_id,
        workspace_id=workspace_id,
        file_name=meta["safe_name"],
        mime_type=content_type or "",
        size_bytes=size,
        storage_key=str(dest.relative_to(UPLOAD_DIR)).replace("\\", "/"),
    )
    return ok(
        {
            "attachment_id": row.id,
            "file_name": row.file_name,
            "mime_type": row.mime_type,
            "size_bytes": row.size_bytes,
            "has_extracted_text": bool(extracted),
            "preview_text": extracted[:4000] if extracted else "",
            "indexing_status": indexing_status,
        }
    )


def init_chunked_attachment(
    *,
    db: Session,
    workspace_id: int,
    conversation_id: str,
    body: ConversationChunkInitBody,
) -> dict:
    conv = get_conversation(db, conversation_id, workspace_id=workspace_id)
    if not conv:
        return fail(404, "Conversation not found")
    if body.file_size > MAX_CHAT_UPLOAD_BYTES:
        return fail(
            400,
            f"File exceeds chat upload limit of {MAX_CHAT_UPLOAD_BYTES} bytes "
            f"({MAX_CHAT_UPLOAD_BYTES // (1024 * 1024)} MB). Use Knowledge for larger corpora.",
        )
    try:
        meta = validate_upload_metadata(
            filename=body.file_name,
            size=body.file_size,
            head=b"",
            max_bytes=MAX_CHAT_UPLOAD_BYTES,
        )
    except FileSecurityError as exc:
        return fail(400, str(exc))

    upload_id = uuid.uuid4().hex
    temp_dir = _attach_temp_root(upload_id)
    (temp_dir / "meta.json").write_text(
        json.dumps(
            {
                "conversation_id": conversation_id,
                "workspace_id": workspace_id,
                "file_name": body.file_name,
                "file_size": body.file_size,
                "chunk_size": body.chunk_size,
                "total_chunks": body.total_chunks,
                "safe_name": meta["safe_name"],
                "storage_name": meta["storage_name"],
            }
        ),
        encoding="utf-8",
    )
    return ok(
        {
            "upload_id": upload_id,
            "uploaded_chunks": [],
            "max_bytes": MAX_CHAT_UPLOAD_BYTES,
        }
    )


def save_chunk(*, upload_id: str, chunk_index: int, content: bytes) -> dict:
    try:
        temp_dir = _attach_temp_root(upload_id)
    except FileSecurityError as exc:
        return fail(400, str(exc))
    if not temp_dir.exists():
        return fail(404, "Upload session not found")
    (temp_dir / f"chunk_{int(chunk_index)}").write_bytes(content)
    return ok({"chunk_index": chunk_index, "uploaded": True})


def complete_chunked_attachment(*, db: Session, workspace_id: int, upload_id: str) -> dict:
    try:
        temp_dir = _attach_temp_root(upload_id)
    except FileSecurityError as exc:
        return fail(400, str(exc))
    if not temp_dir.exists():
        return fail(404, "Upload session not found")
    meta_path = temp_dir / "meta.json"
    if not meta_path.exists():
        return fail(400, "Upload session metadata missing")

    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    conversation_id = str(meta.get("conversation_id") or "")
    total_chunks = int(meta.get("total_chunks") or 0)
    file_size = int(meta.get("file_size") or 0)
    if total_chunks <= 0:
        return fail(400, "Invalid upload metadata")
    if file_size > MAX_CHAT_UPLOAD_BYTES:
        return fail(400, f"File exceeds chat upload limit of {MAX_CHAT_UPLOAD_BYTES} bytes")
    conv = get_conversation(db, conversation_id, workspace_id=workspace_id)
    if not conv:
        return fail(404, "Conversation not found")
    for idx in range(total_chunks):
        if not (temp_dir / f"chunk_{idx}").exists():
            return fail(400, f"Missing chunk index {idx}")

    root = _conv_upload_root(conversation_id)
    dest = root / meta["storage_name"]
    try:
        with open(dest, "wb") as out:
            for idx in range(total_chunks):
                chunk_path = temp_dir / f"chunk_{idx}"
                with open(chunk_path, "rb") as inp:
                    while True:
                        buf = inp.read(1024 * 1024)
                        if not buf:
                            break
                        out.write(buf)
    except Exception as exc:
        if dest.exists():
            dest.unlink(missing_ok=True)
        return fail(500, f"Merge failed: {exc}")

    try:
        with open(dest, "rb") as f:
            head = f.read(16)
        validate_upload_metadata(
            filename=meta["file_name"],
            size=file_size,
            head=head,
            max_bytes=MAX_CHAT_UPLOAD_BYTES,
        )
    except FileSecurityError as exc:
        dest.unlink(missing_ok=True)
        return fail(400, str(exc))

    storage_key = str(dest.relative_to(UPLOAD_DIR)).replace("\\", "/")
    extracted = ""
    indexing_status = "ready"
    if _should_sync_extract(dest, file_size):
        extracted = _extract_and_cache_text(dest, db)
        indexing_status = "extracted" if extracted else "ready"
    else:
        indexing_status = "pending"
        enqueue_attachment_extract(storage_key)

    row = _save_attachment_record(
        db,
        conversation_id=conversation_id,
        workspace_id=workspace_id,
        file_name=meta["safe_name"],
        mime_type="",
        size_bytes=file_size,
        storage_key=storage_key,
    )
    try:
        for p in temp_dir.glob("chunk_*"):
            p.unlink(missing_ok=True)
        meta_path.unlink(missing_ok=True)
        temp_dir.rmdir()
    except Exception:
        pass
    return ok(
        {
            "attachment_id": row.id,
            "file_name": row.file_name,
            "size_bytes": row.size_bytes,
            "has_extracted_text": bool(extracted),
            "preview_text": extracted[:4000] if extracted else "",
            "indexing_status": indexing_status,
        }
    )


def list_attachments(db: Session, *, conversation_id: str, workspace_id: int) -> dict:
    conv = get_conversation(db, conversation_id, workspace_id=workspace_id)
    if not conv:
        return fail(404, "Conversation not found")
    rows = (
        db.query(ConversationAttachment)
        .filter(
            ConversationAttachment.conversation_id == conversation_id,
            ConversationAttachment.workspace_id == workspace_id,
            ConversationAttachment.deleted_at.is_(None),
        )
        .order_by(ConversationAttachment.create_time.asc())
        .all()
    )
    return ok(
        [
            {
                "id": r.id,
                "file_name": r.file_name,
                "mime_type": r.mime_type,
                "size_bytes": r.size_bytes,
                "storage_key": r.storage_key,
                "create_time": r.create_time.isoformat() if r.create_time else None,
            }
            for r in rows
        ]
    )
