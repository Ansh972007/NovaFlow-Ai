from urllib.parse import quote

from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.config import FRONTEND_URL
from app.crypto import create_token
from app.database import get_db
from app.schemas import fail, ok
from app.services.oauth import (
    build_authorize_url,
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
def oauth_start(provider: str, db: Session = Depends(get_db)):
    url = build_authorize_url(provider, db)
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

    base = FRONTEND_URL.rstrip("/")
    if error:
        return RedirectResponse(f"{base}/login/oauth-callback?error={quote(error)}")

    if GMAIL_ONLY_AUTH and provider != "google":
        return RedirectResponse(
            f"{base}/login/oauth-callback?error={quote('Only Google (Gmail) sign-in is allowed')}"
        )

    if provider not in {"google", "microsoft"}:
        return RedirectResponse(f"{base}/login/oauth-callback?error={quote('Unknown provider')}")
    if not code or not state or not verify_oauth_state(state, provider):
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
        return RedirectResponse(frontend_callback_url(token))
    except Exception as exc:
        return RedirectResponse(f"{base}/login/oauth-callback?error={quote(str(exc))}")
