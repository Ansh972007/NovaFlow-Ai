"""Enterprise Knowledge OS tests."""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from app.database import KnowledgeFile, SessionLocal, User, init_db
from app.knowledge_os.curator import analyze_collection
from app.knowledge_os.export import export_collection
from app.knowledge_os.graph import extract_entities_from_text, search_entities
from app.knowledge_os.indexing import detect_duplicates
from app.knowledge_os.integration import retrieve_for_agent
from app.knowledge_os.retrieval import enterprise_retrieve
from app.knowledge_os.search import enterprise_search
from app.knowledge_os.security import can_access_classification, scan_document_content
from app.knowledge_os.service import create_collection, create_folder, get_collection, list_collections
from app.knowledge_os.versioning import create_document_version, list_versions
from app.knowledge_os.plugins import get_connector, list_connectors


@pytest.fixture(scope="module")
def db() -> Session:
    init_db()
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def user_id(db: Session) -> int:
    u = db.query(User).first()
    assert u
    return u.user_id


def test_create_collection_and_tenant_isolation(db: Session, user_id: int):
    kb = create_collection(db, workspace_id=1, user_id=user_id, name="KOS Test Collection")
    assert kb.id
    assert get_collection(db, kb.id, workspace_id=1)
    assert get_collection(db, kb.id, workspace_id=99999) is None


def test_folder_hierarchy(db: Session, user_id: int):
    kb = create_collection(db, workspace_id=1, user_id=user_id, name="Folder Test")
    root = create_folder(db, knowledge_id=kb.id, workspace_id=1, name="docs")
    child = create_folder(db, knowledge_id=kb.id, workspace_id=1, name="api", parent_folder_id=root.id)
    assert child.path == "docs/api"


def test_enterprise_search_metadata(db: Session, user_id: int):
    kb = create_collection(db, workspace_id=1, user_id=user_id, name="Invoice Policies")
    result = enterprise_search(db, workspace_id=1, query="invoice")
    assert "collections" in result
    assert any(c["name"] == "Invoice Policies" for c in result["collections"])


def test_enterprise_retrieve_empty(db: Session):
    result = enterprise_retrieve(db, workspace_id=1, query="nonexistent query xyz", knowledge_id=999999)
    assert result["hit_count"] == 0


def test_security_classification(db: Session):
    assert can_access_classification("restricted", "internal")
    assert not can_access_classification("internal", "secret")
    scan = scan_document_content("Contact admin@test.com for help")
    assert scan["pii_count"] >= 1


def test_version_control(db: Session, user_id: int):
    kb = create_collection(db, workspace_id=1, user_id=user_id, name="Version Test")
    record = KnowledgeFile(knowledge_id=kb.id, file_name="test.txt", file_path=f"{kb.id}/test.txt", status=5)
    db.add(record)
    db.commit()
    db.refresh(record)
    create_document_version(db, record, created_by=user_id, change_summary="Initial")
    versions = list_versions(db, record.id)
    assert len(versions) >= 1


def test_knowledge_graph_entities(db: Session, user_id: int):
    kb = create_collection(db, workspace_id=1, user_id=user_id, name="Graph Test")
    text = "Contact sales@example.com about contract MSA-2024-001"
    entities = extract_entities_from_text(db, workspace_id=1, text=text, knowledge_id=kb.id)
    assert len(entities) >= 1
    found = search_entities(db, workspace_id=1, query="example.com")
    assert isinstance(found, list)


def test_curator_analyze(db: Session, user_id: int):
    kb = create_collection(db, workspace_id=1, user_id=user_id, name="Curator Test")
    report = analyze_collection(db, kb)
    assert "recommendations" in report
    assert "score" in report


def test_export_collection(db: Session, user_id: int):
    kb = create_collection(db, workspace_id=1, user_id=user_id, name="Export Test")
    out = export_collection(db, kb, fmt="markdown")
    assert "Export Test" in out["content"]
    json_out = export_collection(db, kb, fmt="json")
    assert "collection" in json_out["content"]


def test_plugins_registry():
    connectors = list_connectors()
    assert any(c["type"] == "manual" for c in connectors)
    connector = get_connector("manual")
    assert connector.connector_type == "manual"


def test_detect_duplicates_empty(db: Session, user_id: int):
    kb = create_collection(db, workspace_id=1, user_id=user_id, name="Dupe Test")
    dupes = detect_duplicates(db, knowledge_id=kb.id)
    assert isinstance(dupes, list)


def test_retrieve_for_agent(db: Session):
    result = retrieve_for_agent(db, workspace_id=1, query="test", knowledge_id=999999, limit=3)
    assert result["hit_count"] == 0
