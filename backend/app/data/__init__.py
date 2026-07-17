"""
NovaFlow Enterprise Data Platform.

Application modules MUST depend on this package — never on a specific
database vendor, object-store vendor, or vector engine.

Primary target: PostgreSQL 17+
Compatible runtimes: SQLite (dev), MySQL 8 (legacy Docker), PostgreSQL 17+
"""

from app.data.dialect import DialectKind, detect_dialect
from app.data.engine import get_engine_info, create_data_engine
from app.data.soft_delete import purge_permanently, restore_row, soft_delete_row
from app.data.cache import get_cache
from app.data.storage import get_object_storage
from app.data.vectors import get_vector_store

__all__ = [
    "DialectKind",
    "detect_dialect",
    "get_engine_info",
    "create_data_engine",
    "soft_delete_row",
    "restore_row",
    "purge_permanently",
    "get_cache",
    "get_object_storage",
    "get_vector_store",
]
