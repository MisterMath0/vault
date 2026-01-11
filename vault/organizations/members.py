"""
Membership management for Vault.

Handles operations for user memberships in organizations (vault_memberships table).
"""

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from uuid import UUID

from .models import (
    CreateMembershipRequest,
    UpdateMembershipRequest,
    VaultMembership,
)

if TYPE_CHECKING:
    from ..client import Vault


class MembershipManager:
    """
    Manager for organization membership operations.

    Works directly with the vault_memberships table via PostgREST.
    Memberships link users to organizations with optional roles.

    Example:
        ```python
        vault = await Vault.create()

        # Add user to organization
        membership = await vault.memberships.create(
            user_id=user_id,
            organization_id=org_id,
            role_id=role_id
        )

        # List organization members
        members = await vault.memberships.list_by_organization(org_id)

        # List user's organizations
        orgs = await vault.memberships.list_by_user(user_id)
        ```
    """

    def __init__(self, vault: "Vault") -> None:
        """
        Initialize MembershipManager.

        Args:
            vault: Vault client instance
        """
        self.vault = vault
        self.client = vault.client

    async def create(
        self,
        user_id: UUID,
        organization_id: UUID,
        role_id: Optional[UUID] = None,
        metadata: Optional[dict] = None,
    ) -> VaultMembership:
        """
        Create a new membership (add user to organization).

        Args:
            user_id: User UUID
            organization_id: Organization UUID
            role_id: Optional role UUID
            metadata: Optional metadata dict

        Returns:
            Created VaultMembership

        Raises:
            APIError: If user already member or validation fails

        Example:
            ```python
            membership = await vault.memberships.create(
                user_id=user_id,
                organization_id=org_id,
                role_id=editor_role_id,
                metadata={"invited_by": "admin@example.com"}
            )
            ```
        """
        # Validate input
        request = CreateMembershipRequest(
            user_id=user_id,
            organization_id=organization_id,
            role_id=role_id,
            metadata=metadata or {},
        )

        # Insert into vault_memberships
        insert_data = {
            "user_id": str(request.user_id),
            "organization_id": str(request.organization_id),
            "metadata": request.metadata,
        }

        if request.role_id is not None:
            insert_data["role_id"] = str(request.role_id)

        result = await self.client.table("vault_memberships").insert(insert_data).execute()

        if not result.data or len(result.data) == 0:
            raise ValueError("Failed to create membership")

        member_data = result.data[0]
        return VaultMembership(
            id=UUID(member_data["id"]),
            user_id=UUID(member_data["user_id"]),
            organization_id=UUID(member_data["organization_id"]),
            role_id=UUID(member_data["role_id"]) if member_data.get("role_id") else None,
            status=member_data.get("status", "active"),
            metadata=member_data.get("metadata", {}),
            joined_at=datetime.fromisoformat(member_data["joined_at"].replace("Z", "+00:00")),
            updated_at=datetime.fromisoformat(member_data["updated_at"].replace("Z", "+00:00")),
        )

    async def get(self, membership_id: UUID) -> Optional[VaultMembership]:
        """
        Get a membership by ID.

        Args:
            membership_id: Membership UUID

        Returns:
            VaultMembership if found, None otherwise

        Example:
            ```python
            membership = await vault.memberships.get(membership_id)
            ```
        """
        result = await self.client.table("vault_memberships").select("*").eq(
            "id", str(membership_id)
        ).execute()

        if not result.data or len(result.data) == 0:
            return None

        member_data = result.data[0]
        return VaultMembership(
            id=UUID(member_data["id"]),
            user_id=UUID(member_data["user_id"]),
            organization_id=UUID(member_data["organization_id"]),
            role_id=UUID(member_data["role_id"]) if member_data.get("role_id") else None,
            status=member_data.get("status", "active"),
            metadata=member_data.get("metadata", {}),
            joined_at=datetime.fromisoformat(member_data["joined_at"].replace("Z", "+00:00")),
            updated_at=datetime.fromisoformat(member_data["updated_at"].replace("Z", "+00:00")),
        )

    async def get_by_user_and_org(
        self,
        user_id: UUID,
        organization_id: UUID,
    ) -> Optional[VaultMembership]:
        """
        Get a user's membership in a specific organization.

        Args:
            user_id: User UUID
            organization_id: Organization UUID

        Returns:
            VaultMembership if found, None otherwise

        Example:
            ```python
            membership = await vault.memberships.get_by_user_and_org(user_id, org_id)
            if membership:
                print(f"User is a member with role: {membership.role_id}")
            ```
        """
        result = await self.client.table("vault_memberships").select("*").eq(
            "user_id", str(user_id)
        ).eq("organization_id", str(organization_id)).execute()

        if not result.data or len(result.data) == 0:
            return None

        member_data = result.data[0]
        return VaultMembership(
            id=UUID(member_data["id"]),
            user_id=UUID(member_data["user_id"]),
            organization_id=UUID(member_data["organization_id"]),
            role_id=UUID(member_data["role_id"]) if member_data.get("role_id") else None,
            status=member_data.get("status", "active"),
            metadata=member_data.get("metadata", {}),
            joined_at=datetime.fromisoformat(member_data["joined_at"].replace("Z", "+00:00")),
            updated_at=datetime.fromisoformat(member_data["updated_at"].replace("Z", "+00:00")),
        )

    async def list_by_organization(
        self,
        organization_id: UUID,
        limit: int = 50,
        offset: int = 0,
        status: Optional[str] = None,
    ) -> List[VaultMembership]:
        """
        List all members of an organization.

        Args:
            organization_id: Organization UUID
            limit: Maximum number of memberships to return
            offset: Number of memberships to skip
            status: Optional status filter (active, suspended, pending)

        Returns:
            List of VaultMembership instances

        Example:
            ```python
            # List all active members
            members = await vault.memberships.list_by_organization(
                org_id,
                status="active"
            )
            ```
        """
        query = self.client.table("vault_memberships").select("*").eq(
            "organization_id", str(organization_id)
        )

        if status:
            query = query.eq("status", status)

        query = query.range(offset, offset + limit - 1).order("joined_at")

        result = await query.execute()

        if not result.data:
            return []

        return [
            VaultMembership(
                id=UUID(m["id"]),
                user_id=UUID(m["user_id"]),
                organization_id=UUID(m["organization_id"]),
                role_id=UUID(m["role_id"]) if m.get("role_id") else None,
                status=m.get("status", "active"),
                metadata=m.get("metadata", {}),
                joined_at=datetime.fromisoformat(m["joined_at"].replace("Z", "+00:00")),
                updated_at=datetime.fromisoformat(m["updated_at"].replace("Z", "+00:00")),
            )
            for m in result.data
        ]

    async def list_by_user(
        self,
        user_id: UUID,
        limit: int = 50,
        offset: int = 0,
        status: Optional[str] = None,
    ) -> List[VaultMembership]:
        """
        List all organizations a user is a member of.

        Args:
            user_id: User UUID
            limit: Maximum number of memberships to return
            offset: Number of memberships to skip
            status: Optional status filter (active, suspended, pending)

        Returns:
            List of VaultMembership instances

        Example:
            ```python
            # List all user's active memberships
            user_orgs = await vault.memberships.list_by_user(
                user_id,
                status="active"
            )
            ```
        """
        query = self.client.table("vault_memberships").select("*").eq(
            "user_id", str(user_id)
        )

        if status:
            query = query.eq("status", status)

        query = query.range(offset, offset + limit - 1).order("joined_at")

        result = await query.execute()

        if not result.data:
            return []

        return [
            VaultMembership(
                id=UUID(m["id"]),
                user_id=UUID(m["user_id"]),
                organization_id=UUID(m["organization_id"]),
                role_id=UUID(m["role_id"]) if m.get("role_id") else None,
                status=m.get("status", "active"),
                metadata=m.get("metadata", {}),
                joined_at=datetime.fromisoformat(m["joined_at"].replace("Z", "+00:00")),
                updated_at=datetime.fromisoformat(m["updated_at"].replace("Z", "+00:00")),
            )
            for m in result.data
        ]

    async def update(
        self,
        membership_id: UUID,
        role_id: Optional[UUID] = None,
        status: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> VaultMembership:
        """
        Update a membership.

        Args:
            membership_id: Membership UUID
            role_id: New role UUID
            status: New status (active, suspended, pending)
            metadata: New metadata dict (replaces existing)

        Returns:
            Updated VaultMembership

        Raises:
            ValueError: If membership not found

        Example:
            ```python
            # Change user's role
            membership = await vault.memberships.update(
                membership_id,
                role_id=admin_role_id
            )

            # Suspend membership
            membership = await vault.memberships.update(
                membership_id,
                status="suspended"
            )
            ```
        """
        # Validate input
        request = UpdateMembershipRequest(
            role_id=role_id,
            status=status,
            metadata=metadata,
        )

        # Build update data
        update_data = {"updated_at": datetime.utcnow().isoformat()}

        if request.role_id is not None:
            update_data["role_id"] = str(request.role_id)
        if request.status is not None:
            update_data["status"] = request.status
        if request.metadata is not None:
            update_data["metadata"] = request.metadata

        # Update membership
        result = await self.client.table("vault_memberships").update(
            update_data
        ).eq("id", str(membership_id)).execute()

        if not result.data or len(result.data) == 0:
            raise ValueError(f"Membership not found: {membership_id}")

        member_data = result.data[0]
        return VaultMembership(
            id=UUID(member_data["id"]),
            user_id=UUID(member_data["user_id"]),
            organization_id=UUID(member_data["organization_id"]),
            role_id=UUID(member_data["role_id"]) if member_data.get("role_id") else None,
            status=member_data.get("status", "active"),
            metadata=member_data.get("metadata", {}),
            joined_at=datetime.fromisoformat(member_data["joined_at"].replace("Z", "+00:00")),
            updated_at=datetime.fromisoformat(member_data["updated_at"].replace("Z", "+00:00")),
        )

    async def delete(self, membership_id: UUID) -> None:
        """
        Remove a membership (remove user from organization).

        This is always a hard delete as memberships are join records.

        Args:
            membership_id: Membership UUID

        Raises:
            ValueError: If membership not found

        Example:
            ```python
            await vault.memberships.delete(membership_id)
            ```
        """
        result = await self.client.table("vault_memberships").delete().eq(
            "id", str(membership_id)
        ).execute()

        if not result.data or len(result.data) == 0:
            raise ValueError(f"Membership not found: {membership_id}")

    async def delete_by_user_and_org(
        self,
        user_id: UUID,
        organization_id: UUID,
    ) -> None:
        """
        Remove a user from an organization.

        Convenience method to delete membership by user and org IDs.

        Args:
            user_id: User UUID
            organization_id: Organization UUID

        Raises:
            ValueError: If membership not found

        Example:
            ```python
            await vault.memberships.delete_by_user_and_org(user_id, org_id)
            ```
        """
        result = await self.client.table("vault_memberships").delete().eq(
            "user_id", str(user_id)
        ).eq("organization_id", str(organization_id)).execute()

        if not result.data or len(result.data) == 0:
            raise ValueError(
                f"Membership not found for user {user_id} in organization {organization_id}"
            )

    async def count_by_organization(
        self,
        organization_id: UUID,
        status: Optional[str] = None,
    ) -> int:
        """
        Count members in an organization.

        Args:
            organization_id: Organization UUID
            status: Optional status filter (active, suspended, pending)

        Returns:
            Number of members matching the filter

        Example:
            ```python
            # Count all members
            total = await vault.memberships.count_by_organization(org_id)

            # Count active members
            active = await vault.memberships.count_by_organization(
                org_id,
                status="active"
            )
            ```
        """
        query = self.client.table("vault_memberships").select(
            "id", count="exact"
        ).eq("organization_id", str(organization_id))

        if status:
            query = query.eq("status", status)

        result = await query.execute()

        return result.count if result.count is not None else 0
