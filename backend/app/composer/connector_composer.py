from sqlalchemy.orm import Session
from app.database import ConnectorWebhook

def provision_connector_webhook(db: Session, workspace_id: int, direction: str, url: str) -> ConnectorWebhook:
    """Provisions connection webhooks autonomously inside workspace environments."""
    webhook = ConnectorWebhook(
        workspace_id=workspace_id,
        direction=direction,
        url=url,
        status="active",
    )
    db.add(webhook)
    db.commit()
    db.refresh(webhook)
    return webhook
