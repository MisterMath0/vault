"""
API key management for Vault.

Handles creating, validating, and managing API keys
for service-to-service authentication.
"""

import hashlib
import secrets
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, List, Optional
from uuid import UUID

from .models import (
    APIKeyUsage,
    APIKeyValidationResult,
    VaultAPIKey,
    VaultAPIKeyWithSecret,
)

if TYPE_CHECKING:
    from ..client import Vault


class APIKeyManager:
    """
    Manages API key operations.

    API keys provide service-to-service authentication with:
    - Scoped permissions
    - Rate limiting
    - Expiration
    - Usage tracking

    Example:
        ```python
        # Create an API key
        key = await vault.api_keys.create(
            name="backend-service",
            organization_id=org.id,
            scopes=["users:read", "orgs:read"],
            rate_limit=1000  # requests per minute
        )
        # Store key.key securely - it won't be returned again
        print(f"API Key: {key.key}")

        # Validate an API key
        result = await vault.api_keys.validate("vk_xxxxx...")
        if result.valid:
            print(f"Key belongs to org: {result.api_key.organization_id}")
        ```
    """

    # API key prefix
    KEY_PREFIX = "vk_"

    def __init__(self, vault: "Vault") -> None:
        """
        Initialize APIKeyManager.

        Args:
            vault: Main Vault client instance
        """
        self.vault = vault
        self.client = vault.client

    def _generate_key(self) -> str:
        """Generate a secure API key."""
        return f"{self.KEY_PREFIX}{secrets.token_urlsafe(32)}"

    def _hash_key(self, key: str) -> str:
        """
        Hash an API key for storage.

        Uses SHA-256 for fast validation while remaining secure.
        """
        return hashlib.sha256(key.encode("utf-8")).hexdigest()

    def _get_prefix(self, key: str) -> str:
        """Extract prefix from key for identification."""
        return key[:11] if len(key) > 11 else key  # vk_ + 8 chars

    async def create(
        self,
        name: str,
        organization_id: UUID,
        description: Optional[str] = None,
        scopes: Optional[List[str]] = None,
        rate_limit: Optional[int] = None,
        expires_in_days: Optional[int] = None,
    ) -> VaultAPIKeyWithSecret:
        """
        Create a new API key.

        Args:
            name: Name for the API key
            organization_id: Organization this key belongs to
            description: Optional description
            scopes: Permission scopes for this key
            rate_limit: Rate limit in requests per minute
            expires_in_days: Days until expiration (None for no expiration)

        Returns:
            VaultAPIKeyWithSecret with the full key (only returned once)

        Raises:
            ValueError: If organization doesn't exist or name already taken

        Example:
            ```python
            key = await vault.api_keys.create(
                name="backend-service",
                organization_id=org.id,
                scopes=["users:read", "users:write"],
                rate_limit=100
            )
            # IMPORTANT: Store this securely - cannot be retrieved again
            print(f"Your API key: {key.key}")
            ```
        """
        # Verify organization exists
        org = await self.vault.orgs.get(organization_id)
        if not org:
            raise ValueError(f"Organization {organization_id} not found")

        # Generate key
        full_key = self._generate_key()
        key_hash = self._hash_key(full_key)
        key_prefix = self._get_prefix(full_key)

        # Calculate expiration
        expires_at = None
        if expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)

        now = datetime.utcnow()
        key_data = {
            "organization_id": str(organization_id),
            "name": name,
            "description": description,
            "key_prefix": key_prefix,
            "key_hash": key_hash,
            "scopes": scopes or [],
            "rate_limit": rate_limit,
            "is_active": True,
            "expires_at": expires_at.isoformat() if expires_at else None,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }

        result = await self.client.table("vault_api_keys").insert(key_data).execute()

        # Build response with full key
        api_key_data = result.data[0].copy()
        del api_key_data["key_hash"]  # Don't expose hash
        api_key_data["key"] = full_key

        return VaultAPIKeyWithSecret(**api_key_data)

    async def get(self, key_id: UUID) -> Optional[VaultAPIKey]:
        """
        Get an API key by ID.

        Args:
            key_id: API key UUID

        Returns:
            VaultAPIKey instance or None if not found
        """
        result = await self.client.table("vault_api_keys").select(
            "id, organization_id, name, description, key_prefix, scopes, "
            "rate_limit, is_active, last_used_at, expires_at, created_at, updated_at"
        ).eq("id", str(key_id)).execute()

        if not result.data:
            return None

        return VaultAPIKey(**result.data[0])

    async def list_by_organization(
        self,
        organization_id: UUID,
        active_only: bool = True,
        limit: int = 50,
        offset: int = 0,
    ) -> List[VaultAPIKey]:
        """
        List API keys for an organization.

        Args:
            organization_id: Organization UUID
            active_only: Only return active keys
            limit: Maximum keys to return
            offset: Keys to skip

        Returns:
            List of VaultAPIKey instances
        """
        query = self.client.table("vault_api_keys").select(
            "id, organization_id, name, description, key_prefix, scopes, "
            "rate_limit, is_active, last_used_at, expires_at, created_at, updated_at"
        ).eq("organization_id", str(organization_id))

        if active_only:
            query = query.eq("is_active", True)

        result = await query.limit(limit).offset(offset).order(
            "created_at", desc=True
        ).execute()

        return [VaultAPIKey(**k) for k in result.data]

    async def validate(
        self,
        key: str,
        required_scopes: Optional[List[str]] = None,
        log_usage: bool = True,
        endpoint: Optional[str] = None,
        method: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> APIKeyValidationResult:
        """
        Validate an API key.

        Args:
            key: The full API key to validate
            required_scopes: Scopes that must be present (if any)
            log_usage: Whether to log this usage
            endpoint: Endpoint being accessed (for logging)
            method: HTTP method (for logging)
            ip_address: Client IP (for logging)
            user_agent: Client user agent (for logging)

        Returns:
            APIKeyValidationResult with validation status

        Example:
            ```python
            result = await vault.api_keys.validate(
                key="vk_xxxxx...",
                required_scopes=["users:read"],
                endpoint="/api/users",
                method="GET"
            )

            if not result.valid:
                raise HTTPException(401, result.error)

            if result.rate_limited:
                raise HTTPException(429, "Rate limit exceeded")
            ```
        """
        # Check key format
        if not key.startswith(self.KEY_PREFIX):
            return APIKeyValidationResult(
                valid=False,
                error="Invalid API key format",
            )

        # Hash the key for lookup
        key_hash = self._hash_key(key)

        # Find key by hash
        result = await self.client.table("vault_api_keys").select("*").eq(
            "key_hash", key_hash
        ).execute()

        if not result.data:
            return APIKeyValidationResult(
                valid=False,
                error="Invalid API key",
            )

        key_data = result.data[0]

        # Check if active
        if not key_data.get("is_active"):
            return APIKeyValidationResult(
                valid=False,
                error="API key is inactive",
            )

        # Check expiration
        expires_at = key_data.get("expires_at")
        if expires_at:
            if isinstance(expires_at, str):
                expires_at = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            if expires_at < datetime.utcnow().replace(tzinfo=expires_at.tzinfo):
                return APIKeyValidationResult(
                    valid=False,
                    error="API key has expired",
                )

        # Check scopes
        if required_scopes:
            key_scopes = set(key_data.get("scopes", []))
            # Support wildcards
            has_all_scopes = True
            for scope in required_scopes:
                resource, action = scope.split(":") if ":" in scope else (scope, "*")
                if scope not in key_scopes:
                    # Check for wildcards
                    if f"{resource}:*" not in key_scopes and "*:*" not in key_scopes:
                        has_all_scopes = False
                        break

            if not has_all_scopes:
                return APIKeyValidationResult(
                    valid=False,
                    error="Insufficient permissions",
                )

        # Check rate limit
        rate_limit = key_data.get("rate_limit")
        remaining_requests = None

        if rate_limit:
            # Count requests in the last minute
            one_minute_ago = (
                datetime.utcnow() - timedelta(minutes=1)
            ).isoformat()

            count_result = await self.client.table("vault_api_key_usage").select(
                "id", count="exact"
            ).eq("api_key_id", key_data["id"]).gte(
                "created_at", one_minute_ago
            ).execute()

            request_count = count_result.count or 0
            remaining_requests = max(0, rate_limit - request_count)

            if request_count >= rate_limit:
                return APIKeyValidationResult(
                    valid=False,
                    error="Rate limit exceeded",
                    rate_limited=True,
                    remaining_requests=0,
                )

        # Log usage
        if log_usage:
            await self._log_usage(
                api_key_id=UUID(key_data["id"]),
                endpoint=endpoint,
                method=method,
                ip_address=ip_address,
                user_agent=user_agent,
            )

        # Update last_used_at
        await self.client.table("vault_api_keys").update({
            "last_used_at": datetime.utcnow().isoformat(),
        }).eq("id", key_data["id"]).execute()

        # Build API key model (without hash)
        api_key = VaultAPIKey(
            id=key_data["id"],
            organization_id=key_data["organization_id"],
            name=key_data["name"],
            description=key_data.get("description"),
            key_prefix=key_data["key_prefix"],
            scopes=key_data.get("scopes", []),
            rate_limit=key_data.get("rate_limit"),
            is_active=key_data["is_active"],
            last_used_at=key_data.get("last_used_at"),
            expires_at=key_data.get("expires_at"),
            created_at=key_data["created_at"],
            updated_at=key_data["updated_at"],
        )

        return APIKeyValidationResult(
            valid=True,
            api_key=api_key,
            remaining_requests=remaining_requests,
        )

    async def _log_usage(
        self,
        api_key_id: UUID,
        endpoint: Optional[str] = None,
        method: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        response_status: Optional[int] = None,
    ) -> None:
        """Log API key usage."""
        usage_data = {
            "api_key_id": str(api_key_id),
            "endpoint": endpoint,
            "method": method,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "response_status": response_status,
            "created_at": datetime.utcnow().isoformat(),
        }

        await self.client.table("vault_api_key_usage").insert(usage_data).execute()

    async def update(
        self,
        key_id: UUID,
        name: Optional[str] = None,
        description: Optional[str] = None,
        scopes: Optional[List[str]] = None,
        rate_limit: Optional[int] = None,
        is_active: Optional[bool] = None,
    ) -> VaultAPIKey:
        """
        Update an API key.

        Args:
            key_id: API key UUID
            name: New name (optional)
            description: New description (optional)
            scopes: New scopes (optional)
            rate_limit: New rate limit (optional)
            is_active: Enable/disable key (optional)

        Returns:
            Updated VaultAPIKey instance
        """
        updates = {"updated_at": datetime.utcnow().isoformat()}

        if name is not None:
            updates["name"] = name
        if description is not None:
            updates["description"] = description
        if scopes is not None:
            updates["scopes"] = scopes
        if rate_limit is not None:
            updates["rate_limit"] = rate_limit
        if is_active is not None:
            updates["is_active"] = is_active

        result = await self.client.table("vault_api_keys").update(updates).eq(
            "id", str(key_id)
        ).execute()

        if not result.data:
            raise ValueError(f"API key {key_id} not found")

        # Remove hash from response
        key_data = result.data[0].copy()
        if "key_hash" in key_data:
            del key_data["key_hash"]

        return VaultAPIKey(**key_data)

    async def revoke(self, key_id: UUID) -> None:
        """
        Revoke (deactivate) an API key.

        Args:
            key_id: API key UUID

        Example:
            ```python
            await vault.api_keys.revoke(key.id)
            ```
        """
        await self.update(key_id, is_active=False)

    async def delete(self, key_id: UUID) -> None:
        """
        Permanently delete an API key.

        Args:
            key_id: API key UUID
        """
        await self.client.table("vault_api_keys").delete().eq(
            "id", str(key_id)
        ).execute()

    async def rotate(
        self,
        key_id: UUID,
        expires_in_days: Optional[int] = None,
    ) -> VaultAPIKeyWithSecret:
        """
        Rotate an API key (generate new key, keep settings).

        Args:
            key_id: API key UUID
            expires_in_days: New expiration (optional)

        Returns:
            VaultAPIKeyWithSecret with new key

        Example:
            ```python
            # Rotate key and get new secret
            new_key = await vault.api_keys.rotate(old_key.id)
            print(f"New API key: {new_key.key}")
            ```
        """
        # Get existing key
        existing = await self.get(key_id)
        if not existing:
            raise ValueError(f"API key {key_id} not found")

        # Generate new key
        full_key = self._generate_key()
        key_hash = self._hash_key(full_key)
        key_prefix = self._get_prefix(full_key)

        # Calculate expiration
        expires_at = None
        if expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)

        now = datetime.utcnow()
        updates = {
            "key_prefix": key_prefix,
            "key_hash": key_hash,
            "updated_at": now.isoformat(),
        }

        if expires_at:
            updates["expires_at"] = expires_at.isoformat()

        result = await self.client.table("vault_api_keys").update(updates).eq(
            "id", str(key_id)
        ).execute()

        # Build response with full key
        key_data = result.data[0].copy()
        del key_data["key_hash"]
        key_data["key"] = full_key

        return VaultAPIKeyWithSecret(**key_data)

    async def get_usage(
        self,
        key_id: UUID,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[APIKeyUsage]:
        """
        Get usage history for an API key.

        Args:
            key_id: API key UUID
            since: Only entries after this time
            until: Only entries before this time
            limit: Maximum entries to return
            offset: Entries to skip

        Returns:
            List of APIKeyUsage instances
        """
        query = self.client.table("vault_api_key_usage").select("*").eq(
            "api_key_id", str(key_id)
        )

        if since:
            query = query.gte("created_at", since.isoformat())

        if until:
            query = query.lte("created_at", until.isoformat())

        result = await query.limit(limit).offset(offset).order(
            "created_at", desc=True
        ).execute()

        return [APIKeyUsage(**u) for u in result.data]

    async def count_by_organization(
        self,
        organization_id: UUID,
        active_only: bool = True,
    ) -> int:
        """
        Count API keys for an organization.

        Args:
            organization_id: Organization UUID
            active_only: Only count active keys

        Returns:
            Count of keys
        """
        query = self.client.table("vault_api_keys").select(
            "id", count="exact"
        ).eq("organization_id", str(organization_id))

        if active_only:
            query = query.eq("is_active", True)

        result = await query.execute()
        return result.count or 0

    async def cleanup_expired(self) -> int:
        """
        Deactivate all expired API keys.

        Returns:
            Number of keys deactivated
        """
        now = datetime.utcnow().isoformat()

        # Count first
        count_result = await self.client.table("vault_api_keys").select(
            "id", count="exact"
        ).eq("is_active", True).lt("expires_at", now).execute()

        count = count_result.count or 0

        if count > 0:
            # Deactivate expired keys
            await self.client.table("vault_api_keys").update({
                "is_active": False,
                "updated_at": now,
            }).eq("is_active", True).lt("expires_at", now).execute()

        return count

    async def cleanup_old_usage(
        self,
        before: datetime,
        key_id: Optional[UUID] = None,
    ) -> int:
        """
        Delete old API key usage records.

        Args:
            before: Delete records created before this time
            key_id: Only delete for this key (optional)

        Returns:
            Number of records deleted
        """
        # Count first
        query = self.client.table("vault_api_key_usage").select(
            "id", count="exact"
        ).lt("created_at", before.isoformat())

        if key_id:
            query = query.eq("api_key_id", str(key_id))

        count_result = await query.execute()
        count = count_result.count or 0

        if count > 0:
            delete_query = self.client.table("vault_api_key_usage").delete().lt(
                "created_at", before.isoformat()
            )

            if key_id:
                delete_query = delete_query.eq("api_key_id", str(key_id))

            await delete_query.execute()

        return count
