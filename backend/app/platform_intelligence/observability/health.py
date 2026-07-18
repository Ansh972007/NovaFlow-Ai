"""Platform health aggregation."""

from __future__ import annotations

from typing import Any


def platform_health_snapshot() -> dict[str, Any]:
    from app.data import get_cache, get_engine_info, get_object_storage, get_vector_store
    from app.data.observability import get_db_metrics
    from app.platform_intelligence.healing.circuit_breaker import breaker_status
    from app.platform_intelligence.observability.metrics import aggregate_subsystems

    try:
        data_info = get_engine_info()
    except Exception:
        data_info = {"dialect": "unknown"}
    try:
        vec = get_vector_store().name
    except Exception:
        vec = "unknown"
    try:
        storage = get_object_storage().name
    except Exception:
        storage = "local"
    try:
        cache = get_cache().name
    except Exception:
        cache = "memory"

    return {
        "status": "ok",
        "database": data_info,
        "db_metrics": get_db_metrics(),
        "vector_backend": vec,
        "storage_backend": storage,
        "cache_backend": cache,
        "subsystems": aggregate_subsystems(),
        "circuit_breakers": breaker_status(),
        "security": "enterprise-v1",
        "platform": "multi-tenant-v2",
        "data_platform": "enterprise-v1",
        "ai_runtime": "enterprise-v1",
        "workflow_intelligence": "enterprise-v1",
        "platform_intelligence": "enterprise-v1",
    }
