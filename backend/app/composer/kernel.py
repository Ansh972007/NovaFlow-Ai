from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import AIOSKernelConfig, get_db
from app.deps import require_permission
from app.schemas import ok
from app.security.rbac import Permission

router = APIRouter(tags=["AIOS Kernel"])


@router.get("/aios/kernel/status")
def get_kernel_status(
    db: Session = Depends(get_db),
    ctx=Depends(require_permission(Permission.WORKSPACE_READ)),
):
    """Retrieve the core AIOS Kernel configuration and operational heartbeat state."""
    config = db.query(AIOSKernelConfig).first()
    if not config:
        config = AIOSKernelConfig(active_provider_id=None, heartbeat_interval=30)
        db.add(config)
        db.commit()
        db.refresh(config)

    return ok(
        {
            "kernel_version": "12.2.0",
            "status": "active",
            "registered_capabilities_count": 22,
            "active_workers_count": 12,
            "active_provider_id": config.active_provider_id,
            "heartbeat_interval": config.heartbeat_interval,
            "updated_at": config.updated_at.isoformat() if config.updated_at else None,
        }
    )
