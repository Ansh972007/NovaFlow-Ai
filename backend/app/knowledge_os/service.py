"""KOS service — collections, folders, documents with tenant isolation."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.database import KnowledgeBase, KnowledgeFile, KnowledgeFolder, KnowledgeTag


def _safe_json(raw: str | None, default: Any) -> Any:
    try:
        return json.loads(raw or "")
    except (json.JSONDecodeError, TypeError):
        return default


def collection_dict(kb: KnowledgeBase, *, file_count: int = 0) -> dict:
    return {
        "id": kb.id,
        "name": kb.name,
        "description": kb.description,
        "model": kb.model,
        "workspace_id": kb.workspace_id,
        "organization_id": getattr(kb, "organization_id", None),
        "classification": getattr(kb, "classification", None) or "internal",
        "status": getattr(kb, "status", None) or "published",
        "tags": _safe_json(getattr(kb, "tags_json", None), []),
        "labels": _safe_json(getattr(kb, "labels_json", None), []),
        "aliases": _safe_json(getattr(kb, "aliases_json", None), []),
        "retention_policy": getattr(kb, "retention_policy", None) or "standard",
        "review_required": bool(getattr(kb, "review_required", 0)),
        "visibility": getattr(kb, "visibility", None) or "workspace",
        "owner_id": getattr(kb, "owner_id", None),
        "file_count": file_count,
        "create_time": kb.create_time.isoformat() if kb.create_time else None,
        "update_time": kb.update_time.isoformat() if kb.update_time else None,
    }


def document_dict(f: KnowledgeFile) -> dict:
    return {
        "id": f.id,
        "knowledge_id": f.knowledge_id,
        "file_name": f.file_name,
        "file_path": f.file_path,
        "status": f.status,
        "folder_id": getattr(f, "folder_id", None),
        "version_no": getattr(f, "version_no", None) or 1,
        "content_hash": getattr(f, "content_hash", None) or "",
        "document_type": getattr(f, "document_type", None) or "",
        "lifecycle_status": getattr(f, "lifecycle_status", None) or "published",
        "classification": getattr(f, "classification", None) or "internal",
        "metadata": _safe_json(getattr(f, "metadata_json", None), {}),
        "error_message": getattr(f, "error_message", None) or "",
        "update_time": f.update_time.isoformat() if f.update_time else None,
    }


def folder_dict(folder: KnowledgeFolder) -> dict:
    return {
        "id": folder.id,
        "knowledge_id": folder.knowledge_id,
        "parent_folder_id": folder.parent_folder_id,
        "name": folder.name,
        "path": folder.path,
        "labels": _safe_json(folder.labels_json, []),
        "create_time": folder.create_time.isoformat() if folder.create_time else None,
    }


def create_collection(
    db: Session,
    *,
    workspace_id: int,
    user_id: int,
    name: str,
    description: str = "",
    model: str = "text-embedding-3-small",
    organization_id: int | None = None,
    classification: str = "internal",
    tags: list | None = None,
    labels: list | None = None,
) -> KnowledgeBase:
    kb = KnowledgeBase(
        name=name.strip(),
        description=(description or "")[:500],
        model=model,
        user_id=user_id,
        workspace_id=workspace_id,
    )
    if hasattr(kb, "organization_id"):
        kb.organization_id = organization_id
    if hasattr(kb, "owner_id"):
        kb.owner_id = user_id
    if hasattr(kb, "created_by"):
        kb.created_by = user_id
    if hasattr(kb, "classification"):
        kb.classification = classification
    if hasattr(kb, "status"):
        kb.status = "published"
    if hasattr(kb, "tags_json") and tags:
        kb.tags_json = json.dumps(tags)
    if hasattr(kb, "labels_json") and labels:
        kb.labels_json = json.dumps(labels)
    db.add(kb)
    db.commit()
    db.refresh(kb)
    return kb


def get_collection(db: Session, collection_id: int, *, workspace_id: int) -> KnowledgeBase | None:
    kb = db.get(KnowledgeBase, collection_id)
    if not kb or kb.workspace_id != workspace_id:
        return None
    if getattr(kb, "deleted_at", None):
        return None
    return kb


def list_collections(
    db: Session,
    *,
    workspace_id: int,
    name: str = "",
    status: str = "",
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[KnowledgeBase], int]:
    q = db.query(KnowledgeBase).filter(KnowledgeBase.workspace_id == workspace_id)
    if hasattr(KnowledgeBase, "deleted_at"):
        q = q.filter(KnowledgeBase.deleted_at.is_(None))
    if name:
        q = q.filter(KnowledgeBase.name.contains(name))
    if status and hasattr(KnowledgeBase, "status"):
        q = q.filter(KnowledgeBase.status == status)
    total = q.count()
    rows = q.order_by(KnowledgeBase.update_time.desc()).offset(offset).limit(limit).all()
    return rows, total


def create_folder(
    db: Session,
    *,
    knowledge_id: int,
    workspace_id: int,
    name: str,
    parent_folder_id: str | None = None,
    organization_id: int | None = None,
    labels: list | None = None,
) -> KnowledgeFolder:
    path = name.strip()
    if parent_folder_id:
        parent = db.get(KnowledgeFolder, parent_folder_id)
        if parent and parent.knowledge_id == knowledge_id:
            path = f"{parent.path}/{name}".strip("/")
    folder = KnowledgeFolder(
        knowledge_id=knowledge_id,
        workspace_id=workspace_id,
        organization_id=organization_id,
        name=name.strip(),
        parent_folder_id=parent_folder_id,
        path=path,
        labels_json=json.dumps(labels or []),
    )
    db.add(folder)
    db.commit()
    db.refresh(folder)
    return folder


def list_folders(db: Session, *, knowledge_id: int, workspace_id: int) -> list[KnowledgeFolder]:
    return (
        db.query(KnowledgeFolder)
        .filter(KnowledgeFolder.knowledge_id == knowledge_id, KnowledgeFolder.workspace_id == workspace_id)
        .order_by(KnowledgeFolder.path.asc())
        .all()
    )


def list_documents(
    db: Session,
    *,
    knowledge_id: int,
    folder_id: str | None = None,
    limit: int = 100,
) -> list[KnowledgeFile]:
    q = db.query(KnowledgeFile).filter(KnowledgeFile.knowledge_id == knowledge_id)
    if folder_id and hasattr(KnowledgeFile, "folder_id"):
        q = q.filter(KnowledgeFile.folder_id == folder_id)
    return q.order_by(KnowledgeFile.update_time.desc()).limit(limit).all()


def add_tag(
    db: Session,
    *,
    workspace_id: int,
    label: str,
    knowledge_id: int | None = None,
    file_id: int | None = None,
) -> KnowledgeTag:
    tag = KnowledgeTag(
        workspace_id=workspace_id,
        knowledge_id=knowledge_id,
        file_id=file_id,
        label=label.strip().lower(),
    )
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return tag


def archive_collection(db: Session, kb: KnowledgeBase) -> None:
    if hasattr(kb, "legal_hold") and kb.legal_hold:
        raise ValueError("Collection under legal hold")
    if hasattr(kb, "status"):
        kb.status = "archived"
    if hasattr(kb, "archived_at"):
        kb.archived_at = datetime.utcnow()
    kb.update_time = datetime.utcnow()
    db.commit()


def restore_collection(db: Session, kb: KnowledgeBase) -> None:
    if hasattr(kb, "status"):
        kb.status = "published"
    if hasattr(kb, "archived_at"):
        kb.archived_at = None
    if hasattr(kb, "deleted_at"):
        kb.deleted_at = None
    kb.update_time = datetime.utcnow()
    db.commit()
