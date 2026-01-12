"""
Webhooks example demonstrating Vault webhook system.

This example shows how to:
- Register webhooks
- Trigger events
- Verify webhook signatures

Run with:
    python examples/webhooks_example.py
"""

import asyncio
import hashlib
import hmac
import json

from vault import Vault, WebhookEvent


async def main():
    vault = await Vault.create()

    try:
        # =================================================================
        # Setup: Create organization for webhooks
        # =================================================================
        print("Setting up organization...")

        org = await vault.orgs.create(
            name="Webhook Test Org",
            slug="webhook-test-org",
        )
        print(f"  Created org: {org.slug}")

        # =================================================================
        # 1. Create a Webhook
        # =================================================================
        print("\nCreating webhook...")

        webhook = await vault.webhooks.create(
            url="https://webhook.site/your-unique-url",  # Use webhook.site for testing
            events=[
                WebhookEvent.USER_CREATED,
                WebhookEvent.MEMBER_ADDED,
                WebhookEvent.ROLE_ASSIGNED,
            ],
            organization_id=org.id,
            description="Test webhook for user events",
        )

        print(f"  Webhook ID: {webhook.id}")
        print(f"  URL: {webhook.url}")
        print(f"  Events: {webhook.events}")
        print(f"  Secret: {webhook.secret}")
        print("\n  IMPORTANT: Save the secret for signature verification!")

        # =================================================================
        # 2. List Webhooks
        # =================================================================
        print("\nListing webhooks...")

        webhooks = await vault.webhooks.list_by_organization(org.id)
        for wh in webhooks:
            print(f"  - {wh.description or 'No description'} ({wh.url})")

        # =================================================================
        # 3. Trigger a Webhook Manually
        # =================================================================
        print("\nTriggering webhook manually...")

        # This will send HTTP POST to the webhook URL
        deliveries = await vault.webhooks.trigger(
            event=WebhookEvent.USER_CREATED,
            organization_id=org.id,
            data={
                "user_id": "test-user-123",
                "email": "test@example.com",
                "display_name": "Test User",
            },
            sync=True,  # Wait for delivery
        )

        for delivery in deliveries:
            status = "✓" if delivery.success else "✗"
            print(f"  {status} Delivery to {delivery.request_url}")
            print(f"    Status: {delivery.response_status}")
            print(f"    Time: {delivery.response_time_ms}ms")
            if delivery.error_message:
                print(f"    Error: {delivery.error_message}")

        # =================================================================
        # 4. Signature Verification Example
        # =================================================================
        print("\n" + "=" * 60)
        print("SIGNATURE VERIFICATION EXAMPLE")
        print("=" * 60)

        # This is how you'd verify a webhook signature in your receiver
        example_payload = json.dumps(
            {
                "id": "delivery-123",
                "event": "user.created",
                "timestamp": "2024-01-01T00:00:00Z",
                "data": {"user_id": "123", "email": "test@example.com"},
            }
        )

        # Generate signature (this is what Vault sends)
        signature = hmac.new(
            webhook.secret.encode("utf-8"),
            example_payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        print("\nIn your webhook receiver, verify like this:")
        print(
            """
        import hmac
        import hashlib

        def verify_webhook(payload: str, signature: str, secret: str) -> bool:
            expected = hmac.new(
                secret.encode('utf-8'),
                payload.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            return hmac.compare_digest(f'sha256={expected}', signature)

        # In your route handler:
        signature = request.headers.get('X-Vault-Signature')
        if not verify_webhook(request.body, signature, WEBHOOK_SECRET):
            raise HTTPException(401, 'Invalid signature')
        """
        )

        print(f"\nExample signature: sha256={signature}")

        # =================================================================
        # 5. Get Delivery History
        # =================================================================
        print("\nGetting delivery history...")

        history = await vault.webhooks.get_deliveries(webhook.id, limit=10)
        print(f"  Total deliveries: {len(history)}")
        for d in history[:5]:
            print(f"  - {d.event}: {'Success' if d.success else 'Failed'}")

        # =================================================================
        # 6. Update Webhook
        # =================================================================
        print("\nUpdating webhook...")

        updated = await vault.webhooks.update(
            webhook.id,
            events=[WebhookEvent.ALL],  # Subscribe to all events
            description="Updated: All events webhook",
        )
        print(f"  New events: {updated.events}")
        print(f"  New description: {updated.description}")

        # =================================================================
        # 7. Regenerate Secret
        # =================================================================
        print("\nRegenerating webhook secret...")

        regenerated = await vault.webhooks.regenerate_secret(webhook.id)
        print(f"  Old secret: {webhook.secret[:20]}...")
        print(f"  New secret: {regenerated.secret[:20]}...")
        print("  Remember to update your receiver with the new secret!")

        # =================================================================
        # 8. Cleanup
        # =================================================================
        print("\nCleaning up...")

        await vault.webhooks.delete(webhook.id)
        print("  Deleted webhook")

        await vault.orgs.delete(org.id, soft_delete=False)
        print("  Deleted organization")

        print("\nDone!")

    finally:
        await vault.close()


if __name__ == "__main__":
    asyncio.run(main())
