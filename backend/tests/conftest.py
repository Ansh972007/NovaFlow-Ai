import pytest
import os
import tempfile
from pathlib import Path
from sqlalchemy.orm import close_all_sessions

# Shared isolated environment for all test modules
_TEST_DIR = Path(tempfile.mkdtemp(prefix="novaflow-test-global-"))
# Strong test-only credentials (never use in production docs)
TEST_ADMIN_PASSWORD = "NfTest!Admin9xPass!!"
os.environ["DATA_DIR"] = str(_TEST_DIR)
os.environ["DATABASE_URL"] = f"sqlite:///{(_TEST_DIR / 'test.db').as_posix()}"
os.environ["JWT_SECRET"] = "novaflow-test-secret-not-for-production-use-32b"
os.environ["NOVAFLOW_DEMO_SEED"] = "0"
os.environ["MILVUS_URI"] = ""
os.environ["NOVAFLOW_ADMIN_USER"] = "admin"
os.environ["NOVAFLOW_ADMIN_PASSWORD"] = TEST_ADMIN_PASSWORD
os.environ["NOVAFLOW_ENV"] = "development"
os.environ["ALLOW_PUBLIC_REGISTER"] = "1"
os.environ["ALLOW_PASSWORD_LOGIN"] = "1"
os.environ["GMAIL_ONLY_AUTH"] = "1"

from app.database import Base, engine, SessionLocal, User
from app.crypto import hash_password
from app.services.tenancy import ensure_personal_workspace
import app.crypto


@pytest.fixture(autouse=True)
def clean_db_and_keys():
    app.crypto._keys = None

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        admin = User(
            user_name="admin",
            password=hash_password(TEST_ADMIN_PASSWORD),
            email="admin-test@gmail.com",
            role="super_admin",
            must_change_password=0,
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
        ensure_personal_workspace(db, admin)
    finally:
        db.close()

    yield
    close_all_sessions()
