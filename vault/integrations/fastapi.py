"""
FastAPI integration for Vault.

Provides dependency injection and middleware for FastAPI applications.

Example:
    ```python
    from fastapi import FastAPI, Depends
    from vault.integrations.fastapi import VaultFastAPI, get_current_user

    app = FastAPI()
    vault_integration = VaultFastAPI(app)

    @app.get("/me")
    async def get_me(user = Depends(get_current_user)):
        return {"email": user.email}

    @app.post("/posts")
    async def create_post(
        user = Depends(vault_integration.require_permission("posts:write"))
    ):
        return {"created": True}
    ```
"""

from contextvars import ContextVar
from typing import Callable, List, Optional, Union

try:
    from fastapi import Depends, FastAPI, HTTPException, Request
    from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
except ImportError:
    raise ImportError(
        "FastAPI is required for this integration. "
        "Install it with: pip install fastapi"
    )

from ..auth.models import VaultUser
from ..client import Vault

# Context variable to store Vault instance
_vault_ctx: ContextVar[Optional[Vault]] = ContextVar("vault", default=None)
_user_ctx: ContextVar[Optional[VaultUser]] = ContextVar("current_user", default=None)

# Security scheme
security = HTTPBearer(auto_error=False)


class VaultFastAPI:
    """
    FastAPI integration for Vault.

    Provides:
    - Automatic Vault client lifecycle management
    - Dependency injection for current user
    - Permission and role checking dependencies

    Example:
        ```python
        from fastapi import FastAPI
        from vault.integrations.fastapi import VaultFastAPI

        app = FastAPI()
        vault_integration = VaultFastAPI(app)

        # Or manually without lifespan
        vault_integration = VaultFastAPI()
        await vault_integration.setup()
        # ... later
        await vault_integration.teardown()
        ```
    """

    def __init__(
        self,
        app: Optional[FastAPI] = None,
        supabase_url: Optional[str] = None,
        supabase_key: Optional[str] = None,
    ) -> None:
        """
        Initialize VaultFastAPI integration.

        Args:
            app: FastAPI application (optional, for automatic lifecycle)
            supabase_url: Supabase URL (optional, loads from env)
            supabase_key: Supabase key (optional, loads from env)
        """
        self.supabase_url = supabase_url
        self.supabase_key = supabase_key
        self._vault: Optional[Vault] = None

        if app:
            self._setup_lifespan(app)

    def _setup_lifespan(self, app: FastAPI) -> None:
        """Set up automatic Vault lifecycle with FastAPI."""
        original_startup = app.on_event("startup")
        original_shutdown = app.on_event("shutdown")

        @app.on_event("startup")
        async def startup() -> None:
            await self.setup()

        @app.on_event("shutdown")
        async def shutdown() -> None:
            await self.teardown()

    async def setup(self) -> None:
        """Initialize Vault client."""
        self._vault = await Vault.create(
            supabase_url=self.supabase_url,
            supabase_key=self.supabase_key,
        )
        _vault_ctx.set(self._vault)

    async def teardown(self) -> None:
        """Close Vault client."""
        if self._vault:
            await self._vault.close()
            self._vault = None
            _vault_ctx.set(None)

    @property
    def vault(self) -> Vault:
        """Get the Vault instance."""
        if not self._vault:
            raise RuntimeError("Vault not initialized. Call setup() first.")
        return self._vault

    def require_auth(self) -> Callable:
        """
        Dependency that requires authentication.

        Returns the current user or raises 401.

        Example:
            ```python
            @app.get("/me")
            async def get_me(user = Depends(vault_integration.require_auth())):
                return {"email": user.email}
            ```
        """

        async def dependency(
            request: Request,
            credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
        ) -> VaultUser:
            if not credentials:
                raise HTTPException(
                    status_code=401,
                    detail="Not authenticated",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            token = credentials.credentials
            user = await self.vault.sessions.get_user_from_token(token)

            if not user:
                raise HTTPException(
                    status_code=401,
                    detail="Invalid or expired token",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            _user_ctx.set(user)
            return user

        return dependency

    def require_permission(
        self,
        *permissions: str,
        org_id_param: str = "org_id",
        all_required: bool = True,
    ) -> Callable:
        """
        Dependency that requires specific permission(s).

        Args:
            *permissions: Permission strings (e.g., "posts:write")
            org_id_param: Name of path/query parameter containing org ID
            all_required: If True, all permissions required; if False, any one

        Example:
            ```python
            @app.post("/orgs/{org_id}/posts")
            async def create_post(
                org_id: str,
                user = Depends(vault_integration.require_permission("posts:write"))
            ):
                return {"created": True}
            ```
        """

        async def dependency(
            request: Request,
            user: VaultUser = Depends(self.require_auth()),
        ) -> VaultUser:
            # Get org_id from path or query params
            org_id = request.path_params.get(org_id_param) or request.query_params.get(
                org_id_param
            )

            if not org_id:
                raise HTTPException(
                    status_code=400,
                    detail=f"Missing {org_id_param} parameter",
                )

            from uuid import UUID

            try:
                org_uuid = UUID(org_id)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid {org_id_param} format",
                )

            # Check permissions
            if all_required:
                has_permission = await self.vault.permissions.check_all(
                    user.id, org_uuid, list(permissions)
                )
            else:
                has_permission = await self.vault.permissions.check_any(
                    user.id, org_uuid, list(permissions)
                )

            if not has_permission:
                raise HTTPException(
                    status_code=403,
                    detail="Insufficient permissions",
                )

            return user

        return dependency

    def require_role(
        self,
        *roles: str,
        org_id_param: str = "org_id",
        any_role: bool = True,
    ) -> Callable:
        """
        Dependency that requires specific role(s).

        Args:
            *roles: Role names (e.g., "Admin", "Owner")
            org_id_param: Name of path/query parameter containing org ID
            any_role: If True, any role matches; if False, all required

        Example:
            ```python
            @app.delete("/orgs/{org_id}")
            async def delete_org(
                org_id: str,
                user = Depends(vault_integration.require_role("Owner"))
            ):
                return {"deleted": True}
            ```
        """

        async def dependency(
            request: Request,
            user: VaultUser = Depends(self.require_auth()),
        ) -> VaultUser:
            org_id = request.path_params.get(org_id_param) or request.query_params.get(
                org_id_param
            )

            if not org_id:
                raise HTTPException(
                    status_code=400,
                    detail=f"Missing {org_id_param} parameter",
                )

            from uuid import UUID

            try:
                org_uuid = UUID(org_id)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid {org_id_param} format",
                )

            # Check role
            if any_role:
                has_role = await self.vault.permissions.check_any_role(
                    user.id, org_uuid, list(roles)
                )
            else:
                # Check all roles (user must have all specified roles)
                has_role = True
                for role in roles:
                    if not await self.vault.permissions.check_role(
                        user.id, org_uuid, role
                    ):
                        has_role = False
                        break

            if not has_role:
                raise HTTPException(
                    status_code=403,
                    detail=f"Required role: {', '.join(roles)}",
                )

            return user

        return dependency

    def require_org_member(self, org_id_param: str = "org_id") -> Callable:
        """
        Dependency that requires organization membership.

        Args:
            org_id_param: Name of path/query parameter containing org ID

        Example:
            ```python
            @app.get("/orgs/{org_id}/dashboard")
            async def org_dashboard(
                org_id: str,
                user = Depends(vault_integration.require_org_member())
            ):
                return {"dashboard": "data"}
            ```
        """

        async def dependency(
            request: Request,
            user: VaultUser = Depends(self.require_auth()),
        ) -> VaultUser:
            org_id = request.path_params.get(org_id_param) or request.query_params.get(
                org_id_param
            )

            if not org_id:
                raise HTTPException(
                    status_code=400,
                    detail=f"Missing {org_id_param} parameter",
                )

            from uuid import UUID

            try:
                org_uuid = UUID(org_id)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid {org_id_param} format",
                )

            is_member = await self.vault.permissions.is_member(user.id, org_uuid)

            if not is_member:
                raise HTTPException(
                    status_code=403,
                    detail="Not a member of this organization",
                )

            return user

        return dependency

    def require_api_key(
        self,
        *scopes: str,
        header_name: str = "X-API-Key",
    ) -> Callable:
        """
        Dependency that requires a valid API key.

        Args:
            *scopes: Required scopes for the API key
            header_name: Header containing the API key

        Example:
            ```python
            @app.get("/api/data")
            async def get_data(
                api_key = Depends(vault_integration.require_api_key("data:read"))
            ):
                return {"data": [...]}
            ```
        """
        from ..apikeys.models import VaultAPIKey

        async def dependency(request: Request) -> VaultAPIKey:
            api_key = request.headers.get(header_name)

            if not api_key:
                raise HTTPException(
                    status_code=401,
                    detail="API key required",
                )

            result = await self.vault.api_keys.validate(
                key=api_key,
                required_scopes=list(scopes) if scopes else None,
                endpoint=str(request.url.path),
                method=request.method,
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("User-Agent"),
            )

            if not result.valid:
                if result.rate_limited:
                    raise HTTPException(
                        status_code=429,
                        detail="Rate limit exceeded",
                    )
                raise HTTPException(
                    status_code=401,
                    detail=result.error or "Invalid API key",
                )

            return result.api_key

        return dependency


def get_vault() -> Vault:
    """
    Get the current Vault instance.

    Use as a FastAPI dependency to access Vault in your routes.

    Example:
        ```python
        @app.get("/users")
        async def list_users(vault: Vault = Depends(get_vault)):
            return await vault.users.list()
        ```
    """
    vault = _vault_ctx.get()
    if not vault:
        raise RuntimeError(
            "Vault not available. Make sure VaultFastAPI is initialized."
        )
    return vault


def get_current_user() -> Optional[VaultUser]:
    """
    Get the current authenticated user from context.

    Returns None if no user is authenticated.

    Example:
        ```python
        @app.get("/me")
        async def get_me(user: VaultUser = Depends(get_current_user)):
            if not user:
                raise HTTPException(401)
            return {"email": user.email}
        ```
    """
    return _user_ctx.get()
