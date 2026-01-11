"""
Main Vault client.

This is the primary interface users interact with.
"""

from typing import Optional

from .auth import SessionManager, UserManager
from .config import VaultConfig, load_config
from .organizations import MembershipManager, OrganizationManager
from .utils.supabase import VaultSupabaseClient


class Vault:
    """
    Main Vault client for multi-tenant RBAC.

    This is the primary interface for interacting with Vault. It provides
    access to all Vault features: users, organizations, roles, permissions, etc.

    Example:
        ```python
        from vault import Vault

        # Initialize from environment variables
        vault = await Vault.create()

        # Or with explicit config
        vault = await Vault.create(
            supabase_url="https://xxx.supabase.co",
            supabase_key="your-service-key"
        )

        # Use Vault features
        user = await vault.users.create(email="user@example.com", password="secure123")
        org = await vault.orgs.create(name="Acme Corp", slug="acme-corp")
        ```
    """

    def __init__(self, config: VaultConfig, client: VaultSupabaseClient) -> None:
        """
        Initialize Vault client.

        Args:
            config: Vault configuration
            client: Supabase client wrapper

        Note:
            Use Vault.create() instead of direct instantiation.
        """
        self.config = config
        self.client = client

        # Phase 2: User management and sessions
        self.users = UserManager(self)
        self.sessions = SessionManager(self)

        # Phase 3: Organizations and memberships
        self.orgs = OrganizationManager(self)
        self.memberships = MembershipManager(self)

        # These will be implemented in later phases:
        # self.roles = RoleManager(self)
        # self.invites = InvitationManager(self)

    @classmethod
    async def create(
        cls,
        supabase_url: Optional[str] = None,
        supabase_key: Optional[str] = None,
        **kwargs,
    ) -> "Vault":
        """
        Create and initialize a Vault client.

        Args:
            supabase_url: Supabase project URL (optional, loads from env)
            supabase_key: Supabase service role key (optional, loads from env)
            **kwargs: Additional configuration options

        Returns:
            Initialized Vault client

        Raises:
            ValidationError: If required configuration is missing or invalid

        Example:
            ```python
            # Load from environment (.env file or VAULT_* env vars)
            vault = await Vault.create()

            # Explicit configuration
            vault = await Vault.create(
                supabase_url="https://xxx.supabase.co",
                supabase_key="your-service-key"
            )
            ```
        """
        # Build config kwargs
        config_kwargs = kwargs.copy()
        if supabase_url:
            config_kwargs["supabase_url"] = supabase_url
        if supabase_key:
            config_kwargs["supabase_key"] = supabase_key

        # Load configuration
        config = load_config(**config_kwargs)

        # Create Supabase client
        client = await VaultSupabaseClient.create(config)

        # Auto-migrate if enabled
        if config.auto_migrate:
            from .migrations.manager import MigrationManager

            manager = MigrationManager(client)
            await manager.migrate()

        return cls(config=config, client=client)

    async def close(self) -> None:
        """
        Close the Vault client and cleanup resources.

        Example:
            ```python
            vault = await Vault.create()
            try:
                # ... use vault
                pass
            finally:
                await vault.close()
            ```
        """
        await self.client.close()

    async def __aenter__(self) -> "Vault":
        """Context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        await self.close()
