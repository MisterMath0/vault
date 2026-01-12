"""
Vault audit log models.

Pydantic models for audit logging in Vault.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class AuditAction(str, Enum):
    """Standard audit actions for tracking."""

    # User actions
    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"
    USER_DELETED = "user.deleted"
    USER_SIGNED_IN = "user.signed_in"
    USER_SIGNED_OUT = "user.signed_out"

    # Organization actions
    ORG_CREATED = "org.created"
    ORG_UPDATED = "org.updated"
    ORG_DELETED = "org.deleted"

    # Membership actions
    MEMBER_ADDED = "member.added"
    MEMBER_UPDATED = "member.updated"
    MEMBER_REMOVED = "member.removed"

    # Role actions
    ROLE_CREATED = "role.created"
    ROLE_UPDATED = "role.updated"
    ROLE_DELETED = "role.deleted"
    ROLE_ASSIGNED = "role.assigned"

    # Permission actions
    PERMISSION_GRANTED = "permission.granted"
    PERMISSION_REVOKED = "permission.revoked"

    # Invitation actions
    INVITE_SENT = "invite.sent"
    INVITE_ACCEPTED = "invite.accepted"
    INVITE_REVOKED = "invite.revoked"
    INVITE_EXPIRED = "invite.expired"

    # API key actions
    API_KEY_CREATED = "api_key.created"
    API_KEY_REVOKED = "api_key.revoked"
    API_KEY_USED = "api_key.used"

    # Custom action (for user-defined actions)
    CUSTOM = "custom"


class ResourceType(str, Enum):
    """Resource types that can be audited."""

    USER = "user"
    ORGANIZATION = "organization"
    MEMBERSHIP = "membership"
    ROLE = "role"
    PERMISSION = "permission"
    INVITATION = "invitation"
    API_KEY = "api_key"
    SESSION = "session"
    CUSTOM = "custom"


class AuditLogEntry(BaseModel):
    """
    Audit log entry model - represents a single audit event.

    Stored in the vault_audit_log table to track all actions
    performed in the system for compliance and debugging.
    """

    id: UUID
    organization_id: Optional[UUID] = None
    user_id: Optional[UUID] = None

    # What happened
    action: str
    resource_type: Optional[str] = None
    resource_id: Optional[UUID] = None

    # Details
    metadata: Dict[str, Any] = Field(default_factory=dict)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

    # Timestamp
    created_at: datetime

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "organization_id": "456e7890-e89b-12d3-a456-426614174000",
                "user_id": "789e0123-e89b-12d3-a456-426614174000",
                "action": "user.created",
                "resource_type": "user",
                "resource_id": "012e3456-e89b-12d3-a456-426614174000",
                "metadata": {"email": "user@example.com"},
                "ip_address": "192.168.1.1",
                "user_agent": "Mozilla/5.0...",
                "created_at": "2024-01-01T00:00:00Z",
            }
        },
    }


class AuditContext(BaseModel):
    """
    Context for audit logging - captures request context.

    This is passed to audit methods to include request metadata.
    """

    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    request_id: Optional[str] = None
    extra: Dict[str, Any] = Field(default_factory=dict)
