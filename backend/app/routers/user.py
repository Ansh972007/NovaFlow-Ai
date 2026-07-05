from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.crypto import create_token, decrypt_password, decrypt_password_plain, get_public_key_pem, md5_hash
from app.database import User, get_db
from app.deps import get_current_user
from app.schemas import UserCreate, UserLogin, UserPasswordChange, fail, ok

router = APIRouter(tags=["User"])


def user_read(user: User, access_token: str | None = None) -> dict:
    return {
        "user_id": user.user_id,
        "user_name": user.user_name,
        "email": None,
        "delete": user.delete,
        "role": user.role or ("admin" if user.user_id == 1 else "editor"),
        "access_token": access_token,
        "create_time": user.create_time.isoformat() if user.create_time else None,
        "update_time": user.update_time.isoformat() if user.update_time else None,
    }


@router.get("/user/public_key")
def public_key():
    return ok({"public_key": get_public_key_pem()})


@router.post("/user/regist")
def register(body: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.user_name == body.user_name).first():
        return fail(500, "Username already exists")
    user = User(
        user_name=body.user_name,
        password=decrypt_password(body.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_token(user.user_id, user.user_name)
    return ok(user_read(user, token))


@router.post("/user/login")
def login(body: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.user_name == body.user_name).first()
    if not user:
        return {"status_code": 403, "status_message": "Invalid username or password", "data": None}
    try:
        pwd_hash = decrypt_password(body.password)
    except Exception:
        return {"status_code": 403, "status_message": "Invalid username or password", "data": None}
    if user.password != pwd_hash:
        return {"status_code": 403, "status_message": "Invalid username or password", "data": None}
    token = create_token(user.user_id, user.user_name)
    return ok(user_read(user, token))


@router.get("/user/info")
def user_info(user: User = Depends(get_current_user)):
    return ok(user_read(user))


@router.post("/user/logout")
def logout():
    return ok(None)


@router.post("/user/password")
def change_password(
    body: UserPasswordChange,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        current_hash = decrypt_password(body.current_password)
    except Exception:
        return fail(403, "Current password is incorrect")
    if user.password != current_hash:
        return fail(403, "Current password is incorrect")
    try:
        plain_new = decrypt_password_plain(body.new_password)
    except Exception:
        return fail(400, "Invalid new password")
    if len(plain_new.strip()) < 6:
        return fail(400, "New password must be at least 6 characters")
    user.password = md5_hash(plain_new.strip())
    user.update_time = datetime.utcnow()
    db.commit()
    return ok(None)
