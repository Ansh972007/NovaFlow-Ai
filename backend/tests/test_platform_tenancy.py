"""Multi-tenant platform kernel — roles, scoping, invites."""

import os
import tempfile
import uuid
from types import SimpleNamespace

# Isolated DB before app.database binds the engine
_fd, _db_path = tempfile.mkstemp(prefix="nf_platform_", suffix=".db")
os.close(_fd)
os.environ["DATABASE_URL"] = f"sqlite:///{_db_path.replace(os.sep, '/')}"
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-not-for-production-use-32b")
os.environ.setdefault("NOVAFLOW_ENV", "development")

from app.platform.roles import (
    WORKSPACE_ROLES,
    has_workspace_min_role,
    normalize_workspace_role,
    workspace_role_rank,
)
from app.platform.scoping import attach_tenant_fields, require_same_workspace, scoped_query
from app.platform.invites import create_invite, accept_invite, revoke_invite, list_invites
from app.database import (
    Base,
    User,
    Workspace,
    WorkspaceInvite,
    WorkspaceMember,
    Team,
    engine,
    SessionLocal,
)

Base.metadata.create_all(bind=engine)


def test_workspace_role_ladder():
    assert "owner" in WORKSPACE_ROLES
    assert workspace_role_rank("owner") > workspace_role_rank("admin")
    assert workspace_role_rank("admin") > workspace_role_rank("viewer")
    assert has_workspace_min_role("manager", "editor")
    assert not has_workspace_min_role("guest", "viewer")
    assert normalize_workspace_role("workspace_owner") == "owner"
    assert normalize_workspace_role("unknown_role_xyz") == "viewer"


def _fresh_user_ws(db, label: str):
    suffix = f"{label}_{uuid.uuid4().hex[:10]}"
    u = User(
        user_name=f"tenant_{suffix}",
        email=f"tenant_{suffix}@example.com",
        password="x",
        role="user",
    )
    db.add(u)
    db.flush()
    ws = Workspace(
        name=f"WS {suffix}",
        slug=f"ws-{suffix}",
        owner_id=u.user_id,
        workspace_type="team",
        created_by=u.user_id,
        updated_by=u.user_id,
    )
    db.add(ws)
    db.flush()
    db.add(
        WorkspaceMember(
            workspace_id=ws.id,
            user_id=u.user_id,
            role="owner",
        )
    )
    db.commit()
    db.refresh(u)
    db.refresh(ws)
    return u, ws


def test_scoped_query_filters_workspace():
    db = SessionLocal()
    try:
        u1, ws1 = _fresh_user_ws(db, "a")
        u2, ws2 = _fresh_user_ws(db, "b")
        t1 = Team(workspace_id=ws1.id, name="General", slug=f"general-{ws1.id}", created_by=u1.user_id)
        t2 = Team(workspace_id=ws2.id, name="Other", slug=f"other-{ws2.id}", created_by=u2.user_id)
        db.add_all([t1, t2])
        db.commit()

        rows = scoped_query(db, Team, ws1.id).all()
        assert len(rows) >= 1
        assert all(r.workspace_id == ws1.id for r in rows)
        assert not any(r.workspace_id == ws2.id for r in rows)

        obj = Team(name="Attached", slug=f"att-{ws1.id}")
        attach_tenant_fields(obj, workspace_id=ws1.id, user_id=u1.user_id)
        assert obj.workspace_id == ws1.id
        assert obj.created_by == u1.user_id
    finally:
        db.close()


def test_require_same_workspace_opaque():
    resource = SimpleNamespace(workspace_id=10)
    require_same_workspace(resource, 10)
    try:
        require_same_workspace(resource, 99)
        assert False, "expected 404"
    except Exception as exc:
        assert getattr(exc, "status_code", None) == 404


def test_invite_lifecycle():
    db = SessionLocal()
    try:
        owner, ws = _fresh_user_ws(db, "inv")
        suffix = uuid.uuid4().hex[:10]
        invitee = User(
            user_name=f"invitee_{suffix}",
            email=f"invitee_{suffix}@example.com",
            password="x",
            role="user",
        )
        db.add(invitee)
        db.commit()
        db.refresh(invitee)

        invite, token = create_invite(
            db, workspace=ws, email=invitee.email, role="editor", invited_by=owner
        )
        assert invite.status == "pending"
        assert token
        pending = [i for i in list_invites(db, ws.id) if i.status == "pending"]
        assert any(i.id == invite.id for i in pending)

        member = accept_invite(db, token=token, user=invitee)
        assert member.workspace_id == ws.id
        assert member.role == "editor"

        invite2, _ = create_invite(
            db,
            workspace=ws,
            email=f"other_{suffix}@example.com",
            role="viewer",
            invited_by=owner,
        )
        revoke_invite(db, invite_id=invite2.id, workspace_id=ws.id, actor=owner)
        row = db.get(WorkspaceInvite, invite2.id)
        assert row.status == "revoked"
    finally:
        db.close()
