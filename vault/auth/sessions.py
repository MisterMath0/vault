"""
Session management for Vault.

Handles user authentication sessions and token validation.

Wraps: supabase_auth._async.gotrue_client.AsyncGoTrueClient
Source: venv/lib/python3.14/site-packages/supabase_auth/_async/gotrue_client.py
"""

from typing import Optional

from supabase_auth.types import SignInWithPasswordCredentials

from .models import VaultSession, VaultUser


class SessionManager:
    """
    Manages authentication sessions.

    Provides methods for signing in, signing out, and validating sessions.
    """

    def __init__(self, vault) -> None:
        """
        Initialize SessionManager.

        Args:
            vault: Main Vault client instance
        """
        self.vault = vault
        self.client = vault.client

    async def sign_in_with_password(
        self, email: str, password: str
    ) -> VaultSession:
        """
        Sign in a user with email and password.

        Wraps: supabase_auth._async.gotrue_client.AsyncGoTrueClient.sign_in_with_password
        Source: venv/lib/python3.14/site-packages/supabase_auth/_async/gotrue_client.py

        Args:
            email: User email address
            password: User password

        Returns:
            VaultSession with access token and user data

        Raises:
            AuthApiError: If credentials are invalid

        Example:
            ```python
            session = await vault.sessions.sign_in_with_password(
                email="user@example.com",
                password="secure123"
            )
            print(f"Logged in as: {session.user.email}")
            print(f"Access token: {session.access_token}")
            ```
        """
        credentials: SignInWithPasswordCredentials = {
            "email": email,
            "password": password,
        }

        # Sign in via Supabase auth
        auth_response = await self.client.auth.sign_in_with_password(credentials)

        # Get vault user by supabase_auth_id
        result = await self.client.table("vault_users").select("*").eq(
            "supabase_auth_id", auth_response.user.id
        ).execute()

        if not result.data:
            raise ValueError(
                f"User with supabase_auth_id {auth_response.user.id} not found in vault_users"
            )

        vault_user = VaultUser(**result.data[0])

        # Update last_sign_in_at
        from datetime import datetime

        await self.client.table("vault_users").update(
            {"last_sign_in_at": datetime.utcnow().isoformat()}
        ).eq("id", str(vault_user.id)).execute()

        # Create VaultSession
        return VaultSession(
            access_token=auth_response.session.access_token,
            refresh_token=auth_response.session.refresh_token,
            expires_at=auth_response.session.expires_at or 0,
            expires_in=auth_response.session.expires_in or 3600,
            token_type=auth_response.session.token_type,
            user=vault_user,
        )

    async def get_session(self) -> Optional[VaultSession]:
        """
        Get the current session if one exists.

        Wraps: supabase_auth._async.gotrue_client.AsyncGoTrueClient.get_session
        Source: venv/lib/python3.14/site-packages/supabase_auth/_async/gotrue_client.py

        Returns:
            VaultSession if session exists, None otherwise

        Example:
            ```python
            session = await vault.sessions.get_session()
            if session:
                print(f"Current user: {session.user.email}")
            else:
                print("Not logged in")
            ```
        """
        auth_session = await self.client.auth.get_session()

        if not auth_session:
            return None

        # Get vault user
        result = await self.client.table("vault_users").select("*").eq(
            "supabase_auth_id", auth_session.user.id
        ).execute()

        if not result.data:
            return None

        vault_user = VaultUser(**result.data[0])

        return VaultSession(
            access_token=auth_session.access_token,
            refresh_token=auth_session.refresh_token,
            expires_at=auth_session.expires_at or 0,
            expires_in=auth_session.expires_in or 3600,
            token_type=auth_session.token_type,
            user=vault_user,
        )

    async def get_user_from_token(self, token: str) -> Optional[VaultUser]:
        """
        Get user from an access token.

        Wraps: supabase_auth._async.gotrue_client.AsyncGoTrueClient.get_user
        Source: venv/lib/python3.14/site-packages/supabase_auth/_async/gotrue_client.py

        Args:
            token: JWT access token

        Returns:
            VaultUser if token is valid, None otherwise

        Example:
            ```python
            user = await vault.sessions.get_user_from_token(access_token)
            if user:
                print(f"Token belongs to: {user.email}")
            ```
        """
        try:
            auth_user_response = await self.client.auth.get_user(token)
            auth_user = auth_user_response.user

            # Get vault user
            result = await self.client.table("vault_users").select("*").eq(
                "supabase_auth_id", auth_user.id
            ).execute()

            if not result.data:
                return None

            return VaultUser(**result.data[0])

        except Exception:
            return None

    async def sign_out(self, token: str) -> None:
        """
        Sign out a user session.

        Wraps: supabase_auth._async.gotrue_client.AsyncGoTrueClient.sign_out
        Source: venv/lib/python3.14/site-packages/supabase_auth/_async/gotrue_client.py

        Args:
            token: Access token to sign out

        Example:
            ```python
            await vault.sessions.sign_out(session.access_token)
            ```
        """
        await self.client.auth.sign_out()

    async def refresh_session(self, refresh_token: str) -> VaultSession:
        """
        Refresh an expired session.

        Wraps: supabase_auth._async.gotrue_client.AsyncGoTrueClient.refresh_session
        Source: venv/lib/python3.14/site-packages/supabase_auth/_async/gotrue_client.py

        Args:
            refresh_token: Refresh token from previous session

        Returns:
            New VaultSession with fresh tokens

        Example:
            ```python
            new_session = await vault.sessions.refresh_session(
                old_session.refresh_token
            )
            ```
        """
        auth_response = await self.client.auth.refresh_session(refresh_token)

        # Get vault user
        result = await self.client.table("vault_users").select("*").eq(
            "supabase_auth_id", auth_response.user.id
        ).execute()

        if not result.data:
            raise ValueError(
                f"User with supabase_auth_id {auth_response.user.id} not found"
            )

        vault_user = VaultUser(**result.data[0])

        return VaultSession(
            access_token=auth_response.session.access_token,
            refresh_token=auth_response.session.refresh_token,
            expires_at=auth_response.session.expires_at or 0,
            expires_in=auth_response.session.expires_in or 3600,
            token_type=auth_response.session.token_type,
            user=vault_user,
        )
