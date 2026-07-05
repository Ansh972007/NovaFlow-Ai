from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_admin
from app.schemas import ok
from app.services.workspace_settings import get_chat_config, get_embedding_model, load_settings, settings_dict, update_settings

router = APIRouter(tags=["LLM"])


@router.get("/llm")
def all_llm(db: Session = Depends(get_db), user=Depends(get_current_user)):
    load_settings(db)
    cfg = get_chat_config()
    model = cfg["model"]
    return ok(
        [
            {
                "id": 1,
                "name": "OpenAI",
                "server_name": "OpenAI",
                "models": [{"id": 1, "model_name": model, "online": True}],
                "model_list": [{"model_name": model}],
            }
        ]
    )


@router.get("/llm/assistant")
def assistant_llm(db: Session = Depends(get_db), user=Depends(get_current_user)):
    load_settings(db)
    model = get_chat_config()["model"]
    return ok({"llm_model": {"model_name": model}, "model_name": model})


@router.get("/llm/knowledge")
def knowledge_llm(db: Session = Depends(get_db), user=Depends(get_current_user)):
    load_settings(db)
    model = get_embedding_model()
    return ok({"embedding_model": {"model_name": model}})


@router.get("/llm/settings")
def get_llm_settings(db: Session = Depends(get_db), user=Depends(require_admin)):
    return ok(settings_dict(db))


@router.patch("/llm/settings")
def patch_llm_settings(body: dict, db: Session = Depends(get_db), user=Depends(require_admin)):
    return ok(update_settings(db, body))
