"""
Vault - Multi-tenant RBAC library with Supabase integration.

Keep YOUR data in YOUR tables while using Supabase for auth.

Example:
    ```python
    from vault import Vault

    # Initialize Vault
    vault = await Vault.create()

    # Coming in Phase 2+:
    # user = await vault.users.create(email="user@example.com")
    # org = await vault.orgs.create(name="Acme Corp")
    ```
"""

from .client import Vault
from .config import VaultConfig, load_config

__version__ = "0.1.0"

__all__ = [
    "Vault",
    "VaultConfig",
    "load_config",
]
