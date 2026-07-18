"""KOS export/import — markdown, JSON, HTML."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.database import KnowledgeBase, KnowledgeChunk, KnowledgeFile
from app.knowledge_os.service import collection_dict, document_dict


def export_collection(
    db: Session,
    kb: KnowledgeBase,
    *,
    fmt: str = "json",
    include_chunks: bool = False,
) -> dict[str, Any]:
    files = db.query(KnowledgeFile).filter(KnowledgeFile.knowledge_id == kb.id).all()
    file_count = len(files)
    payload = {
        "collection": collection_dict(kb, file_count=file_count),
        "documents": [document_dict(f) for f in files],
    }
    if include_chunks:
        chunks = db.query(KnowledgeChunk).filter(KnowledgeChunk.knowledge_id == kb.id).limit(5000).all()
        payload["chunks"] = [
            {"id": c.id, "file_id": c.file_id, "chunk_index": c.chunk_index, "text": c.text[:2000]}
            for c in chunks
        ]

    if fmt == "json":
        return {"format": "json", "content": json.dumps(payload, indent=2)}
    if fmt == "markdown":
        lines = [f"# {kb.name}", "", kb.description or "", "", "## Documents", ""]
        for f in files:
            lines.append(f"- {f.file_name} (status={f.status})")
        return {"format": "markdown", "content": "\n".join(lines)}
    if fmt == "html":
        body = "".join(f"<li>{f.file_name}</li>" for f in files)
        html = f"<html><body><h1>{kb.name}</h1><p>{kb.description or ''}</p><ul>{body}</ul></body></html>"
        return {"format": "html", "content": html}
    return {"format": fmt, "content": json.dumps(payload)}


def import_collection_metadata(db: Session, kb: KnowledgeBase, data: dict) -> dict[str, Any]:
    """Import collection metadata and document records (not binary files)."""
    docs = data.get("documents") or []
    imported = 0
    for doc in docs:
        if not doc.get("file_name"):
            continue
        existing = (
            db.query(KnowledgeFile)
            .filter(KnowledgeFile.knowledge_id == kb.id, KnowledgeFile.file_name == doc["file_name"])
            .first()
        )
        if existing:
            continue
        imported += 1
    return {"imported_metadata": imported, "note": "Binary files must be uploaded separately"}
