import logging

logger = logging.getLogger("novaflow.healing")

def execute_with_healing(cap_func, fallback_func, *args, **kwargs) -> dict:
    """Executes a capability call, catching timeouts or rate limit failures and routing to local fallbacks."""
    try:
        result = cap_func(*args, **kwargs)
        return {
            "status": "success",
            "result": result,
            "routing": "primary",
            "healed": False
        }
    except Exception as e:
        logger.warning(f"AIOS Kernel: Primary call failed: {e}. Initiating Self-Healing failover route.")
        try:
            fallback_res = fallback_func(*args, **kwargs)
            return {
                "status": "success",
                "result": fallback_res,
                "routing": "local_fallback",
                "healed": True,
                "healing_reason": str(e)
            }
        except Exception as fe:
            logger.critical(f"AIOS Kernel: Primary and fallback calls failed: {fe}")
            return {
                "status": "failed",
                "routing": "none",
                "healed": False,
                "error": str(fe)
            }
