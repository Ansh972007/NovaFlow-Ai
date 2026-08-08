import json
import math
import os
import re
from pathlib import Path

from pypdf import PdfReader
from sqlalchemy.orm import Session

from app.config import OPENAI_EMBEDDING_MODEL, UPLOAD_DIR
from app.database import KnowledgeBase, KnowledgeChunk, KnowledgeFile
from app.services.embeddings import embed_texts_sync, parse_embedding, rank_by_embedding
from app.services.vector_store import delete_by_file, milvus_enabled, search_vectors, upsert_vectors


def _embedding_ready(db: Session | None) -> bool:
    """True when Settings vault or env has an API key usable for embeddings."""
    from app.services.workspace_settings import get_chat_config

    cfg = get_chat_config(db)
    if not (cfg.get("api_key") or "").strip():
        return False
    # Anthropic cannot embed with the OpenAI embeddings endpoint
    if cfg.get("provider_type") == "anthropic":
        return False
    return True


def _llm_answer_enabled(db: Session | None) -> bool:
    flag = os.environ.get("KNOWLEDGE_LLM_ANSWER", "").strip().lower()
    if flag in ("0", "false", "no"):
        return False
    from app.services.workspace_settings import get_chat_config

    cfg = get_chat_config(db)
    if not (cfg.get("api_key") or "").strip():
        return False
    provider = (cfg.get("provider_type") or "").strip().lower()
    return provider not in ("none", "")


def _parse_file_meta(record: KnowledgeFile) -> dict:
    raw = getattr(record, "metadata_json", None) or "{}"
    try:
        return json.loads(raw) if raw else {}
    except (json.JSONDecodeError, TypeError):
        return {}


def _set_file_meta(record: KnowledgeFile, patch: dict) -> None:
    meta = _parse_file_meta(record)
    meta.update(patch)
    record.metadata_json = json.dumps(meta)


def mask_sensitive_text(text: str) -> str:
    from app.knowledge_os.security import PII_PATTERNS

    out = text or ""
    for pattern in PII_PATTERNS.values():
        out = pattern.sub(lambda m: "█" * min(len(m.group(0)), 12), out)
    return out


def build_extractive_digest(hits: list[dict], query: str = "") -> str:
    if not hits:
        return ""
    q_tokens = set(_tokenize(query))
    lines: list[str] = []
    for i, hit in enumerate(hits, 1):
        src = hit.get("file_name") or "document"
        text = (hit.get("text") or "").strip()
        snippet = text[:500]
        if q_tokens and text:
            sentences = re.split(r"(?<=[.!?])\s+", text)
            best = snippet
            best_score = -1
            for sent in sentences:
                st = set(_tokenize(sent))
                overlap = len(q_tokens & st)
                if overlap > best_score:
                    best_score = overlap
                    best = sent
            snippet = best[:500]
        snippet = snippet + ("…" if len(text) > len(snippet) else "")
        lines.append(f"[{i}] {src}: {snippet}")
    return "\n\n".join(lines)


def build_citations(hits: list[dict], mask: bool = False) -> list[dict]:
    citations = []
    for i, hit in enumerate(hits, 1):
        src = hit.get("file_name") or "document"
        text = (hit.get("text") or "").strip()[:1000]
        preview = text[:240] + ("…" if len(text) > 240 else "")
        if mask:
            preview = mask_sensitive_text(preview)
        citations.append(
            {
                "n": i,
                "file_name": src,
                "score": hit.get("score"),
                "method": hit.get("method"),
                "preview": preview,
            }
        )
    return citations


def kb_file_stats(db: Session, knowledge_ids: list[int]) -> dict[int, dict]:
    if not knowledge_ids:
        return {}
    from sqlalchemy import func

    rows = (
        db.query(KnowledgeFile.knowledge_id, KnowledgeFile.status, func.count(KnowledgeFile.id))
        .filter(KnowledgeFile.knowledge_id.in_(knowledge_ids))
        .group_by(KnowledgeFile.knowledge_id, KnowledgeFile.status)
        .all()
    )
    stats: dict[int, dict] = {}
    for kid, status, cnt in rows:
        bucket = stats.setdefault(kid, {"total": 0, "ready": 0, "indexing": 0})
        bucket["total"] += int(cnt)
        if status == 2:
            bucket["ready"] += int(cnt)
        elif status in (1, 4, 5):
            bucket["indexing"] += int(cnt)
    return stats


