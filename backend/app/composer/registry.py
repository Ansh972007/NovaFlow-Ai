import json
from sqlalchemy.orm import Session
from app.database import CapabilityDNA, UniversalCapability, UniversalAsset, WorkflowFragment

DEFAULT_CAPABILITY_PRESETS = [
    {
        "id": "cap_voice",
        "category": "voice",
        "inputs_json": json.dumps({"audio_stream": "string"}),
        "outputs_json": json.dumps({"transcription": "string"}),
        "latency_budget_ms": 300,
    },
    {
        "id": "cap_workflow",
        "category": "orchestration",
        "inputs_json": json.dumps({"goal": "string"}),
        "outputs_json": json.dumps({"status": "string", "execution_logs": "array"}),
        "latency_budget_ms": 1000,
    },
    {
        "id": "cap_knowledge",
        "category": "rag",
        "inputs_json": json.dumps({"query": "string"}),
        "outputs_json": json.dumps({"documents": "array"}),
        "latency_budget_ms": 500,
    },
    {
        "id": "cap_ocr",
        "category": "vision",
        "inputs_json": json.dumps({"image_url": "string"}),
        "outputs_json": json.dumps({"text": "string"}),
        "latency_budget_ms": 800,
    },
    {
        "id": "cap_telegram",
        "category": "connector",
        "inputs_json": json.dumps({"token": "string", "message": "string"}),
        "outputs_json": json.dumps({"success": "boolean"}),
        "latency_budget_ms": 600,
    },
]


def ensure_default_capabilities(db: Session):
    """Seed the default platform capability DNA profiles if they do not exist."""
    for preset in DEFAULT_CAPABILITY_PRESETS:
        exists = db.query(CapabilityDNA).filter(CapabilityDNA.id == preset["id"]).first()
        if not exists:
            dna = CapabilityDNA(
                id=preset["id"],
                category=preset["category"],
                inputs_json=preset["inputs_json"],
                outputs_json=preset["outputs_json"],
                latency_budget_ms=preset["latency_budget_ms"],
            )
            db.add(dna)
    db.commit()


def get_all_capabilities(db: Session, workspace_id: int) -> list[dict]:
    """Retrieve all capabilities (preset and workspace-registered)."""
    ensure_default_capabilities(db)
    
    dnas = db.query(CapabilityDNA).all()
    dnas_dict = {
        d.id: {
            "id": d.id,
            "category": d.category,
            "inputs": json.loads(d.inputs_json),
            "outputs": json.loads(d.outputs_json),
            "latency": d.latency_budget_ms,
            "reliability": d.reliability_score,
            "type": "preset",
        }
        for d in dnas
    }
    
    workspace_caps = db.query(UniversalCapability).filter(
        UniversalCapability.workspace_id == workspace_id,
        UniversalCapability.status == "active"
    ).all()
    
    for wc in workspace_caps:
        if wc.dna_id in dnas_dict:
            dnas_dict[wc.dna_id]["type"] = "workspace"
            dnas_dict[wc.dna_id]["name"] = wc.name
            
    return list(dnas_dict.values())
