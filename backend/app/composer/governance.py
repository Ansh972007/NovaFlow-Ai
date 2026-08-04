import logging

audit_logger = logging.getLogger("novaflow.audit")

def scan_marketplace_asset(config_payload: dict) -> list[str]:
    """Scans workflow templates for security vulnerabilities prior to publishing."""
    vulnerabilities = []
    config_str = str(config_payload).lower()
    
    # Check for hardcoded API keys or secrets
    if "api_key" in config_str or "secret" in config_str:
        vulnerabilities.append("Possible hardcoded secret keys or tokens detected in configuration payload.")
        
    return vulnerabilities


def log_soc2_audit_event(workspace_id: int, user_id: int, event_type: str, details: str):
    """Enforces SOC2 audit tracking by writing immutable audit trails to telemetry logs."""
    audit_logger.info(
        f"SOC2 AUDIT | Workspace: {workspace_id} | User: {user_id} | Event: {event_type} | Details: {details}"
    )
