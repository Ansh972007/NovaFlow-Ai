import secrets
from urllib.parse import quote

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse, Response
from sqlalchemy.orm import Session

from app.config import FRONTEND_URL
from app.crypto import create_token, hash_password
from app.database import User, get_db
from app.schemas import fail, ok
from app.services.oauth import frontend_callback_url
from app.services.saml_auth import (
    build_saml_login_redirect,
    parse_saml_response,
    saml_enabled,
    saml_status,
    sp_metadata_xml,
)
from app.services.tenancy import ensure_personal_workspace

router = APIRouter(tags=["SAML"])


def _find_or_create_saml_user(db: Session, profile: dict) -> User:
    username = profile["username"]
    user = db.query(User).filter(User.user_name == username).first()
    if not user:
        user = User(
            user_name=username,
            password=hash_password(secrets.token_hex(16)),
            email=(profile.get("email") or "")[:255],
            oauth_provider="saml",
            role="editor",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        ensure_personal_workspace(db, user)
    elif profile.get("email") and not user.email:
        user.email = profile["email"][:255]
        if not user.oauth_provider:
            user.oauth_provider = "saml"
        db.commit()
    return user


@router.get("/auth/saml/status")
def get_saml_status():
    return ok(saml_status())


@router.get("/auth/saml/metadata")
def saml_metadata():
    if not saml_enabled():
        return Response(content="SAML not configured", status_code=404)
    return Response(content=sp_metadata_xml(), media_type="application/xml")


@router.get("/auth/saml/start")
def saml_start():
    url = build_saml_login_redirect()
    if not url:
        return fail(404, "SAML is not configured")
    return RedirectResponse(url)


@router.post("/auth/saml/acs")
async def saml_acs(request: Request, db: Session = Depends(get_db)):
    base = FRONTEND_URL.rstrip("/")
    form = await request.form()
    saml_response = form.get("SAMLResponse")
    if not saml_response:
        return RedirectResponse(f"{base}/login/oauth-callback?error={quote('Missing SAMLResponse')}")

    profile = parse_saml_response(str(saml_response))
    if not profile:
        return RedirectResponse(f"{base}/login/oauth-callback?error={quote('Invalid SAML assertion')}")

    try:
        user = _find_or_create_saml_user(db, profile)
        token = create_token(user.user_id, user.user_name)
        return RedirectResponse(frontend_callback_url(token))
    except Exception as exc:
        return RedirectResponse(f"{base}/login/oauth-callback?error={quote(str(exc))}")
