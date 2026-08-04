import pytest
from fastapi.testclient import TestClient
from app.main import app
from tests.test_smoke import client, _auth_headers

from app.composer.generator import generate_custom_component
from app.composer.credentials import secure_vault_save, secure_vault_read, mask_credential
from app.composer.ontology import get_ontology_schema
from app.composer.resources import estimate_solution_resources, schedule_solution_task


def test_custom_component_generation(client):
    headers = _auth_headers(client)
    from app.database import get_db
    db = next(get_db())
    
    dna = generate_custom_component(db, "PDF Translator", "Translate PDFs autonomously")
    assert dna.id == "cap_custom_pdf_translator"
    assert dna.category == "custom"
    assert dna.reliability_score == 0.98


def test_credential_vault_masking():
    plain = "sk-proj-supersecretkey123"
    enc = secure_vault_save(plain)
    assert enc != plain
    
    dec = secure_vault_read(enc)
    assert dec == plain
    
    masked = mask_credential(plain)
    assert masked == "sk-p...y123"


def test_business_ontology_and_resources():
    schema = get_ontology_schema("healthcare")
    assert "Patient" in schema["entities"]
    assert "check_hipaa_compliance" in schema["rules"]
    
    resources = estimate_solution_resources(["cap_voice", "cap_ocr"])
    assert resources["vram_allocation_gb"] == 6.0
    assert resources["worker_threads"] == 4
    
    queue = schedule_solution_task("voice_stream", {})
    assert queue == "realtime_worker_queue"


def test_sandbox_twin_execution_api(client):
    headers = _auth_headers(client)
    
    # 1. Compile project goal
    res = client.post(
        "/api/v1/aios/project",
        headers=headers,
        json={"goal": "Synthesize voice logs with ocr text"}
    )
    assert res.status_code == 200
    project_id = res.json()["data"]["project_id"]
    
    # 2. Run trial sandbox run
    trial_res = client.post(f"/api/v1/aios/project/{project_id}/sandbox-trial", headers=headers)
    assert trial_res.status_code == 200
    report = trial_res.json()["data"]
    assert report["status"] == "success"
    assert report["total_latency_ms"] > 0
    assert len(report["logs"]) >= 2
    
    # 3. Inject failure
    fail_res = client.post(
        f"/api/v1/aios/project/{project_id}/sandbox-trial?inject_error_node=cap_voice",
        headers=headers
    )
    assert fail_res.status_code == 200
    fail_report = fail_res.json()["data"]
    assert fail_report["status"] == "failed"
    assert "Injected error triggered" in "".join(fail_report["logs"])
