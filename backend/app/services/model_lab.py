import json
from datetime import datetime

from sqlalchemy.orm import Session

from app.database import FineTuneDataset, FineTuneJob, KnowledgeBase, KnowledgeChunk, KnowledgeFile


def dataset_dict_from_row(row: FineTuneDataset) -> dict:
    from app.services.finetune import dataset_dict

    return dataset_dict(row)


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
    rows: list[dict] = []
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
            .limit(max_rows)
            .all()
        )
        for chunk, file in chunks:
            text = (chunk.text or "").strip()
            if len(text) < 40:
                continue
            preview = text[:400]
            rows.append(
                {
                    "system": system_prompt,
                    "user": (
                        f"From document «{file.file_name}», explain the key points a user should know. "
                        f"Start with a one-sentence takeaway, then 2–4 bullets.\n\nExcerpt:\n{preview}"
                    ),
                    "assistant": text[:1500],
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
