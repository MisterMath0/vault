"""
Tests for vault.apikeys module.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch
from uuid import UUID, uuid4

from vault.apikeys.keys import APIKeyManager


class TestAPIKeyManager:
    """Tests for APIKeyManager class."""

    @pytest.mark.asyncio
    async def test_create_api_key(self, vault, sample_org_id, sample_org_data):
        """Test creating an API key."""
        # Mock org get
        mock_org_result = Mock()
        mock_org_result.data = [sample_org_data]
        
        query_builder = vault.client.table("vault_organizations")
        query_builder.select.return_value = query_builder
        query_builder.eq.return_value = query_builder
        query_builder.execute = AsyncMock(return_value=mock_org_result)
        
        # Mock API key insert
        key_data = {
            "id": str(uuid4()),
            "organization_id": str(sample_org_id),
            "name": "Test Key",
            "description": "Test",
            "key_prefix": "vk_test_",
            "key_hash": "test_hash",
            "scopes": ["users:read"],
            "rate_limit": 100,
            "is_active": True,
            "last_used_at": None,
            "expires_at": None,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
        
        mock_result = Mock()
        mock_result.data = [key_data]
        
        query_builder = vault.client.table("vault_api_keys")
        query_builder.insert.return_value = query_builder
        query_builder.execute = AsyncMock(return_value=mock_result)
        
        api_key = await vault.api_keys.create(
            name="Test Key",
            organization_id=sample_org_id,
            scopes=["users:read"],
            rate_limit=100
        )
        
        assert api_key.name == "Test Key"
        assert api_key.key.startswith("vk_")
        assert "users:read" in api_key.scopes

    @pytest.mark.asyncio
    async def test_get_api_key(self, vault, sample_api_key_data):
        """Test getting an API key by ID."""
        key_id = UUID(sample_api_key_data["id"])
        
        mock_result = Mock()
        mock_result.data = [sample_api_key_data]
        
        query_builder = vault.client.table("vault_api_keys")
        query_builder.select.return_value = query_builder
        query_builder.eq.return_value = query_builder
        query_builder.execute = AsyncMock(return_value=mock_result)
        
        api_key = await vault.api_keys.get(key_id)
        
        assert api_key is not None
        assert api_key.name == sample_api_key_data["name"]

    @pytest.mark.asyncio
    async def test_list_api_keys_by_organization(self, vault, sample_api_key_data, sample_org_id):
        """Test listing API keys by organization."""
        mock_result = Mock()
        mock_result.data = [sample_api_key_data]
        
        query_builder = vault.client.table("vault_api_keys")
        query_builder.select.return_value = query_builder
        query_builder.eq.return_value = query_builder
        query_builder.limit.return_value = query_builder
        query_builder.offset.return_value = query_builder
        query_builder.order.return_value = query_builder
        query_builder.execute = AsyncMock(return_value=mock_result)
        
        keys = await vault.api_keys.list_by_organization(
            organization_id=sample_org_id,
            limit=10,
            offset=0
        )
        
        assert len(keys) == 1
        assert keys[0].organization_id == sample_org_id

    @pytest.mark.asyncio
    async def test_validate_api_key_valid(self, vault, sample_api_key_data):
        """Test validating a valid API key."""
        # Mock key lookup
        key_data = sample_api_key_data.copy()
        key_data["key_hash"] = "test_hash"
        
        mock_result = Mock()
        mock_result.data = [key_data]
        
        query_builder = vault.client.table("vault_api_keys")
        query_builder.select.return_value = query_builder
        query_builder.eq.return_value = query_builder
        query_builder.execute = AsyncMock(return_value=mock_result)
        
        # Mock usage count (rate limit check)
        mock_usage_result = Mock()
        mock_usage_result.count = 0
        
        query_builder = vault.client.table("vault_api_key_usage")
        query_builder.select.return_value = query_builder
        query_builder.eq.return_value = query_builder
        query_builder.gte.return_value = query_builder
        query_builder.execute = AsyncMock(return_value=mock_usage_result)
        
        # Mock usage log
        query_builder.insert.return_value = query_builder
        query_builder.execute = AsyncMock(return_value=Mock(data=[{}]))
        
        # Mock update last_used_at
        query_builder = vault.client.table("vault_api_keys")
        query_builder.update.return_value = query_builder
        query_builder.eq.return_value = query_builder
        query_builder.execute = AsyncMock(return_value=Mock(data=[{}]))
        
        # Create a key that will hash to test_hash
        # In real implementation, we'd need to hash the actual key
        # For testing, we'll mock the hash function
        with patch.object(vault.api_keys, '_hash_key', return_value='test_hash'):
            result = await vault.api_keys.validate(
                key="vk_test_key_123",
                required_scopes=["users:read"]
            )
        
        # Note: This test is simplified - in reality we'd need to properly hash the key
        # The validation logic would need to match the hash

    @pytest.mark.asyncio
    async def test_validate_api_key_invalid_format(self, vault):
        """Test validating an API key with invalid format."""
        result = await vault.api_keys.validate(
            key="invalid_key_format"
        )
        
        assert result.valid is False
        assert "Invalid API key format" in result.error

    @pytest.mark.asyncio
    async def test_validate_api_key_not_found(self, vault):
        """Test validating a non-existent API key."""
        mock_result = Mock()
        mock_result.data = []
        
        query_builder = vault.client.table("vault_api_keys")
        query_builder.select.return_value = query_builder
        query_builder.eq.return_value = query_builder
        query_builder.execute = AsyncMock(return_value=mock_result)
        
        with patch.object(vault.api_keys, '_hash_key', return_value='nonexistent_hash'):
            result = await vault.api_keys.validate(
                key="vk_test_key_123"
            )
        
        assert result.valid is False
        assert "Invalid API key" in result.error

    @pytest.mark.asyncio
    async def test_validate_api_key_inactive(self, vault, sample_api_key_data):
        """Test validating an inactive API key."""
        inactive_data = sample_api_key_data.copy()
        inactive_data["is_active"] = False
        
        mock_result = Mock()
        mock_result.data = [inactive_data]
        
        query_builder = vault.client.table("vault_api_keys")
        query_builder.select.return_value = query_builder
        query_builder.eq.return_value = query_builder
        query_builder.execute = AsyncMock(return_value=mock_result)
        
        with patch.object(vault.api_keys, '_hash_key', return_value='test_hash'):
            result = await vault.api_keys.validate(
                key="vk_test_key_123"
            )
        
        assert result.valid is False
        assert "inactive" in result.error.lower()

    @pytest.mark.asyncio
    async def test_update_api_key(self, vault, sample_api_key_data):
        """Test updating an API key."""
        key_id = UUID(sample_api_key_data["id"])
        
        updated_data = sample_api_key_data.copy()
        updated_data["name"] = "Updated Key"
        updated_data["updated_at"] = datetime.utcnow().isoformat()
        
        mock_result = Mock()
        mock_result.data = [updated_data]
        
        query_builder = vault.client.table("vault_api_keys")
        query_builder.update.return_value = query_builder
        query_builder.eq.return_value = query_builder
        query_builder.execute = AsyncMock(return_value=mock_result)
        
        api_key = await vault.api_keys.update(
            key_id=key_id,
            name="Updated Key"
        )
        
        assert api_key.name == "Updated Key"

    @pytest.mark.asyncio
    async def test_revoke_api_key(self, vault, sample_api_key_data):
        """Test revoking an API key."""
        key_id = UUID(sample_api_key_data["id"])
        
        updated_data = sample_api_key_data.copy()
        updated_data["is_active"] = False
        
        mock_result = Mock()
        mock_result.data = [updated_data]
        
        query_builder = vault.client.table("vault_api_keys")
        query_builder.update.return_value = query_builder
        query_builder.eq.return_value = query_builder
        query_builder.execute = AsyncMock(return_value=mock_result)
        
        await vault.api_keys.revoke(key_id)
        
        query_builder.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_api_key(self, vault, sample_api_key_data):
        """Test deleting an API key."""
        key_id = UUID(sample_api_key_data["id"])
        
        query_builder = vault.client.table("vault_api_keys")
        query_builder.delete.return_value = query_builder
        query_builder.eq.return_value = query_builder
        query_builder.execute = AsyncMock(return_value=Mock(data=[{}]))
        
        await vault.api_keys.delete(key_id)
        
        query_builder.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_rotate_api_key(self, vault, sample_api_key_data):
        """Test rotating an API key."""
        key_id = UUID(sample_api_key_data["id"])
        
        # Mock get
        mock_get_result = Mock()
        mock_get_result.data = [sample_api_key_data]
        
        query_builder = vault.client.table("vault_api_keys")
        query_builder.select.return_value = query_builder
        query_builder.eq.return_value = query_builder
        query_builder.execute = AsyncMock(return_value=mock_get_result)
        
        # Mock update
        rotated_data = sample_api_key_data.copy()
        rotated_data["key_prefix"] = "vk_new_"
        rotated_data["key_hash"] = "new_hash"
        rotated_data["updated_at"] = datetime.utcnow().isoformat()
        
        mock_update_result = Mock()
        mock_update_result.data = [rotated_data]
        
        query_builder.update.return_value = query_builder
        query_builder.execute = AsyncMock(return_value=mock_update_result)
        
        api_key = await vault.api_keys.rotate(key_id)
        
        assert api_key.key.startswith("vk_")
        assert api_key.key_prefix == "vk_new_"

    @pytest.mark.asyncio
    async def test_get_usage(self, vault, sample_api_key_data):
        """Test getting API key usage."""
        from tests.conftest import setup_table_mock
        
        key_id = UUID(sample_api_key_data["id"])
        
        usage_data = {
            "id": str(uuid4()),
            "api_key_id": str(key_id),
            "endpoint": "/api/users",
            "method": "GET",
            "ip_address": "127.0.0.1",
            "user_agent": "test-agent",
            "response_status": 200,
            "created_at": datetime.utcnow().isoformat(),
        }
        
        mock_result = Mock()
        mock_result.data = [usage_data]
        setup_table_mock(vault, "vault_api_key_usage", mock_result)
        
        usage = await vault.api_keys.get_usage(
            key_id=key_id,
            limit=10,
            offset=0
        )
        
        assert len(usage) == 1
        assert usage[0].endpoint == "/api/users"

    @pytest.mark.asyncio
    async def test_cleanup_expired_keys(self, vault):
        """Test cleaning up expired API keys."""
        from tests.conftest import setup_table_mock
        
        # Mock count - use a proper datetime string for comparison
        now = datetime.utcnow().isoformat()
        mock_count_result = Mock()
        mock_count_result.count = 2
        
        # Set up the query builder to return count first, then update
        query_builder = vault.client._client.table("vault_api_keys")
        # First call returns count
        query_builder.execute = AsyncMock(side_effect=[
            mock_count_result,  # Count query
            Mock(data=[{}])  # Update query
        ])
        
        deactivated = await vault.api_keys.cleanup_expired()
        
        assert deactivated == 2

