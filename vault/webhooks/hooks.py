"""
Webhook management for Vault.

Handles webhook registration, triggering, and delivery tracking.
"""

import asyncio
import hashlib
import hmac
import secrets
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from uuid import UUID, uuid4

import httpx

from .models import (
    VaultWebhook,
    WebhookDelivery,
    WebhookEvent,
    WebhookPayload,
)

if TYPE_CHECKING:
    from ..client import Vault


class WebhookManager:
    """
    Manages webhook operations.

    Handles creating, updating, and triggering webhooks.
    Supports automatic retries and delivery tracking.

    Example:
        ```python
        # Create a webhook
        webhook = await vault.webhooks.create(
            url="https://example.com/hooks",
            events=["user.created", "member.added"],
            organization_id=org.id
        )

        # Trigger webhook for an event
        await vault.webhooks.trigger(
            event=WebhookEvent.USER_CREATED,
            organization_id=org.id,
            data={"user_id": str(user.id), "email": user.email}
        )
        ```
    """

    # Configuration
    DEFAULT_TIMEOUT = 30  # seconds
    MAX_RETRIES = 3
    RETRY_DELAYS = [1, 5, 30]  # seconds
    MAX_FAILURES_BEFORE_DISABLE = 10

    def __init__(self, vault: "Vault") -> None:
        """
        Initialize WebhookManager.

        Args:
            vault: Main Vault client instance
        """
        self.vault = vault
        self.client = vault.client
        self._http_client: Optional[httpx.AsyncClient] = None

    async def _get_http_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client for webhook delivery."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=self.DEFAULT_TIMEOUT)
        return self._http_client

    def _generate_secret(self) -> str:
        """Generate a secure webhook secret."""
        return f"whsec_{secrets.token_urlsafe(32)}"

    def _sign_payload(self, payload: str, secret: str) -> str:
        """
        Generate HMAC-SHA256 signature for webhook payload.

        Args:
            payload: JSON payload string
            secret: Webhook secret

        Returns:
            Hex-encoded signature
        """
        return hmac.new(
            secret.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    async def create(
        self,
        url: str,
        events: List[str | WebhookEvent],
        organization_id: Optional[UUID] = None,
        description: Optional[str] = None,
    ) -> VaultWebhook:
        """
        Create a new webhook.

        Args:
            url: URL to receive webhook events
            events: List of events to subscribe to
            organization_id: Organization to scope webhook to (None for global)
            description: Optional description

        Returns:
            VaultWebhook instance with secret (only returned on creation)

        Example:
            ```python
            webhook = await vault.webhooks.create(
                url="https://example.com/hooks",
                events=[WebhookEvent.USER_CREATED, WebhookEvent.MEMBER_ADDED],
                organization_id=org.id,
                description="User events webhook"
            )
            # Store webhook.secret securely - it won't be returned again
            ```
        """
        # Convert enum values to strings
        event_strings = [
            e.value if isinstance(e, WebhookEvent) else e for e in events
        ]

        # Generate secret
        secret = self._generate_secret()

        now = datetime.utcnow()
        webhook_data = {
            "url": url,
            "secret": secret,
            "events": event_strings,
            "organization_id": str(organization_id) if organization_id else None,
            "description": description,
            "is_active": True,
            "failure_count": 0,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }

        result = await self.client.table("vault_webhooks").insert(
            webhook_data
        ).execute()

        return VaultWebhook(**result.data[0])

    async def get(self, webhook_id: UUID) -> Optional[VaultWebhook]:
        """
        Get a webhook by ID.

        Args:
            webhook_id: Webhook UUID

        Returns:
            VaultWebhook instance or None if not found
        """
        result = await self.client.table("vault_webhooks").select("*").eq(
            "id", str(webhook_id)
        ).execute()

        if not result.data:
            return None

        return VaultWebhook(**result.data[0])

    async def list_by_organization(
        self,
        organization_id: Optional[UUID] = None,
        active_only: bool = True,
        limit: int = 50,
        offset: int = 0,
    ) -> List[VaultWebhook]:
        """
        List webhooks for an organization.

        Args:
            organization_id: Organization UUID (None for global webhooks)
            active_only: Only return active webhooks
            limit: Maximum webhooks to return
            offset: Webhooks to skip

        Returns:
            List of VaultWebhook instances
        """
        query = self.client.table("vault_webhooks").select("*")

        if organization_id:
            query = query.eq("organization_id", str(organization_id))
        else:
            query = query.is_("organization_id", "null")

        if active_only:
            query = query.eq("is_active", True)

        result = await query.limit(limit).offset(offset).order(
            "created_at", desc=True
        ).execute()

        return [VaultWebhook(**wh) for wh in result.data]

    async def update(
        self,
        webhook_id: UUID,
        url: Optional[str] = None,
        events: Optional[List[str | WebhookEvent]] = None,
        description: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> VaultWebhook:
        """
        Update a webhook.

        Args:
            webhook_id: Webhook UUID
            url: New URL (optional)
            events: New event list (optional)
            description: New description (optional)
            is_active: Enable/disable webhook (optional)

        Returns:
            Updated VaultWebhook instance
        """
        updates: Dict[str, Any] = {"updated_at": datetime.utcnow().isoformat()}

        if url is not None:
            updates["url"] = url

        if events is not None:
            updates["events"] = [
                e.value if isinstance(e, WebhookEvent) else e for e in events
            ]

        if description is not None:
            updates["description"] = description

        if is_active is not None:
            updates["is_active"] = is_active
            if is_active:
                # Reset failure count when re-enabling
                updates["failure_count"] = 0

        result = await self.client.table("vault_webhooks").update(updates).eq(
            "id", str(webhook_id)
        ).execute()

        if not result.data:
            raise ValueError(f"Webhook {webhook_id} not found")

        return VaultWebhook(**result.data[0])

    async def delete(self, webhook_id: UUID) -> None:
        """
        Delete a webhook.

        Args:
            webhook_id: Webhook UUID
        """
        await self.client.table("vault_webhooks").delete().eq(
            "id", str(webhook_id)
        ).execute()

    async def regenerate_secret(self, webhook_id: UUID) -> VaultWebhook:
        """
        Regenerate webhook secret.

        Args:
            webhook_id: Webhook UUID

        Returns:
            Updated VaultWebhook with new secret
        """
        new_secret = self._generate_secret()

        result = await self.client.table("vault_webhooks").update({
            "secret": new_secret,
            "updated_at": datetime.utcnow().isoformat(),
        }).eq("id", str(webhook_id)).execute()

        if not result.data:
            raise ValueError(f"Webhook {webhook_id} not found")

        return VaultWebhook(**result.data[0])

    async def trigger(
        self,
        event: WebhookEvent | str,
        organization_id: Optional[UUID] = None,
        data: Optional[Dict[str, Any]] = None,
        sync: bool = False,
    ) -> List[WebhookDelivery]:
        """
        Trigger webhooks for an event.

        Args:
            event: Event type
            organization_id: Organization context
            data: Event data payload
            sync: If True, wait for all deliveries; if False, fire and forget

        Returns:
            List of WebhookDelivery records (empty if sync=False)

        Example:
            ```python
            await vault.webhooks.trigger(
                event=WebhookEvent.USER_CREATED,
                organization_id=org.id,
                data={
                    "user_id": str(user.id),
                    "email": user.email,
                    "display_name": user.display_name
                }
            )
            ```
        """
        event_str = event.value if isinstance(event, WebhookEvent) else event

        # Find matching webhooks
        webhooks = await self._find_matching_webhooks(event_str, organization_id)

        if not webhooks:
            return []

        # Build payload
        payload = WebhookPayload(
            id=str(uuid4()),
            event=event_str,
            timestamp=datetime.utcnow(),
            organization_id=str(organization_id) if organization_id else None,
            data=data or {},
        )

        if sync:
            # Deliver synchronously and collect results
            deliveries = []
            for webhook in webhooks:
                delivery = await self._deliver_webhook(webhook, payload)
                deliveries.append(delivery)
            return deliveries
        else:
            # Fire and forget - schedule deliveries as background tasks
            for webhook in webhooks:
                asyncio.create_task(self._deliver_webhook(webhook, payload))
            return []

    async def _find_matching_webhooks(
        self,
        event: str,
        organization_id: Optional[UUID],
    ) -> List[VaultWebhook]:
        """Find webhooks that match an event."""
        # Get organization-specific webhooks
        org_webhooks = []
        if organization_id:
            result = await self.client.table("vault_webhooks").select("*").eq(
                "organization_id", str(organization_id)
            ).eq("is_active", True).execute()
            org_webhooks = result.data

        # Get global webhooks
        global_result = await self.client.table("vault_webhooks").select("*").is_(
            "organization_id", "null"
        ).eq("is_active", True).execute()

        all_webhooks = org_webhooks + global_result.data

        # Filter by event
        matching = []
        for wh_data in all_webhooks:
            events = wh_data.get("events", [])
            if "*" in events or event in events:
                matching.append(VaultWebhook(**wh_data))

        return matching

    async def _deliver_webhook(
        self,
        webhook: VaultWebhook,
        payload: WebhookPayload,
        attempt: int = 1,
    ) -> WebhookDelivery:
        """Deliver webhook payload with retries."""
        import json

        payload_json = payload.model_dump_json()
        signature = self._sign_payload(payload_json, webhook.secret)

        headers = {
            "Content-Type": "application/json",
            "X-Vault-Signature": f"sha256={signature}",
            "X-Vault-Event": payload.event,
            "X-Vault-Delivery": payload.id,
        }

        delivery_data = {
            "webhook_id": str(webhook.id),
            "event": payload.event,
            "request_url": webhook.url,
            "request_headers": headers,
            "request_body": json.loads(payload_json),
            "attempt_number": attempt,
            "created_at": datetime.utcnow().isoformat(),
        }

        start_time = datetime.utcnow()

        try:
            http_client = await self._get_http_client()
            response = await http_client.post(
                webhook.url,
                content=payload_json,
                headers=headers,
            )

            response_time = int(
                (datetime.utcnow() - start_time).total_seconds() * 1000
            )

            delivery_data.update({
                "response_status": response.status_code,
                "response_body": response.text[:1000] if response.text else None,
                "response_time_ms": response_time,
                "success": 200 <= response.status_code < 300,
            })

            # Update webhook status
            if delivery_data["success"]:
                await self._mark_success(webhook.id)
            else:
                await self._mark_failure(webhook.id)

        except Exception as e:
            delivery_data.update({
                "success": False,
                "error_message": str(e)[:500],
            })
            await self._mark_failure(webhook.id)

            # Retry if not max attempts
            if attempt < self.MAX_RETRIES:
                delay = self.RETRY_DELAYS[min(attempt - 1, len(self.RETRY_DELAYS) - 1)]
                await asyncio.sleep(delay)
                return await self._deliver_webhook(webhook, payload, attempt + 1)

        # Store delivery record
        result = await self.client.table("vault_webhook_deliveries").insert(
            delivery_data
        ).execute()

        return WebhookDelivery(**result.data[0])

    async def _mark_success(self, webhook_id: UUID) -> None:
        """Mark webhook as successfully delivered."""
        await self.client.table("vault_webhooks").update({
            "last_triggered_at": datetime.utcnow().isoformat(),
            "last_success_at": datetime.utcnow().isoformat(),
            "failure_count": 0,
        }).eq("id", str(webhook_id)).execute()

    async def _mark_failure(self, webhook_id: UUID) -> None:
        """Mark webhook delivery as failed, potentially disabling."""
        # Get current failure count
        result = await self.client.table("vault_webhooks").select(
            "failure_count"
        ).eq("id", str(webhook_id)).execute()

        if not result.data:
            return

        failure_count = result.data[0].get("failure_count", 0) + 1

        updates = {
            "last_triggered_at": datetime.utcnow().isoformat(),
            "last_failure_at": datetime.utcnow().isoformat(),
            "failure_count": failure_count,
        }

        # Disable if too many failures
        if failure_count >= self.MAX_FAILURES_BEFORE_DISABLE:
            updates["is_active"] = False

        await self.client.table("vault_webhooks").update(updates).eq(
            "id", str(webhook_id)
        ).execute()

    async def get_deliveries(
        self,
        webhook_id: UUID,
        success: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[WebhookDelivery]:
        """
        Get delivery history for a webhook.

        Args:
            webhook_id: Webhook UUID
            success: Filter by success status
            limit: Maximum deliveries to return
            offset: Deliveries to skip

        Returns:
            List of WebhookDelivery instances
        """
        query = self.client.table("vault_webhook_deliveries").select("*").eq(
            "webhook_id", str(webhook_id)
        )

        if success is not None:
            query = query.eq("success", success)

        result = await query.limit(limit).offset(offset).order(
            "created_at", desc=True
        ).execute()

        return [WebhookDelivery(**d) for d in result.data]

    async def cleanup_old_deliveries(
        self,
        before: datetime,
        webhook_id: Optional[UUID] = None,
    ) -> int:
        """
        Delete old webhook delivery records.

        Args:
            before: Delete deliveries created before this time
            webhook_id: Only delete for this webhook (optional)

        Returns:
            Number of deliveries deleted
        """
        # Count first
        query = self.client.table("vault_webhook_deliveries").select(
            "id", count="exact"
        ).lt("created_at", before.isoformat())

        if webhook_id:
            query = query.eq("webhook_id", str(webhook_id))

        count_result = await query.execute()
        count = count_result.count or 0

        if count > 0:
            delete_query = self.client.table("vault_webhook_deliveries").delete().lt(
                "created_at", before.isoformat()
            )

            if webhook_id:
                delete_query = delete_query.eq("webhook_id", str(webhook_id))

            await delete_query.execute()

        return count

    async def close(self) -> None:
        """Close HTTP client."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
