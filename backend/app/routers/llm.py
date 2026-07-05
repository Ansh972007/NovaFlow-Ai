from fastapi import APIRouter, Depends

from app.config import EMBEDDING_MODELS, OPENAI_MODEL
from app.deps import get_current_user
from app.schemas import ok

router = APIRouter(tags=["LLM"])


@router.get("/llm")
def all_llm(user=Depends(get_current_user)):
    return ok(
        [
            {
                "id": 1,
                "name": "OpenAI",
                "server_name": "OpenAI",
                "models": [{"id": 1, "model_name": OPENAI_MODEL, "online": True}],
                "model_list": [{"model_name": OPENAI_MODEL}],
            }
        ]
    )


@router.get("/llm/assistant")
def assistant_llm(user=Depends(get_current_user)):
    return ok({"llm_model": {"model_name": OPENAI_MODEL}, "model_name": OPENAI_MODEL})


@router.get("/llm/knowledge")
def knowledge_llm(user=Depends(get_current_user)):
    return ok({"embedding_model": {"model_name": EMBEDDING_MODELS[0]}})
