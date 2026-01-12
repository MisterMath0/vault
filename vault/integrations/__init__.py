"""
Vault framework integrations.

Provides adapters and utilities for popular web frameworks.
"""

# FastAPI adapter is imported conditionally to avoid requiring fastapi
# as a hard dependency

__all__ = []

try:
    from .fastapi import VaultFastAPI, get_current_user, get_vault

    __all__.extend(["VaultFastAPI", "get_current_user", "get_vault"])
except ImportError:
    pass
