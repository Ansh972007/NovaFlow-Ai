from sqlalchemy.orm import Session
from app.database import KnowledgeFile

def classify_and_index_document(db: Session, workspace_id: int, name: str, size: int) -> KnowledgeFile:
    """Classifies files autonomously and registers metadata entries for indexing."""
    doc_type = "document"
    if name.endswith((".csv", ".xlsx", ".json")):
        doc_type = "structured_data"
    elif name.endswith((".png", ".jpg", ".pdf")):
        doc_type = "scanned_media"
        
    kfile = KnowledgeFile(
        workspace_id=workspace_id,
        file_name=name,
        size_bytes=size,
        document_type=doc_type,
        lifecycle_status="indexing",
    )
    db.add(kfile)
    db.commit()
    db.refresh(kfile)
    return kfile
