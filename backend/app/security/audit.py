"""Immutable security audit logging."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Optional

from sqlalchemy.orm import Session

logger = logging.getLogger("novaflow.security.audit")


def audit_log(
    db: Optional[Session],
    *,
    action: str,
    actor_user_id: Optional[int] = None,
    workspace_id: Optional[int] = None,
    resource_type: str = "",
    resource_id: str = "",
    ip: str = "",
    user_agent: str = "",
    success: bool = True,
    detail: Optional[dict[str, Any]] = None,
) -> None:
    """Persist an audit event. Never raises to callers — logging must not break auth."""
    payload = {
        "ts": datetime.utcnow().isoformat() + "Z",
        "action": action,
        "actor_user_id": actor_user_id,
        "workspace_id": workspace_id,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "ip": ip,
        "success": success,
        "detail": detail or {},
    }
    try:
        logger.info("AUDIT %s", json.dumps(payload, default=str))
    except Exception:
        pass

    if db is None:
        return
    try:
        from app.database import SecurityAuditLog

        row = SecurityAuditLog(
            action=action[:120],
            actor_user_id=actor_user_id,
            workspace_id=workspace_id,
            resource_type=(resource_type or "")[:64],
            resource_id=(resource_id or "")[:128],
            ip_address=(ip or "")[:64],
            user_agent=(user_agent or "")[:512],
            success=1 if success else 0,
            detail_json=json.dumps(detail or {}, default=str)[:8000],
            created_at=datetime.utcnow(),
        )
        db.add(row)
        db.commit()
    except Exception as exc:
        logger.warning("Failed to persist audit log: %s", exc)
        try:
            db.rollback()
        except Exception:
            pass
