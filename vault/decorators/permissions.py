"""
Permission decorators for Vault.

Provides decorators for protecting routes/endpoints with permission checks.
"""

import functools
from typing import Any, Callable, List, Optional, Union
from uuid import UUID

from ..auth.models import VaultUser


def require_permission(
    permission: Union[str, List[str]],
    *,
    vault=None,
    require_all: bool = True,
    org_id_param: str = "organization_id",
):
    """
    Decorator to require specific permission(s) for a route/endpoint.

    This decorator validates that the authenticated user has the required
    permission(s) within the specified organization.

    Args:
        permission: Permission string or list of permissions to check
        vault: Vault client instance
        require_all: If True, all permissions required. If False, any permission is sufficient.
        org_id_param: Name of the parameter containing organization_id

    Usage with FastAPI:
        ```python
        from fastapi import FastAPI, Header
        from vault.decorators import require_auth, require_permission

        app = FastAPI()
        vault = await Vault.create()

        @app.post("/posts")
        @require_auth(vault=vault)
        @require_permission("posts:write", vault=vault)
        async def create_post(
            user: VaultUser,
            organization_id: UUID,
            authorization: str = Header(...)
        ):
            return {"message": "Post created"}

        # Multiple permissions (require all)
        @app.delete("/posts/{post_id}")
        @require_auth(vault=vault)
        @require_permission(["posts:write", "posts:delete"], vault=vault)
        async def delete_post(user: VaultUser, organization_id: UUID, post_id: str):
            return {"deleted": True}

        # Multiple permissions (require any)
        @app.get("/admin")
        @require_auth(vault=vault)
        @require_permission(["admin:*", "owner:*"], vault=vault, require_all=False)
        async def admin_dashboard(user: VaultUser, organization_id: UUID):
            return {"admin": True}
        ```

    Note:
        - Requires @require_auth decorator to be applied first
        - Expects 'user' (VaultUser) and 'organization_id' (UUID) in kwargs
        - The organization_id parameter name can be customized via org_id_param
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Get user from kwargs (should be set by @require_auth)
            user: Optional[VaultUser] = kwargs.get("user")
            if not user:
                raise ValueError(
                    "User not found in request. "
                    "Apply @require_auth decorator before @require_permission."
                )

            # Get organization_id from kwargs
            org_id = kwargs.get(org_id_param)
            if not org_id:
                raise ValueError(
                    f"Organization ID not found. "
                    f"Pass '{org_id_param}' parameter to the function."
                )

            # Convert to UUID if string
            if isinstance(org_id, str):
                org_id = UUID(org_id)

            # Get vault instance
            vault_instance = vault
            if not vault_instance:
                if "vault" in kwargs:
                    vault_instance = kwargs["vault"]
                elif args and hasattr(args[0], "permissions"):
                    vault_instance = args[0]

            if not vault_instance:
                raise ValueError(
                    "Vault instance not provided. "
                    "Pass vault instance via decorator: @require_permission(..., vault=vault)"
                )

            # Check permissions
            permissions_list = [permission] if isinstance(permission, str) else permission

            if require_all:
                has_permission = await vault_instance.permissions.check_all(
                    user_id=user.id,
                    organization_id=org_id,
                    permissions=permissions_list,
                )
            else:
                has_permission = await vault_instance.permissions.check_any(
                    user_id=user.id,
                    organization_id=org_id,
                    permissions=permissions_list,
                )

            if not has_permission:
                perms_str = ", ".join(permissions_list)
                raise PermissionError(
                    f"Permission denied. Required: {perms_str}"
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def require_org_role(
    role: Union[str, List[str]],
    *,
    vault=None,
    org_id_param: str = "organization_id",
):
    """
    Decorator to require a specific role within an organization.

    Args:
        role: Role name or list of role names (any will satisfy)
        vault: Vault client instance
        org_id_param: Name of the parameter containing organization_id

    Usage:
        ```python
        @app.delete("/org/{organization_id}")
        @require_auth(vault=vault)
        @require_org_role("Owner", vault=vault)
        async def delete_org(user: VaultUser, organization_id: UUID):
            return {"deleted": True}

        # Multiple roles (any will work)
        @app.post("/org/{organization_id}/settings")
        @require_auth(vault=vault)
        @require_org_role(["Owner", "Admin"], vault=vault)
        async def update_settings(user: VaultUser, organization_id: UUID):
            return {"updated": True}
        ```
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Get user from kwargs
            user: Optional[VaultUser] = kwargs.get("user")
            if not user:
                raise ValueError(
                    "User not found in request. "
                    "Apply @require_auth decorator before @require_org_role."
                )

            # Get organization_id from kwargs
            org_id = kwargs.get(org_id_param)
            if not org_id:
                raise ValueError(
                    f"Organization ID not found. "
                    f"Pass '{org_id_param}' parameter to the function."
                )

            # Convert to UUID if string
            if isinstance(org_id, str):
                org_id = UUID(org_id)

            # Get vault instance
            vault_instance = vault
            if not vault_instance:
                if "vault" in kwargs:
                    vault_instance = kwargs["vault"]
                elif args and hasattr(args[0], "permissions"):
                    vault_instance = args[0]

            if not vault_instance:
                raise ValueError(
                    "Vault instance not provided. "
                    "Pass vault instance via decorator: @require_org_role(..., vault=vault)"
                )

            # Check role
            roles_list = [role] if isinstance(role, str) else role

            has_role = await vault_instance.permissions.check_any_role(
                user_id=user.id,
                organization_id=org_id,
                role_names=roles_list,
            )

            if not has_role:
                roles_str = " or ".join(roles_list)
                raise PermissionError(
                    f"Role required: {roles_str}"
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def require_org_member(
    *,
    vault=None,
    org_id_param: str = "organization_id",
):
    """
    Decorator to require the user to be a member of the organization.

    Args:
        vault: Vault client instance
        org_id_param: Name of the parameter containing organization_id

    Usage:
        ```python
        @app.get("/org/{organization_id}/dashboard")
        @require_auth(vault=vault)
        @require_org_member(vault=vault)
        async def org_dashboard(user: VaultUser, organization_id: UUID):
            return {"dashboard": "data"}
        ```
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Get user from kwargs
            user: Optional[VaultUser] = kwargs.get("user")
            if not user:
                raise ValueError(
                    "User not found in request. "
                    "Apply @require_auth decorator before @require_org_member."
                )

            # Get organization_id from kwargs
            org_id = kwargs.get(org_id_param)
            if not org_id:
                raise ValueError(
                    f"Organization ID not found. "
                    f"Pass '{org_id_param}' parameter to the function."
                )

            # Convert to UUID if string
            if isinstance(org_id, str):
                org_id = UUID(org_id)

            # Get vault instance
            vault_instance = vault
            if not vault_instance:
                if "vault" in kwargs:
                    vault_instance = kwargs["vault"]
                elif args and hasattr(args[0], "permissions"):
                    vault_instance = args[0]

            if not vault_instance:
                raise ValueError(
                    "Vault instance not provided. "
                    "Pass vault instance via decorator: @require_org_member(vault=vault)"
                )

            # Check membership
            is_member = await vault_instance.permissions.is_member(
                user_id=user.id,
                organization_id=org_id,
            )

            if not is_member:
                raise PermissionError(
                    "You are not a member of this organization."
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


class RequirePermission:
    """
    Class-based permission decorator with Vault instance binding.

    Example:
        ```python
        from fastapi import FastAPI, Depends
        from vault import Vault
        from vault.decorators.permissions import RequirePermission

        vault = await Vault.create()
        require_write = RequirePermission(vault, "posts:write")

        @app.post("/posts")
        async def create_post(
            user: VaultUser = Depends(require_auth.dependency),
            organization_id: UUID = ...,
            _perm=Depends(require_write.dependency)
        ):
            return {"created": True}
        ```
    """

    def __init__(
        self,
        vault,
        permission: Union[str, List[str]],
        require_all: bool = True,
    ) -> None:
        self.vault = vault
        self.permission = permission
        self.require_all = require_all

    def __call__(self, func: Callable) -> Callable:
        return require_permission(
            self.permission,
            vault=self.vault,
            require_all=self.require_all,
        )(func)

    async def check(self, user: VaultUser, organization_id: UUID) -> bool:
        """
        Check if user has the required permission.

        Args:
            user: Authenticated user
            organization_id: Organization UUID

        Returns:
            True if user has permission, False otherwise
        """
        permissions_list = (
            [self.permission] if isinstance(self.permission, str) else self.permission
        )

        if self.require_all:
            return await self.vault.permissions.check_all(
                user_id=user.id,
                organization_id=organization_id,
                permissions=permissions_list,
            )
        else:
            return await self.vault.permissions.check_any(
                user_id=user.id,
                organization_id=organization_id,
                permissions=permissions_list,
            )


class RequireOrgRole:
    """
    Class-based role decorator with Vault instance binding.

    Example:
        ```python
        vault = await Vault.create()
        require_admin = RequireOrgRole(vault, ["Owner", "Admin"])

        @app.delete("/org/{org_id}")
        async def delete_org(
            user: VaultUser = Depends(require_auth.dependency),
            organization_id: UUID = ...,
            _role=Depends(require_admin.check)
        ):
            return {"deleted": True}
        ```
    """

    def __init__(self, vault, role: Union[str, List[str]]) -> None:
        self.vault = vault
        self.role = role

    def __call__(self, func: Callable) -> Callable:
        return require_org_role(self.role, vault=self.vault)(func)

    async def check(self, user: VaultUser, organization_id: UUID) -> bool:
        """
        Check if user has the required role.

        Args:
            user: Authenticated user
            organization_id: Organization UUID

        Returns:
            True if user has role, False otherwise
        """
        roles_list = [self.role] if isinstance(self.role, str) else self.role

        return await self.vault.permissions.check_any_role(
            user_id=user.id,
            organization_id=organization_id,
            role_names=roles_list,
        )
