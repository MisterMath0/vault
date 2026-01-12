"""
Vault API key models.

Pydantic models for API keys in Vault.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class VaultAPIKey(BaseModel):
    """
    API key model for service-to-service authentication.

    API keys are stored in vault_api_keys table and provide
    a way for services to authenticate without user context.
    """

    id: UUID
    organization_id: UUID

    # Key identification
    name: str
    description: Optional[str] = None
    key_prefix: str  # First 8 chars for identification

    # Note: key_hash is NOT included - never expose the hash

    # Permissions
    scopes: List[str] = Field(default_factory=list)

    # Rate limiting
    rate_limit: Optional[int] = None  # Requests per minute

    # Status and tracking
    is_active: bool = True
    last_used_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None

    # Timestamps
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "organization_id": "456e7890-e89b-12d3-a456-426614174000",
                "name": "production-api",
                "description": "Production API key for backend services",
                "key_prefix": "vk_abc123",
                "scopes": ["users:read", "orgs:read"],
                "rate_limit": 1000,
                "is_active": True,
                "last_used_at": "2024-01-01T12:00:00Z",
                "expires_at": None,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
            }
        },
    }


class VaultAPIKeyWithSecret(VaultAPIKey):
    """
    API key with the full secret key.

    Only returned on creation - the full key is never stored
    and cannot be retrieved again.
    """

    key: str  # The full API key (only on creation)


class APIKeyUsage(BaseModel):
    """
    API key usage record for tracking and rate limiting.
    """

    id: UUID
    api_key_id: UUID

    # Request details
    endpoint: Optional[str] = None
    method: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

    # Response
    response_status: Optional[int] = None

    # Timestamp
    created_at: datetime

    model_config = {
        "from_attributes": True,
    }


class CreateAPIKeyRequest(BaseModel):
    """Request model for creating an API key."""

    name: str = Field(..., min_length=1, max_length=255)
    organization_id: UUID
    description: Optional[str] = Field(None, max_length=500)
    scopes: List[str] = Field(
        default_factory=list,
        description="Permission scopes for this key",
    )
    rate_limit: Optional[int] = Field(
        None,
        ge=1,
        le=100000,
        description="Rate limit in requests per minute",
    )
    expires_in_days: Optional[int] = Field(
        None,
        ge=1,
        le=365,
        description="Days until key expires (None for no expiration)",
    )


class UpdateAPIKeyRequest(BaseModel):
    """Request model for updating an API key."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=500)
    scopes: Optional[List[str]] = None
    rate_limit: Optional[int] = Field(None, ge=1, le=100000)
    is_active: Optional[bool] = None


class APIKeyValidationResult(BaseModel):
    """Result of API key validation."""

    valid: bool
    api_key: Optional[VaultAPIKey] = None
    error: Optional[str] = None
    rate_limited: bool = False
    remaining_requests: Optional[int] = None
