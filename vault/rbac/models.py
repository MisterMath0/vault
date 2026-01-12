"""
Vault RBAC models.

Pydantic models for roles and permissions in Vault.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class VaultRole(BaseModel):
    """
    Vault role model - represents a role in the vault_roles table.

    Roles define sets of permissions that can be assigned to users
    within an organization via memberships.
    """

    id: UUID
    organization_id: UUID

    name: str
    description: Optional[str] = None

    # Permissions as array: ["posts:read", "posts:write", "users:*"]
    permissions: List[str] = Field(default_factory=list)

    # Is this the default role for new members?
    is_default: bool = False

    # System roles can't be deleted (owner, admin)
    is_system: bool = False

    # Timestamps
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "organization_id": "456e7890-e89b-12d3-a456-426614174000",
                "name": "Editor",
                "description": "Can read and write posts",
                "permissions": ["posts:read", "posts:write", "comments:read"],
                "is_default": False,
                "is_system": False,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
            }
        },
    }


class CreateRoleRequest(BaseModel):
    """Request model for creating a new role."""

    organization_id: UUID
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    permissions: List[str] = Field(default_factory=list)
    is_default: bool = False


class UpdateRoleRequest(BaseModel):
    """Request model for updating an existing role."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    permissions: Optional[List[str]] = None
    is_default: Optional[bool] = None


class VaultPermission(BaseModel):
    """
    Represents a single permission in the resource:action format.

    This is a utility model for working with permissions.
    Permissions follow the format: resource:action

    Examples:
        - posts:read - Read posts
        - posts:write - Write posts
        - posts:* - All post operations
        - *:read - Read all resources
        - admin:* - Full admin access
    """

    resource: str = Field(..., min_length=1, max_length=100)
    action: str = Field(..., min_length=1, max_length=100)

    @classmethod
    def from_string(cls, permission: str) -> "VaultPermission":
        """Parse a permission string into a VaultPermission object."""
        if ":" not in permission:
            raise ValueError(f"Invalid permission format: {permission}. Expected 'resource:action'")
        parts = permission.split(":", 1)
        return cls(resource=parts[0], action=parts[1])

    def to_string(self) -> str:
        """Convert to permission string format."""
        return f"{self.resource}:{self.action}"

    def matches(self, required: "VaultPermission") -> bool:
        """
        Check if this permission grants the required permission.

        Supports wildcards:
        - posts:* matches posts:read, posts:write, etc.
        - *:read matches posts:read, users:read, etc.
        - *:* matches everything
        """
        # Check resource match
        resource_match = (
            self.resource == "*" or
            required.resource == "*" or
            self.resource == required.resource
        )

        # Check action match
        action_match = (
            self.action == "*" or
            required.action == "*" or
            self.action == required.action
        )

        return resource_match and action_match

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "resource": "posts",
                "action": "write",
            }
        },
    }


def check_permission(granted: List[str], required: str) -> bool:
    """
    Check if any granted permission satisfies the required permission.

    Args:
        granted: List of permission strings the user has
        required: The permission string being checked

    Returns:
        True if permission is granted, False otherwise

    Examples:
        >>> check_permission(["posts:read", "posts:write"], "posts:read")
        True
        >>> check_permission(["posts:*"], "posts:write")
        True
        >>> check_permission(["admin:*"], "posts:delete")
        False
    """
    try:
        required_perm = VaultPermission.from_string(required)
    except ValueError:
        return False

    for perm_str in granted:
        try:
            granted_perm = VaultPermission.from_string(perm_str)
            if granted_perm.matches(required_perm):
                return True
        except ValueError:
            continue

    return False


def check_permissions(granted: List[str], required: List[str], require_all: bool = True) -> bool:
    """
    Check if granted permissions satisfy the required permissions.

    Args:
        granted: List of permission strings the user has
        required: List of permission strings being checked
        require_all: If True, all required permissions must be granted.
                    If False, at least one required permission must be granted.

    Returns:
        True if permissions check passes, False otherwise
    """
    if not required:
        return True

    if require_all:
        return all(check_permission(granted, req) for req in required)
    else:
        return any(check_permission(granted, req) for req in required)
