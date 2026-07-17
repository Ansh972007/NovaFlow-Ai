"""Transaction helpers — deadlock retry, optimistic locking, idempotency."""

from __future__ import annotations

import logging
import random
import time
from functools import wraps
from typing import Any, Callable, TypeVar

from fastapi import HTTPException
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

logger = logging.getLogger("novaflow.data.transactions")

F = TypeVar("F", bound=Callable[..., Any])


def with_deadlock_retry(max_attempts: int = 3, base_delay: float = 0.05) -> Callable[[F], F]:
    def decorator(fn: F) -> F:
        @wraps(fn)
        def wrapper(*args, **kwargs):
            last: Exception | None = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return fn(*args, **kwargs)
                except OperationalError as exc:
                    last = exc
                    msg = str(exc).lower()
                    if "deadlock" not in msg and "lock wait" not in msg and "serialization" not in msg:
                        raise
                    if attempt >= max_attempts:
                        raise
                    delay = base_delay * (2 ** (attempt - 1)) + random.uniform(0, 0.05)
                    logger.warning("Deadlock/retryable lock on %s attempt %s: %s", fn.__name__, attempt, exc)
                    time.sleep(delay)
            assert last is not None
            raise last

        return wrapper  # type: ignore[return-value]

    return decorator


def check_optimistic_lock(obj: Any, expected_version: int | None) -> None:
    if expected_version is None or not hasattr(obj, "row_version"):
        return
    current = int(getattr(obj, "row_version") or 1)
    if current != int(expected_version):
        raise HTTPException(
            status_code=409,
            detail=f"Optimistic lock conflict: expected version {expected_version}, found {current}",
        )


def bump_version(obj: Any) -> None:
    if hasattr(obj, "row_version"):
        obj.row_version = int(getattr(obj, "row_version") or 1) + 1


def transactional(db: Session, fn: Callable[[], Any]) -> Any:
    """Run fn inside the current session; commit on success, rollback on error."""
    try:
        result = fn()
        db.commit()
        return result
    except Exception:
        db.rollback()
        raise
