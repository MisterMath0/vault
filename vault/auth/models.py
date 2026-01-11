"""
Vault auth models.

Pydantic models for users and sessions in Vault.
"""

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class VaultUser(BaseModel):
    """
    Vault user model - represents a user in the vault_users table.

    This is the source of truth for user data, synced to/from Supabase auth.
    """

    id: UUID
    email: EmailStr
    email_verified: bool = False
    phone: Optional[str] = None
    phone_verified: bool = False

    # Auth provider tracking
    supabase_auth_id: Optional[UUID] = None
    auth_provider: str = "email"

    # Profile
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    # Status
    status: str = "active"
    last_sign_in_at: Optional[datetime] = None

    # Timestamps
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "email": "user@example.com",
                "email_verified": True,
                "display_name": "John Doe",
                "auth_provider": "email",
                "status": "active",
                "metadata": {"role": "admin"},
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
            }
        },
    }


class CreateUserRequest(BaseModel):
    """Request model for creating a new user."""

    email: EmailStr
    password: Optional[str] = Field(
        None,
        min_length=6,
        description="Password (if creating with email/password)",
    )
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    email_confirm: bool = Field(
        default=False,
        description="Auto-confirm email (skips verification)",
    )


class UpdateUserRequest(BaseModel):
    """Request model for updating an existing user."""

    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=6)
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    status: Optional[str] = None


class VaultSession(BaseModel):
    """
    Vault session model - represents an auth session.

    Wraps Supabase auth session with additional Vault user data.
    """

    access_token: str
    refresh_token: str
    expires_at: int
    expires_in: int
    token_type: str = "bearer"
    user: VaultUser

    model_config = {
        "json_schema_extra": {
            "example": {
                "access_token": "eyJhbGc...",
                "refresh_token": "xyz123...",
                "expires_at": 1704067200,
                "expires_in": 3600,
                "token_type": "bearer",
            }
        }
    }
