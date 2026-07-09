import json
import re
from datetime import datetime

from sqlalchemy.orm import Session

from app.database import FineTuneDataset, FineTuneJob, KnowledgeBase, KnowledgeChunk, KnowledgeFile


def dataset_dict_from_row(row: FineTuneDataset) -> dict:
    from app.services.finetune import dataset_dict

    return dataset_dict(row)


_QUESTION_TEMPLATES = [
    (
        "What is the main takeaway from «{doc}» regarding this excerpt?\n\n{excerpt}",
        "Takeaway: {lede}\n\nKey points:\n{bullets}\n\nSource: {doc}",
    ),
    (
        "A teammate asks: \"Can you explain this from «{doc}»?\"\n\n{excerpt}",
        "{lede}\n\nDetails:\n{bullets}\n\n(From {doc})",
    ),
    (
        "Summarize the critical facts in this «{doc}» passage for someone new to the topic.\n\n{excerpt}",
        "{lede}\n\n{bullets}\n\nDocument: {doc}",
    ),
    (
        "Based on «{doc}», what should someone remember from the following?\n\n{excerpt}",
        "Remember:\n{bullets}\n\nIn short: {lede}\n\n— {doc}",
    ),
]


def _first_sentence(text: str, limit: int = 220) -> str:
    text = re.sub(r"\s+", " ", (text or "")).strip()
    if not text:
        return ""
    m = re.search(r"^(.+?[.!?])(\s|$)", text)
    sent = m.group(1).strip() if m else text
    return sent[:limit]


def _bulletize(text: str, max_bullets: int = 4) -> str:
    text = re.sub(r"\s+", " ", (text or "")).strip()
    # Split on sentence boundaries
    parts = re.split(r"(?<=[.!?])\s+", text)
    bullets = []
    for p in parts:
        p = p.strip()
        if len(p) < 20:
            continue
        # Keep short clauses
        if len(p) > 160:
            p = p[:157] + "…"
        bullets.append(f"- {p}")
        if len(bullets) >= max_bullets:
            break
    if not bullets and text:
        bullets = [f"- {text[:160]}{'…' if len(text) > 160 else ''}"]
    return "\n".join(bullets)


def _near_dup(a: str, b: str) -> bool:
    ta = set(re.findall(r"[a-z0-9]{3,}", (a or "").lower()))
    tb = set(re.findall(r"[a-z0-9]{3,}", (b or "").lower()))
    if not ta or not tb:
        return False
    inter = len(ta & tb)
    return inter / min(len(ta), len(tb)) >= 0.85


def knowledge_to_training_rows(
    db: Session,
    knowledge_ids: list[int],
    workspace_id: int,
    *,
    system_prompt: str = (
        "You are a precise specialist trained on internal documents. "
        "Answer clearly: lead with the point, then short supporting detail. Cite the document name when relevant."
    ),
    max_rows: int = 200,
) -> list[dict]:
    """Build diversified Q→A rows (not echo stubs) from knowledge chunks."""
    rows: list[dict] = []
    seen_previews: list[str] = []
    tpl_i = 0

    for kid in knowledge_ids:
        kb = db.get(KnowledgeBase, kid)
        if not kb or kb.workspace_id != workspace_id:
            continue
        chunks = (
            db.query(KnowledgeChunk, KnowledgeFile)
            .join(KnowledgeFile, KnowledgeChunk.file_id == KnowledgeFile.id)
            .filter(
                KnowledgeChunk.knowledge_id == kid,
                KnowledgeFile.status == 2,
            )
            .order_by(KnowledgeChunk.id)
            .limit(max(max_rows * 2, 50))
            .all()
        )
        for chunk, file in chunks:
            text = (chunk.text or "").strip()
            if len(text) < 40:
                continue
            preview = text[:420]
            if any(_near_dup(preview, prev) for prev in seen_previews[-40:]):
                continue
            seen_previews.append(preview)

            lede = _first_sentence(text)
            bullets = _bulletize(text)
            doc = file.file_name or "document"
            q_tpl, a_tpl = _QUESTION_TEMPLATES[tpl_i % len(_QUESTION_TEMPLATES)]
            tpl_i += 1

            user = q_tpl.format(doc=doc, excerpt=preview)
            assistant = a_tpl.format(doc=doc, lede=lede, bullets=bullets, excerpt=preview)

            rows.append(
                {
                    "system": system_prompt,
                    "user": user,
                    "assistant": assistant[:1800],
                }
            )
            # Add a terse factoid variant for longer passages
            if len(text) > 280 and len(rows) < max_rows:
                fact = lede or preview[:180]
                rows.append(
                    {
                        "system": system_prompt,
                        "user": f"Quick fact check from «{doc}»: what does this say?\n\n{preview[:280]}",
                        "assistant": f"{fact}\n\n(Source: {doc})",
                    }
                )
            if len(rows) >= max_rows:
                return rows
    return rows


