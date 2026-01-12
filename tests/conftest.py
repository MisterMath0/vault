"""
Pytest configuration and fixtures for Vault tests.

Provides mock Supabase client and test fixtures.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, Mock
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from vault.config import VaultConfig
from vault.client import Vault
from vault.utils.supabase import VaultSupabaseClient


@pytest.fixture
def mock_supabase_client():
    """Create a mock Supabase client."""
    client = AsyncMock()
    
    # Mock auth client
    auth_client = AsyncMock()
    auth_admin = AsyncMock()
    auth_client.admin = auth_admin
    client.auth = auth_client
    
    # Store query builders by table name so we can configure them
    query_builders = {}
    
    # Mock table method that returns a query builder
    def table_mock(table_name: str):
        # Return existing query builder if we've seen this table before
        if table_name not in query_builders:
            query_builder = Mock()
            # Make all methods return self for chaining
            query_builder.select = Mock(return_value=query_builder)
            query_builder.insert = Mock(return_value=query_builder)
            query_builder.update = Mock(return_value=query_builder)
            query_builder.delete = Mock(return_value=query_builder)
            query_builder.eq = Mock(return_value=query_builder)
            query_builder.is_ = Mock(return_value=query_builder)
            query_builder.limit = Mock(return_value=query_builder)
            query_builder.offset = Mock(return_value=query_builder)
            query_builder.order = Mock(return_value=query_builder)
            query_builder.range = Mock(return_value=query_builder)
            query_builder.gte = Mock(return_value=query_builder)
            query_builder.lte = Mock(return_value=query_builder)
            query_builder.lt = Mock(return_value=query_builder)
            # Default execute returns empty result
            query_builder.execute = AsyncMock(return_value=Mock(data=[], count=0))
            query_builders[table_name] = query_builder
        return query_builders[table_name]
    
    client.table = Mock(side_effect=table_mock)
    client.schema = Mock(return_value=client)
    client.postgrest = client
    client._query_builders = query_builders  # Expose for test configuration
    
    return client


@pytest.fixture
def mock_vault_supabase_client(mock_supabase_client):
    """Create a mock VaultSupabaseClient."""
    config = VaultConfig(
        supabase_url="https://test.supabase.co",
        supabase_key="test-service-key-12345678901234567890"
    )
    client = VaultSupabaseClient(config=config, client=mock_supabase_client)
    return client


@pytest.fixture
def vault_config():
    """Create a test VaultConfig."""
    return VaultConfig(
        supabase_url="https://test.supabase.co",
        supabase_key="test-service-key-12345678901234567890",
        db_schema="public",
        debug=True,
    )


@pytest.fixture
async def vault(mock_vault_supabase_client, vault_config):
    """Create a test Vault instance."""
    vault_instance = Vault(config=vault_config, client=mock_vault_supabase_client)
    return vault_instance


def setup_table_mock(vault, table_name, execute_return_value):
    """
    Helper function to set up a table mock with a specific execute return value.

    Args:
        vault: Vault instance
        table_name: Name of the table
        execute_return_value: Mock result to return from execute()
    """
    # Get the mock client and access its query builders cache
    mock_client = vault.client._client
    # Call table() to get or create the cached query builder
    query_builder = mock_client.table(table_name)
    # Update the execute method to return our result
    query_builder.execute = AsyncMock(return_value=execute_return_value)
    return query_builder


@pytest.fixture
def sample_user_id():
    """Generate a sample user UUID."""
    return uuid4()


@pytest.fixture
def sample_org_id():
    """Generate a sample organization UUID."""
    return uuid4()


@pytest.fixture
def sample_role_id():
    """Generate a sample role UUID."""
    return uuid4()


@pytest.fixture
def sample_user_data(sample_user_id):
    """Create sample user data."""
    return {
        "id": str(sample_user_id),
        "email": "test@example.com",
        "email_verified": True,
        "phone": None,
        "phone_verified": False,
        "supabase_auth_id": str(uuid4()),
        "auth_provider": "email",
        "display_name": "Test User",
        "avatar_url": None,
        "metadata": {},
        "status": "active",
        "last_sign_in_at": None,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }


@pytest.fixture
def sample_org_data(sample_org_id):
    """Create sample organization data."""
    return {
        "id": str(sample_org_id),
        "name": "Test Organization",
        "slug": "test-org",
        "settings": {},
        "metadata": {},
        "status": "active",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }


@pytest.fixture
def sample_role_data(sample_role_id, sample_org_id):
    """Create sample role data."""
    return {
        "id": str(sample_role_id),
        "organization_id": str(sample_org_id),
        "name": "Editor",
        "description": "Can edit content",
        "permissions": ["posts:read", "posts:write"],
        "is_default": False,
        "is_system": False,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }


@pytest.fixture
def sample_membership_data(sample_user_id, sample_org_id, sample_role_id):
    """Create sample membership data."""
    return {
        "id": str(uuid4()),
        "user_id": str(sample_user_id),
        "organization_id": str(sample_org_id),
        "role_id": str(sample_role_id),
        "status": "active",
        "metadata": {},
        "joined_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }


@pytest.fixture
def sample_invitation_data(sample_org_id, sample_role_id):
    """Create sample invitation data."""
    return {
        "id": str(uuid4()),
        "organization_id": str(sample_org_id),
        "email": "invited@example.com",
        "role_id": str(sample_role_id),
        "invited_by": str(uuid4()),
        "token": "test-token-123",
        "expires_at": (datetime.utcnow() + timedelta(days=7)).isoformat(),
        "accepted_at": None,
        "accepted_by": None,
        "created_at": datetime.utcnow().isoformat(),
    }


@pytest.fixture
def sample_webhook_data(sample_org_id):
    """Create sample webhook data."""
    return {
        "id": str(uuid4()),
        "url": "https://example.com/webhook",
        "secret": "whsec_test_secret",
        "events": ["user.created", "member.added"],
        "organization_id": str(sample_org_id),
        "description": "Test webhook",
        "is_active": True,
        "failure_count": 0,
        "last_triggered_at": None,
        "last_success_at": None,
        "last_failure_at": None,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }


@pytest.fixture
def sample_api_key_data(sample_org_id):
    """Create sample API key data."""
    return {
        "id": str(uuid4()),
        "organization_id": str(sample_org_id),
        "name": "Test API Key",
        "description": "Test key",
        "key_prefix": "vk_test_",
        "key_hash": "test_hash",
        "scopes": ["users:read", "orgs:read"],
        "rate_limit": 100,
        "is_active": True,
        "last_used_at": None,
        "expires_at": None,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }


@pytest.fixture
def sample_audit_log_data(sample_user_id, sample_org_id):
    """Create sample audit log data."""
    return {
        "id": str(uuid4()),
        "action": "user.created",
        "user_id": str(sample_user_id),
        "organization_id": str(sample_org_id),
        "resource_type": "user",
        "resource_id": str(uuid4()),
        "metadata": {"email": "test@example.com"},
        "ip_address": "127.0.0.1",
        "user_agent": "test-agent",
        "created_at": datetime.utcnow().isoformat(),
    }
