def assign_digital_employee_role(workspace_id: int, agent_id: str, corporate_role: str, target_kpis: list[str]) -> dict:
    """Configures agents as digital employee entities with structured KPI and tool bounds."""
    return {
        "workspace_id": workspace_id,
        "agent_id": agent_id,
        "role": corporate_role,
        "kpis": target_kpis,
        "status": "onboarded"
    }
