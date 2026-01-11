"""
Authentication decorators for Vault.

Provides decorators for protecting routes/endpoints with authentication.
"""

import functools
from typing import Any, Callable, Optional

from ..auth.models import VaultUser


def require_auth(func: Optional[Callable] = None, *, vault=None):
    """
    Decorator to require authentication for a route/endpoint.

    This decorator validates the access token and injects the VaultUser
    into the function as a keyword argument.

    Args:
        func: The function to decorate
        vault: Vault client instance (optional, can be passed during decoration)

    Usage with FastAPI:
        ```python
        from fastapi import FastAPI, Header
        from vault.decorators import require_auth

        app = FastAPI()
        vault = await Vault.create()

        @app.get("/protected")
        @require_auth(vault=vault)
        async def protected_route(user: VaultUser, authorization: str = Header(...)):
            return {"message": f"Hello {user.email}"}
        ```

    Usage with framework-agnostic approach:
        ```python
        @require_auth
        async def my_function(token: str, user: VaultUser = None):
            # user is injected by decorator after validation
            print(f"Authenticated as: {user.email}")
        ```

    Note:
        The decorator expects the access token to be available either:
        1. As 'authorization' header (FastAPI, Flask)
        2. As 'token' parameter
        3. Via custom token extraction (override get_token)
    """

    def decorator(f: Callable) -> Callable:
        @functools.wraps(f)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Extract token from arguments
            token = None

            # Check for 'authorization' header (FastAPI style)
            if "authorization" in kwargs:
                auth_header = kwargs["authorization"]
                if auth_header.startswith("Bearer "):
                    token = auth_header[7:]
                else:
                    token = auth_header

            # Check for 'token' parameter
            elif "token" in kwargs:
                token = kwargs["token"]

            # Check for 'access_token' parameter
            elif "access_token" in kwargs:
                token = kwargs["access_token"]

            if not token:
                raise ValueError(
                    "No authentication token provided. "
                    "Pass token via 'authorization' header, 'token', or 'access_token' parameter."
                )

            # Get vault instance
            vault_instance = vault
            if not vault_instance:
                # Try to find vault in kwargs or args
                if "vault" in kwargs:
                    vault_instance = kwargs["vault"]
                elif args and hasattr(args[0], "sessions"):
                    # Might be a class method with self
                    vault_instance = args[0]

            if not vault_instance:
                raise ValueError(
                    "Vault instance not provided. "
                    "Pass vault instance via decorator: @require_auth(vault=vault)"
                )

            # Validate token and get user
            user = await vault_instance.sessions.get_user_from_token(token)

            if not user:
                raise ValueError("Invalid or expired token")

            # Inject user into kwargs
            kwargs["user"] = user

            # Call the original function
            return await f(*args, **kwargs)

        return wrapper

    # Support both @require_auth and @require_auth(vault=vault)
    if func is None:
        return decorator
    else:
        return decorator(func)


class RequireAuth:
    """
    Class-based authentication decorator with Vault instance binding.

    This is useful when you want to create a decorator instance that
    remembers the Vault client.

    Example:
        ```python
        from fastapi import FastAPI, Depends
        from vault import Vault
        from vault.decorators.auth import RequireAuth

        vault = await Vault.create()
        require_auth = RequireAuth(vault)

        @app.get("/protected")
        async def protected(user: VaultUser = Depends(require_auth.dependency)):
            return {"user": user.email}
        ```
    """

    def __init__(self, vault) -> None:
        """
        Initialize the decorator with a Vault instance.

        Args:
            vault: Vault client instance
        """
        self.vault = vault

    def __call__(self, func: Callable) -> Callable:
        """
        Decorate a function with authentication requirement.

        Args:
            func: Function to decorate

        Returns:
            Decorated function
        """
        return require_auth(func, vault=self.vault)

    async def dependency(self, authorization: str) -> VaultUser:
        """
        FastAPI dependency for authentication.

        Usage:
            ```python
            @app.get("/route")
            async def route(user: VaultUser = Depends(require_auth.dependency)):
                return {"user": user.email}
            ```

        Args:
            authorization: Authorization header value

        Returns:
            Authenticated VaultUser

        Raises:
            ValueError: If token is invalid
        """
        token = authorization
        if authorization.startswith("Bearer "):
            token = authorization[7:]

        user = await self.vault.sessions.get_user_from_token(token)

        if not user:
            raise ValueError("Invalid or expired token")

        return user