def kb_status_from_stats(stats: dict | None) -> tuple[str, int]:
    ready = int((stats or {}).get("ready") or 0)
    indexing = int((stats or {}).get("indexing") or 0)
    if ready > 0 and indexing == 0:
        return "ready", 1
    if indexing > 0:
        return "indexing", 0
    return "empty", 0


def should_mask_kb_content(kb: KnowledgeBase | None) -> bool:
    from app.knowledge_os.security import classification_rank

    level = (getattr(kb, "classification", None) or "internal").lower()
    return classification_rank(level) >= classification_rank("confidential")


def retrieve_knowledge(
    db: Session,
    knowledge_id: int,
    query: str,
    limit: int = 5,
) -> dict:
    hits = search_chunks_semantic(db, knowledge_id, query, limit)
    method = hits[0].get("method") if hits else "none"
    kb = db.get(KnowledgeBase, knowledge_id)
    mask = should_mask_kb_content(kb)
    digest = build_extractive_digest(hits, query)
    if mask:
        digest = mask_sensitive_text(digest)
    for hit in hits:
        if mask:
            hit["text"] = mask_sensitive_text(hit.get("text") or "")
    return {
        "data": hits,
        "total": len(hits),
        "method": method,
        "extractive_digest": digest,
        "citations": build_citations(hits, mask=mask),
        "embedding_available": _embedding_ready(db),
        "llm_answer_available": _llm_answer_enabled(db),
    }


def delete_knowledge_file(db: Session, record: KnowledgeFile) -> None:
    delete_by_file(record.id)
    db.query(KnowledgeChunk).filter(KnowledgeChunk.file_id == record.id).delete()
    path = UPLOAD_DIR / record.file_path
    if path.exists():
        path.unlink()
    db.delete(record)
    db.commit()


def delete_knowledge_base(db: Session, kb: KnowledgeBase) -> None:
    from app.database import AssistantKnowledge
    files = db.query(KnowledgeFile).filter(KnowledgeFile.knowledge_id == kb.id).all()
    for f in files:
        delete_knowledge_file(db, f)
    db.query(AssistantKnowledge).filter(AssistantKnowledge.knowledge_id == kb.id).delete()
    db.delete(kb)
    db.commit()
    """True when Settings vault or env has an API key usable for embeddings."""
    from app.services.workspace_settings import get_chat_config

    cfg = get_chat_config(db)
    if not (cfg.get("api_key") or "").strip():
        return False
    # Anthropic cannot embed with the OpenAI embeddings endpoint
    if cfg.get("provider_type") == "anthropic":
        return False
    return True


def extract_text(path: Path, db: Session | None = None) -> str:
    suffix = path.suffix.lower()
    if suffix in {".txt", ".md"}:
        return path.read_text(encoding="utf-8", errors="ignore")
    if suffix in {".csv", ".tsv", ".docx", ".html", ".htm", ".json", ".xlsx", ".xlsm", ".pptx"}:
        from app.services.doc_parse import extract_document

        return extract_document(path)
    if suffix == ".pdf":
        reader = PdfReader(str(path))
        parts = []
        for page in reader.pages:
            parts.append(page.extract_text() or "")
        return "\n".join(parts)
    if suffix in {".doc", ".ppt", ".xls"}:
        from app.services.doc_parse import extract_document

        return extract_document(path)

    from app.services.ocr import extract_image_text, is_image_path

    if is_image_path(path):
        api_key = ""
        base_url = ""
        model = ""
        if db is not None:
            try:
                from app.services.llm_providers import get_active_provider_row, resolve_api_key
                from app.services.workspace_settings import get_chat_config

                row = get_active_provider_row(db)
                api_key = resolve_api_key(row) or ""
                cfg = get_chat_config(db)
                base_url = cfg.get("base_url") or ""
                model = cfg.get("model") or ""
            except Exception:
                pass
        return extract_image_text(path, api_key=api_key or None, base_url=base_url or None, model=model or None)

    from app.services.doc_parse import is_supported_suffix

    if not is_supported_suffix(suffix):
        raise ValueError(
            f"Unsupported file type '{suffix or 'unknown'}'. "
            "Accepted: pdf, docx, txt, md, csv, tsv, xlsx, pptx, html, json, and common images."
        )
    return path.read_text(encoding="utf-8", errors="ignore")


