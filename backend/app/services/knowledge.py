import json
import re
from pathlib import Path

from pypdf import PdfReader
from sqlalchemy.orm import Session

from app.config import OPENAI_API_KEY, OPENAI_EMBEDDING_MODEL, UPLOAD_DIR
from app.database import KnowledgeBase, KnowledgeChunk, KnowledgeFile
from app.services.embeddings import embed_texts_sync, parse_embedding, rank_by_embedding
from app.services.vector_store import delete_by_file, milvus_enabled, search_vectors, upsert_vectors


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


def _embed_chunks(db: Session, kb: KnowledgeBase, chunk_rows: list[KnowledgeChunk]):
    if not OPENAI_API_KEY or not chunk_rows:
        return
    model = kb.model or OPENAI_EMBEDDING_MODEL
    batch_size = 32
    for i in range(0, len(chunk_rows), batch_size):
        batch = chunk_rows[i : i + batch_size]
        texts = [(c.text or "")[:8000] for c in batch]
        vectors = embed_texts_sync(texts, model)
        milvus_rows: list[tuple[int, int, int, list[float]]] = []
        for chunk, vec in zip(batch, vectors):
            chunk.embedding_json = json.dumps(vec)
            if milvus_enabled() and chunk.id:
                milvus_rows.append((chunk.id, chunk.knowledge_id, chunk.file_id, vec))
        if milvus_rows:
            upsert_vectors(milvus_rows)
    db.commit()


def process_file_record(db: Session, record: KnowledgeFile, chunk_size: int = 1000, chunk_overlap: int = 100):
    record.status = 1
    db.commit()
    try:
        path = UPLOAD_DIR / record.file_path
        text = extract_text(path)
        pieces = chunk_text(text, chunk_size, chunk_overlap)
        delete_by_file(record.id)
        db.query(KnowledgeChunk).filter(KnowledgeChunk.file_id == record.id).delete()
        chunk_rows: list[KnowledgeChunk] = []
        for i, piece in enumerate(pieces):
            row = KnowledgeChunk(
                knowledge_id=record.knowledge_id,
                file_id=record.id,
                chunk_index=i,
                text=piece,
            )
            db.add(row)
            chunk_rows.append(row)
        db.commit()
        for row in chunk_rows:
            db.refresh(row)
        kb = db.get(KnowledgeBase, record.knowledge_id)
        if kb and chunk_rows:
            _embed_chunks(db, kb, chunk_rows)
        record.status = 2 if pieces else 3
    except Exception:
        record.status = 3
    db.commit()


def _token_search(db: Session, knowledge_id: int, query: str, limit: int) -> list[dict]:
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
                "method": "keyword",
            }
        )
    return data


def _milvus_hits(db: Session, knowledge_id: int, query_vec: list[float], limit: int) -> list[dict]:
    hits = search_vectors(knowledge_id, query_vec, limit)
    if not hits:
        return []
    chunk_ids = [cid for cid, _ in hits]
    score_map = {cid: score for cid, score in hits}
    rows = (
        db.query(KnowledgeChunk, KnowledgeFile)
        .join(KnowledgeFile, KnowledgeChunk.file_id == KnowledgeFile.id)
        .filter(
            KnowledgeChunk.id.in_(chunk_ids),
            KnowledgeChunk.knowledge_id == knowledge_id,
            KnowledgeFile.status == 2,
        )
        .all()
    )
    data = []
    for chunk, file in rows:
        data.append(
            {
                "text": chunk.text,
                "chunk_index": chunk.chunk_index,
                "file_id": file.id,
                "file_name": file.file_name,
                "score": round(score_map.get(chunk.id, 0), 4),
                "method": "milvus",
            }
        )
    data.sort(key=lambda x: -x["score"])
    return data[:limit]


def _vector_search(db: Session, knowledge_id: int, query: str, limit: int, model: str) -> list[dict]:
    if not OPENAI_API_KEY:
        return []
    vectors = embed_texts_sync([query[:8000]], model)
    if not vectors:
        return []
    query_vec = vectors[0]

    if milvus_enabled():
        milvus_results = _milvus_hits(db, knowledge_id, query_vec, limit)
        if milvus_results:
            return milvus_results

    rows = (
        db.query(KnowledgeChunk, KnowledgeFile)
        .join(KnowledgeFile, KnowledgeChunk.file_id == KnowledgeFile.id)
        .filter(KnowledgeChunk.knowledge_id == knowledge_id, KnowledgeFile.status == 2)
        .all()
    )
    prepared = [(chunk, file, parse_embedding(chunk.embedding_json)) for chunk, file in rows]
    ranked = rank_by_embedding(prepared, query_vec, limit)
    data = []
    for score, chunk, file in ranked:
        data.append(
            {
                "text": chunk.text,
                "chunk_index": chunk.chunk_index,
                "file_id": file.id,
                "file_name": file.file_name,
                "score": round(score, 4),
                "method": "vector",
            }
        )
    return data


def search_chunks_semantic(db: Session, knowledge_id: int, query: str, limit: int = 5) -> list[dict]:
    if not query.strip():
        return []

    kb = db.get(KnowledgeBase, knowledge_id)
    model = (kb.model if kb else None) or OPENAI_EMBEDDING_MODEL

    vector_hits = _vector_search(db, knowledge_id, query.strip(), limit, model)
    if vector_hits:
        return vector_hits
    return _token_search(db, knowledge_id, query.strip(), limit)


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

    hits.sort(key=lambda h: h.get("score", 0), reverse=True)
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
