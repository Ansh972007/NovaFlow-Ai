import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import ADMIN_PASSWORD, ADMIN_USER, DATA_DIR, DEMO_SEED
from app.crypto import hash_password
from app.database import SessionLocal, User, init_db
from app.routers import (
    analytics,
    api_keys,
    assistant,
    auth_oauth,
    auth_saml,
    agents,
    chat_ws,
    emergency,
    evaluation,
    finetune,
    integrations,
    knowledge,
    llm,
    marketplace,
    model_lab,
    projects,
    user,
    workflow,
    workspace,
    notifications,
)
from app.workflow_intelligence.router import router as workflow_intelligence_router
from app.platform_intelligence.router import router as platform_intelligence_router
from app.conversation.router import router as conversation_router
from app.knowledge_os.router import router as knowledge_os_router
from app.agent_os.router import router as agent_os_router
from app.connectivity.router import router as connectivity_router
from app.eiap.router import router as eiap_router
from app.platform_intelligence.tracing.middleware import TraceMiddleware
from app.schemas import ok
from app.security.config import (
    CORS_ALLOWED_ORIGINS,
    assert_production_bootstrap_safe,
    require_secure_jwt_secret,
)
from app.security.middleware import SecurityHeadersMiddleware
from app.services.demo_seed import seed_demo_data
from app.services.llm_providers import ensure_default_provider
from app.services.tenancy import ensure_personal_workspace
from app.services.workspace_settings import load_settings
from app.services.vector_store import init_vector_store, vector_backend

API_PREFIX = "/api/v1"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    require_secure_jwt_secret()
    assert_production_bootstrap_safe(ADMIN_PASSWORD)
    init_db()
    db = SessionLocal()
    try:
        if db.query(User).count() == 0:
            admin = User(
                user_name=ADMIN_USER,
                password=hash_password(ADMIN_PASSWORD),
                role="super_admin",
            )
            db.add(admin)
            db.commit()
            db.refresh(admin)
            ensure_personal_workspace(db, admin)
            print(f"[NovaFlow] Default admin created: {ADMIN_USER}")
        if DEMO_SEED:
            seed_demo_data(db)
        load_settings(db)
        ensure_default_provider(db)
    finally:
        db.close()
    init_vector_store()

    from app.services.eval_scheduler import background_scheduler_loop

    stop_event = asyncio.Event()
    scheduler_task = asyncio.create_task(background_scheduler_loop(stop_event))
    yield
    stop_event.set()
    scheduler_task.cancel()
    try:
        await scheduler_task
    except asyncio.CancelledError:
        pass


app = FastAPI(title="NovaFlow API", version="9.9.0", lifespan=lifespan)

# Order: outermost last added runs first for request. Trace + security first.
app.add_middleware(TraceMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOWED_ORIGINS or ["http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Workspace-Id", "X-Api-Key", "Accept"],
)

app.include_router(user.router, prefix=API_PREFIX)
app.include_router(auth_oauth.router, prefix=API_PREFIX)
app.include_router(auth_saml.router, prefix=API_PREFIX)
app.include_router(assistant.router, prefix=API_PREFIX)
app.include_router(agents.router, prefix=API_PREFIX)
app.include_router(knowledge.router, prefix=API_PREFIX)
app.include_router(llm.router, prefix=API_PREFIX)
app.include_router(workflow.router, prefix=API_PREFIX)
app.include_router(workflow_intelligence_router, prefix=API_PREFIX)
app.include_router(platform_intelligence_router, prefix=API_PREFIX)
app.include_router(conversation_router, prefix=API_PREFIX)
app.include_router(knowledge_os_router, prefix=API_PREFIX)
app.include_router(agent_os_router, prefix=API_PREFIX)
app.include_router(connectivity_router, prefix=API_PREFIX)
app.include_router(eiap_router, prefix=API_PREFIX)
app.include_router(marketplace.router, prefix=API_PREFIX)
app.include_router(api_keys.router, prefix=API_PREFIX)
app.include_router(analytics.router, prefix=API_PREFIX)
app.include_router(workspace.router, prefix=API_PREFIX)
app.include_router(emergency.router, prefix=API_PREFIX)
app.include_router(evaluation.router, prefix=API_PREFIX)
app.include_router(finetune.router, prefix=API_PREFIX)
app.include_router(model_lab.router, prefix=API_PREFIX)
app.include_router(projects.router, prefix=API_PREFIX)
app.include_router(integrations.router, prefix=API_PREFIX)
app.include_router(notifications.router, prefix=API_PREFIX)
app.include_router(chat_ws.router, prefix=API_PREFIX)
from app.routers import voice_ws
app.include_router(voice_ws.router, prefix=API_PREFIX)


@app.get("/health")
def health():
    from app.data import get_cache, get_engine_info, get_object_storage, get_vector_store
    from app.data.observability import get_db_metrics

    try:
        data_info = get_engine_info()
    except Exception:
        data_info = {"dialect": "unknown"}
    try:
        vec = get_vector_store().name
    except Exception:
        vec = vector_backend()
    try:
        storage = get_object_storage().name
    except Exception:
        storage = "local"
    try:
        cache = get_cache().name
    except Exception:
        cache = "memory"
    return ok(
        {
            "service": "novaflow-api",
            "status": "ok",
            "version": "9.9.0",
            "vector_backend": vec,
            "storage_backend": storage,
            "cache_backend": cache,
            "database": data_info,
            "db_metrics": get_db_metrics(),
            "security": "enterprise-v1",
            "platform": "multi-tenant-v2",
            "data_platform": "enterprise-v1",
            "ai_runtime": "enterprise-v1",
            "workflow_intelligence": "enterprise-v1",
            "platform_intelligence": "enterprise-v1",
            "conversation_platform": "enterprise-v1",
            "knowledge_os": "enterprise-v1",
            "agent_os": "enterprise-v1",
            "connectivity_platform": "enterprise-v1",
            "intelligence_autonomy": "enterprise-v1",
        }
    )


@app.get("/")
def root():
    return ok({"name": "NovaFlow API", "version": "9.9.0"})
