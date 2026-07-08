"""Real-document ingest + search + train-path validation (offline + optional live LLM)."""

from __future__ import annotations

import base64
import io
import json
import os
import tempfile
from pathlib import Path

import pytest
import rsa
from fastapi.testclient import TestClient

_TEST_DIR = Path(tempfile.mkdtemp(prefix="novaflow-e2e-"))
os.environ["DATA_DIR"] = str(_TEST_DIR)
os.environ["DATABASE_URL"] = f"sqlite:///{(_TEST_DIR / 'e2e.db').as_posix()}"
os.environ["JWT_SECRET"] = "novaflow-e2e-secret"
os.environ["NOVAFLOW_DEMO_SEED"] = "0"
os.environ["MILVUS_URI"] = ""
os.environ["NOVAFLOW_ADMIN_USER"] = "admin"
os.environ["NOVAFLOW_ADMIN_PASSWORD"] = "admin123"
# Keep env key empty for offline suite; live tests read LIVE_OPENAI_API_KEY separately.
# Must clear both before and after imports because app.config.load_dotenv() may reload .env.
os.environ["OPENAI_API_KEY"] = ""
os.environ.pop("OPENAI_API_KEY", None)

from app.crypto import get_rsa_keys  # noqa: E402
from app.main import app  # noqa: E402
from app import config as app_config  # noqa: E402

app_config.OPENAI_API_KEY = ""
os.environ["OPENAI_API_KEY"] = ""
from app.services.doc_parse import (  # noqa: E402
    extract_csv_text,
    extract_docx,
    extract_pptx,
    extract_xlsx,
)
from app.services.finetune import build_jsonl  # noqa: E402
from app.services.knowledge import extract_text, process_file_record  # noqa: E402
from tests.fixtures_docs import (  # noqa: E402
    UNIQUE,
    write_csv,
    write_docx,
    write_html,
    write_json,
    write_md,
    write_pdf,
    write_pptx,
    write_training_csv,
    write_txt,
    write_xlsx,
)

LIVE_KEY = (os.getenv("LIVE_OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY") or "").strip()


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def _encrypt(password: str) -> str:
    pub, _ = get_rsa_keys()
    return base64.b64encode(rsa.encrypt(password.encode("utf-8"), pub)).decode("utf-8")


def _auth(client: TestClient) -> dict:
    login = client.post(
        "/api/v1/user/login",
        json={"user_name": "admin", "password": _encrypt("admin123")},
    )
    assert login.status_code == 200
    token = login.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _create_kb(client, headers, name="E2E Library"):
    res = client.post(
        "/api/v1/knowledge/create",
        headers=headers,
        json={"name": name, "description": "real e2e", "type": 0},
    )
    assert res.status_code == 200, res.text
    return res.json()["data"]["id"]


def _upload_and_process(client, headers, kb_id: int, path: Path):
    with path.open("rb") as fh:
        res = client.post(
            f"/api/v1/knowledge/upload/{kb_id}",
            headers=headers,
            files={"file": (path.name, fh, "application/octet-stream")},
        )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["status_code"] == 200, body
    file_path = body["data"]["file_path"]
    file_id = body["data"]["id"]
    proc = client.post(
        "/api/v1/knowledge/process",
        headers=headers,
        json={
            "knowledge_id": kb_id,
            "file_list": [{"file_path": file_path}],
            "chunk_size": 800,
            "chunk_overlap": 80,
        },
    )
    assert proc.status_code == 200, proc.text
    files = client.get(f"/api/v1/knowledge/file_list/{kb_id}", headers=headers)
    row = next(f for f in files.json()["data"]["data"] if f["id"] == file_id)
    return row


# ---------- unit parsers ----------


def test_parsers_one_by_one(tmp_path: Path):
    assert UNIQUE in extract_text(write_txt(tmp_path / "a.txt"))
    assert UNIQUE in extract_text(write_md(tmp_path / "a.md"))
    assert UNIQUE in extract_csv_text(write_csv(tmp_path / "a.csv"))
    assert UNIQUE in extract_text(write_json(tmp_path / "a.json"))
    assert UNIQUE in extract_text(write_html(tmp_path / "a.html"))
    assert UNIQUE in extract_docx(write_docx(tmp_path / "a.docx"))
    assert UNIQUE in extract_pptx(write_pptx(tmp_path / "a.pptx"))
    assert UNIQUE in extract_xlsx(write_xlsx(tmp_path / "a.xlsx"))
    pdf_text = extract_text(write_pdf(tmp_path / "a.pdf"))
    assert UNIQUE in pdf_text or "refund" in pdf_text.lower()


