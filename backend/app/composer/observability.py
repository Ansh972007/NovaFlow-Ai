import logging
from sqlalchemy.orm import Session
from app.database import CostLedger

logger = logging.getLogger("novaflow.observability")

def log_execution_telemetry(db: Session, workspace_id: int, solution_id: str, latency_ms: int, tokens: int, cost_usd: float):
    """Enforce real-time metric tracking for Solution Graph runs by appending to the FinOps ledger."""
    try:
        ledger = CostLedger(
            workspace_id=workspace_id,
            action=f"AIOS Run: {solution_id}",
            cost=cost_usd,
            status=1,
        )
        db.add(ledger)
        db.commit()
    except Exception as e:
        logger.error(f"Failed to log cost ledger telemetry: {e}")
        
    logger.info(
        f"AIOS METRICS | Solution: {solution_id} | Latency: {latency_ms}ms | Tokens: {tokens} | Cost: ${cost_usd:.6f}"
    )
