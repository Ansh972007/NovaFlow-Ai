from sqlalchemy.orm import Session
from app.database import WorkspaceIntegration

def analyze_solution_gaps(db: Session, workspace_id: int, required_capabilities: list[str]) -> list[str]:
    """Inspect required capabilities against active workspace integrations to identify missing credentials."""
    missing = []
    
    integration = db.query(WorkspaceIntegration).filter(
        WorkspaceIntegration.workspace_id == workspace_id
    ).first()
    
    for cap in required_capabilities:
        if cap == "cap_telegram":
            if not integration or not integration.telegram_bot_token_enc:
                missing.append("telegram_bot_token")
        elif cap == "cap_github":
            if not integration or not integration.github_token_enc:
                missing.append("github_token")
        elif cap == "cap_jira":
            if not integration or not integration.jira_api_token_enc:
                missing.append("jira_api_token")
        elif cap == "cap_slack":
            if not integration or not (integration.slack_webhook_url_enc or integration.slack_bot_token_enc):
                missing.append("slack_webhook_url")
        elif cap == "cap_discord":
            if not integration or not integration.discord_webhook_url_enc:
                missing.append("discord_webhook_url")
        elif cap == "cap_smtp":
            if not integration or not integration.smtp_password_enc:
                missing.append("smtp_password")
                
    return missing
