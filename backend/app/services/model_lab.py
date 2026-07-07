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
    system_prompt: str = "You are a helpful assistant trained on internal documents.",
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
                    "user": f"Summarize and explain the key points from this document excerpt ({file.file_name}):\n\n{preview}",
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
        system_prompt=system_prompt or "You are a helpful assistant trained on internal documents.",
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
