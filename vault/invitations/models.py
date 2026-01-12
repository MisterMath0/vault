"""
Vault invitation models.

Pydantic models for organization invitations in Vault.
"""

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class VaultInvitation(BaseModel):
    """
    Vault invitation model - represents an invitation to join an organization.

    Invitations are stored in the vault_invitations table and track
    who was invited, by whom, and when they accepted.
    """

    id: UUID
    organization_id: UUID
    email: EmailStr
    role_id: Optional[UUID] = None

    # Who sent the invite
    invited_by: Optional[UUID] = None

    # Token for accepting
    token: str
    expires_at: datetime

    # Tracking
    accepted_at: Optional[datetime] = None
    accepted_by: Optional[UUID] = None

    # Timestamps
    created_at: datetime

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "organization_id": "456e7890-e89b-12d3-a456-426614174000",
                "email": "newuser@example.com",
                "role_id": "789e0123-e89b-12d3-a456-426614174000",
                "invited_by": "012e3456-e89b-12d3-a456-426614174000",
                "token": "abc123xyz",
                "expires_at": "2024-01-08T00:00:00Z",
                "accepted_at": None,
                "accepted_by": None,
                "created_at": "2024-01-01T00:00:00Z",
            }
        },
    }


class CreateInvitationRequest(BaseModel):
    """Request model for creating a new invitation."""

    organization_id: UUID
    email: EmailStr = Field(..., description="Email address to invite")
    role_id: Optional[UUID] = Field(None, description="Role to assign on acceptance")
    invited_by: Optional[UUID] = Field(None, description="User ID who sent the invite")
    expires_in_days: int = Field(
        default=7,
        ge=1,
        le=30,
        description="Days until invitation expires",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata to include with invite",
    )
