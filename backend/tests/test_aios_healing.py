import pytest
from fastapi.testclient import TestClient
from app.main import app
from tests.test_smoke import client, _auth_headers

from app.composer.testing_engine import run_solution_test_assertions
from app.composer.optimizer import optimize_route_latency
from app.composer.healing import execute_with_healing
from app.composer.evolution import mine_patterns, evolve_solution_graph
from app.composer.governance import scan_marketplace_asset
from app.composer.employee import assign_digital_employee_role


def test_testing_engine_validations():
    report = run_solution_test_assertions("sol_123", {"goal": "test goal"})
    assert report["test_run_status"] == "passed"
    
    fail_report = run_solution_test_assertions("sol_123", {})
    assert fail_report["test_run_status"] == "failed"
    assert len(fail_report["errors"]) == 1


def test_runtime_optimizer():
    providers = [
        {"name": "gpt-4", "latency": 800},
        {"name": "groq-llama", "latency": 150},
        {"name": "gemini-flash", "latency": 250}
    ]
    best = optimize_route_latency("cap_workflow", providers)
    assert best["name"] == "groq-llama"


def test_self_healing_logic():
    def primary_fail():
        raise ConnectionError("Endpoint down.")
        
    def fallback_ok():
        return "fallback result"
        
    report = execute_with_healing(primary_fail, fallback_ok)
    assert report["status"] == "success"
    assert report["routing"] == "local_fallback"
    assert report["healed"] is True
    assert "Endpoint down" in report["healing_reason"]


def test_evolution_mining_and_pruning():
    logs = [
        {"execution_path": ["cap_ocr", "cap_workflow"], "success": True},
        {"execution_path": ["cap_voice", "cap_telegram"], "success": True},
        {"execution_path": ["cap_ocr"], "success": False}
    ]
    patterns = mine_patterns(logs)
    assert "cap_ocr->cap_workflow" in patterns
    assert "cap_voice->cap_telegram" in patterns
    
    # Graph pruning
    payload = {
        "nodes": {
            "cap_ocr": {"type": "capability"},
            "cap_unused": {"type": "capability"},
            "db_orders": {"type": "database"}
        },
        "edges": [
            {"source": "cap_ocr", "target": "db_orders"}
        ],
        "required_capabilities": ["cap_ocr"]
    }
    evolved = evolve_solution_graph(payload)
    assert evolved["evolved"] is True
    assert "cap_unused" not in evolved["nodes"]
    assert "cap_ocr" in evolved["nodes"]


def test_marketplace_security_scan():
    config = {
        "name": "dangerous template",
        "api_key": "supersecretkey123"
    }
    vulns = scan_marketplace_asset(config)
    assert len(vulns) == 1
    assert "Possible hardcoded secret" in vulns[0]


def test_digital_employee():
    emp = assign_digital_employee_role(1, "agent_9", "Support Representative", ["ticket_resolution_time"])
    assert emp["role"] == "Support Representative"
    assert emp["status"] == "onboarded"


def test_deploy_and_healing_apis(client):
    headers = _auth_headers(client)
    
    # 1. Compile project goal
    res = client.post(
        "/api/v1/aios/project",
        headers=headers,
        json={"goal": "Process ordering system"}
    )
    assert res.status_code == 200
    data = res.json()["data"]
    project_id = data["project_id"]
    
    # 2. Deploy solution graph
    deploy_res = client.post(f"/api/v1/aios/project/{project_id}/deploy", headers=headers)
    assert deploy_res.status_code == 200
    assert deploy_res.json()["data"]["status"] == "deployed"
    
    # 3. Simulate healing endpoint
    heal_res = client.post(f"/api/v1/aios/project/{project_id}/heal", headers=headers)
    assert heal_res.status_code == 200
    heal_data = heal_res.json()["data"]
    assert heal_data["routing"] == "local_fallback"
    assert heal_data["healed"] is True
