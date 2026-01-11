"""
User management for Vault.

Handles creating, reading, updating, and deleting users.
Syncs between vault_users table and Supabase auth.users.

Wraps: supabase_auth._async.gotrue_admin_api.AsyncGoTrueAdminAPI
Source: venv/lib/python3.14/site-packages/supabase_auth/_async/gotrue_admin_api.py
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from supabase_auth.types import AdminUserAttributes

from .models import CreateUserRequest, UpdateUserRequest, VaultUser


class UserManager:
    """
    Manages user CRUD operations with vault_users table and Supabase auth sync.

    The flow for user management:
    1. Create/update in vault_users (source of truth)
    2. Sync to Supabase auth.users (for authentication)
    3. Store supabase_auth_id link for sync tracking
    """

    def __init__(self, vault) -> None:
        """
        Initialize UserManager.

        Args:
            vault: Main Vault client instance
        """
        self.vault = vault
        self.client = vault.client

    async def create(
        self,
        email: str,
        password: Optional[str] = None,
        display_name: Optional[str] = None,
        avatar_url: Optional[str] = None,
        metadata: Optional[dict] = None,
        email_confirm: bool = False,
    ) -> VaultUser:
        """
        Create a new user in Vault and sync to Supabase auth.

        Wraps: supabase_auth._async.gotrue_admin_api.GoTrueAdminAPI.create_user
        Source: venv/lib/python3.14/site-packages/supabase_auth/_async/gotrue_admin_api.py:119

        Args:
            email: User email address
            password: Password (optional, can be set later)
            display_name: User's display name
            avatar_url: URL to user's avatar image
            metadata: Additional user metadata (any JSON-serializable dict)
            email_confirm: Auto-confirm email (skip verification)

        Returns:
            VaultUser instance

        Raises:
            Exception: If user creation fails

        Example:
            ```python
            user = await vault.users.create(
                email="user@example.com",
                password="secure123",
                display_name="John Doe"
            )
            ```
        """
        # First, create in Supabase auth to get auth user
        # This ensures authentication works
        auth_attributes: AdminUserAttributes = {
            "email": email,
            "email_confirm": email_confirm,
        }

        if password:
            auth_attributes["password"] = password

        # Add user_metadata (Supabase stores display_name, avatar_url here)
        user_metadata = {}
        if display_name:
            user_metadata["display_name"] = display_name
        if avatar_url:
            user_metadata["avatar_url"] = avatar_url
        if metadata:
            user_metadata.update(metadata)

        if user_metadata:
            auth_attributes["user_metadata"] = user_metadata

        # Create user in Supabase auth
        auth_response = await self.client.auth.admin.create_user(auth_attributes)
        auth_user = auth_response.user

        # Now create in vault_users table (our source of truth)
        now = datetime.utcnow()
        vault_user_data = {
            "email": email,
            "email_verified": email_confirm,
            "display_name": display_name,
            "avatar_url": avatar_url,
            "metadata": metadata or {},
            "supabase_auth_id": auth_user.id,
            "auth_provider": "email",
            "status": "active",
            "last_sign_in_at": None,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }

        result = await self.client.table("vault_users").insert(vault_user_data).execute()

        # Convert to VaultUser model
        user_dict = result.data[0]
        return VaultUser(**user_dict)

    async def get(self, user_id: UUID) -> Optional[VaultUser]:
        """
        Get a user by their Vault user ID.

        Args:
            user_id: Vault user UUID

        Returns:
            VaultUser instance or None if not found

        Example:
            ```python
            user = await vault.users.get(user_id)
            if user:
                print(f"Found user: {user.email}")
            ```
        """
        result = await self.client.table("vault_users").select("*").eq(
            "id", str(user_id)
        ).execute()

        if not result.data:
            return None

        return VaultUser(**result.data[0])

    async def get_by_email(self, email: str) -> Optional[VaultUser]:
        """
        Get a user by their email address.

        Args:
            email: User email address

        Returns:
            VaultUser instance or None if not found

        Example:
            ```python
            user = await vault.users.get_by_email("user@example.com")
            ```
        """
        result = await self.client.table("vault_users").select("*").eq(
            "email", email
        ).execute()

        if not result.data:
            return None

        return VaultUser(**result.data[0])

    async def list(
        self,
        limit: int = 50,
        offset: int = 0,
        status: Optional[str] = None,
    ) -> List[VaultUser]:
        """
        List users with optional filtering and pagination.

        Args:
            limit: Maximum number of users to return
            offset: Number of users to skip
            status: Filter by status (active, suspended, deleted)

        Returns:
            List of VaultUser instances

        Example:
            ```python
            # Get first 50 active users
            users = await vault.users.list(status="active")

            # Pagination
            page2 = await vault.users.list(limit=50, offset=50)
            ```
        """
        query = self.client.table("vault_users").select("*")

        if status:
            query = query.eq("status", status)

        result = await query.limit(limit).offset(offset).order(
            "created_at", desc=True
        ).execute()

        return [VaultUser(**user_dict) for user_dict in result.data]

    async def update(
        self,
        user_id: UUID,
        email: Optional[str] = None,
        password: Optional[str] = None,
        display_name: Optional[str] = None,
        avatar_url: Optional[str] = None,
        metadata: Optional[dict] = None,
        status: Optional[str] = None,
    ) -> VaultUser:
        """
        Update a user's information.

        Wraps: supabase_auth._async.gotrue_admin_api.GoTrueAdminAPI.update_user_by_id
        Source: venv/lib/python3.14/site-packages/supabase_auth/_async/gotrue_admin_api.py:164

        Args:
            user_id: Vault user UUID
            email: New email address
            password: New password
            display_name: New display name
            avatar_url: New avatar URL
            metadata: New metadata (replaces existing)
            status: New status (active, suspended, deleted)

        Returns:
            Updated VaultUser instance

        Example:
            ```python
            user = await vault.users.update(
                user_id,
                display_name="Jane Doe",
                status="suspended"
            )
            ```
        """
        # Get current user to get supabase_auth_id
        current_user = await self.get(user_id)
        if not current_user:
            raise ValueError(f"User {user_id} not found")

        # Update in vault_users first
        vault_updates = {"updated_at": datetime.utcnow().isoformat()}

        if email is not None:
            vault_updates["email"] = email
        if display_name is not None:
            vault_updates["display_name"] = display_name
        if avatar_url is not None:
            vault_updates["avatar_url"] = avatar_url
        if metadata is not None:
            vault_updates["metadata"] = metadata
        if status is not None:
            vault_updates["status"] = status

        result = await self.client.table("vault_users").update(vault_updates).eq(
            "id", str(user_id)
        ).execute()

        # Sync to Supabase auth if we have supabase_auth_id
        if current_user.supabase_auth_id:
            auth_attributes: AdminUserAttributes = {}

            if email is not None:
                auth_attributes["email"] = email
            if password is not None:
                auth_attributes["password"] = password

            # Update user_metadata in Supabase
            user_metadata = {}
            if display_name is not None:
                user_metadata["display_name"] = display_name
            if avatar_url is not None:
                user_metadata["avatar_url"] = avatar_url

            if user_metadata:
                auth_attributes["user_metadata"] = user_metadata

            if auth_attributes:
                await self.client.auth.admin.update_user_by_id(
                    str(current_user.supabase_auth_id), auth_attributes
                )

        return VaultUser(**result.data[0])

    async def delete(self, user_id: UUID, soft_delete: bool = True) -> None:
        """
        Delete a user.

        Wraps: supabase_auth._async.gotrue_admin_api.GoTrueAdminAPI.delete_user
        Source: venv/lib/python3.14/site-packages/supabase_auth/_async/gotrue_admin_api.py:183

        Args:
            user_id: Vault user UUID
            soft_delete: If True, mark as deleted; if False, permanently delete

        Example:
            ```python
            # Soft delete (mark as deleted)
            await vault.users.delete(user_id)

            # Hard delete (permanent)
            await vault.users.delete(user_id, soft_delete=False)
            ```
        """
        # Get user to get supabase_auth_id
        user = await self.get(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")

        if soft_delete:
            # Just update status to deleted
            await self.update(user_id, status="deleted")
        else:
            # Permanently delete from both vault_users and Supabase auth
            if user.supabase_auth_id:
                await self.client.auth.admin.delete_user(
                    str(user.supabase_auth_id), should_soft_delete=False
                )

            await self.client.table("vault_users").delete().eq(
                "id", str(user_id)
            ).execute()

    async def count(self, status: Optional[str] = None) -> int:
        """
        Count total users.

        Args:
            status: Filter by status (active, suspended, deleted)

        Returns:
            Total count of users

        Example:
            ```python
            total = await vault.users.count()
            active = await vault.users.count(status="active")
            ```
        """
        query = self.client.table("vault_users").select("id", count="exact")

        if status:
            query = query.eq("status", status)

        result = await query.execute()
        return result.count or 0
