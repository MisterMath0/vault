"""
Audit logging for Vault.

Provides comprehensive audit logging for tracking all actions
performed in the system.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from uuid import UUID

from .models import AuditAction, AuditContext, AuditLogEntry, ResourceType

if TYPE_CHECKING:
    from ..client import Vault


class AuditLogger:
    """
    Manages audit logging operations.

    Provides methods to log actions, query audit history,
    and generate compliance reports.

    Example:
        ```python
        # Log a user action
        await vault.audit.log(
            action=AuditAction.USER_CREATED,
            user_id=admin.id,
            resource_type=ResourceType.USER,
            resource_id=new_user.id,
            metadata={"email": new_user.email}
        )

        # Query audit log
        entries = await vault.audit.list_by_organization(org.id)
        ```
    """

    def __init__(self, vault: "Vault") -> None:
        """
        Initialize AuditLogger.

        Args:
            vault: Main Vault client instance
        """
        self.vault = vault
        self.client = vault.client
        self._enabled = True

    def disable(self) -> None:
        """Disable audit logging (useful for bulk operations)."""
        self._enabled = False

    def enable(self) -> None:
        """Enable audit logging."""
        self._enabled = True

    @property
    def is_enabled(self) -> bool:
        """Check if audit logging is enabled."""
        return self._enabled

    async def log(
        self,
        action: AuditAction | str,
        user_id: Optional[UUID] = None,
        organization_id: Optional[UUID] = None,
        resource_type: Optional[ResourceType | str] = None,
        resource_id: Optional[UUID] = None,
        metadata: Optional[Dict[str, Any]] = None,
        context: Optional[AuditContext] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditLogEntry:
        """
        Log an audit event.

        Args:
            action: The action being performed (from AuditAction enum or custom string)
            user_id: ID of user performing the action
            organization_id: Organization context (if applicable)
            resource_type: Type of resource being acted on
            resource_id: ID of the resource being acted on
            metadata: Additional details about the action
            context: Request context (ip, user agent, etc.)
            ip_address: IP address (alternative to context)
            user_agent: User agent string (alternative to context)

        Returns:
            AuditLogEntry instance

        Example:
            ```python
            entry = await vault.audit.log(
                action=AuditAction.USER_CREATED,
                user_id=admin.id,
                organization_id=org.id,
                resource_type=ResourceType.USER,
                resource_id=new_user.id,
                metadata={
                    "email": new_user.email,
                    "display_name": new_user.display_name
                }
            )
            ```
        """
        if not self._enabled:
            # Return a dummy entry when disabled
            return AuditLogEntry(
                id=UUID("00000000-0000-0000-0000-000000000000"),
                action=action.value if isinstance(action, AuditAction) else action,
                created_at=datetime.utcnow(),
            )

        # Get values from context if provided
        if context:
            ip_address = ip_address or context.ip_address
            user_agent = user_agent or context.user_agent
            if context.extra:
                metadata = {**(metadata or {}), **context.extra}

        # Build entry data
        entry_data = {
            "action": action.value if isinstance(action, AuditAction) else action,
            "user_id": str(user_id) if user_id else None,
            "organization_id": str(organization_id) if organization_id else None,
            "resource_type": (
                resource_type.value
                if isinstance(resource_type, ResourceType)
                else resource_type
            ),
            "resource_id": str(resource_id) if resource_id else None,
            "metadata": metadata or {},
            "ip_address": ip_address,
            "user_agent": user_agent,
            "created_at": datetime.utcnow().isoformat(),
        }

        result = await self.client.table("vault_audit_log").insert(entry_data).execute()

        return AuditLogEntry(**result.data[0])

    async def log_user_action(
        self,
        action: AuditAction,
        user_id: UUID,
        target_user_id: Optional[UUID] = None,
        organization_id: Optional[UUID] = None,
        metadata: Optional[Dict[str, Any]] = None,
        context: Optional[AuditContext] = None,
    ) -> AuditLogEntry:
        """
        Convenience method for logging user-related actions.

        Args:
            action: User action (USER_CREATED, USER_UPDATED, etc.)
            user_id: ID of user performing the action
            target_user_id: ID of user being acted upon (if different)
            organization_id: Organization context
            metadata: Additional details
            context: Request context

        Returns:
            AuditLogEntry instance
        """
        return await self.log(
            action=action,
            user_id=user_id,
            organization_id=organization_id,
            resource_type=ResourceType.USER,
            resource_id=target_user_id or user_id,
            metadata=metadata,
            context=context,
        )

    async def log_org_action(
        self,
        action: AuditAction,
        user_id: UUID,
        organization_id: UUID,
        metadata: Optional[Dict[str, Any]] = None,
        context: Optional[AuditContext] = None,
    ) -> AuditLogEntry:
        """
        Convenience method for logging organization-related actions.

        Args:
            action: Organization action (ORG_CREATED, ORG_UPDATED, etc.)
            user_id: ID of user performing the action
            organization_id: ID of organization being acted on
            metadata: Additional details
            context: Request context

        Returns:
            AuditLogEntry instance
        """
        return await self.log(
            action=action,
            user_id=user_id,
            organization_id=organization_id,
            resource_type=ResourceType.ORGANIZATION,
            resource_id=organization_id,
            metadata=metadata,
            context=context,
        )

    async def get(self, entry_id: UUID) -> Optional[AuditLogEntry]:
        """
        Get an audit log entry by ID.

        Args:
            entry_id: Audit entry UUID

        Returns:
            AuditLogEntry instance or None if not found
        """
        result = await self.client.table("vault_audit_log").select("*").eq(
            "id", str(entry_id)
        ).execute()

        if not result.data:
            return None

        return AuditLogEntry(**result.data[0])

    async def list_by_organization(
        self,
        organization_id: UUID,
        action: Optional[AuditAction | str] = None,
        user_id: Optional[UUID] = None,
        resource_type: Optional[ResourceType | str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AuditLogEntry]:
        """
        List audit entries for an organization.

        Args:
            organization_id: Organization UUID
            action: Filter by action type
            user_id: Filter by user who performed action
            resource_type: Filter by resource type
            since: Only entries after this time
            until: Only entries before this time
            limit: Maximum entries to return
            offset: Entries to skip

        Returns:
            List of AuditLogEntry instances
        """
        query = self.client.table("vault_audit_log").select("*").eq(
            "organization_id", str(organization_id)
        )

        if action:
            action_value = action.value if isinstance(action, AuditAction) else action
            query = query.eq("action", action_value)

        if user_id:
            query = query.eq("user_id", str(user_id))

        if resource_type:
            type_value = (
                resource_type.value
                if isinstance(resource_type, ResourceType)
                else resource_type
            )
            query = query.eq("resource_type", type_value)

        if since:
            query = query.gte("created_at", since.isoformat())

        if until:
            query = query.lte("created_at", until.isoformat())

        result = await query.limit(limit).offset(offset).order(
            "created_at", desc=True
        ).execute()

        return [AuditLogEntry(**entry) for entry in result.data]

    async def list_by_user(
        self,
        user_id: UUID,
        action: Optional[AuditAction | str] = None,
        organization_id: Optional[UUID] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AuditLogEntry]:
        """
        List audit entries for a user (actions they performed).

        Args:
            user_id: User UUID
            action: Filter by action type
            organization_id: Filter by organization
            since: Only entries after this time
            until: Only entries before this time
            limit: Maximum entries to return
            offset: Entries to skip

        Returns:
            List of AuditLogEntry instances
        """
        query = self.client.table("vault_audit_log").select("*").eq(
            "user_id", str(user_id)
        )

        if action:
            action_value = action.value if isinstance(action, AuditAction) else action
            query = query.eq("action", action_value)

        if organization_id:
            query = query.eq("organization_id", str(organization_id))

        if since:
            query = query.gte("created_at", since.isoformat())

        if until:
            query = query.lte("created_at", until.isoformat())

        result = await query.limit(limit).offset(offset).order(
            "created_at", desc=True
        ).execute()

        return [AuditLogEntry(**entry) for entry in result.data]

    async def list_by_resource(
        self,
        resource_type: ResourceType | str,
        resource_id: UUID,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AuditLogEntry]:
        """
        List audit entries for a specific resource.

        Args:
            resource_type: Type of resource
            resource_id: Resource UUID
            since: Only entries after this time
            until: Only entries before this time
            limit: Maximum entries to return
            offset: Entries to skip

        Returns:
            List of AuditLogEntry instances
        """
        type_value = (
            resource_type.value
            if isinstance(resource_type, ResourceType)
            else resource_type
        )

        query = self.client.table("vault_audit_log").select("*").eq(
            "resource_type", type_value
        ).eq("resource_id", str(resource_id))

        if since:
            query = query.gte("created_at", since.isoformat())

        if until:
            query = query.lte("created_at", until.isoformat())

        result = await query.limit(limit).offset(offset).order(
            "created_at", desc=True
        ).execute()

        return [AuditLogEntry(**entry) for entry in result.data]

    async def count_by_organization(
        self,
        organization_id: UUID,
        action: Optional[AuditAction | str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
    ) -> int:
        """
        Count audit entries for an organization.

        Args:
            organization_id: Organization UUID
            action: Filter by action type
            since: Only entries after this time
            until: Only entries before this time

        Returns:
            Count of entries
        """
        query = self.client.table("vault_audit_log").select(
            "id", count="exact"
        ).eq("organization_id", str(organization_id))

        if action:
            action_value = action.value if isinstance(action, AuditAction) else action
            query = query.eq("action", action_value)

        if since:
            query = query.gte("created_at", since.isoformat())

        if until:
            query = query.lte("created_at", until.isoformat())

        result = await query.execute()
        return result.count or 0

    async def cleanup_old_entries(
        self,
        before: datetime,
        organization_id: Optional[UUID] = None,
    ) -> int:
        """
        Delete audit entries older than a given date.

        Args:
            before: Delete entries created before this time
            organization_id: Only delete for this organization (optional)

        Returns:
            Number of entries deleted

        Example:
            ```python
            from datetime import datetime, timedelta

            # Delete entries older than 90 days
            cutoff = datetime.utcnow() - timedelta(days=90)
            deleted = await vault.audit.cleanup_old_entries(before=cutoff)
            print(f"Deleted {deleted} old audit entries")
            ```
        """
        # Count first
        query = self.client.table("vault_audit_log").select(
            "id", count="exact"
        ).lt("created_at", before.isoformat())

        if organization_id:
            query = query.eq("organization_id", str(organization_id))

        count_result = await query.execute()
        count = count_result.count or 0

        if count > 0:
            # Delete
            delete_query = self.client.table("vault_audit_log").delete().lt(
                "created_at", before.isoformat()
            )

            if organization_id:
                delete_query = delete_query.eq("organization_id", str(organization_id))

            await delete_query.execute()

        return count
