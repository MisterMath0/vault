"""
Vault - Multi-tenant RBAC library with Supabase integration.

Keep YOUR data in YOUR tables while using Supabase for auth.

Example:
    ```python
    from vault import Vault

    # Initialize Vault
    vault = await Vault.create()

    # User management
    user = await vault.users.create(email="user@example.com", password="secure123")

    # Organization management
    org = await vault.orgs.create(name="Acme Corp", slug="acme-corp")

    # Add user to organization with role
    membership = await vault.memberships.create(user.id, org.id)

    # RBAC - roles and permissions
    role = await vault.roles.create(org.id, "Editor", permissions=["posts:*"])
    can_write = await vault.permissions.check(user.id, org.id, "posts:write")
    ```
"""

from .client import Vault
from .config import VaultConfig, load_config
from .rbac import VaultPermission, VaultRole, check_permission, check_permissions

__version__ = "0.1.0"

__all__ = [
    # Main client
    "Vault",
    "VaultConfig",
    "load_config",
    # RBAC models and utilities
    "VaultRole",
    "VaultPermission",
    "check_permission",
    "check_permissions",
]
