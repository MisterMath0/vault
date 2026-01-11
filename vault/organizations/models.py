"""
Vault organizations models.

Pydantic models for organizations and memberships in Vault.
"""

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class VaultOrganization(BaseModel):
    """
    Vault organization model - represents an organization in the vault_organizations table.

    Organizations are the top-level tenant entities for multi-tenant RBAC.
    """

    id: UUID
    name: str
    slug: str

    # Settings and metadata
    settings: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    # Status
    status: str = "active"

    # Timestamps
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "Acme Corp",
                "slug": "acme-corp",
                "settings": {"billing_tier": "pro"},
                "metadata": {"industry": "technology"},
                "status": "active",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
            }
        },
    }


class CreateOrganizationRequest(BaseModel):
    """Request model for creating a new organization."""

    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=255, pattern=r"^[a-z0-9-]+$")
    settings: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class UpdateOrganizationRequest(BaseModel):
    """Request model for updating an existing organization."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    slug: Optional[str] = Field(None, min_length=1, max_length=255, pattern=r"^[a-z0-9-]+$")
    settings: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    status: Optional[str] = None


class VaultMembership(BaseModel):
    """
    Vault membership model - represents a user's membership in an organization.

    Links users to organizations with optional roles.
    """

    id: UUID
    user_id: UUID
    organization_id: UUID
    role_id: Optional[UUID] = None

    # Status
    status: str = "active"

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)

    # Timestamps
    joined_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "user_id": "456e7890-e89b-12d3-a456-426614174000",
                "organization_id": "789e0123-e89b-12d3-a456-426614174000",
                "role_id": "012e3456-e89b-12d3-a456-426614174000",
                "status": "active",
                "metadata": {},
                "joined_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
            }
        },
    }


class CreateMembershipRequest(BaseModel):
    """Request model for creating a new membership."""

    user_id: UUID
    organization_id: UUID
    role_id: Optional[UUID] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class UpdateMembershipRequest(BaseModel):
    """Request model for updating an existing membership."""

    role_id: Optional[UUID] = None
    status: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
