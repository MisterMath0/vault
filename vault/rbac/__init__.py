"""
Vault RBAC module.

Provides role-based access control with permissions management.
"""

from .models import (
    CreateRoleRequest,
    UpdateRoleRequest,
    VaultPermission,
    VaultRole,
    check_permission,
    check_permissions,
)
from .permissions import PermissionManager
from .roles import RoleManager

__all__ = [
    # Managers
    "RoleManager",
    "PermissionManager",
    # Models
    "VaultRole",
    "VaultPermission",
    "CreateRoleRequest",
    "UpdateRoleRequest",
    # Utility functions
    "check_permission",
    "check_permissions",
]
