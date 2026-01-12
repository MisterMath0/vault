"""
Tests for vault.webhooks module.
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch
from uuid import UUID, uuid4

from vault.webhooks.hooks import WebhookManager
from vault.webhooks.models import WebhookEvent, WebhookPayload


class TestWebhookManager:
    """Tests for WebhookManager class."""

    @pytest.mark.asyncio
    async def test_create_webhook(self, vault, sample_webhook_data, sample_org_id):
        """Test creating a webhook."""
        mock_result = Mock()
        mock_result.data = [sample_webhook_data]
        
        query_builder = vault.client.table("vault_webhooks")
        query_builder.insert.return_value = query_builder
        query_builder.execute = AsyncMock(return_value=mock_result)
        
        webhook = await vault.webhooks.create(
            url="https://example.com/webhook",
            events=["user.created", "member.added"],
            organization_id=sample_org_id
        )
        
        assert webhook.url == "https://example.com/webhook"
        assert len(webhook.events) == 2
        assert webhook.organization_id == sample_org_id

    @pytest.mark.asyncio
    async def test_get_webhook(self, vault, sample_webhook_data):
        """Test getting a webhook by ID."""
        webhook_id = UUID(sample_webhook_data["id"])
        
        mock_result = Mock()
        mock_result.data = [sample_webhook_data]
        
        query_builder = vault.client.table("vault_webhooks")
        query_builder.select.return_value = query_builder
        query_builder.eq.return_value = query_builder
        query_builder.execute = AsyncMock(return_value=mock_result)
        
        webhook = await vault.webhooks.get(webhook_id)
        
        assert webhook is not None
        assert webhook.url == sample_webhook_data["url"]

    @pytest.mark.asyncio
    async def test_list_webhooks_by_organization(self, vault, sample_webhook_data, sample_org_id):
        """Test listing webhooks by organization."""
        mock_result = Mock()
        mock_result.data = [sample_webhook_data]
        
        query_builder = vault.client.table("vault_webhooks")
        query_builder.select.return_value = query_builder
        query_builder.eq.return_value = query_builder
        query_builder.limit.return_value = query_builder
        query_builder.offset.return_value = query_builder
        query_builder.order.return_value = query_builder
        query_builder.execute = AsyncMock(return_value=mock_result)
        
        webhooks = await vault.webhooks.list_by_organization(
            organization_id=sample_org_id,
            limit=10,
            offset=0
        )
        
        assert len(webhooks) == 1
        assert webhooks[0].organization_id == sample_org_id

    @pytest.mark.asyncio
    async def test_update_webhook(self, vault, sample_webhook_data):
        """Test updating a webhook."""
        webhook_id = UUID(sample_webhook_data["id"])
        
        updated_data = sample_webhook_data.copy()
        updated_data["url"] = "https://new-url.com/webhook"
        updated_data["updated_at"] = datetime.utcnow().isoformat()
        
        mock_result = Mock()
        mock_result.data = [updated_data]
        
        query_builder = vault.client.table("vault_webhooks")
        query_builder.update.return_value = query_builder
        query_builder.eq.return_value = query_builder
        query_builder.execute = AsyncMock(return_value=mock_result)
        
        webhook = await vault.webhooks.update(
            webhook_id=webhook_id,
            url="https://new-url.com/webhook"
        )
        
        assert webhook.url == "https://new-url.com/webhook"

    @pytest.mark.asyncio
    async def test_delete_webhook(self, vault, sample_webhook_data):
        """Test deleting a webhook."""
        webhook_id = UUID(sample_webhook_data["id"])
        
        query_builder = vault.client.table("vault_webhooks")
        query_builder.delete.return_value = query_builder
        query_builder.eq.return_value = query_builder
        query_builder.execute = AsyncMock(return_value=Mock(data=[{}]))
        
        await vault.webhooks.delete(webhook_id)
        
        query_builder.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_regenerate_secret(self, vault, sample_webhook_data):
        """Test regenerating webhook secret."""
        webhook_id = UUID(sample_webhook_data["id"])
        
        updated_data = sample_webhook_data.copy()
        updated_data["secret"] = "whsec_new_secret"
        updated_data["updated_at"] = datetime.utcnow().isoformat()
        
        mock_result = Mock()
        mock_result.data = [updated_data]
        
        query_builder = vault.client.table("vault_webhooks")
        query_builder.update.return_value = query_builder
        query_builder.eq.return_value = query_builder
        query_builder.execute = AsyncMock(return_value=mock_result)
        
        webhook = await vault.webhooks.regenerate_secret(webhook_id)
        
        assert webhook.secret == "whsec_new_secret"

    @pytest.mark.asyncio
    async def test_trigger_webhook_sync(self, vault, sample_webhook_data, sample_org_id):
        """Test triggering webhook synchronously."""
        # Mock HTTP client
        mock_http_client = AsyncMock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "OK"
        mock_http_client.post = AsyncMock(return_value=mock_response)

        vault.webhooks._get_http_client = AsyncMock(return_value=mock_http_client)

        # Create delivery data (with ID to match WebhookDelivery model)
        delivery_data = {
            "id": str(uuid4()),
            "webhook_id": sample_webhook_data["id"],
            "event": "user.created",
            "request_url": sample_webhook_data["url"],
            "request_headers": {},
            "request_body": {},
            "response_status": 200,
            "response_body": "OK",
            "response_time_ms": 100,
            "success": True,
            "attempt_number": 1,
            "created_at": datetime.utcnow().isoformat(),
        }

        # Set up mocks for the webhooks table
        # First call: find org webhooks
        # Second call: find global webhooks
        # Third call: mark success
        webhooks_query = vault.client.table("vault_webhooks")
        webhooks_query.select.return_value = webhooks_query
        webhooks_query.eq.return_value = webhooks_query
        webhooks_query.is_.return_value = webhooks_query
        webhooks_query.update.return_value = webhooks_query

        org_webhooks_result = Mock()
        org_webhooks_result.data = [sample_webhook_data]
        global_webhooks_result = Mock()
        global_webhooks_result.data = []
        mark_success_result = Mock()
        mark_success_result.data = []

        webhooks_query.execute = AsyncMock(side_effect=[
            org_webhooks_result,    # _find_matching_webhooks: org webhooks
            global_webhooks_result, # _find_matching_webhooks: global webhooks
            mark_success_result,    # _mark_success update
        ])

        # Set up delivery insert mock
        mock_delivery_result = Mock()
        mock_delivery_result.data = [delivery_data]

        deliveries_query = vault.client.table("vault_webhook_deliveries")
        deliveries_query.insert.return_value = deliveries_query
        deliveries_query.execute = AsyncMock(return_value=mock_delivery_result)

        deliveries = await vault.webhooks.trigger(
            event=WebhookEvent.USER_CREATED,
            organization_id=sample_org_id,
            data={"user_id": str(uuid4())},
            sync=True
        )

        assert len(deliveries) == 1
        assert deliveries[0].success is True

    @pytest.mark.asyncio
    async def test_trigger_webhook_async(self, vault, sample_webhook_data, sample_org_id):
        """Test triggering webhook asynchronously."""
        # Mock finding webhooks
        mock_find_result = Mock()
        mock_find_result.data = [sample_webhook_data]
        
        query_builder = vault.client.table("vault_webhooks")
        query_builder.select.return_value = query_builder
        query_builder.eq.return_value = query_builder
        query_builder.is_.return_value = query_builder
        query_builder.execute = AsyncMock(return_value=mock_find_result)
        
        deliveries = await vault.webhooks.trigger(
            event=WebhookEvent.USER_CREATED,
            organization_id=sample_org_id,
            data={"user_id": str(uuid4())},
            sync=False
        )
        
        # Should return empty list for async
        assert len(deliveries) == 0

    @pytest.mark.asyncio
    async def test_get_deliveries(self, vault, sample_webhook_data):
        """Test getting webhook deliveries."""
        webhook_id = UUID(sample_webhook_data["id"])
        
        delivery_data = {
            "id": str(uuid4()),
            "webhook_id": str(webhook_id),
            "event": "user.created",
            "request_url": sample_webhook_data["url"],
            "request_headers": {},
            "request_body": {},
            "response_status": 200,
            "response_body": "OK",
            "response_time_ms": 100,
            "success": True,
            "attempt_number": 1,
            "created_at":datetime.utcnow().isoformat(), 
        }
        
        mock_result = Mock()
        mock_result.data = [delivery_data]
        
        query_builder = vault.client.table("vault_webhook_deliveries")
        query_builder.select.return_value = query_builder
        query_builder.eq.return_value = query_builder
        query_builder.limit.return_value = query_builder
        query_builder.offset.return_value = query_builder
        query_builder.order.return_value = query_builder
        query_builder.execute = AsyncMock(return_value=mock_result)
        
        deliveries = await vault.webhooks.get_deliveries(
            webhook_id=webhook_id,
            limit=10,
            offset=0
        )
        
        assert len(deliveries) == 1
        assert deliveries[0].success is True

    @pytest.mark.asyncio
    async def test_cleanup_old_deliveries(self, vault, sample_webhook_data):
        """Test cleaning up old deliveries."""
        webhook_id = UUID(sample_webhook_data["id"])
        before = datetime.utcnow()
        
        # Mock count - first call returns count, second call is delete
        mock_count_result = Mock()
        mock_count_result.count = 5
        
        query_builder = vault.client._client.table("vault_webhook_deliveries")
        query_builder.execute = AsyncMock(side_effect=[
            mock_count_result,  # Count query
            Mock(data=[{}])  # Delete query
        ])
        
        deleted = await vault.webhooks.cleanup_old_deliveries(
            before=before,
            webhook_id=webhook_id
        )
        
        assert deleted == 5

    @pytest.mark.asyncio
    async def test_close_webhook_manager(self, vault):
        """Test closing webhook manager."""
        mock_http_client = AsyncMock()
        vault.webhooks._http_client = mock_http_client
        
        await vault.webhooks.close()
        
        mock_http_client.aclose.assert_called_once()
        assert vault.webhooks._http_client is None

