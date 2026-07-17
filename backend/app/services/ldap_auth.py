import secrets

from app.config import LDAP_BASE_DN, LDAP_BIND_DN, LDAP_BIND_PASSWORD, LDAP_URL, LDAP_USER_FILTER


def ldap_enabled() -> bool:
    return bool(LDAP_URL.strip() and LDAP_BASE_DN.strip())


def ldap_status() -> dict:
    return {
        "enabled": ldap_enabled(),
        "url": LDAP_URL if ldap_enabled() else "",
        "base_dn": LDAP_BASE_DN if ldap_enabled() else "",
    }


def authenticate_ldap(username: str, password: str) -> dict | None:
    if not ldap_enabled() or not username or not password:
        return None
    try:
        import ldap3
    except ImportError:
        raise RuntimeError("ldap3 package not installed")

    user_filter = LDAP_USER_FILTER.replace("{username}", ldap3.utils.conv.escape_filter_chars(username))
    server = ldap3.Server(LDAP_URL, get_info=ldap3.NONE)
    conn = ldap3.Connection(server, user=LDAP_BIND_DN or None, password=LDAP_BIND_PASSWORD or None, auto_bind=True)
    conn.search(LDAP_BASE_DN, user_filter, attributes=["cn", "mail", "uid", "sAMAccountName"])
    if not conn.entries:
        return None
    entry = conn.entries[0]
    user_dn = entry.entry_dn
    user_conn = ldap3.Connection(server, user=user_dn, password=password, auto_bind=False)
    if not user_conn.bind():
        return None
    name = str(getattr(entry, "cn", username) or username)
    email = str(getattr(entry, "mail", "") or "")
    return {"dn": user_dn, "name": name, "email": email, "username": username}


def find_or_create_ldap_user(db, username: str, profile: dict) -> "User":
    from app.database import User
    from app.crypto import hash_password
    from app.services.tenancy import ensure_personal_workspace

    user = db.query(User).filter(User.user_name == username).first()
    if not user:
        user = User(
            user_name=username,
            password=hash_password(secrets.token_hex(16)),
            email=(profile.get("email") or "")[:255],
            role="editor",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        ensure_personal_workspace(db, user)
    elif profile.get("email") and not user.email:
        user.email = profile["email"][:255]
        db.commit()
    return user
