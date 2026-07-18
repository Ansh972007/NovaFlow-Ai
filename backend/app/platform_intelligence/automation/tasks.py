"""Platform automation — maintenance tasks."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

logger = logging.getLogger("novaflow.platform.automation")


def purge_old_metrics(db: Session, *, days: int = 90) -> int:
    from app.database import PlatformMetric

    cutoff = datetime.utcnow() - timedelta(days=days)
    count = db.query(PlatformMetric).filter(PlatformMetric.create_time < cutoff).delete()
    db.commit()
    return count


def purge_old_events(db: Session, *, days: int = 180) -> int:
    from app.database import PlatformEvent

    cutoff = datetime.utcnow() - timedelta(days=days)
    count = db.query(PlatformEvent).filter(PlatformEvent.create_time < cutoff).delete()
    db.commit()
    return count


def compact_cache_tags(workspace_id: int) -> int:
    from app.data.cache import get_cache

    try:
        return get_cache().invalidate_tags([f"ws:{workspace_id}"])
    except Exception:
        return 0


def run_integrity_check(db: Session) -> dict:
    from app.data.migration_health import post_migration_verify
    from app.database import engine

    report = post_migration_verify(engine)
    return {"migration_health": report, "checked_at": datetime.utcnow().isoformat()}


async def platform_maintenance_tick() -> None:
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        m = purge_old_metrics(db, days=90)
        e = purge_old_events(db, days=180)
        integrity = run_integrity_check(db)
        logger.info("Platform maintenance: metrics_purged=%s events_purged=%s", m, e)
    except Exception as exc:
        logger.warning("Platform maintenance failed: %s", exc)
    finally:
        db.close()
