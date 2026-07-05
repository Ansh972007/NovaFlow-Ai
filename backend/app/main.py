from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import ADMIN_PASSWORD, ADMIN_USER, DATA_DIR, DEMO_SEED
from app.crypto import md5_hash
from app.database import SessionLocal, User, init_db
from app.routers import analytics, assistant, auth_oauth, chat_ws, knowledge, llm, user, workflow, workspace
from app.services.demo_seed import seed_demo_data
from app.services.llm_providers import ensure_default_provider
from app.services.tenancy import ensure_personal_workspace
from app.services.workspace_settings import load_settings
from app.services.vector_store import init_vector_store, vector_backend
from app.schemas import ok

API_PREFIX = "/api/v1"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    init_db()
    db = SessionLocal()
    try:
        if db.query(User).count() == 0:
            admin = User(
                user_name=ADMIN_USER,
                password=md5_hash(ADMIN_PASSWORD),
                role="admin",
            )
            db.add(admin)
            db.commit()
            db.refresh(admin)
            ensure_personal_workspace(db, admin)
            print(f"[NovaFlow] Default admin: {ADMIN_USER} / (see NOVAFLOW_ADMIN_PASSWORD)")
        if DEMO_SEED:
            seed_demo_data(db)
        load_settings(db)
        ensure_default_provider(db)
    finally:
        db.close()
    init_vector_store()
    yield


app = FastAPI(title="NovaFlow API", version="1.5.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(user.router, prefix=API_PREFIX)
app.include_router(auth_oauth.router, prefix=API_PREFIX)
app.include_router(assistant.router, prefix=API_PREFIX)
app.include_router(knowledge.router, prefix=API_PREFIX)
app.include_router(llm.router, prefix=API_PREFIX)
app.include_router(workflow.router, prefix=API_PREFIX)
app.include_router(analytics.router, prefix=API_PREFIX)
app.include_router(workspace.router, prefix=API_PREFIX)
app.include_router(chat_ws.router, prefix=API_PREFIX)


@app.get("/health")
def health():
    return ok(
        {
            "service": "novaflow-api",
            "status": "ok",
            "version": "1.5.0",
            "vector_backend": vector_backend(),
        }
    )


@app.get("/")
def root():
    return ok({"name": "NovaFlow API", "version": "1.5.0"})
