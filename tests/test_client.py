"""
Tests for vault.client module.
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch

from vault.client import Vault
from vault.config import VaultConfig


class TestVault:
    """Tests for Vault client class."""

    @pytest.mark.asyncio
    async def test_vault_create_with_kwargs(self, mock_vault_supabase_client):
        """Test creating Vault instance with kwargs."""
        config = VaultConfig(
            supabase_url="https://test.supabase.co",
            supabase_key="test-key-12345678901234567890"
        )
        
        with patch('vault.client.VaultSupabaseClient.create', return_value=mock_vault_supabase_client):
            vault = await Vault.create(
                supabase_url="https://test.supabase.co",
                supabase_key="test-key-12345678901234567890"
            )
            
            assert vault.config.supabase_url == "https://test.supabase.co"
            assert vault.config.supabase_key == "test-key-12345678901234567890"
            assert vault.client is not None

    @pytest.mark.asyncio
    async def test_vault_create_auto_migrate(self, mock_vault_supabase_client):
        """Test Vault creation with auto_migrate enabled."""
        with patch('vault.client.VaultSupabaseClient.create', return_value=mock_vault_supabase_client):
            with patch('vault.migrations.manager.MigrationManager') as mock_migration:
                mock_manager = AsyncMock()
                mock_migration.return_value = mock_manager
                
                vault = await Vault.create(
                    supabase_url="https://test.supabase.co",
                    supabase_key="test-key-12345678901234567890",
                    auto_migrate=True
                )
                
                mock_manager.migrate.assert_called_once()

    @pytest.mark.asyncio
    async def test_vault_initialization(self, vault):
        """Test Vault instance initialization."""
        assert vault.config is not None
        assert vault.client is not None
        assert vault.users is not None
        assert vault.sessions is not None
        assert vault.orgs is not None
        assert vault.memberships is not None
        assert vault.roles is not None
        assert vault.permissions is not None
        assert vault.invites is not None
        assert vault.audit is not None
        assert vault.webhooks is not None
        assert vault.api_keys is not None

    @pytest.mark.asyncio
    async def test_vault_context_manager(self, vault):
        """Test Vault as context manager."""
        async with vault as v:
            assert v is vault
            assert v.config is not None

    @pytest.mark.asyncio
    async def test_vault_close(self, vault):
        """Test closing Vault client."""
        vault.webhooks.close = AsyncMock()
        vault.client.close = AsyncMock()
        
        await vault.close()
        
        vault.webhooks.close.assert_called_once()
        vault.client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_vault_context_manager_exit(self, vault):
        """Test context manager exit calls close."""
        vault.close = AsyncMock()
        
        async with vault:
            pass
        
        vault.close.assert_called_once()