def chunk_text(text: str, size: int = 1000, overlap: int = 100) -> list[str]:
    """Sentence-aware sliding windows; falls back to char windows when needed."""
    text = re.sub(r"\s+", " ", (text or "")).strip()
    if not text:
        return []

    # Prefer splitting on sentence boundaries for cleaner RAG passages
    sentences = re.split(r"(?<=[.!?])\s+", text)
    if len(sentences) <= 1:
        sentences = [text]

    chunks: list[str] = []
    buf = ""
    for sent in sentences:
        candidate = f"{buf} {sent}".strip() if buf else sent
        if len(candidate) <= size:
            buf = candidate
            continue
        if buf:
            chunks.append(buf)
        if len(sent) <= size:
            # Overlap: keep a trailing slice of the previous chunk
            if chunks and overlap > 0:
                tail = chunks[-1][-overlap:]
                buf = f"{tail} {sent}".strip()
                if len(buf) > size:
                    buf = sent
            else:
                buf = sent
        else:
            # Long sentence — hard-split with overlap
            start = 0
            while start < len(sent):
                end = min(len(sent), start + size)
                chunks.append(sent[start:end])
                if end >= len(sent):
                    break
                start = max(start + 1, end - overlap)
            buf = ""
    if buf:
        chunks.append(buf)
    return chunks


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", (text or "").lower())


def _embed_chunks(db: Session, kb: KnowledgeBase, chunk_rows: list[KnowledgeChunk]):
    if not chunk_rows or not _embedding_ready(db):
        return
    from app.services.workspace_settings import get_chat_config

    cfg = get_chat_config(db)
    model = kb.model or cfg.get("embedding_model") or OPENAI_EMBEDDING_MODEL
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
    if hasattr(record, "error_message"):
        record.error_message = ""
    db.commit()
    try:
        path = UPLOAD_DIR / record.file_path
        if not path.exists():
            raise FileNotFoundError(f"Uploaded file missing on disk: {record.file_path}")
        text = extract_text(path, db)
        kb = db.get(KnowledgeBase, record.knowledge_id)
        kb_class = (getattr(kb, "classification", None) or "internal") if kb else "internal"
        from app.knowledge_os.security import scan_document_content

        scan = scan_document_content(text[:50000], classification=kb_class)
        _set_file_meta(
            record,
            {
                "pii_count": scan.get("pii_count", 0),
                "pii_findings": scan.get("pii_findings", [])[:5],
            },
        )
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
        if pieces:
            record.status = 2
            if hasattr(record, "error_message"):
                record.error_message = ""
        else:
            record.status = 3
            if hasattr(record, "error_message"):
                record.error_message = "No extractable text found in file"
    except Exception as exc:
        record.status = 3
        if hasattr(record, "error_message"):
            record.error_message = str(exc)[:1000]
    db.commit()


def _token_search(db: Session, knowledge_id: int, query: str, limit: int) -> list[dict]:
    """Lightweight BM25-ish keyword ranking over chunk tokens (no external deps)."""
    q_tokens = _tokenize(query)
    if not q_tokens:
        return []
    q_set = set(q_tokens)
    q_tf: dict[str, int] = {}
    for t in q_tokens:
        q_tf[t] = q_tf.get(t, 0) + 1

    rows = (
        db.query(KnowledgeChunk, KnowledgeFile)
        .join(KnowledgeFile, KnowledgeChunk.file_id == KnowledgeFile.id)
        .filter(KnowledgeChunk.knowledge_id == knowledge_id, KnowledgeFile.status == 2)
        .all()
    )
    if not rows:
        return []

    # Document frequency for IDF
    df: dict[str, int] = {}
    docs: list[tuple[KnowledgeChunk, KnowledgeFile, list[str]]] = []
    for chunk, file in rows:
        tokens = _tokenize(chunk.text or "")
        if not tokens:
            continue
        docs.append((chunk, file, tokens))
        for t in set(tokens):
            if t in q_set:
                df[t] = df.get(t, 0) + 1

    n_docs = max(len(docs), 1)
    avgdl = sum(len(t) for _, _, t in docs) / n_docs
    k1, b = 1.5, 0.75

    scored: list[tuple[float, KnowledgeChunk, KnowledgeFile]] = []
    for chunk, file, tokens in docs:
        # Skip docs with no query overlap quickly
        if not (q_set & set(tokens)):
            continue
        tf: dict[str, int] = {}
        for t in tokens:
            tf[t] = tf.get(t, 0) + 1
        dl = len(tokens)
        score = 0.0
        for term, qf in q_tf.items():
            f = tf.get(term, 0)
            if not f:
                continue
            idf = math.log(1 + (n_docs - df.get(term, 0) + 0.5) / (df.get(term, 0) + 0.5))
            denom = f + k1 * (1 - b + b * dl / max(avgdl, 1.0))
            score += idf * ((f * (k1 + 1)) / denom) * (1.0 + 0.1 * min(qf, 3))
        # Phrase / consecutive token bonus
        text_l = (chunk.text or "").lower()
        q_raw = (query or "").lower().strip()
        if len(q_raw) > 4 and q_raw in text_l:
            score += 1.25
        name = (file.file_name or "").lower()
        if any(t in name for t in q_set if len(t) > 3):
            score += 0.4
        if score > 0:
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
                "score": round(score, 4),
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
    if not _embedding_ready(db):
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


