"""Engine factory — pool / PgBouncer / dialect-aware connect args."""

from __future__ import annotations

from typing import Any

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine

from app.data.config import load_data_config
from app.data.dialect import DialectKind, detect_dialect, dialect_capabilities


def create_data_engine(database_url: str | None = None, **overrides: Any) -> Engine:
    """Create a SQLAlchemy engine with production pool settings.

    When DB_PGBOUNCER_MODE=1, uses NullPool (PgBouncer owns pooling).
    """
    from sqlalchemy.pool import NullPool, QueuePool

    cfg = load_data_config()
    url = database_url or cfg.database_url
    kind = detect_dialect(url)
    connect_args: dict[str, Any] = {}
    if kind == DialectKind.SQLITE:
        connect_args["check_same_thread"] = False

    engine_kwargs: dict[str, Any] = {
        "pool_pre_ping": True,
        "connect_args": connect_args,
    }

    if cfg.enable_pgbouncer_mode or kind == DialectKind.SQLITE:
        engine_kwargs["poolclass"] = NullPool if cfg.enable_pgbouncer_mode else QueuePool
        if not cfg.enable_pgbouncer_mode and kind == DialectKind.SQLITE:
            engine_kwargs.pop("poolclass", None)
    else:
        engine_kwargs.update(
            {
                "pool_size": overrides.get("pool_size", cfg.pool_size),
                "max_overflow": overrides.get("max_overflow", cfg.max_overflow),
                "pool_timeout": overrides.get("pool_timeout", cfg.pool_timeout),
                "pool_recycle": overrides.get("pool_recycle", cfg.pool_recycle),
            }
        )

    engine = create_engine(url, **engine_kwargs)

    if kind == DialectKind.POSTGRESQL and cfg.statement_timeout_ms > 0:

        @event.listens_for(engine, "connect")
        def _set_pg_timeout(dbapi_conn, connection_record):  # noqa: ANN001
            try:
                with dbapi_conn.cursor() as cur:
                    cur.execute(f"SET statement_timeout = {int(cfg.statement_timeout_ms)}")
            except Exception:
                pass

    return engine


def get_engine_info(engine: Engine | None = None) -> dict:
    cfg = load_data_config()
    url = cfg.database_url
    kind = detect_dialect(url)
    # redact credentials
    safe = url
    if "@" in url:
        try:
            scheme, rest = url.split("://", 1)
            creds, hostpart = rest.split("@", 1)
            safe = f"{scheme}://***:***@{hostpart}"
        except ValueError:
            safe = scheme_part_redacted(url)
    return {
        "dialect": kind.value,
        "url": safe,
        "capabilities": dialect_capabilities(kind),
        "pgbouncer_mode": cfg.enable_pgbouncer_mode,
        "pool_size": cfg.pool_size,
        "vector_provider": cfg.vector_provider,
        "storage_provider": cfg.storage_provider,
        "primary_target": "postgresql-17+",
    }


def scheme_part_redacted(url: str) -> str:
    return "redacted"


def ping_database(engine: Engine) -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
