"""
Role management for Vault.

Handles CRUD operations for roles in the vault_roles table.
"""

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from uuid import UUID

from .models import (
    CreateRoleRequest,
    UpdateRoleRequest,
    VaultRole,
)

if TYPE_CHECKING:
    from ..client import Vault


class RoleManager:
    """
    Manager for role CRUD operations.

    Works directly with the vault_roles table via PostgREST.
    Roles define sets of permissions that can be assigned to users
    within an organization via memberships.

    Example:
        ```python
        vault = await Vault.create()

        # Create role
        role = await vault.roles.create(
            organization_id=org.id,
            name="Editor",
            permissions=["posts:read", "posts:write"]
        )

        # Get role by name
        role = await vault.roles.get_by_name(org.id, "Editor")

        # List roles for organization
        roles = await vault.roles.list_by_organization(org.id)
        ```
    """

    def __init__(self, vault: "Vault") -> None:
        """
        Initialize RoleManager.

        Args:
            vault: Vault client instance
        """
        self.vault = vault
        self.client = vault.client

    async def create(
        self,
        organization_id: UUID,
        name: str,
        permissions: Optional[List[str]] = None,
        description: Optional[str] = None,
        is_default: bool = False,
    ) -> VaultRole:
        """
        Create a new role.

        Creates a role in the vault_roles table for an organization.
        Role names must be unique within an organization.

        Args:
            organization_id: Organization UUID the role belongs to
            name: Role name (unique within organization)
            permissions: List of permission strings (e.g., ["posts:read", "posts:write"])
            description: Optional description of the role
            is_default: If True, new members get this role automatically

        Returns:
            Created VaultRole

        Raises:
            APIError: If role name already exists in organization

        Example:
            ```python
            role = await vault.roles.create(
                organization_id=org.id,
                name="Editor",
                permissions=["posts:read", "posts:write", "comments:*"],
                description="Can manage posts and comments",
                is_default=False
            )
            ```
        """
        # Validate input
        request = CreateRoleRequest(
            organization_id=organization_id,
            name=name,
            permissions=permissions or [],
            description=description,
            is_default=is_default,
        )

        # If this role is default, unset other default roles first
        if request.is_default:
            await self._unset_default_role(organization_id)

        # Insert into vault_roles
        result = await self.client.table("vault_roles").insert(
            {
                "organization_id": str(request.organization_id),
                "name": request.name,
                "description": request.description,
                "permissions": request.permissions,
                "is_default": request.is_default,
                "is_system": False,
            }
        ).execute()

        if not result.data or len(result.data) == 0:
            raise ValueError("Failed to create role")

        return self._parse_role(result.data[0])

    async def create_system_roles(self, organization_id: UUID) -> List[VaultRole]:
        """
        Create default system roles for an organization.

        Creates the standard Owner and Admin roles that cannot be deleted.
        Call this when creating a new organization.

        Args:
            organization_id: Organization UUID

        Returns:
            List of created system roles (Owner, Admin, Member)

        Example:
            ```python
            # After creating an organization
            org = await vault.orgs.create(name="Acme", slug="acme")
            system_roles = await vault.roles.create_system_roles(org.id)
            ```
        """
        system_roles = [
            {
                "organization_id": str(organization_id),
                "name": "Owner",
                "description": "Full access to all organization resources",
                "permissions": ["*:*"],
                "is_default": False,
                "is_system": True,
            },
            {
                "organization_id": str(organization_id),
                "name": "Admin",
                "description": "Administrative access to organization",
                "permissions": ["admin:*", "users:*", "roles:*"],
                "is_default": False,
                "is_system": True,
            },
            {
                "organization_id": str(organization_id),
                "name": "Member",
                "description": "Default member access",
                "permissions": ["read:*"],
                "is_default": True,
                "is_system": True,
            },
        ]

        result = await self.client.table("vault_roles").insert(system_roles).execute()

        if not result.data:
            raise ValueError("Failed to create system roles")

        return [self._parse_role(role) for role in result.data]

    async def get(self, role_id: UUID) -> Optional[VaultRole]:
        """
        Get a role by ID.

        Args:
            role_id: Role UUID

        Returns:
            VaultRole if found, None otherwise

        Example:
            ```python
            role = await vault.roles.get(role_id)
            if role:
                print(f"Role: {role.name}, Permissions: {role.permissions}")
            ```
        """
        result = await self.client.table("vault_roles").select("*").eq(
            "id", str(role_id)
        ).execute()

        if not result.data or len(result.data) == 0:
            return None

        return self._parse_role(result.data[0])

    async def get_by_name(
        self,
        organization_id: UUID,
        name: str,
    ) -> Optional[VaultRole]:
        """
        Get a role by name within an organization.

        Args:
            organization_id: Organization UUID
            name: Role name

        Returns:
            VaultRole if found, None otherwise

        Example:
            ```python
            role = await vault.roles.get_by_name(org.id, "Editor")
            ```
        """
        result = await self.client.table("vault_roles").select("*").eq(
            "organization_id", str(organization_id)
        ).eq("name", name).execute()

        if not result.data or len(result.data) == 0:
            return None

        return self._parse_role(result.data[0])

    async def get_default_role(self, organization_id: UUID) -> Optional[VaultRole]:
        """
        Get the default role for an organization.

        Args:
            organization_id: Organization UUID

        Returns:
            VaultRole marked as default, or None if not set

        Example:
            ```python
            default_role = await vault.roles.get_default_role(org.id)
            if default_role:
                print(f"Default role: {default_role.name}")
            ```
        """
        result = await self.client.table("vault_roles").select("*").eq(
            "organization_id", str(organization_id)
        ).eq("is_default", True).execute()

        if not result.data or len(result.data) == 0:
            return None

        return self._parse_role(result.data[0])

    async def list_by_organization(
        self,
        organization_id: UUID,
        limit: int = 50,
        offset: int = 0,
        include_system: bool = True,
    ) -> List[VaultRole]:
        """
        List roles for an organization.

        Args:
            organization_id: Organization UUID
            limit: Maximum number of roles to return
            offset: Number of roles to skip
            include_system: If True, includes system roles (Owner, Admin)

        Returns:
            List of VaultRole instances

        Example:
            ```python
            # List all roles
            roles = await vault.roles.list_by_organization(org.id)

            # List only custom roles
            custom_roles = await vault.roles.list_by_organization(
                org.id,
                include_system=False
            )
            ```
        """
        query = self.client.table("vault_roles").select("*").eq(
            "organization_id", str(organization_id)
        )

        if not include_system:
            query = query.eq("is_system", False)

        query = query.range(offset, offset + limit - 1).order("created_at")

        result = await query.execute()

        if not result.data:
            return []

        return [self._parse_role(role) for role in result.data]

    async def update(
        self,
        role_id: UUID,
        name: Optional[str] = None,
        description: Optional[str] = None,
        permissions: Optional[List[str]] = None,
        is_default: Optional[bool] = None,
    ) -> VaultRole:
        """
        Update a role.

        System roles (Owner, Admin) cannot have their permissions modified,
        but their description can be updated.

        Args:
            role_id: Role UUID
            name: New role name
            description: New description
            permissions: New permissions list (replaces existing)
            is_default: Whether this is the default role

        Returns:
            Updated VaultRole

        Raises:
            ValueError: If role not found or trying to modify system role permissions

        Example:
            ```python
            role = await vault.roles.update(
                role_id,
                permissions=["posts:read", "posts:write", "posts:delete"]
            )
            ```
        """
        # Check if role exists and is not a system role
        existing = await self.get(role_id)
        if not existing:
            raise ValueError(f"Role not found: {role_id}")

        if existing.is_system and permissions is not None:
            raise ValueError("Cannot modify permissions of system roles")

        # Validate input
        request = UpdateRoleRequest(
            name=name,
            description=description,
            permissions=permissions,
            is_default=is_default,
        )

        # If setting as default, unset other default roles first
        if request.is_default:
            await self._unset_default_role(existing.organization_id)

        # Build update data
        update_data = {"updated_at": datetime.utcnow().isoformat()}

        if request.name is not None:
            update_data["name"] = request.name
        if request.description is not None:
            update_data["description"] = request.description
        if request.permissions is not None:
            update_data["permissions"] = request.permissions
        if request.is_default is not None:
            update_data["is_default"] = request.is_default

        # Update role
        result = await self.client.table("vault_roles").update(
            update_data
        ).eq("id", str(role_id)).execute()

        if not result.data or len(result.data) == 0:
            raise ValueError(f"Role not found: {role_id}")

        return self._parse_role(result.data[0])

    async def delete(self, role_id: UUID) -> None:
        """
        Delete a role.

        System roles (Owner, Admin, Member) cannot be deleted.
        Members with this role will have their role_id set to NULL.

        Args:
            role_id: Role UUID

        Raises:
            ValueError: If role not found or is a system role

        Example:
            ```python
            await vault.roles.delete(role_id)
            ```
        """
        # Check if role exists and is not a system role
        existing = await self.get(role_id)
        if not existing:
            raise ValueError(f"Role not found: {role_id}")

        if existing.is_system:
            raise ValueError("Cannot delete system roles")

        # Delete role
        result = await self.client.table("vault_roles").delete().eq(
            "id", str(role_id)
        ).execute()

        if not result.data or len(result.data) == 0:
            raise ValueError(f"Role not found: {role_id}")

    async def add_permissions(self, role_id: UUID, permissions: List[str]) -> VaultRole:
        """
        Add permissions to a role.

        Args:
            role_id: Role UUID
            permissions: Permissions to add

        Returns:
            Updated VaultRole

        Example:
            ```python
            role = await vault.roles.add_permissions(
                role_id,
                ["comments:write", "comments:delete"]
            )
            ```
        """
        existing = await self.get(role_id)
        if not existing:
            raise ValueError(f"Role not found: {role_id}")

        if existing.is_system:
            raise ValueError("Cannot modify permissions of system roles")

        # Merge permissions, avoiding duplicates
        current_perms = set(existing.permissions)
        current_perms.update(permissions)

        return await self.update(role_id, permissions=list(current_perms))

    async def remove_permissions(self, role_id: UUID, permissions: List[str]) -> VaultRole:
        """
        Remove permissions from a role.

        Args:
            role_id: Role UUID
            permissions: Permissions to remove

        Returns:
            Updated VaultRole

        Example:
            ```python
            role = await vault.roles.remove_permissions(
                role_id,
                ["comments:delete"]
            )
            ```
        """
        existing = await self.get(role_id)
        if not existing:
            raise ValueError(f"Role not found: {role_id}")

        if existing.is_system:
            raise ValueError("Cannot modify permissions of system roles")

        # Remove specified permissions
        current_perms = set(existing.permissions)
        current_perms.difference_update(permissions)

        return await self.update(role_id, permissions=list(current_perms))

    async def count(
        self,
        organization_id: UUID,
        include_system: bool = True,
    ) -> int:
        """
        Count roles for an organization.

        Args:
            organization_id: Organization UUID
            include_system: If True, includes system roles in count

        Returns:
            Number of roles

        Example:
            ```python
            role_count = await vault.roles.count(org.id)
            ```
        """
        query = self.client.table("vault_roles").select("id", count="exact").eq(
            "organization_id", str(organization_id)
        )

        if not include_system:
            query = query.eq("is_system", False)

        result = await query.execute()

        return result.count if result.count is not None else 0

    async def _unset_default_role(self, organization_id: UUID) -> None:
        """Unset the current default role for an organization."""
        await self.client.table("vault_roles").update(
            {"is_default": False, "updated_at": datetime.utcnow().isoformat()}
        ).eq("organization_id", str(organization_id)).eq("is_default", True).execute()

    def _parse_role(self, data: dict) -> VaultRole:
        """Parse database row into VaultRole model."""
        return VaultRole(
            id=UUID(data["id"]),
            organization_id=UUID(data["organization_id"]),
            name=data["name"],
            description=data.get("description"),
            permissions=data.get("permissions", []),
            is_default=data.get("is_default", False),
            is_system=data.get("is_system", False),
            created_at=datetime.fromisoformat(data["created_at"].replace("Z", "+00:00")),
            updated_at=datetime.fromisoformat(data["updated_at"].replace("Z", "+00:00")),
        )