def create_dataset_from_knowledge(
    db: Session,
    user_id: int,
    workspace_id: int,
    knowledge_ids: list[int],
    name: str,
    system_prompt: str = "",
) -> FineTuneDataset:
    rows = knowledge_to_training_rows(
        db,
        knowledge_ids,
        workspace_id,
        system_prompt=system_prompt
        or (
            "You are a precise specialist trained on internal documents. "
            "Answer clearly: lead with the point, then short supporting detail. Cite the document name when relevant."
        ),
    )
    if not rows:
        raise ValueError("No training rows could be generated from selected knowledge bases")
    row = FineTuneDataset(
        name=name[:120],
        description=f"Generated from knowledge bases: {', '.join(str(k) for k in knowledge_ids)}",
        user_id=user_id,
        workspace_id=workspace_id,
        rows_json=json.dumps(rows),
        update_time=datetime.utcnow(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def pipeline_dict(job: FineTuneJob, eval_run: dict | None = None) -> dict:
    from app.services.finetune import job_dict

    payload = job_dict(job)
    payload["auto_eval_suite_id"] = job.auto_eval_suite_id
    payload["auto_eval_run_id"] = job.auto_eval_run_id
    if eval_run:
        payload["auto_eval"] = eval_run
    return payload


def _parse_knowledge_ids_from_dataset(dataset: FineTuneDataset | None) -> list[int]:
    if not dataset or not dataset.description:
        return []
    # "Generated from knowledge bases: 1, 2"
    text = dataset.description
    if "knowledge bases:" not in text.lower():
        return []
    try:
        part = text.split(":", 1)[1]
        return [int(x.strip()) for x in part.split(",") if x.strip().isdigit()]
    except Exception:
        return []


def deploy_finetune_to_assistant(
    db: Session,
    job: FineTuneJob,
    user_id: int,
    workspace_id: int,
    *,
    name: str = "",
    prompt: str = "",
    activate: bool = True,
    provider_id: int | None = None,
    knowledge_ids: list[int] | None = None,
) -> dict:
    """Apply fine-tuned model to workspace provider and publish a live Chat assistant."""
    from app.database import Assistant, FineTuneDataset
    from app.routers.assistant import assistant_dict
    from app.services.finetune import apply_finetuned_model
    from app.services.knowledge import set_assistant_knowledge

    provider = apply_finetuned_model(
        db,
        job,
        provider_id=provider_id,
        activate=activate,
    )

    dataset = db.get(FineTuneDataset, job.dataset_id) if job.dataset_id else None
    kids = knowledge_ids if knowledge_ids is not None else _parse_knowledge_ids_from_dataset(dataset)

    ass_name = (name or "").strip() or f"Fine-tuned · {job.fine_tuned_model[:48]}"
    ass_prompt = (prompt or "").strip()
    if len(ass_prompt) < 20:
        ass_prompt = (
            "You are a specialist assistant powered by a fine-tuned model trained on this "
            "workspace's knowledge. Answer structure: direct answer first, then short supporting "
            "detail. Cite document names when recalling specific facts. If unsure, say what is missing "
            "rather than guessing. Stay faithful to the documents you were trained on."
        )

    a = Assistant(
        name=ass_name[:80],
        prompt=ass_prompt,
        desc=f"Deployed from Model Lab job #{job.id} · {job.fine_tuned_model}"[:500],
        logo="",
        user_id=user_id,
        workspace_id=workspace_id,
        status=1,
    )
    db.add(a)
    db.commit()
    db.refresh(a)

    if kids:
        valid = []
        for kid in kids:
            kb = db.get(KnowledgeBase, int(kid))
            if kb and kb.workspace_id == workspace_id:
                valid.append(int(kid))
        if valid:
            set_assistant_knowledge(db, a.id, valid)
            a.update_time = datetime.utcnow()
            db.commit()
            db.refresh(a)

    return {
        "assistant": assistant_dict(a),
        "provider": provider,
        "fine_tuned_model": job.fine_tuned_model,
        "knowledge_ids": kids or [],
        "chat_path": f"/chat?app={a.id}",
    }
