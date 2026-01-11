"""
Organization management for Vault.

Handles CRUD operations for organizations in the vault_organizations table.
"""

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from uuid import UUID

from postgrest.exceptions import APIError

from .models import (
    CreateOrganizationRequest,
    UpdateOrganizationRequest,
    VaultOrganization,
)

if TYPE_CHECKING:
    from ..client import Vault


class OrganizationManager:
    """
    Manager for organization CRUD operations.

    Works directly with the vault_organizations table via PostgREST.
    Organizations are the top-level tenant entities for multi-tenant RBAC.

    Example:
        ```python
        vault = await Vault.create()

        # Create organization
        org = await vault.orgs.create(
            name="Acme Corp",
            slug="acme-corp"
        )

        # Get organization by slug
        org = await vault.orgs.get_by_slug("acme-corp")

        # List all organizations
        orgs = await vault.orgs.list()
        ```
    """

    def __init__(self, vault: "Vault") -> None:
        """
        Initialize OrganizationManager.

        Args:
            vault: Vault client instance
        """
        self.vault = vault
        self.client = vault.client

    async def create(
        self,
        name: str,
        slug: str,
        settings: Optional[dict] = None,
        metadata: Optional[dict] = None,
    ) -> VaultOrganization:
        """
        Create a new organization.

        Creates an organization in the vault_organizations table.
        Slugs must be unique and lowercase.

        Args:
            name: Organization name (display name)
            slug: Unique slug for the organization (lowercase, hyphens only)
            settings: Optional settings dict (billing tier, feature flags, etc.)
            metadata: Optional metadata dict (custom fields)

        Returns:
            Created VaultOrganization

        Raises:
            APIError: If slug already exists or validation fails

        Example:
            ```python
            org = await vault.orgs.create(
                name="Acme Corp",
                slug="acme-corp",
                settings={"billing_tier": "pro"},
                metadata={"industry": "technology"}
            )
            ```
        """
        # Validate input
        request = CreateOrganizationRequest(
            name=name,
            slug=slug,
            settings=settings or {},
            metadata=metadata or {},
        )

        # Insert into vault_organizations
        result = await self.client.table("vault_organizations").insert(
            {
                "name": request.name,
                "slug": request.slug,
                "settings": request.settings,
                "metadata": request.metadata,
            }
        ).execute()

        if not result.data or len(result.data) == 0:
            raise ValueError("Failed to create organization")

        org_data = result.data[0]
        return VaultOrganization(
            id=UUID(org_data["id"]),
            name=org_data["name"],
            slug=org_data["slug"],
            settings=org_data.get("settings", {}),
            metadata=org_data.get("metadata", {}),
            status=org_data.get("status", "active"),
            created_at=datetime.fromisoformat(org_data["created_at"].replace("Z", "+00:00")),
            updated_at=datetime.fromisoformat(org_data["updated_at"].replace("Z", "+00:00")),
        )

    async def get(self, organization_id: UUID) -> Optional[VaultOrganization]:
        """
        Get an organization by ID.

        Args:
            organization_id: Organization UUID

        Returns:
            VaultOrganization if found, None otherwise

        Example:
            ```python
            org = await vault.orgs.get(org_id)
            if org:
                print(f"Found: {org.name}")
            ```
        """
        result = await self.client.table("vault_organizations").select("*").eq(
            "id", str(organization_id)
        ).execute()

        if not result.data or len(result.data) == 0:
            return None

        org_data = result.data[0]
        return VaultOrganization(
            id=UUID(org_data["id"]),
            name=org_data["name"],
            slug=org_data["slug"],
            settings=org_data.get("settings", {}),
            metadata=org_data.get("metadata", {}),
            status=org_data.get("status", "active"),
            created_at=datetime.fromisoformat(org_data["created_at"].replace("Z", "+00:00")),
            updated_at=datetime.fromisoformat(org_data["updated_at"].replace("Z", "+00:00")),
        )

    async def get_by_slug(self, slug: str) -> Optional[VaultOrganization]:
        """
        Get an organization by slug.

        Args:
            slug: Organization slug (unique identifier)

        Returns:
            VaultOrganization if found, None otherwise

        Example:
            ```python
            org = await vault.orgs.get_by_slug("acme-corp")
            ```
        """
        result = await self.client.table("vault_organizations").select("*").eq(
            "slug", slug
        ).execute()

        if not result.data or len(result.data) == 0:
            return None

        org_data = result.data[0]
        return VaultOrganization(
            id=UUID(org_data["id"]),
            name=org_data["name"],
            slug=org_data["slug"],
            settings=org_data.get("settings", {}),
            metadata=org_data.get("metadata", {}),
            status=org_data.get("status", "active"),
            created_at=datetime.fromisoformat(org_data["created_at"].replace("Z", "+00:00")),
            updated_at=datetime.fromisoformat(org_data["updated_at"].replace("Z", "+00:00")),
        )

    async def list(
        self,
        limit: int = 50,
        offset: int = 0,
        status: Optional[str] = None,
    ) -> List[VaultOrganization]:
        """
        List organizations with optional filtering.

        Args:
            limit: Maximum number of organizations to return
            offset: Number of organizations to skip
            status: Optional status filter (active, suspended, deleted)

        Returns:
            List of VaultOrganization instances

        Example:
            ```python
            # List all active organizations
            orgs = await vault.orgs.list(status="active")

            # Paginate results
            page_2 = await vault.orgs.list(limit=10, offset=10)
            ```
        """
        query = self.client.table("vault_organizations").select("*")

        if status:
            query = query.eq("status", status)

        query = query.range(offset, offset + limit - 1).order("created_at")

        result = await query.execute()

        if not result.data:
            return []

        return [
            VaultOrganization(
                id=UUID(org["id"]),
                name=org["name"],
                slug=org["slug"],
                settings=org.get("settings", {}),
                metadata=org.get("metadata", {}),
                status=org.get("status", "active"),
                created_at=datetime.fromisoformat(org["created_at"].replace("Z", "+00:00")),
                updated_at=datetime.fromisoformat(org["updated_at"].replace("Z", "+00:00")),
            )
            for org in result.data
        ]

    async def update(
        self,
        organization_id: UUID,
        name: Optional[str] = None,
        slug: Optional[str] = None,
        settings: Optional[dict] = None,
        metadata: Optional[dict] = None,
        status: Optional[str] = None,
    ) -> VaultOrganization:
        """
        Update an organization.

        Args:
            organization_id: Organization UUID
            name: New organization name
            slug: New slug (must be unique)
            settings: New settings dict (replaces existing)
            metadata: New metadata dict (replaces existing)
            status: New status (active, suspended, deleted)

        Returns:
            Updated VaultOrganization

        Raises:
            ValueError: If organization not found
            APIError: If slug conflicts or validation fails

        Example:
            ```python
            org = await vault.orgs.update(
                org_id,
                name="New Name",
                settings={"billing_tier": "enterprise"}
            )
            ```
        """
        # Validate input
        request = UpdateOrganizationRequest(
            name=name,
            slug=slug,
            settings=settings,
            metadata=metadata,
            status=status,
        )

        # Build update data
        update_data = {"updated_at": datetime.utcnow().isoformat()}

        if request.name is not None:
            update_data["name"] = request.name
        if request.slug is not None:
            update_data["slug"] = request.slug
        if request.settings is not None:
            update_data["settings"] = request.settings
        if request.metadata is not None:
            update_data["metadata"] = request.metadata
        if request.status is not None:
            update_data["status"] = request.status

        # Update organization
        result = await self.client.table("vault_organizations").update(
            update_data
        ).eq("id", str(organization_id)).execute()

        if not result.data or len(result.data) == 0:
            raise ValueError(f"Organization not found: {organization_id}")

        org_data = result.data[0]
        return VaultOrganization(
            id=UUID(org_data["id"]),
            name=org_data["name"],
            slug=org_data["slug"],
            settings=org_data.get("settings", {}),
            metadata=org_data.get("metadata", {}),
            status=org_data.get("status", "active"),
            created_at=datetime.fromisoformat(org_data["created_at"].replace("Z", "+00:00")),
            updated_at=datetime.fromisoformat(org_data["updated_at"].replace("Z", "+00:00")),
        )

    async def delete(
        self,
        organization_id: UUID,
        soft_delete: bool = True,
    ) -> None:
        """
        Delete an organization.

        By default performs a soft delete (marks as deleted).
        Hard delete permanently removes the organization and all related data.

        Args:
            organization_id: Organization UUID
            soft_delete: If True, marks as deleted. If False, permanently deletes.

        Raises:
            ValueError: If organization not found

        Example:
            ```python
            # Soft delete (recoverable)
            await vault.orgs.delete(org_id)

            # Hard delete (permanent)
            await vault.orgs.delete(org_id, soft_delete=False)
            ```
        """
        if soft_delete:
            # Soft delete: mark as deleted
            result = await self.client.table("vault_organizations").update(
                {"status": "deleted", "updated_at": datetime.utcnow().isoformat()}
            ).eq("id", str(organization_id)).execute()

            if not result.data or len(result.data) == 0:
                raise ValueError(f"Organization not found: {organization_id}")
        else:
            # Hard delete: permanently remove
            result = await self.client.table("vault_organizations").delete().eq(
                "id", str(organization_id)
            ).execute()

            if not result.data or len(result.data) == 0:
                raise ValueError(f"Organization not found: {organization_id}")

    async def count(self, status: Optional[str] = None) -> int:
        """
        Count organizations.

        Args:
            status: Optional status filter (active, suspended, deleted)

        Returns:
            Number of organizations matching the filter

        Example:
            ```python
            # Count all organizations
            total = await vault.orgs.count()

            # Count active organizations
            active_count = await vault.orgs.count(status="active")
            ```
        """
        query = self.client.table("vault_organizations").select("id", count="exact")

        if status:
            query = query.eq("status", status)

        result = await query.execute()

        return result.count if result.count is not None else 0
