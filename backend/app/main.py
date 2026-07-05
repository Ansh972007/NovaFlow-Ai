from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import ADMIN_PASSWORD, ADMIN_USER, DATA_DIR
from app.crypto import md5_hash
from app.database import SessionLocal, User, init_db
from app.routers import assistant, chat_ws, knowledge, llm, user
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
            )
            db.add(admin)
            db.commit()
            print(f"[NovaFlow] Default admin: {ADMIN_USER} / (see NOVAFLOW_ADMIN_PASSWORD)")
    finally:
        db.close()
    yield


app = FastAPI(title="NovaFlow API", version="0.5.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(user.router, prefix=API_PREFIX)
app.include_router(assistant.router, prefix=API_PREFIX)
app.include_router(knowledge.router, prefix=API_PREFIX)
app.include_router(llm.router, prefix=API_PREFIX)
app.include_router(chat_ws.router, prefix=API_PREFIX)


@app.get("/health")
def health():
    return ok({"service": "novaflow-api", "status": "ok"})


@app.get("/")
def root():
    return ok({"name": "NovaFlow API", "version": "0.5.0"})
