"""
Vault decorators module.

Provides decorators for authentication and authorization.
"""

from .auth import RequireAuth, require_auth

__all__ = ["require_auth", "RequireAuth"]
