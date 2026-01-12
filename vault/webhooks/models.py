"""
Vault webhook models.

Pydantic models for webhooks in Vault.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl


class WebhookEvent(str, Enum):
    """Events that can trigger webhooks."""

    # User events
    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"
    USER_DELETED = "user.deleted"
    USER_SIGNED_IN = "user.signed_in"
    USER_SIGNED_OUT = "user.signed_out"

    # Organization events
    ORG_CREATED = "org.created"
    ORG_UPDATED = "org.updated"
    ORG_DELETED = "org.deleted"

    # Membership events
    MEMBER_ADDED = "member.added"
    MEMBER_UPDATED = "member.updated"
    MEMBER_REMOVED = "member.removed"

    # Role events
    ROLE_CREATED = "role.created"
    ROLE_UPDATED = "role.updated"
    ROLE_DELETED = "role.deleted"
    ROLE_ASSIGNED = "role.assigned"

    # Invitation events
    INVITE_SENT = "invite.sent"
    INVITE_ACCEPTED = "invite.accepted"
    INVITE_REVOKED = "invite.revoked"

    # API key events
    API_KEY_CREATED = "api_key.created"
    API_KEY_REVOKED = "api_key.revoked"

    # Wildcard for all events
    ALL = "*"


class VaultWebhook(BaseModel):
    """
    Webhook configuration model.

    Webhooks are stored in vault_webhooks table and define
    endpoints to receive event notifications.
    """

    id: UUID
    organization_id: Optional[UUID] = None  # None = global webhook

    # Webhook configuration
    url: str
    secret: str  # For HMAC signature verification
    description: Optional[str] = None

    # Events to listen for
    events: List[str] = Field(default_factory=list)

    # Status
    is_active: bool = True
    failure_count: int = 0
    last_triggered_at: Optional[datetime] = None
    last_success_at: Optional[datetime] = None
    last_failure_at: Optional[datetime] = None

    # Timestamps
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "organization_id": "456e7890-e89b-12d3-a456-426614174000",
                "url": "https://example.com/webhooks/vault",
                "secret": "whsec_xxxxxxxxxxxx",
                "description": "Production webhook",
                "events": ["user.created", "user.deleted", "member.added"],
                "is_active": True,
                "failure_count": 0,
                "last_triggered_at": "2024-01-01T12:00:00Z",
                "last_success_at": "2024-01-01T12:00:00Z",
                "last_failure_at": None,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
            }
        },
    }


class WebhookDelivery(BaseModel):
    """
    Webhook delivery attempt record.

    Tracks individual delivery attempts for debugging and retry logic.
    """

    id: UUID
    webhook_id: UUID
    event: str

    # Request details
    request_url: str
    request_headers: Dict[str, str] = Field(default_factory=dict)
    request_body: Dict[str, Any] = Field(default_factory=dict)

    # Response details
    response_status: Optional[int] = None
    response_body: Optional[str] = None
    response_time_ms: Optional[int] = None

    # Status
    success: bool = False
    error_message: Optional[str] = None
    attempt_number: int = 1

    # Timestamp
    created_at: datetime

    model_config = {
        "from_attributes": True,
    }


class CreateWebhookRequest(BaseModel):
    """Request model for creating a webhook."""

    url: HttpUrl = Field(..., description="URL to receive webhook events")
    events: List[str] = Field(
        ...,
        min_length=1,
        description="List of events to subscribe to",
    )
    organization_id: Optional[UUID] = Field(
        None,
        description="Organization to scope webhook to (None for global)",
    )
    description: Optional[str] = Field(None, max_length=500)


class UpdateWebhookRequest(BaseModel):
    """Request model for updating a webhook."""

    url: Optional[HttpUrl] = None
    events: Optional[List[str]] = None
    description: Optional[str] = Field(None, max_length=500)
    is_active: Optional[bool] = None


class WebhookPayload(BaseModel):
    """Standard webhook payload structure."""

    id: str  # Unique delivery ID
    event: str
    timestamp: datetime
    organization_id: Optional[str] = None
    data: Dict[str, Any] = Field(default_factory=dict)
