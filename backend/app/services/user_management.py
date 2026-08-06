"""User role management and per-user API key configuration system."""

from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.database import User, TeamInvitation
from app.crypto import encrypt_secret, decrypt_secret
from datetime import datetime, timedelta
import secrets
import hashlib


class UserRoleManager:
    """Manage user roles and team invitations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def set_user_role(self, user_id: int, role: str, set_by_user_id: int) -> Dict[str, Any]:
        """
        Set user role (only can be changed by admin or higher role).
        
        Args:
            user_id: User to update
            role: New role (admin, editor, viewer)
            set_by_user_id: User making the change
            
        Returns:
            Result dict with success status
        """
        # Check if the changer has permission
        setter = self.db.query(User).filter(User.user_id == set_by_user_id).first()
        if not setter:
            return {"success": False, "message": "Setter not found"}
        
        # Only admins can change roles
        if setter.role != "admin":
            return {"success": False, "message": "Only admins can change roles"}
        
        # Update user role
        user = self.db.query(User).filter(User.user_id == user_id).first()
        if not user:
            return {"success": False, "message": "User not found"}
        
        user.role = role
        user.update_time = datetime.utcnow()
        self.db.commit()
        
        return {
            "success": True,
            "message": f"User role updated to {role}",
            "user_id": user_id,
            "new_role": role
        }
    
    def create_team_invitation(
        self, 
        workspace_id: int, 
        invited_by: int, 
        invited_email: str, 
        role: str = "editor"
    ) -> Dict[str, Any]:
        """
        Create team invitation with specific role.
        
        Args:
            workspace_id: Workspace to invite to
            invited_by: User ID of inviter
            invited_email: Email to invite
            role: Role to assign when accepted
            
        Returns:
            Invitation details
        """
        # Check if inviter is admin
        inviter = self.db.query(User).filter(User.user_id == invited_by).first()
        if not inviter or inviter.role != "admin":
            return {"success": False, "message": "Only admins can send invitations"}
        
        # Check if invitation already exists
        existing = self.db.query(TeamInvitation).filter(
            TeamInvitation.invited_email == invited_email,
            TeamInvitation.workspace_id == workspace_id,
            TeamInvitation.status == "pending"
        ).first()
        
        if existing:
            return {"success": False, "message": "Pending invitation already exists"}
        
        # Create invitation token
        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        # Set expiration (7 days)
        expires_at = datetime.utcnow() + timedelta(days=7)
        
        invitation = TeamInvitation(
            workspace_id=workspace_id,
            invited_by=invited_by,
            invited_email=invited_email,
            invited_role=role,
            invitation_token=token_hash,
            status="pending",
            expires_at=expires_at
        )
        
        self.db.add(invitation)
        self.db.commit()
        
        return {
            "success": True,
            "invitation_id": invitation.id,
            "token": token,  # Return actual token for email link
            "expires_at": expires_at.isoformat(),
            "role": role
        }
    
    def accept_invitation(self, token: str, user_id: int) -> Dict[str, Any]:
        """
        Accept team invitation and assign role.
        
        Args:
            token: Invitation token
            user_id: User accepting the invitation
            
        Returns:
            Result dict
        """
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        invitation = self.db.query(TeamInvitation).filter(
            TeamInvitation.invitation_token == token_hash,
            TeamInvitation.status == "pending"
        ).first()
        
        if not invitation:
            return {"success": False, "message": "Invalid or expired invitation"}
        
        if invitation.expires_at < datetime.utcnow():
            invitation.status = "expired"
            self.db.commit()
            return {"success": False, "message": "Invitation has expired"}
        
        # Update user role
        user = self.db.query(User).filter(User.user_id == user_id).first()
        if not user:
            return {"success": False, "message": "User not found"}
        
        user.role = invitation.invited_role
        invitation.status = "accepted"
        invitation.accepted_at = datetime.utcnow()
        
        self.db.commit()
        
        return {
            "success": True,
            "message": f"Invitation accepted. Role set to {invitation.invited_role}",
            "role": invitation.invited_role
        }


class UserApiKeyManager:
    """Manage per-user API keys and configuration."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def set_user_api_key(
        self, 
        user_id: int, 
        api_key: str, 
        provider: str = "openrouter",
        model: str = "openai/gpt-4o-mini",
        base_url: str = ""
    ) -> Dict[str, Any]:
        """
        Set user's personal API key and configuration.
        
        Args:
            user_id: User ID
            api_key: User's API key
            provider: Provider type (openrouter, openai, etc.)
            model: User's preferred model
            base_url: Custom base URL if needed
            
        Returns:
            Result dict
        """
        user = self.db.query(User).filter(User.user_id == user_id).first()
        if not user:
            return {"success": False, "message": "User not found"}
        
        # Encrypt API key
        encrypted_key = encrypt_secret(api_key)
        
        # Update user configuration
        user.user_api_key_enc = encrypted_key
        user.user_api_provider = provider
        user.user_api_model = model
        user.user_api_base_url = base_url
        user.update_time = datetime.utcnow()
        
        self.db.commit()
        
        return {
            "success": True,
            "message": "User API key configured successfully",
            "provider": provider,
            "model": model
        }
    
    def get_user_api_config(self, user_id: int) -> Dict[str, Any]:
        """
        Get user's API configuration.
        
        Args:
            user_id: User ID
            
        Returns:
            User's API configuration
        """
        user = self.db.query(User).filter(User.user_id == user_id).first()
        if not user:
            return {"success": False, "message": "User not found"}
        
        api_key = None
        if user.user_api_key_enc:
            try:
                api_key = decrypt_secret(user.user_api_key_enc)
            except Exception:
                pass
        
        return {
            "success": True,
            "user_id": user_id,
            "has_api_key": bool(api_key),
            "api_key_preview": f"{api_key[:10]}..." if api_key else None,
            "provider": user.user_api_provider or "openrouter",
            "model": user.user_api_model or "openai/gpt-4o-mini",
            "base_url": user.user_api_base_url or ""
        }
    
    def get_user_api_key(self, user_id: int) -> Optional[str]:
        """
        Get user's decrypted API key.
        
        Args:
            user_id: User ID
            
        Returns:
            Decrypted API key or None
        """
        user = self.db.query(User).filter(User.user_id == user_id).first()
        if not user or not user.user_api_key_enc:
            return None
        
        try:
            return decrypt_secret(user.user_api_key_enc)
        except Exception:
            return None
    
    def get_base_url_for_user(self, user_id: int) -> str:
        """
        Get user's preferred base URL.
        
        Args:
            user_id: User ID
            
        Returns:
            Base URL or default
        """
        user = self.db.query(User).filter(User.user_id == user_id).first()
        if not user:
            return "https://openrouter.ai/api/v1"
        
        if user.user_api_base_url:
            return user.user_api_base_url
        
        # Return default based on provider
        provider = user.user_api_provider or "openrouter"
        if provider == "openrouter":
            return "https://openrouter.ai/api/v1"
        elif provider == "openai":
            return "https://api.openai.com/v1"
        else:
            return "https://openrouter.ai/api/v1"
    
    def get_model_for_user(self, user_id: int) -> str:
        """
        Get user's preferred model.
        
        Args:
            user_id: User ID
            
        Returns:
            Model name or default
        """
        user = self.db.query(User).filter(User.user_id == user_id).first()
        if not user:
            return "openai/gpt-4o-mini"
        
        return user.user_api_model or "openai/gpt-4o-mini"