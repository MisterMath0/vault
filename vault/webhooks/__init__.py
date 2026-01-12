"""
Vault webhooks module.

Provides webhook functionality for notifying external services
about events in Vault.
"""

from .hooks import WebhookManager
from .models import (
    VaultWebhook,
    WebhookDelivery,
    WebhookEvent,
)

__all__ = [
    "WebhookManager",
    "VaultWebhook",
    "WebhookDelivery",
    "WebhookEvent",
]
