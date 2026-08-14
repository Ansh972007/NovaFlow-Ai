from urllib.parse import quote

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.config import FRONTEND_URL
from app.crypto import create_token
from app.database import get_db
from app.schemas import fail, ok
from app.services.oauth import (
    build_authorize_url,
    decode_oauth_state,
    exchange_code,
    fetch_userinfo,
    find_or_create_oauth_user,
    frontend_callback_url,
    list_enabled_providers,
    verify_oauth_state,
)

router = APIRouter(tags=["OAuth"])


@router.get("/auth/oauth/providers")
def oauth_providers(db: Session = Depends(get_db)):
    return ok(list_enabled_providers(db))


@router.get("/auth/oauth/{provider}/start")
def oauth_start(
    provider: str,
    return_to: str | None = None,
    request: Request = None,
    db: Session = Depends(get_db),
):
    if not return_to and request:
        ref = request.headers.get("referer") or request.headers.get("origin")
        if ref and "://" in ref:
            scheme, rest = ref.split("://", 1)
            host = rest.split("/")[0]
            return_to = f"{scheme}://{host}"

    url = build_authorize_url(provider, db, return_to=return_to)
    if not url:
        return fail(404, f"OAuth provider '{provider}' is not configured")
    return RedirectResponse(url)


@router.get("/auth/oauth/{provider}/callback")
async def oauth_callback(
    provider: str,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
):
    from app.config import GMAIL_ONLY_AUTH

    state_data = decode_oauth_state(state, provider) if state else None
    base = (
        (state_data.get("return_to") if state_data else None)
        or FRONTEND_URL
        or "http://localhost:3000"
    ).rstrip("/")

    if error:
        return RedirectResponse(f"{base}/login/oauth-callback?error={quote(error)}")

    if GMAIL_ONLY_AUTH and provider != "google":
        return RedirectResponse(
            f"{base}/login/oauth-callback?error={quote('Only Google (Gmail) sign-in is allowed')}"
        )

    if provider not in {"google", "microsoft"}:
        return RedirectResponse(f"{base}/login/oauth-callback?error={quote('Unknown provider')}")
    if not code or not state or not state_data:
        return RedirectResponse(f"{base}/login/oauth-callback?error={quote('Invalid OAuth state')}")

    try:
        token_data = await exchange_code(provider, code, db)
        profile = await fetch_userinfo(provider, token_data, db)
        user = find_or_create_oauth_user(
            db,
            provider,
            profile["sub"],
            profile.get("email"),
            profile.get("name") or "",
        )
        token = create_token(user.user_id, user.user_name)
        return RedirectResponse(frontend_callback_url(token, base_url=base))
    except Exception as exc:
        return RedirectResponse(f"{base}/login/oauth-callback?error={quote(str(exc))}")
