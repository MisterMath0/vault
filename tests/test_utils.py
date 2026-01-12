"""
Tests for vault.utils module.
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch

from vault.utils.supabase import VaultSupabaseClient
from vault.config import VaultConfig


class TestVaultSupabaseClient:
    """Tests for VaultSupabaseClient class."""

    @pytest.mark.asyncio
    async def test_create_client(self, vault_config):
        """Test creating a VaultSupabaseClient."""
        with patch('vault.utils.supabase.create_client') as mock_create:
            mock_client = AsyncMock()
            mock_create.return_value = mock_client
            
            client = await VaultSupabaseClient.create(vault_config)
            
            assert client.config == vault_config
            assert client._client == mock_client
            mock_create.assert_called_once()

    def test_auth_property(self, mock_vault_supabase_client):
        """Test accessing auth property."""
        auth = mock_vault_supabase_client.auth
        assert auth is not None

    def test_table_method(self, mock_vault_supabase_client):
        """Test table method."""
        query_builder = mock_vault_supabase_client.table("vault_users")
        assert query_builder is not None

    def test_schema_method(self, mock_vault_supabase_client):
        """Test schema method."""
        result = mock_vault_supabase_client.schema("vault")
        assert result is not None

    @pytest.mark.asyncio
    async def test_close_client(self, mock_vault_supabase_client):
        """Test closing client."""
        # Should not raise
        await mock_vault_supabase_client.close()

