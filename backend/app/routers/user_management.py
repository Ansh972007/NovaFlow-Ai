"""API routes for user role management and per-user API key configuration."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db
from app.deps import get_current_user
from app.services.user_management import UserRoleManager, UserApiKeyManager

router = APIRouter(tags=["User Management"])


class SetUserRoleRequest(BaseModel):
    user_id: int
    role: str  # admin, editor, viewer


class CreateInvitationRequest(BaseModel):
    workspace_id: int
    invited_email: str
    role: str = "editor"


class AcceptInvitationRequest(BaseModel):
    token: str


class SetUserApiKeyRequest(BaseModel):
    api_key: str
    provider: str = "openrouter"
    model: str = "openai/gpt-4o-mini"
    base_url: str = ""


@router.post("/user/role")
def set_user_role(request: SetUserRoleRequest, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    """Set user role (admin only)."""
    role_manager = UserRoleManager(db)
    result = role_manager.set_user_role(request.user_id, request.role, current_user.user_id)
    
    if not result["success"]:
        raise HTTPException(status_code=403, detail=result["message"])
    
    return result


@router.post("/invitation/create")
def create_invitation(request: CreateInvitationRequest, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    """Create team invitation with role assignment (admin only)."""
    role_manager = UserRoleManager(db)
    result = role_manager.create_team_invitation(
        request.workspace_id,
        current_user.user_id,
        request.invited_email,
        request.role
    )
    
    if not result["success"]:
        raise HTTPException(status_code=403, detail=result["message"])
    
    return result


@router.post("/invitation/accept")
def accept_invitation(request: AcceptInvitationRequest, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    """Accept team invitation and assign role."""
    role_manager = UserRoleManager(db)
    result = role_manager.accept_invitation(request.token, current_user.user_id)
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    
    return result


@router.post("/user/api-key")
def set_user_api_key(request: SetUserApiKeyRequest, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    """Set user's personal API key and configuration."""
    api_key_manager = UserApiKeyManager(db)
    result = api_key_manager.set_user_api_key(
        current_user.user_id,
        request.api_key,
        request.provider,
        request.model,
        request.base_url
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    
    return result


@router.get("/user/api-config")
def get_user_api_config(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    """Get user's API configuration."""
    api_key_manager = UserApiKeyManager(db)
    return api_key_manager.get_user_api_config(current_user.user_id)


@router.get("/user/role")
def get_user_role(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    """Get current user's role."""
    return {
        "user_id": current_user.user_id,
        "user_name": current_user.user_name,
        "role": current_user.role,
        "email": current_user.email
    }