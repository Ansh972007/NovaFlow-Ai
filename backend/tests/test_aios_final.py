import pytest
from fastapi.testclient import TestClient
from app.main import app
from tests.test_smoke import client, _auth_headers

from app.composer.observability import log_execution_telemetry
from app.composer.doc_generator import generate_solution_documentation
from app.composer.migration_wrapper import migrate_legacy_workflow_to_solution


def test_observability_and_docs_logic(client):
    headers = _auth_headers(client)
    from app.database import get_db
    db = next(get_db())
    
    # Assert cost ledger logging doesn't fail
    log_execution_telemetry(db, 1, "sol_test_123", 450, 800, 0.0045)
    
    # Assert markdown generator compiles sections
    docs = generate_solution_documentation("sol_test_123", {
        "nodes": {
            "cap_ocr": {"type": "vision"}
        },
        "edges": []
    })
    assert "# Deployed Solution Guide: sol_test_123" in docs
    assert "cap_ocr" in docs


def test_legacy_migration_wrapper():
    legacy = {
        "nodes": [
            {"id": "node_1", "type": "agent", "name": "Helper Agent"},
            {"id": "node_2", "type": "db", "name": "Target DB"}
        ],
        "edges": [
            {"source": "node_1", "target": "node_2"}
        ]
    }
    migrated = migrate_legacy_workflow_to_solution(legacy)
    assert "node_1" in migrated["nodes"]
    assert migrated["nodes"]["node_1"]["type"] == "agent"
    assert len(migrated["edges"]) == 1


def test_final_integration_endpoints(client):
    headers = _auth_headers(client)
    
    # 1. Compile project goal
    res = client.post(
        "/api/v1/aios/project",
        headers=headers,
        json={"goal": "Index medical records with ocr"}
    )
    assert res.status_code == 200
    project_id = res.json()["data"]["project_id"]
    
    # 2. Get dashboard metrics summary
    dashboard_res = client.get("/api/v1/aios/dashboard/summary", headers=headers)
    assert dashboard_res.status_code == 200
    summary = dashboard_res.json()["data"]
    assert summary["projects_count"] >= 1
    assert "total_cost_usd" in summary
    
    # 3. Get compiled solution documentation
    docs_res = client.get(f"/api/v1/aios/project/{project_id}/docs", headers=headers)
    assert docs_res.status_code == 200
    markdown_data = docs_res.json()["data"]["markdown"]
    assert "Deployed Solution Guide" in markdown_data
    
    # 4. Migrate legacy POST API
    migrate_res = client.post(
        "/api/v1/aios/project/migrate-legacy",
        headers=headers,
        json={
            "nodes": [{"id": "n1", "type": "voice"}],
            "edges": []
        }
    )
    assert migrate_res.status_code == 200
    assert "n1" in migrate_res.json()["data"]["nodes"]
