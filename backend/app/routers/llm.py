from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_admin
from app.schemas import fail, ok
from app.services.llm_providers import (
    activate_provider,
    create_provider,
    delete_provider,
    list_provider_types,
    list_providers,
    update_provider,
    verify_provider,
)
from app.services.workspace_settings import get_chat_config, get_embedding_model, load_settings, settings_dict, update_settings

router = APIRouter(tags=["LLM"])


@router.get("/llm")
def all_llm(db: Session = Depends(get_db), user=Depends(get_current_user)):
    load_settings(db)
    providers = list_providers(db)
    if not providers:
        cfg = get_chat_config(db)
        model = cfg["model"]
        return ok(
            [
                {
                    "id": 1,
                    "name": cfg.get("provider_name") or "Default",
                    "server_name": cfg.get("provider_name") or "Default",
                    "models": [{"id": 1, "model_name": model, "online": True}],
                    "model_list": [{"model_name": model}],
                }
            ]
        )
    return ok(
        [
            {
                "id": p["id"],
                "name": p["name"],
                "server_name": p["name"],
                "provider_type": p["provider_type"],
                "is_active": p["is_active"],
                "models": [{"id": p["id"], "model_name": p["chat_model"], "online": True}],
                "model_list": [{"model_name": p["chat_model"]}],
            }
            for p in providers
        ]
    )


@router.get("/llm/assistant")
def assistant_llm(db: Session = Depends(get_db), user=Depends(get_current_user)):
    load_settings(db)
    cfg = get_chat_config(db)
    model = cfg["model"]
    return ok({"llm_model": {"model_name": model}, "model_name": model, "provider": cfg.get("provider_name")})


@router.get("/llm/knowledge")
def knowledge_llm(db: Session = Depends(get_db), user=Depends(get_current_user)):
    load_settings(db)
    model = get_embedding_model(db)
    return ok({"embedding_model": {"model_name": model}})


@router.get("/llm/settings")
def get_llm_settings(db: Session = Depends(get_db), user=Depends(require_admin)):
    return ok(settings_dict(db))


@router.patch("/llm/settings")
def patch_llm_settings(body: dict, db: Session = Depends(get_db), user=Depends(require_admin)):
    return ok(update_settings(db, body))


@router.get("/llm/provider-types")
def get_provider_types(user=Depends(require_admin)):
    return ok(list_provider_types())


@router.get("/llm/providers")
def get_providers(db: Session = Depends(get_db), user=Depends(require_admin)):
    load_settings(db)
    return ok(list_providers(db))


@router.post("/llm/providers")
def post_provider(body: dict, db: Session = Depends(get_db), user=Depends(require_admin)):
    try:
        return ok(create_provider(db, body))
    except ValueError as exc:
        return fail(400, str(exc))


@router.patch("/llm/providers/{provider_id}")
def patch_provider(provider_id: int, body: dict, db: Session = Depends(get_db), user=Depends(require_admin)):
    try:
        return ok(update_provider(db, provider_id, body))
    except ValueError as exc:
        return fail(404, str(exc))


@router.delete("/llm/providers/{provider_id}")
def remove_provider(provider_id: int, db: Session = Depends(get_db), user=Depends(require_admin)):
    try:
        delete_provider(db, provider_id)
        return ok({"deleted": provider_id})
    except ValueError as exc:
        return fail(404, str(exc))


@router.post("/llm/providers/{provider_id}/activate")
def set_active_provider(provider_id: int, db: Session = Depends(get_db), user=Depends(require_admin)):
    try:
        return ok(activate_provider(db, provider_id))
    except ValueError as exc:
        return fail(404, str(exc))


@router.post("/llm/providers/{provider_id}/verify")
def verify_provider_api(provider_id: int, db: Session = Depends(get_db), user=Depends(require_admin)):
    try:
        result = verify_provider(db, provider_id)
        if not result.get("ok"):
            return fail(400, result.get("detail") or "Provider verify failed")
        return ok(result)
    except ValueError as exc:
        return fail(404, str(exc))
    except Exception as exc:
        return fail(400, str(exc)[:240])
