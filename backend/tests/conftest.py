import pytest
import os
import tempfile
from pathlib import Path
from sqlalchemy.orm import close_all_sessions

# Set shared isolated environment variables for all test modules
_TEST_DIR = Path(tempfile.mkdtemp(prefix="novaflow-test-global-"))
os.environ["DATA_DIR"] = str(_TEST_DIR)
os.environ["DATABASE_URL"] = f"sqlite:///{(_TEST_DIR / 'test.db').as_posix()}"
os.environ["JWT_SECRET"] = "novaflow-test-secret"
os.environ["NOVAFLOW_DEMO_SEED"] = "0"
os.environ["MILVUS_URI"] = ""
os.environ["NOVAFLOW_ADMIN_USER"] = "admin"
os.environ["NOVAFLOW_ADMIN_PASSWORD"] = "admin123"

# Force imports to use these variables
from app.database import Base, engine, SessionLocal, User
from app.crypto import hash_password
from app.services.tenancy import ensure_personal_workspace
import app.crypto

@pytest.fixture(autouse=True)
def clean_db_and_keys():
    # Force reset of cached RSA keys so they align with the current test session directory
    app.crypto._keys = None
    
    # Drop all existing tables and re-create schema for a fresh, isolated state
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    # Seed the baseline super_admin user required by verification suites
    db = SessionLocal()
    try:
        admin = User(
            user_name="admin",
            password=hash_password("admin123"),
            role="super_admin",
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
        ensure_personal_workspace(db, admin)
    finally:
        db.close()
        
    yield
    
    # Close any open connections to release file locks on SQLite
    close_all_sessions()
