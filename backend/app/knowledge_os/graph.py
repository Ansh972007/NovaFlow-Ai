"""KOS knowledge graph — entity extraction and relationships."""

from __future__ import annotations

import json
import re
import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.database import KnowledgeEntity, KnowledgeFile, KnowledgeRelationship


ENTITY_PATTERNS = {
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
    "project": re.compile(r"\b(?:project|initiative)\s+[A-Z][A-Za-z0-9_-]{2,40}\b", re.I),
    "product": re.compile(r"\b(?:product|SKU|item)\s+[A-Z][A-Za-z0-9_-]{2,40}\b", re.I),
    "contract": re.compile(r"\b(?:contract|agreement|MSA|SOW)\s+[A-Z0-9-]{3,30}\b", re.I),
    "invoice": re.compile(r"\b(?:invoice|INV)[#:\s-]*[A-Z0-9-]{3,20}\b", re.I),
}


def extract_entities_from_text(
    db: Session,
    *,
    workspace_id: int,
    text: str,
    knowledge_id: int | None = None,
    file_id: int | None = None,
    organization_id: int | None = None,
) -> list[KnowledgeEntity]:
    """Rule-based entity extraction — extensible via plugins."""
    found: dict[str, KnowledgeEntity] = {}
    for entity_type, pattern in ENTITY_PATTERNS.items():
        for match in pattern.finditer(text or ""):
            name = match.group(0).strip()[:200]
            key = f"{entity_type}:{name.lower()}"
            if key in found:
                continue
            entity = KnowledgeEntity(
                id=uuid.uuid4().hex,
                workspace_id=workspace_id,
                organization_id=organization_id,
                knowledge_id=knowledge_id,
                file_id=file_id,
                entity_type=entity_type,
                name=name,
                aliases_json="[]",
            )
            db.add(entity)
            found[key] = entity
    if found:
        db.commit()
    return list(found.values())


def build_graph_for_file(
    db: Session,
    *,
    file: KnowledgeFile,
    workspace_id: int,
    text: str,
    organization_id: int | None = None,
) -> dict[str, Any]:
    """Extract entities and co-occurrence relationships from a document."""
    entities = extract_entities_from_text(
        db,
        workspace_id=workspace_id,
        text=text,
        knowledge_id=file.knowledge_id,
        file_id=file.id,
        organization_id=organization_id,
    )
    relationships = []
    for i, src in enumerate(entities):
        for tgt in entities[i + 1 : i + 4]:
            rel = KnowledgeRelationship(
                id=uuid.uuid4().hex,
                workspace_id=workspace_id,
                source_entity_id=src.id,
                target_entity_id=tgt.id,
                relation_type="co_occurs",
                confidence=0.7,
                source_file_id=file.id,
            )
            db.add(rel)
            relationships.append(rel)
    if relationships:
        db.commit()
    return {
        "entity_count": len(entities),
        "relationship_count": len(relationships),
        "entities": [{"id": e.id, "type": e.entity_type, "name": e.name} for e in entities],
    }


def search_entities(
    db: Session,
    *,
    workspace_id: int,
    query: str = "",
    entity_type: str = "",
    limit: int = 50,
) -> list[dict]:
    q = db.query(KnowledgeEntity).filter(KnowledgeEntity.workspace_id == workspace_id)
    if query:
        q = q.filter(KnowledgeEntity.name.contains(query))
    if entity_type:
        q = q.filter(KnowledgeEntity.entity_type == entity_type)
    rows = q.order_by(KnowledgeEntity.create_time.desc()).limit(limit).all()
    return [{"id": r.id, "type": r.entity_type, "name": r.name, "file_id": r.file_id} for r in rows]


def get_entity_graph(
    db: Session,
    *,
    workspace_id: int,
    entity_id: str,
    depth: int = 1,
) -> dict[str, Any]:
    entity = db.get(KnowledgeEntity, entity_id)
    if not entity or entity.workspace_id != workspace_id:
        return {"nodes": [], "edges": []}

    nodes = {entity.id: {"id": entity.id, "type": entity.entity_type, "name": entity.name}}
    edges = []
    rels = (
        db.query(KnowledgeRelationship)
        .filter(
            KnowledgeRelationship.workspace_id == workspace_id,
            (KnowledgeRelationship.source_entity_id == entity_id)
            | (KnowledgeRelationship.target_entity_id == entity_id),
        )
        .limit(100)
        .all()
    )
    for rel in rels:
        edges.append(
            {
                "id": rel.id,
                "source": rel.source_entity_id,
                "target": rel.target_entity_id,
                "type": rel.relation_type,
                "confidence": rel.confidence,
            }
        )
        for eid in (rel.source_entity_id, rel.target_entity_id):
            if eid not in nodes:
                e = db.get(KnowledgeEntity, eid)
                if e:
                    nodes[eid] = {"id": e.id, "type": e.entity_type, "name": e.name}
    return {"nodes": list(nodes.values()), "edges": edges, "depth": depth}
