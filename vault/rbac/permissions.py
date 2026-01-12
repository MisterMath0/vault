"""
Permission management for Vault.

Handles permission checking and validation for users within organizations.
"""

from typing import TYPE_CHECKING, List, Optional
from uuid import UUID

from .models import check_permission, check_permissions

if TYPE_CHECKING:
    from ..client import Vault


class PermissionManager:
    """
    Manager for permission checking operations.

    Provides methods to check if a user has specific permissions
    within an organization based on their role.

    Example:
        ```python
        vault = await Vault.create()

        # Check if user has permission
        can_write = await vault.permissions.check(
            user_id=user.id,
            organization_id=org.id,
            permission="posts:write"
        )

        # Check multiple permissions
        can_admin = await vault.permissions.check_all(
            user_id=user.id,
            organization_id=org.id,
            permissions=["users:read", "users:write"]
        )
        ```
    """

    def __init__(self, vault: "Vault") -> None:
        """
        Initialize PermissionManager.

        Args:
            vault: Vault client instance
        """
        self.vault = vault
        self.client = vault.client

    async def get_user_permissions(
        self,
        user_id: UUID,
        organization_id: UUID,
    ) -> List[str]:
        """
        Get all permissions for a user in an organization.

        Looks up the user's membership and role to get their permissions.

        Args:
            user_id: User UUID
            organization_id: Organization UUID

        Returns:
            List of permission strings the user has

        Example:
            ```python
            perms = await vault.permissions.get_user_permissions(
                user_id=user.id,
                organization_id=org.id
            )
            # ["posts:read", "posts:write", "comments:*"]
            ```
        """
        # Get the user's membership in this organization
        membership = await self.vault.memberships.get_by_user_and_org(
            user_id=user_id,
            organization_id=organization_id,
        )

        if not membership:
            return []

        if membership.status != "active":
            return []

        if not membership.role_id:
            return []

        # Get the role
        role = await self.vault.roles.get(membership.role_id)

        if not role:
            return []

        return role.permissions

    async def check(
        self,
        user_id: UUID,
        organization_id: UUID,
        permission: str,
    ) -> bool:
        """
        Check if a user has a specific permission in an organization.

        Supports wildcard matching:
        - posts:* matches posts:read, posts:write, etc.
        - *:read matches any resource's read action
        - *:* matches everything (admin access)

        Args:
            user_id: User UUID
            organization_id: Organization UUID
            permission: Permission string to check (e.g., "posts:write")

        Returns:
            True if user has the permission, False otherwise

        Example:
            ```python
            if await vault.permissions.check(user.id, org.id, "posts:write"):
                # User can write posts
                pass
            ```
        """
        user_perms = await self.get_user_permissions(user_id, organization_id)
        return check_permission(user_perms, permission)

    async def check_all(
        self,
        user_id: UUID,
        organization_id: UUID,
        permissions: List[str],
    ) -> bool:
        """
        Check if a user has ALL specified permissions.

        Args:
            user_id: User UUID
            organization_id: Organization UUID
            permissions: List of permission strings to check

        Returns:
            True if user has ALL permissions, False otherwise

        Example:
            ```python
            if await vault.permissions.check_all(
                user.id, org.id,
                ["users:read", "users:write", "users:delete"]
            ):
                # User has full user management access
                pass
            ```
        """
        user_perms = await self.get_user_permissions(user_id, organization_id)
        return check_permissions(user_perms, permissions, require_all=True)

    async def check_any(
        self,
        user_id: UUID,
        organization_id: UUID,
        permissions: List[str],
    ) -> bool:
        """
        Check if a user has ANY of the specified permissions.

        Args:
            user_id: User UUID
            organization_id: Organization UUID
            permissions: List of permission strings to check

        Returns:
            True if user has at least one permission, False otherwise

        Example:
            ```python
            if await vault.permissions.check_any(
                user.id, org.id,
                ["admin:*", "users:*"]
            ):
                # User has some admin access
                pass
            ```
        """
        user_perms = await self.get_user_permissions(user_id, organization_id)
        return check_permissions(user_perms, permissions, require_all=False)

    async def check_role(
        self,
        user_id: UUID,
        organization_id: UUID,
        role_name: str,
    ) -> bool:
        """
        Check if a user has a specific role in an organization.

        Args:
            user_id: User UUID
            organization_id: Organization UUID
            role_name: Role name to check (e.g., "Admin", "Editor")

        Returns:
            True if user has the role, False otherwise

        Example:
            ```python
            if await vault.permissions.check_role(user.id, org.id, "Admin"):
                # User is an admin
                pass
            ```
        """
        # Get the user's membership
        membership = await self.vault.memberships.get_by_user_and_org(
            user_id=user_id,
            organization_id=organization_id,
        )

        if not membership or membership.status != "active":
            return False

        if not membership.role_id:
            return False

        # Get the role
        role = await self.vault.roles.get(membership.role_id)

        if not role:
            return False

        return role.name.lower() == role_name.lower()

    async def check_any_role(
        self,
        user_id: UUID,
        organization_id: UUID,
        role_names: List[str],
    ) -> bool:
        """
        Check if a user has any of the specified roles.

        Args:
            user_id: User UUID
            organization_id: Organization UUID
            role_names: List of role names to check

        Returns:
            True if user has any of the roles, False otherwise

        Example:
            ```python
            if await vault.permissions.check_any_role(
                user.id, org.id,
                ["Owner", "Admin"]
            ):
                # User is an owner or admin
                pass
            ```
        """
        # Get the user's membership
        membership = await self.vault.memberships.get_by_user_and_org(
            user_id=user_id,
            organization_id=organization_id,
        )

        if not membership or membership.status != "active":
            return False

        if not membership.role_id:
            return False

        # Get the role
        role = await self.vault.roles.get(membership.role_id)

        if not role:
            return False

        # Case-insensitive comparison
        role_name_lower = role.name.lower()
        return any(name.lower() == role_name_lower for name in role_names)

    async def get_role_permissions(self, role_id: UUID) -> List[str]:
        """
        Get permissions for a specific role.

        Args:
            role_id: Role UUID

        Returns:
            List of permission strings for the role

        Example:
            ```python
            perms = await vault.permissions.get_role_permissions(role_id)
            ```
        """
        role = await self.vault.roles.get(role_id)

        if not role:
            return []

        return role.permissions

    async def is_member(
        self,
        user_id: UUID,
        organization_id: UUID,
    ) -> bool:
        """
        Check if a user is an active member of an organization.

        Args:
            user_id: User UUID
            organization_id: Organization UUID

        Returns:
            True if user is an active member, False otherwise

        Example:
            ```python
            if await vault.permissions.is_member(user.id, org.id):
                # User is part of the organization
                pass
            ```
        """
        membership = await self.vault.memberships.get_by_user_and_org(
            user_id=user_id,
            organization_id=organization_id,
        )

        return membership is not None and membership.status == "active"

    async def is_owner(
        self,
        user_id: UUID,
        organization_id: UUID,
    ) -> bool:
        """
        Check if a user is an owner of an organization.

        Args:
            user_id: User UUID
            organization_id: Organization UUID

        Returns:
            True if user is the owner, False otherwise

        Example:
            ```python
            if await vault.permissions.is_owner(user.id, org.id):
                # User owns the organization
                pass
            ```
        """
        return await self.check_role(user_id, organization_id, "Owner")

    async def is_admin(
        self,
        user_id: UUID,
        organization_id: UUID,
    ) -> bool:
        """
        Check if a user is an admin of an organization.

        Owners are also considered admins.

        Args:
            user_id: User UUID
            organization_id: Organization UUID

        Returns:
            True if user is an admin (or owner), False otherwise

        Example:
            ```python
            if await vault.permissions.is_admin(user.id, org.id):
                # User has admin access
                pass
            ```
        """
        return await self.check_any_role(user_id, organization_id, ["Owner", "Admin"])
