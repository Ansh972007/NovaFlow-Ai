"""Enterprise Knowledge no-LLM RAG tests."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import UPLOAD_DIR
from app.database import SessionLocal, KnowledgeFile
from app.services.knowledge import process_file_record
from tests.test_smoke import _auth_headers, client as test_client


@pytest.fixture
def auth_headers(test_client: TestClient):
    return _auth_headers(test_client)


def _create_kb(client: TestClient, headers: dict) -> int:
    res = client.post(
        "/api/v1/knowledge/create",
        headers=headers,
        json={"name": "No-LLM Test KB", "description": "test", "classification": "internal"},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["status_code"] == 200
    return body["data"]["id"]


def _upload_text(client: TestClient, headers: dict, kb_id: int, name: str, content: str) -> dict:
    from io import BytesIO

    res = client.post(
        f"/api/v1/knowledge/upload/{kb_id}",
        headers=headers,
        files={"file": (name, BytesIO(content.encode("utf-8")), "text/plain")},
    )
    assert res.status_code == 200, res.text
    return res.json()["data"]


def test_get_knowledge_by_id(test_client: TestClient, auth_headers: dict):
    kb_id = _create_kb(test_client, auth_headers)
    res = test_client.get(f"/api/v1/knowledge/{kb_id}", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["id"] == kb_id
    assert data["status"] == "empty"
    assert data["file_count"] == 0

    missing = test_client.get("/api/v1/knowledge/999999", headers=auth_headers)
    assert missing.status_code == 200
    assert missing.json()["status_code"] == 404


def test_knowledge_no_llm_search_keyword(test_client: TestClient, auth_headers: dict):
    os.environ.pop("OPENAI_API_KEY", None)
    kb_id = _create_kb(test_client, auth_headers)
    uploaded = _upload_text(
        test_client,
        auth_headers,
        kb_id,
        "policy.txt",
        "NovaFlow enterprise knowledge retrieval works without any LLM API key configured.",
    )
    proc = test_client.post(
        "/api/v1/knowledge/process",
        headers=auth_headers,
        json={
            "knowledge_id": kb_id,
            "file_list": [{"file_path": uploaded["file_path"]}],
            "chunk_size": 200,
            "chunk_overlap": 20,
        },
    )
    assert proc.status_code == 200

    db = SessionLocal()
    try:
        record = db.get(KnowledgeFile, uploaded["id"])
        assert record is not None
        process_file_record(db, record, chunk_size=200, chunk_overlap=20)
    finally:
        db.close()

    search = test_client.get(
        "/api/v1/knowledge/search",
        headers=auth_headers,
        params={"knowledge_id": kb_id, "q": "enterprise knowledge", "limit": 5},
    )
    assert search.status_code == 200
    body = search.json()["data"]
    assert body["total"] >= 1
    assert body["method"] == "keyword"
    assert body["embedding_available"] is False
    hits = body["data"]
    assert hits and hits[0]["method"] == "keyword"


def test_knowledge_retrieve_extractive(test_client: TestClient, auth_headers: dict):
    kb_id = _create_kb(test_client, auth_headers)
    uploaded = _upload_text(
        test_client,
        auth_headers,
        kb_id,
        "faq.txt",
        "Password reset instructions: contact support@company.com for help.",
    )
    db = SessionLocal()
    try:
        record = db.get(KnowledgeFile, uploaded["id"])
        process_file_record(db, record, chunk_size=200, chunk_overlap=20)
    finally:
        db.close()

    res = test_client.post(
        "/api/v1/knowledge/retrieve",
        headers=auth_headers,
        json={"knowledge_id": kb_id, "q": "password reset", "limit": 3},
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["total"] >= 1
    assert "extractive_digest" in data
    assert "[1]" in data["extractive_digest"]
    assert data["llm_answer_available"] is False


def test_knowledge_answer_extractive_fallback(test_client: TestClient, auth_headers: dict):
    kb_id = _create_kb(test_client, auth_headers)
    uploaded = _upload_text(test_client, auth_headers, kb_id, "note.txt", "The contract renewal deadline is March 15.")
    db = SessionLocal()
    try:
        record = db.get(KnowledgeFile, uploaded["id"])
        process_file_record(db, record, chunk_size=200, chunk_overlap=20)
    finally:
        db.close()

    res = test_client.post(
        "/api/v1/knowledge/answer",
        headers=auth_headers,
        json={"knowledge_id": kb_id, "q": "renewal deadline", "limit": 3},
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert data.get("extractive") is True
    assert "March" in data.get("answer", "") or data.get("total", 0) >= 1


def test_knowledge_pii_scan_on_process(test_client: TestClient, auth_headers: dict):
    kb_id = _create_kb(test_client, auth_headers)
    uploaded = _upload_text(
        test_client,
        auth_headers,
        kb_id,
        "contacts.txt",
        "Please email alice@example.com or call 555-123-4567 for billing.",
    )
    db = SessionLocal()
    try:
        record = db.get(KnowledgeFile, uploaded["id"])
        process_file_record(db, record, chunk_size=200, chunk_overlap=20)
        db.refresh(record)
        from app.services.knowledge import _parse_file_meta

        meta = _parse_file_meta(record)
        assert meta.get("pii_count", 0) > 0
    finally:
        db.close()

    files = test_client.get(f"/api/v1/knowledge/file_list/{kb_id}", headers=auth_headers)
    row = files.json()["data"]["data"][0]
    assert row["pii_count"] > 0


def test_knowledge_chunked_upload_large_file(test_client: TestClient, auth_headers: dict):
    kb_id = _create_kb(test_client, auth_headers)
    chunk_payload = b"x" * (9 * 1024 * 1024)  # >8MB triggers chunked path
    file_size = len(chunk_payload)
    chunk_size = 8 * 1024 * 1024
    total_chunks = 2

    init = test_client.post(
        f"/api/v1/knowledge/upload-chunk/init/{kb_id}",
        headers=auth_headers,
        json={
            "file_name": "large.txt",
            "file_size": file_size,
            "chunk_size": chunk_size,
            "total_chunks": total_chunks,
        },
    )
    assert init.status_code == 200, init.text
    upload_id = init.json()["data"]["upload_id"]

    from io import BytesIO

    half = file_size // 2
    for idx, start in enumerate([0, half]):
        part = chunk_payload[start : start + (half if idx == 0 else file_size - half)]
        res = test_client.post(
            f"/api/v1/knowledge/upload-chunk/{upload_id}/{idx}",
            headers=auth_headers,
            files={"file": (f"chunk_{idx}", BytesIO(part), "text/plain")},
        )
        assert res.status_code == 200, res.text

    complete = test_client.post(f"/api/v1/knowledge/upload-chunk/complete/{upload_id}", headers=auth_headers)
    assert complete.status_code == 200, complete.text
    data = complete.json()["data"]
    assert data["file_path"]
    dest = UPLOAD_DIR / data["file_path"]
    assert dest.exists()
    assert dest.stat().st_size == file_size


def test_delete_knowledge_file(test_client: TestClient, auth_headers: dict):
    kb_id = _create_kb(test_client, auth_headers)
    uploaded = _upload_text(test_client, auth_headers, kb_id, "temp.txt", "temporary file")
    file_id = uploaded["id"]
    path = UPLOAD_DIR / uploaded["file_path"]
    assert path.exists()

    deleted = test_client.delete(f"/api/v1/knowledge/file/{file_id}", headers=auth_headers)
    assert deleted.status_code == 200
    assert not path.exists()

    files = test_client.get(f"/api/v1/knowledge/file_list/{kb_id}", headers=auth_headers)
    assert files.json()["data"]["total"] == 0


def test_file_list_total_count(test_client: TestClient, auth_headers: dict):
    kb_id = _create_kb(test_client, auth_headers)
    _upload_text(test_client, auth_headers, kb_id, "a.txt", "one")
    _upload_text(test_client, auth_headers, kb_id, "b.txt", "two")
    res = test_client.get(f"/api/v1/knowledge/file_list/{kb_id}", headers=auth_headers)
    body = res.json()["data"]
    assert body["total"] == 2
    assert len(body["data"]) == 2