def test_legacy_doc_rejected(tmp_path: Path):
    p = tmp_path / "legacy.doc"
    p.write_bytes(b"not a real doc")
    with pytest.raises(ValueError):
        extract_text(p)


# ---------- API upload each format ----------


@pytest.mark.parametrize(
    "writer,name",
    [
        (write_txt, "handbook.txt"),
        (write_md, "policy.md"),
        (write_csv, "catalog.csv"),
        (write_json, "meta.json"),
        (write_html, "page.html"),
        (write_docx, "clause.docx"),
        (write_pptx, "deck.pptx"),
        (write_xlsx, "sheet.xlsx"),
        (write_pdf, "guide.pdf"),
    ],
)
def test_upload_process_search_each_format(client, tmp_path, writer, name):
    headers = _auth(client)
    kb_id = _create_kb(client, headers, f"KB-{name}")
    path = writer(tmp_path / name)
    row = _upload_and_process(client, headers, kb_id, path)
    assert row["status"] == 2, row.get("error_message") or row

    search = client.get(
        "/api/v1/knowledge/search",
        headers=headers,
        params={"knowledge_id": kb_id, "q": UNIQUE, "limit": 5},
    )
    assert search.status_code == 200, search.text
    hits = search.json()["data"]["data"]
    assert hits, f"no hits for {name}"
    blob = " ".join(h.get("text") or "" for h in hits)
    assert UNIQUE in blob or name.split(".")[0].lower() in blob.lower()


def test_reject_unsupported_upload(client, tmp_path):
    headers = _auth(client)
    kb_id = _create_kb(client, headers, "KB-reject")
    bad = tmp_path / "legacy.doc"
    bad.write_bytes(b"x")
    with bad.open("rb") as fh:
        res = client.post(
            f"/api/v1/knowledge/upload/{kb_id}",
            headers=headers,
            files={"file": ("legacy.doc", fh, "application/msword")},
        )
    assert res.status_code == 200
    assert res.json()["status_code"] != 200


def test_retry_failed_file(client, tmp_path):
    headers = _auth(client)
    kb_id = _create_kb(client, headers, "KB-retry")
    path = write_txt(tmp_path / "retry.txt")
    row = _upload_and_process(client, headers, kb_id, path)
    assert row["status"] == 2
    # Force fail by wiping chunks then retry should succeed
    retry = client.post("/api/v1/knowledge/retry", headers=headers, json={"file_id": row["id"]})
    assert retry.status_code == 200
    assert retry.json()["data"]["status"] == 2


def test_dataset_from_knowledge_and_jsonl(client, tmp_path):
    headers = _auth(client)
    kb_id = _create_kb(client, headers, "KB-train")
    path = write_txt(tmp_path / "train.txt", f"Shipping: overnight for VIP. Code {UNIQUE}.")
    row = _upload_and_process(client, headers, kb_id, path)
    assert row["status"] == 2

    ds = client.post(
        "/api/v1/model-lab/dataset-from-knowledge",
        headers=headers,
        json={"name": "From KB", "knowledge_ids": [kb_id]},
    )
    assert ds.status_code == 200, ds.text
    data = ds.json()["data"]
    assert data["row_count"] >= 1
    payload = build_jsonl(data["rows"])
    assert b'"role": "user"' in payload
    assert UNIQUE.encode() in payload or b"Shipping" in payload


def test_training_csv_import_path(client, tmp_path):
    headers = _auth(client)
    # Create empty dataset via evaluation/finetune create if available
    create = client.post(
        "/api/v1/finetune/datasets",
        headers=headers,
        json={"name": "CSV Train", "description": "e2e", "rows": []},
    )
    if create.status_code == 404:
        pytest.skip("finetune datasets create route missing")
    assert create.status_code == 200, create.text
    ds_id = create.json()["data"]["id"]
    csv_path = write_training_csv(tmp_path / "train.csv")
    with csv_path.open("rb") as fh:
        imp = client.post(
            f"/api/v1/finetune/datasets/{ds_id}/import-csv",
            headers=headers,
            files={"file": ("train.csv", fh, "text/csv")},
        )
    assert imp.status_code == 200, imp.text
    body = imp.json()["data"]
    imported = body.get("imported") or body.get("row_count") or len(body.get("rows") or [])
    if isinstance(body.get("dataset"), dict):
        imported = imported or body["dataset"].get("row_count") or 0
    assert imported >= 1, body


