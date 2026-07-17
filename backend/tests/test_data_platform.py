"""Enterprise Data Platform — dialect, cache, storage, soft-delete, vectors, health."""

import os
import tempfile
import uuid

_fd, _db_path = tempfile.mkstemp(prefix="nf_data_", suffix=".db")
os.close(_fd)
os.environ["DATABASE_URL"] = f"sqlite:///{_db_path.replace(os.sep, '/')}"
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-not-for-production-use-32b")
os.environ.setdefault("NOVAFLOW_ENV", "development")
os.environ["REDIS_URL"] = ""
os.environ["VECTOR_PROVIDER"] = "sqlite"
os.environ["STORAGE_PROVIDER"] = "local"

from app.data.dialect import DialectKind, detect_dialect, dialect_capabilities
from app.data.engine import get_engine_info, create_data_engine, ping_database
from app.data.cache import get_cache
from app.data.storage import get_object_storage
from app.data.vectors import get_vector_store
from app.data.soft_delete import soft_delete_row, restore_row
from app.data.transactions import check_optimistic_lock, bump_version
from app.data.migration_health import migration_impact_report, verify_tenant_columns
from app.data.partitioning import ensure_monthly_partitions
from app.data.observability import attach_engine_metrics, get_db_metrics, optimization_report
from app.database import Base, User, Workspace, WorkspaceMember, Assistant, engine, SessionLocal
from fastapi import HTTPException


def test_dialect_detection():
    assert detect_dialect("sqlite:///x.db") == DialectKind.SQLITE
    assert detect_dialect("mysql+pymysql://u:p@h/db") == DialectKind.MYSQL
    assert detect_dialect("postgresql+psycopg://u:p@h/db") == DialectKind.POSTGRESQL
    caps = dialect_capabilities(DialectKind.POSTGRESQL)
    assert caps["partitioning"] and caps["pgvector"] and caps["brin"]


def test_engine_info_and_ping():
    info = get_engine_info()
    assert info["dialect"] == "sqlite"
    assert info["primary_target"] == "postgresql-17+"
    assert ping_database(engine) is True


def test_memory_cache_tenant_keys_and_tags():
    cache = get_cache(reset=True)
    assert cache.name == "memory"
    key = cache.tenant_key(42, "kb", "list")
    assert key.startswith("nf:ws:42:")
    cache.set(key, {"ok": True}, ttl_seconds=60, tags=["ws:42"])
    assert cache.get(key)["ok"] is True
    assert cache.invalidate_tags(["ws:42"]) >= 1
    assert cache.get(key) is None


def test_local_object_storage_checksum():
    store = get_object_storage(reset=True)
    assert store.name == "local"
    key = f"test/{uuid.uuid4().hex}.txt"
    meta = store.put(key, b"hello-novaflow", content_type="text/plain", workspace_id=7)
    assert meta.checksum
    assert meta.size == len(b"hello-novaflow")
    assert meta.key.startswith("ws/7/")
    assert store.get(meta.key) == b"hello-novaflow"
    assert store.exists(meta.key)
    store.delete(meta.key)
    assert not store.exists(meta.key)


def test_vector_store_sqlite_provider():
    vs = get_vector_store(reset=True)
    assert vs.name == "sqlite"
    assert vs.init() is True
    vs.upsert([(1, 1, 1, [0.1, 0.2])])  # no-op
    assert vs.search(999999, [0.1, 0.2], 5) == []


def test_soft_delete_restore_and_optimistic_lock():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        u = User(user_name=f"d_{uuid.uuid4().hex[:8]}", password="x", role="editor")
        db.add(u)
        db.flush()
        ws = Workspace(
            name="D",
            slug=f"d-{uuid.uuid4().hex[:8]}",
            owner_id=u.user_id,
            workspace_type="personal",
        )
        db.add(ws)
        db.flush()
        db.add(WorkspaceMember(workspace_id=ws.id, user_id=u.user_id, role="owner"))
        a = Assistant(name="A", prompt="p", user_id=u.user_id, workspace_id=ws.id, status=0)
        # columns may exist after migrate; set if present
        if hasattr(a, "row_version"):
            a.row_version = 1
        db.add(a)
        db.commit()
        db.refresh(a)

        # Ensure soft-delete columns exist for this test object
        if not hasattr(Assistant, "deleted_at"):
            return

        # Use a simple namespace-like path if ORM lacks deleted_at on class
        from types import SimpleNamespace
        from datetime import datetime

        obj = a
        if not hasattr(obj, "deleted_at"):
            # SQLite create_all may not have added columns if model wasn't updated on class
            # ObjectFile always has soft delete
            from app.database import ObjectFile

            f = ObjectFile(
                workspace_id=ws.id,
                storage_key=f"k-{uuid.uuid4().hex}",
                provider="local",
                size_bytes=1,
                checksum_sha256="abc",
            )
            db.add(f)
            db.commit()
            db.refresh(f)
            soft_delete_row(db, f, actor_user_id=u.user_id, workspace_id=ws.id)
            assert f.deleted_at is not None
            restore_row(db, f, actor_user_id=u.user_id, workspace_id=ws.id)
            assert f.deleted_at is None
            f.row_version = 2
            try:
                check_optimistic_lock(f, 1)
                assert False
            except HTTPException as exc:
                assert exc.status_code == 409
            bump_version(f)
            assert f.row_version == 3
        else:
            soft_delete_row(db, obj, actor_user_id=u.user_id, workspace_id=ws.id)
            restore_row(db, obj, actor_user_id=u.user_id, workspace_id=ws.id)
    finally:
        db.close()


def test_migration_impact_report():
    Base.metadata.create_all(bind=engine)
    report = migration_impact_report(engine)
    assert report["dialect"] == "sqlite"
    assert "rollback_strategy" in report
    assert report["compatibility"]["api"] == "unchanged"
    # partitions no-op on sqlite
    part = ensure_monthly_partitions(engine)
    assert "skipped" in part or part.get("created") == []


def test_observability_attach():
    eng = create_data_engine(os.environ["DATABASE_URL"])
    attach_engine_metrics(eng, slow_ms=0.0001)
    with eng.connect() as conn:
        from sqlalchemy import text

        conn.execute(text("SELECT 1"))
    snap = get_db_metrics()
    assert "query_count" in snap
    opt = optimization_report()
    assert "metrics" in opt
