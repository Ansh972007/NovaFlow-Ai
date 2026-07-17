import hashlib
import secrets

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import ApiKey, get_db
from app.deps import require_permission
from app.schemas import fail, ok
from app.security.rbac import Permission

router = APIRouter(tags=["API Keys"])


def _hash_key(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


@router.get("/api-keys")
def list_api_keys(db: Session = Depends(get_db), ctx=Depends(require_permission(Permission.API_KEY_MANAGE))):
    rows = (
        ctx.query(ApiKey)
        .filter(ApiKey.user_id == ctx.user.user_id)
        .order_by(ApiKey.create_time.desc())
        .all()
    )
    return ok(
        [
            {
                "id": k.id,
                "name": k.name,
                "key_prefix": k.key_prefix,
                "create_time": k.create_time.isoformat() if k.create_time else None,
            }
            for k in rows
        ]
    )


@router.post("/api-keys")
def create_api_key(body: dict, db: Session = Depends(get_db), ctx=Depends(require_permission(Permission.API_KEY_MANAGE))):
    name = (body.get("name") or "API key").strip()[:80]
    raw = f"nf_{secrets.token_urlsafe(32)}"
    row = ApiKey(
        name=name,
        key_prefix=raw[:12],
        key_hash=_hash_key(raw),
    )
    ctx.attach(row)
    db.add(row)
    db.commit()
    db.refresh(row)
    ctx.audit("apikey.created", resource_type="api_key", resource_id=str(row.id))
    return ok({"id": row.id, "name": name, "key": raw, "key_prefix": row.key_prefix})


@router.post("/api-keys/delete")
def delete_api_key(
    key_id: int = None,
    body: dict = None,
    db: Session = Depends(get_db),
    ctx=Depends(require_permission(Permission.API_KEY_MANAGE)),
):
    kid = key_id or (body or {}).get("id")
    row = ctx.fetch(ApiKey, kid)
    if not row or row.user_id != ctx.user.user_id:
        return fail(404, "API key not found")
    db.delete(row)
    db.commit()
    ctx.audit("apikey.deleted", resource_type="api_key", resource_id=str(kid))
    return ok(None)