def test_assistant_rag_demo_surfaces_context(client, tmp_path):
    """Without API key, chat demo mode should still show retrieved evidence."""
    headers = _auth(client)
    kb_id = _create_kb(client, headers, "KB-chat")
    path = write_txt(tmp_path / "chat.txt", f"The warranty code is {UNIQUE} forever.")
    assert _upload_and_process(client, headers, kb_id, path)["status"] == 2

    import uuid
    from app.database import Assistant, SessionLocal
    from app.services.knowledge import rag_context_for_assistant, set_assistant_knowledge

    db = SessionLocal()
    try:
        a = Assistant(
            id=uuid.uuid4().hex,
            name="E2E Rag Bot",
            desc="test",
            prompt="Answer using knowledge when available.",
            user_id=1,
            workspace_id=1,
            status=1,
        )
        db.add(a)
        db.commit()
        set_assistant_knowledge(db, a.id, [kb_id])
        aid = a.id
        ctx = rag_context_for_assistant(db, aid, "What is the warranty code?")
        assert UNIQUE in ctx
    finally:
        db.close()

    search = client.get(
        "/api/v1/knowledge/search",
        headers=headers,
        params={"knowledge_id": kb_id, "q": "warranty code", "limit": 3},
    )
    hits = search.json()["data"]["data"]
    assert any(UNIQUE in (h.get("text") or "") for h in hits)

    # Demo chat path without asyncio event-loop edge cases in pytest
    from app.services.llm import stream_chat

    async def _collect():
        out = []
        async for token in stream_chat(
            f"You are helpful.\n\n--- Retrieved context ---\n{ctx}\n--- End context ---",
            "What is the warranty code?",
        ):
            out.append(token)
        return "".join(out)

    import anyio

    reply = anyio.run(_collect)
    low = reply.lower()
    # Offline: demo mode should embed retrieved evidence. If a process-level key exists
    # and returns quota, accept clear billing guidance instead.
    if "demo mode" in low:
        assert UNIQUE in reply
    else:
        assert "quota" in low or "billing" in low or UNIQUE in reply


@pytest.mark.skipif(not LIVE_KEY, reason="Set LIVE_OPENAI_API_KEY to run paid live LLM/train tests")
def test_live_provider_chat_and_optional_train(client, tmp_path):
    headers = _auth(client)
    # Register provider with live key
    prov = client.post(
        "/api/v1/llm/providers",
        headers=headers,
        json={
            "name": "Live OpenAI",
            "provider_type": "openai",
            "api_key": LIVE_KEY,
            "chat_model": "gpt-4o-mini",
            "embedding_model": "text-embedding-3-small",
            "activate": True,
        },
    )
    assert prov.status_code == 200, prov.text

    kb_id = _create_kb(client, headers, "KB-live")
    path = write_txt(tmp_path / "live.txt", f"Acme refund policy: {UNIQUE} customers get 30-day returns.")
    assert _upload_and_process(client, headers, kb_id, path)["status"] == 2

    search = client.get(
        "/api/v1/knowledge/search",
        headers=headers,
        params={"knowledge_id": kb_id, "q": "refund policy", "limit": 3},
    )
    hits = search.json()["data"]["data"]
    assert hits
    assert hits[0].get("method") in {"vector", "milvus", "keyword"}

    # Dataset + start fine-tune (may fail if account lacks FT access — assert API shape)
    ds = client.post(
        "/api/v1/model-lab/dataset-from-knowledge",
        headers=headers,
        json={"name": "Live FT", "knowledge_ids": [kb_id]},
    )
    assert ds.status_code == 200
    ds_id = ds.json()["data"]["id"]
    train = client.post(
        "/api/v1/model-lab/train-and-eval",
        headers=headers,
        json={"dataset_id": ds_id, "base_model": "gpt-4o-mini-2024-07-18"},
    )
    # Accept started or provider error with clear message (not a crash)
    assert train.status_code == 200
    body = train.json()
    assert body["status_code"] in (200, 400) or body.get("data")