def _hit_key(hit: dict) -> str:
    return f"{hit.get('file_id')}:{hit.get('chunk_index')}"


def _rrf_fuse(lists: list[list[dict]], limit: int, k: int = 60) -> list[dict]:
    """Reciprocal Rank Fusion across retrieval lists (vector + keyword)."""
    scores: dict[str, float] = {}
    best: dict[str, dict] = {}
    methods: dict[str, set[str]] = {}
    for hits in lists:
        for rank, hit in enumerate(hits, start=1):
            key = _hit_key(hit)
            scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank)
            methods.setdefault(key, set()).add(hit.get("method") or "unknown")
            # Prefer higher native score when merging duplicates
            prev = best.get(key)
            if prev is None or float(hit.get("score") or 0) >= float(prev.get("score") or 0):
                best[key] = dict(hit)
    ranked = sorted(scores.items(), key=lambda x: -x[1])
    out = []
    for key, rrf in ranked[:limit]:
        hit = best[key]
        hit["rrf"] = round(rrf, 5)
        used = methods.get(key) or set()
        hit["method"] = "hybrid" if len(used) > 1 else next(iter(used), "hybrid")
        # Light filename / query boost for hybrid ranking display
        out.append(hit)
    return out


def search_chunks_semantic(db: Session, knowledge_id: int, query: str, limit: int = 5) -> list[dict]:
    if not query.strip():
        return []

    kb = db.get(KnowledgeBase, knowledge_id)
    from app.services.workspace_settings import get_chat_config

    cfg = get_chat_config(db)
    model = (kb.model if kb else None) or cfg.get("embedding_model") or OPENAI_EMBEDDING_MODEL
    q = query.strip()
    fetch = max(limit * 2, 8)

    vector_hits = _vector_search(db, knowledge_id, q, fetch, model)
    keyword_hits = _token_search(db, knowledge_id, q, fetch)

    if vector_hits and keyword_hits:
        fused = _rrf_fuse([vector_hits, keyword_hits], limit)
        # Boost when file name tokens overlap the query
        q_tokens = set(re.findall(r"[a-z0-9]+", q.lower()))
        for hit in fused:
            name = (hit.get("file_name") or "").lower()
            if q_tokens and any(t in name for t in q_tokens if len(t) > 3):
                hit["score"] = round(float(hit.get("score") or 0) + 0.05, 4)
        fused.sort(key=lambda h: (-(h.get("rrf") or 0), -(h.get("score") or 0)))
        return fused[:limit]
    if vector_hits:
        return vector_hits[:limit]
    return keyword_hits[:limit]


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


def rag_hits_for_assistant(db: Session, assistant_id: str, query: str, limit: int = 5) -> list[dict]:
    ids = get_assistant_knowledge_ids(db, assistant_id)
    if not ids:
        return []
    # Gather per-KB lists then fuse with RRF so vector vs keyword / cross-KB scores are comparable
    lists: list[list[dict]] = []
    fetch = max(limit * 2, 8)
    for kid in ids:
        hits = search_chunks_semantic(db, kid, query, fetch)
        if hits:
            lists.append(hits)
    if not lists:
        return []
    if len(lists) == 1:
        return lists[0][:limit]
    return _rrf_fuse(lists, limit)


def rag_context_for_assistant(db: Session, assistant_id: str, query: str, limit: int = 5) -> str:
    hits = rag_hits_for_assistant(db, assistant_id, query, limit)
    if not hits:
        return ""

    parts = []
    for i, hit in enumerate(hits, 1):
        source = hit.get("file_name") or "document"
        text = (hit.get("text") or "")[:1200]
        parts.append(f"[{i}] ({source})\n{text}")

    return "\n\n".join(parts)


def kb_upload_dir(kb_id: int) -> Path:
    d = UPLOAD_DIR / str(kb_id)
    d.mkdir(parents=True, exist_ok=True)
    return d


def process_file_records_bg(record_ids: list[int], chunk_size: int = 1000, chunk_overlap: int = 100):
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        for rid in record_ids:
            record = db.get(KnowledgeFile, rid)
            if record:
                process_file_record(db, record, chunk_size, chunk_overlap)
    finally:
        db.close()
