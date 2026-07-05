import re
from pathlib import Path

from pypdf import PdfReader
from sqlalchemy.orm import Session

from app.config import UPLOAD_DIR
from app.database import KnowledgeBase, KnowledgeChunk, KnowledgeFile


def extract_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".txt", ".md", ".csv"}:
        return path.read_text(encoding="utf-8", errors="ignore")
    if suffix == ".pdf":
        reader = PdfReader(str(path))
        parts = []
        for page in reader.pages:
            parts.append(page.extract_text() or "")
        return "\n".join(parts)
    return path.read_text(encoding="utf-8", errors="ignore")


def chunk_text(text: str, size: int = 1000, overlap: int = 100) -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = min(len(text), start + size)
        chunks.append(text[start:end])
        if end >= len(text):
            break
        start = max(start + 1, end - overlap)
    return chunks


def process_file_record(db: Session, record: KnowledgeFile, chunk_size: int = 1000, chunk_overlap: int = 100):
    record.status = 1
    db.commit()
    try:
        path = UPLOAD_DIR / record.file_path
        text = extract_text(path)
        pieces = chunk_text(text, chunk_size, chunk_overlap)
        db.query(KnowledgeChunk).filter(KnowledgeChunk.file_id == record.id).delete()
        for i, piece in enumerate(pieces):
            db.add(
                KnowledgeChunk(
                    knowledge_id=record.knowledge_id,
                    file_id=record.id,
                    chunk_index=i,
                    text=piece,
                )
            )
        record.status = 2 if pieces else 3
    except Exception:
        record.status = 3
    db.commit()


def search_chunks_semantic(db: Session, knowledge_id: int, query: str, limit: int = 5) -> list[dict]:
    q_tokens = set(re.findall(r"[a-z0-9]+", query.lower()))
    if not q_tokens:
        return []

    rows = (
        db.query(KnowledgeChunk, KnowledgeFile)
        .join(KnowledgeFile, KnowledgeChunk.file_id == KnowledgeFile.id)
        .filter(KnowledgeChunk.knowledge_id == knowledge_id, KnowledgeFile.status == 2)
        .all()
    )
    scored: list[tuple[float, KnowledgeChunk, KnowledgeFile]] = []
    for chunk, file in rows:
        text = chunk.text or ""
        c_tokens = set(re.findall(r"[a-z0-9]+", text.lower()))
        if not c_tokens:
            continue
        overlap = q_tokens & c_tokens
        if not overlap:
            continue
        score = len(overlap) / (len(q_tokens) ** 0.5)
        if any(len(t) > 4 for t in overlap):
            score += 0.5
        scored.append((score, chunk, file))

    scored.sort(key=lambda x: -x[0])
    data = []
    for score, chunk, file in scored[:limit]:
        data.append(
            {
                "text": chunk.text,
                "chunk_index": chunk.chunk_index,
                "file_id": file.id,
                "file_name": file.file_name,
                "score": round(score, 3),
            }
        )
    return data


def search_chunks(db: Session, knowledge_id: int, keyword: str, page: int, limit: int):
    q = (
        db.query(KnowledgeChunk, KnowledgeFile)
        .join(KnowledgeFile, KnowledgeChunk.file_id == KnowledgeFile.id)
        .filter(KnowledgeChunk.knowledge_id == knowledge_id)
    )
    if keyword:
        q = q.filter(KnowledgeChunk.text.contains(keyword))
    total = q.count()
    rows = q.offset((page - 1) * limit).limit(limit).all()
    data = []
    for chunk, file in rows:
        data.append(
            {
                "text": chunk.text,
                "chunk_index": chunk.chunk_index,
                "file_id": file.id,
                "file_name": file.file_name,
            }
        )
    return data, total


def get_assistant_knowledge_ids(db: Session, assistant_id: str) -> list[int]:
    from app.database import AssistantKnowledge

    rows = db.query(AssistantKnowledge.knowledge_id).filter(
        AssistantKnowledge.assistant_id == assistant_id
    ).all()
    return [r[0] for r in rows]


def set_assistant_knowledge(db: Session, assistant_id: str, knowledge_ids: list[int]):
    from app.database import AssistantKnowledge

    db.query(AssistantKnowledge).filter(AssistantKnowledge.assistant_id == assistant_id).delete()
    for kid in knowledge_ids:
        db.add(AssistantKnowledge(assistant_id=assistant_id, knowledge_id=kid))
    db.commit()


def rag_context_for_assistant(db: Session, assistant_id: str, query: str, limit: int = 5) -> str:
    kid_list = get_assistant_knowledge_ids(db, assistant_id)
    if not kid_list or not query.strip():
        return ""

    hits = []
    per_kb = max(2, limit // max(len(kid_list), 1))
    for kid in kid_list:
        chunks = search_chunks_semantic(db, kid, query.strip(), per_kb)
        hits.extend(chunks)

    if not hits:
        return ""

    parts = []
    for i, hit in enumerate(hits[:limit], 1):
        source = hit.get("file_name") or "document"
        text = (hit.get("text") or "")[:1200]
        parts.append(f"[{i}] ({source})\n{text}")

    return "\n\n".join(parts)


def kb_upload_dir(kb_id: int) -> Path:
    d = UPLOAD_DIR / str(kb_id)
    d.mkdir(parents=True, exist_ok=True)
    return d
