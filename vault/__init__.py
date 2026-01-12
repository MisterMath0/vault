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

    # Invitations
    invite = await vault.invites.create(org.id, "new@example.com", role_id=role.id)

    # Audit logging
    await vault.audit.log(AuditAction.USER_CREATED, user_id=admin.id)

    # Webhooks
    webhook = await vault.webhooks.create(
        url="https://example.com/hooks",
        events=["user.created"]
    )

    # API Keys
    api_key = await vault.api_keys.create(name="backend", organization_id=org.id)
    ```
"""

from .apikeys import APIKeyManager, VaultAPIKey
from .audit import AuditAction, AuditLogEntry, AuditLogger, ResourceType
from .client import Vault
from .config import VaultConfig, load_config
from .invitations import InvitationManager, VaultInvitation
from .rbac import VaultPermission, VaultRole, check_permission, check_permissions
from .webhooks import VaultWebhook, WebhookEvent, WebhookManager

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
    # Invitations
    "InvitationManager",
    "VaultInvitation",
    # Audit logging
    "AuditLogger",
    "AuditLogEntry",
    "AuditAction",
    "ResourceType",
    # Webhooks
    "WebhookManager",
    "VaultWebhook",
    "WebhookEvent",
    # API Keys
    "APIKeyManager",
    "VaultAPIKey",
]
