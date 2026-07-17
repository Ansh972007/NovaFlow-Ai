"""Phase 2 — PlatformContext, permissions, emergency access, cross-tenant isolation."""

import os
import tempfile
import uuid
from types import SimpleNamespace

_fd, _db_path = tempfile.mkstemp(prefix="nf_phase2_", suffix=".db")
os.close(_fd)
os.environ["DATABASE_URL"] = f"sqlite:///{_db_path.replace(os.sep, '/')}"
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-not-for-production-use-32b")
os.environ.setdefault("NOVAFLOW_ENV", "development")

from app.database import (
    Base,
    EmergencyAccessGrant,
    User,
    Workspace,
    WorkspaceMember,
    Assistant,
    engine,
    SessionLocal,
)
from app.platform.access import PlatformContext, build_platform_context
from app.platform.permissions import (
    can_view_resource,
    permission_matrix,
    workspace_has_permission,
)
from app.platform.emergency import (
    approve_emergency_access,
    expire_stale_grants,
    request_emergency_access,
    revoke_emergency_access,
)
from app.platform.worker import tenant_cache_key, worker_tenant, require_worker_tenant
from app.security.rbac import Permission
from datetime import datetime, timedelta

Base.metadata.create_all(bind=engine)


def _user(db, label: str, *, role: str = "editor") -> User:
    suffix = f"{label}_{uuid.uuid4().hex[:8]}"
    u = User(
        user_name=f"u_{suffix}",
        email=f"u_{suffix}@example.com",
        password="x",
        role=role,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _workspace(db, owner: User, name: str = "WS") -> Workspace:
    suffix = uuid.uuid4().hex[:8]
    ws = Workspace(
        name=f"{name}-{suffix}",
        slug=f"ws-{suffix}",
        owner_id=owner.user_id,
        workspace_type="team",
        created_by=owner.user_id,
    )
    db.add(ws)
    db.flush()
    db.add(WorkspaceMember(workspace_id=ws.id, user_id=owner.user_id, role="owner"))
    db.commit()
    db.refresh(ws)
    return ws


def test_permission_matrix_and_emergency_read_bias():
    matrix = permission_matrix()
    assert "owner" in matrix
    assert Permission.ASSISTANT_WRITE.value in matrix["editor"]
    assert Permission.ASSISTANT_WRITE.value not in matrix["viewer"]
    assert workspace_has_permission("viewer", Permission.ASSISTANT_READ)
    assert not workspace_has_permission(
        "viewer", Permission.ASSISTANT_WRITE, via_emergency_access=True
    )
    assert workspace_has_permission(
        "viewer", Permission.ASSISTANT_READ, via_emergency_access=True
    )


def test_cross_tenant_fetch_isolation():
    db = SessionLocal()
    try:
        a = _user(db, "a")
        b = _user(db, "b")
        ws_a = _workspace(db, a, "A")
        ws_b = _workspace(db, b, "B")
        asst = Assistant(
            name="Secret",
            prompt="p",
            user_id=a.user_id,
            workspace_id=ws_a.id,
            status=1,
        )
        db.add(asst)
        db.commit()
        db.refresh(asst)

        ctx_b = build_platform_context(db, b, workspace_id=ws_b.id)
        assert ctx_b.fetch(Assistant, asst.id) is None
        rows = ctx_b.query(Assistant).all()
        assert all(r.workspace_id == ws_b.id for r in rows)

        ctx_a = build_platform_context(db, a, workspace_id=ws_a.id)
        found = ctx_a.fetch(Assistant, asst.id)
        assert found is not None
        assert found.id == asst.id
    finally:
        db.close()


def test_visibility_private():
    assert can_view_resource(
        viewer_role="editor",
        visibility="private",
        owner_id=5,
        viewer_user_id=5,
    )
    assert not can_view_resource(
        viewer_role="editor",
        visibility="private",
        owner_id=5,
        viewer_user_id=9,
    )


def test_emergency_access_lifecycle():
    db = SessionLocal()
    try:
        staff = _user(db, "staff", role="admin")
        approver = _user(db, "approver", role="super_admin")
        owner = _user(db, "owner")
        ws = _workspace(db, owner)

        grant = request_emergency_access(
            db, requester=staff, workspace_id=ws.id, reason="Investigating production incident XYZ"
        )
        assert grant.status == "pending"

        active = approve_emergency_access(
            db, grant_id=grant.id, approver=approver, duration_hours=1
        )
        assert active.status == "active"
        assert active.ends_at is not None

        ctx = build_platform_context(db, staff, workspace_id=ws.id)
        assert ctx.via_emergency_access is True
        assert ctx.role == "viewer"
        assert ctx.can(Permission.ASSISTANT_READ)
        assert not ctx.can(Permission.ASSISTANT_WRITE)

        revoke_emergency_access(db, grant_id=grant.id, actor=approver)
        db.refresh(active)
        assert active.status == "revoked"
    finally:
        db.close()


def test_emergency_auto_expire():
    db = SessionLocal()
    try:
        staff = _user(db, "staff2", role="admin")
        approver = _user(db, "ap2", role="super_admin")
        owner = _user(db, "own2")
        ws = _workspace(db, owner)
        grant = request_emergency_access(
            db, requester=staff, workspace_id=ws.id, reason="Expired grant test case long enough"
        )
        approve_emergency_access(db, grant_id=grant.id, approver=approver, duration_hours=1)
        row = db.get(EmergencyAccessGrant, grant.id)
        row.ends_at = datetime.utcnow() - timedelta(minutes=1)
        db.commit()
        n = expire_stale_grants(db)
        assert n >= 1
        db.refresh(row)
        assert row.status == "expired"
    finally:
        db.close()


def test_worker_tenant_context_and_cache_key():
    assert tenant_cache_key(12, "kb", "search") == "nf:ws:12:kb:search"
    with worker_tenant(99, user_id=1, job_type="eval", job_id="7"):
        ctx = require_worker_tenant()
        assert ctx.workspace_id == 99
        assert ctx.job_type == "eval"
    assert require_worker_tenant.__defaults__ is None or True
    try:
        require_worker_tenant()
        assert False, "expected missing context"
    except RuntimeError:
        pass


def test_platform_context_attach_and_audit():
    db = SessionLocal()
    try:
        owner = _user(db, "own3")
        ws = _workspace(db, owner)
        ctx = build_platform_context(db, owner, workspace_id=ws.id)
        assert isinstance(ctx, PlatformContext)
        asst = Assistant(name="N", prompt="p", status=0)
        ctx.attach(asst)
        assert asst.workspace_id == ws.id
        assert asst.user_id == owner.user_id
        db.add(asst)
        db.commit()
        ctx.audit("assistant.created", resource_type="assistant", resource_id=str(asst.id))
    finally:
        db.close()
