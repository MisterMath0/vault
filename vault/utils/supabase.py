"""
Supabase client wrapper for Vault.

Provides a thin wrapper around the Supabase AsyncClient with Vault-specific configuration.

Package versions this was built against:
- supabase: 2.27.1
- supabase-auth: 2.27.1
- postgrest: 2.27.1

Source references:
- supabase._async.client.AsyncClient: venv/lib/python3.14/site-packages/supabase/_async/client.py
- supabase_auth._async.gotrue_client: venv/lib/python3.14/site-packages/supabase_auth/_async/gotrue_client.py
"""

from typing import Optional

from supabase import AsyncClient, create_client
from supabase.lib.client_options import AsyncClientOptions
from supabase_auth import AsyncMemoryStorage

from ..config import VaultConfig


class VaultSupabaseClient:
    """
    Wrapper around Supabase AsyncClient with Vault-specific configuration.

    This class provides:
    1. Configured client with service role key (for admin operations)
    2. Access to auth admin API
    3. Access to database queries for vault_* tables
    4. Proper schema configuration

    Example:
        ```python
        from vault.utils.supabase import VaultSupabaseClient
        from vault.config import VaultConfig

        config = VaultConfig()
        client = await VaultSupabaseClient.create(config)

        # Use admin auth API
        user = await client.auth.admin.create_user(...)

        # Query vault tables
        result = await client.table("vault_users").select("*").execute()
        ```
    """

    def __init__(self, config: VaultConfig, client: AsyncClient) -> None:
        """
        Initialize the Vault Supabase client.

        Args:
            config: Vault configuration
            client: Initialized Supabase AsyncClient

        Note:
            Use VaultSupabaseClient.create() instead of direct instantiation.
        """
        self.config = config
        self._client = client

    @classmethod
    async def create(cls, config: VaultConfig) -> "VaultSupabaseClient":
        """
        Create and initialize a VaultSupabaseClient.

        Wraps: supabase._async.client.AsyncClient.create
        Source: venv/lib/python3.14/site-packages/supabase/_async/client.py

        Args:
            config: Vault configuration with Supabase credentials

        Returns:
            Initialized VaultSupabaseClient

        Example:
            ```python
            config = VaultConfig(
                supabase_url="https://xxx.supabase.co",
                supabase_key="service-role-key"
            )
            client = await VaultSupabaseClient.create(config)
            ```
        """
        # Configure client options
        options = AsyncClientOptions(
            schema=config.db_schema,
            storage=AsyncMemoryStorage(),
            # Use service role key for admin operations
            headers={
                "apikey": config.supabase_key,
                "Authorization": f"Bearer {config.supabase_key}",
            },
        )

        # Create the async client
        # Note: We use create_client instead of AsyncClient.create
        # because create_client is the recommended factory method
        client = create_client(
            supabase_url=config.supabase_url,
            supabase_key=config.supabase_key,
            options=options,
        )

        return cls(config=config, client=client)

    @property
    def auth(self):
        """
        Access Supabase Auth client.

        Provides access to:
        - auth.admin: Admin API (create_user, delete_user, etc.)
        - auth.sign_up, auth.sign_in: User operations
        - auth.get_session, auth.get_user: Session management

        Returns:
            AsyncSupabaseAuthClient

        Example:
            ```python
            # Admin operations
            user = await client.auth.admin.create_user(attributes)

            # User operations
            response = await client.auth.sign_up(credentials)
            ```
        """
        return self._client.auth

    @property
    def db(self):
        """
        Access PostgREST database client.

        Returns:
            AsyncPostgrestClient for database queries

        Example:
            ```python
            # Query vault_users table
            result = await client.db.table("vault_users").select("*").execute()
            ```
        """
        return self._client.postgrest

    def table(self, table_name: str):
        """
        Create a query builder for a specific table.

        Wraps: supabase._async.client.AsyncClient.table
        Source: venv/lib/python3.14/site-packages/supabase/_async/client.py

        Args:
            table_name: Name of the table (e.g., "vault_users")

        Returns:
            AsyncRequestBuilder for chaining queries

        Example:
            ```python
            # Select users
            users = await client.table("vault_users").select("*").execute()

            # Insert user
            result = await client.table("vault_users").insert({
                "email": "user@example.com",
                "display_name": "User"
            }).execute()

            # Update user
            result = await client.table("vault_users").update({
                "display_name": "New Name"
            }).eq("id", user_id).execute()
            ```
        """
        return self._client.table(table_name)

    def schema(self, schema: str):
        """
        Select a database schema.

        Args:
            schema: Schema name (e.g., "public", "vault")

        Returns:
            AsyncPostgrestClient configured for the schema

        Example:
            ```python
            # Query from specific schema
            result = await client.schema("vault").table("users").select("*").execute()
            ```
        """
        return self._client.schema(schema)

    async def close(self) -> None:
        """
        Close the client and cleanup resources.

        Should be called when done using the client.

        Example:
            ```python
            client = await VaultSupabaseClient.create(config)
            try:
                # ... use client
                pass
            finally:
                await client.close()
            ```
        """
        # Supabase client doesn't have explicit close in 2.27.1
        # but we provide this for future-proofing
        pass


async def create_supabase_client(config: VaultConfig) -> VaultSupabaseClient:
    """
    Convenience function to create a VaultSupabaseClient.

    Args:
        config: Vault configuration

    Returns:
        Initialized VaultSupabaseClient

    Example:
        ```python
        from vault.config import load_config
        from vault.utils.supabase import create_supabase_client

        config = load_config()
        client = await create_supabase_client(config)
        ```
    """
    return await VaultSupabaseClient.create(config)
