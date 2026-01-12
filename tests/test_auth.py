"""
Tests for vault.auth module.
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid4

from vault.auth.models import VaultUser, VaultSession
from vault.auth.users import UserManager
from vault.auth.sessions import SessionManager


class TestUserManager:
    """Tests for UserManager class."""

    @pytest.mark.asyncio
    async def test_create_user(self, vault, sample_user_id):
        """Test creating a user."""
        from tests.conftest import setup_table_mock
        
        # Mock Supabase auth response
        auth_user = Mock()
        auth_user.id = str(uuid4())
        auth_response = Mock()
        auth_response.user = auth_user
        
        vault.client._client.auth.admin.create_user = AsyncMock(return_value=auth_response)
        
        # Mock vault_users table insert
        mock_result = Mock()
        mock_result.data = [{
            "id": str(sample_user_id),
            "email": "test@example.com",
            "email_verified": False,
            "supabase_auth_id": str(auth_user.id),
            "auth_provider": "email",
            "status": "active",
            "display_name": "Test User",
            "avatar_url": None,
            "metadata": {},
            "last_sign_in_at": None,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }]
        
        # Set up the table mock
        setup_table_mock(vault, "vault_users", mock_result)
        
        user = await vault.users.create(
            email="test@example.com",
            password="password123",
            display_name="Test User"
        )
        
        assert user.email == "test@example.com"
        assert user.display_name == "Test User"
        assert str(user.supabase_auth_id) == auth_user.id
        vault.client._client.auth.admin.create_user.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user(self, vault, sample_user_data):
        """Test getting a user by ID."""
        from tests.conftest import setup_table_mock
        
        mock_result = Mock()
        mock_result.data = [sample_user_data]
        setup_table_mock(vault, "vault_users", mock_result)
        
        user = await vault.users.get(UUID(sample_user_data["id"]))
        
        assert user is not None
        assert user.email == sample_user_data["email"]
        assert user.id == UUID(sample_user_data["id"])

    @pytest.mark.asyncio
    async def test_get_user_not_found(self, vault):
        """Test getting a non-existent user."""
        mock_result = Mock()
        mock_result.data = []
        
        query_builder = vault.client.table("vault_users")
        query_builder.select.return_value = query_builder
        query_builder.eq.return_value = query_builder
        query_builder.execute = AsyncMock(return_value=mock_result)
        
        user = await vault.users.get(uuid4())
        
        assert user is None

    @pytest.mark.asyncio
    async def test_get_user_by_email(self, vault, sample_user_data):
        """Test getting a user by email."""
        from tests.conftest import setup_table_mock
        
        mock_result = Mock()
        mock_result.data = [sample_user_data]
        setup_table_mock(vault, "vault_users", mock_result)
        
        user = await vault.users.get_by_email("test@example.com")
        
        assert user is not None
        assert user.email == "test@example.com"

    @pytest.mark.asyncio
    async def test_list_users(self, vault, sample_user_data):
        """Test listing users."""
        from tests.conftest import setup_table_mock
        
        mock_result = Mock()
        mock_result.data = [sample_user_data]
        setup_table_mock(vault, "vault_users", mock_result)
        
        users = await vault.users.list(limit=10, offset=0)
        
        assert len(users) == 1
        assert users[0].email == sample_user_data["email"]

    @pytest.mark.asyncio
    async def test_update_user(self, vault, sample_user_data, sample_user_id):
        """Test updating a user."""
        # Mock get user
        mock_get_result = Mock()
        mock_get_result.data = [sample_user_data]
        
        query_builder = vault.client.table("vault_users")
        query_builder.select.return_value = query_builder
        query_builder.eq.return_value = query_builder
        query_builder.execute = AsyncMock(return_value=mock_get_result)
        
        # Mock update
        updated_data = sample_user_data.copy()
        updated_data["display_name"] = "Updated Name"
        updated_data["updated_at"] = datetime.utcnow().isoformat()
        
        mock_update_result = Mock()
        mock_update_result.data = [updated_data]
        
        query_builder.update.return_value = query_builder
        query_builder.execute = AsyncMock(return_value=mock_update_result)
        
        # Mock auth update
        vault.client.auth.admin.update_user_by_id = AsyncMock()
        
        user = await vault.users.update(
            UUID(sample_user_data["id"]),
            display_name="Updated Name"
        )
        
        assert user.display_name == "Updated Name"

    @pytest.mark.asyncio
    async def test_delete_user_soft(self, vault, sample_user_data):
        """Test soft deleting a user."""
        # Mock get user
        mock_get_result = Mock()
        mock_get_result.data = [sample_user_data]
        
        query_builder = vault.client.table("vault_users")
        query_builder.select.return_value = query_builder
        query_builder.eq.return_value = query_builder
        query_builder.execute = AsyncMock(return_value=mock_get_result)
        
        # Mock update (soft delete)
        vault.users.update = AsyncMock()
        
        await vault.users.delete(UUID(sample_user_data["id"]), soft_delete=True)
        
        vault.users.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_user_hard(self, vault, sample_user_data):
        """Test hard deleting a user."""
        # Mock get user
        mock_get_result = Mock()
        mock_get_result.data = [sample_user_data]

        query_builder = vault.client.table("vault_users")

        # Set up the chaining methods
        query_builder.select.return_value = query_builder
        query_builder.eq.return_value = query_builder
        query_builder.delete.return_value = query_builder

        # Use side_effect to handle multiple execute calls
        mock_get_result_exec = AsyncMock(return_value=mock_get_result)
        mock_delete_result_exec = AsyncMock(return_value=Mock(data=[]))
        query_builder.execute = AsyncMock(side_effect=[mock_get_result_exec.return_value, mock_delete_result_exec.return_value])

        # Mock auth delete
        vault.client.auth.admin.delete_user = AsyncMock()

        await vault.users.delete(UUID(sample_user_data["id"]), soft_delete=False)

        vault.client.auth.admin.delete_user.assert_called_once()

    @pytest.mark.asyncio
    async def test_count_users(self, vault):
        """Test counting users."""
        mock_result = Mock()
        mock_result.count = 5
        
        query_builder = vault.client.table("vault_users")
        query_builder.select.return_value = query_builder
        query_builder.eq.return_value = query_builder
        query_builder.execute = AsyncMock(return_value=mock_result)
        
        count = await vault.users.count()
        
        assert count == 5


class TestSessionManager:
    """Tests for SessionManager class."""

    @pytest.mark.asyncio
    async def test_sign_in_with_password(self, vault, sample_user_data):
        """Test signing in with password."""
        # Mock auth sign in
        auth_user = Mock()
        auth_user.id = sample_user_data["supabase_auth_id"]
        
        auth_session = Mock()
        auth_session.access_token = "access_token"
        auth_session.refresh_token = "refresh_token"
        auth_session.expires_at = 1234567890
        auth_session.expires_in = 3600
        auth_session.token_type = "bearer"
        
        auth_response = Mock()
        auth_response.user = auth_user
        auth_response.session = auth_session
        
        vault.client._client.auth.sign_in_with_password = AsyncMock(return_value=auth_response)
        
        # Mock vault_users table query
        mock_result = Mock()
        mock_result.data = [sample_user_data]
        
        query_builder = vault.client.table("vault_users")
        query_builder.select.return_value = query_builder
        query_builder.eq.return_value = query_builder
        query_builder.execute = AsyncMock(return_value=mock_result)
        query_builder.update.return_value = query_builder
        
        session = await vault.sessions.sign_in_with_password(
            email="test@example.com",
            password="password123"
        )
        
        assert session is not None
        assert session.access_token == "access_token"
        assert session.user.email == "test@example.com"

    @pytest.mark.asyncio
    async def test_get_session(self, vault, sample_user_data):
        """Test getting current session."""
        # Mock auth get_session
        auth_user = Mock()
        auth_user.id = sample_user_data["supabase_auth_id"]
        
        auth_session = Mock()
        auth_session.user = auth_user
        auth_session.access_token = "access_token"
        auth_session.refresh_token = "refresh_token"
        auth_session.expires_at = 1234567890
        auth_session.expires_in = 3600
        auth_session.token_type = "bearer"
        
        vault.client._client.auth.get_session = AsyncMock(return_value=auth_session)
        
        # Mock vault_users table query
        mock_result = Mock()
        mock_result.data = [sample_user_data]
        
        query_builder = vault.client.table("vault_users")
        query_builder.select.return_value = query_builder
        query_builder.eq.return_value = query_builder
        query_builder.execute = AsyncMock(return_value=mock_result)
        
        session = await vault.sessions.get_session()
        
        assert session is not None
        assert session.user.email == sample_user_data["email"]

    @pytest.mark.asyncio
    async def test_get_session_no_session(self, vault):
        """Test getting session when none exists."""
        vault.client._client.auth.get_session = AsyncMock(return_value=None)
        
        session = await vault.sessions.get_session()
        
        assert session is None

    @pytest.mark.asyncio
    async def test_get_user_from_token(self, vault, sample_user_data):
        """Test getting user from token."""
        # Mock auth get_user
        auth_user = Mock()
        auth_user.id = sample_user_data["supabase_auth_id"]
        
        auth_response = Mock()
        auth_response.user = auth_user
        
        vault.client._client.auth.get_user = AsyncMock(return_value=auth_response)
        
        # Mock vault_users table query
        mock_result = Mock()
        mock_result.data = [sample_user_data]
        
        query_builder = vault.client.table("vault_users")
        query_builder.select.return_value = query_builder
        query_builder.eq.return_value = query_builder
        query_builder.execute = AsyncMock(return_value=mock_result)
        
        user = await vault.sessions.get_user_from_token("token")
        
        assert user is not None
        assert user.email == sample_user_data["email"]

    @pytest.mark.asyncio
    async def test_get_user_from_token_invalid(self, vault):
        """Test getting user from invalid token."""
        vault.client._client.auth.get_user = AsyncMock(side_effect=Exception("Invalid token"))
        
        user = await vault.sessions.get_user_from_token("invalid_token")
        
        assert user is None

    @pytest.mark.asyncio
    async def test_sign_out(self, vault):
        """Test signing out."""
        vault.client._client.auth.sign_out = AsyncMock()
        
        await vault.sessions.sign_out("token")
        
        vault.client._client.auth.sign_out.assert_called_once()

    @pytest.mark.asyncio
    async def test_refresh_session(self, vault, sample_user_data):
        """Test refreshing session."""
        # Mock auth refresh
        auth_user = Mock()
        auth_user.id = sample_user_data["supabase_auth_id"]
        
        auth_session = Mock()
        auth_session.access_token = "new_access_token"
        auth_session.refresh_token = "new_refresh_token"
        auth_session.expires_at = 1234567890
        auth_session.expires_in = 3600
        auth_session.token_type = "bearer"
        
        auth_response = Mock()
        auth_response.user = auth_user
        auth_response.session = auth_session
        
        vault.client._client.auth.refresh_session = AsyncMock(return_value=auth_response)
        
        # Mock vault_users table query
        mock_result = Mock()
        mock_result.data = [sample_user_data]
        
        query_builder = vault.client.table("vault_users")
        query_builder.select.return_value = query_builder
        query_builder.eq.return_value = query_builder
        query_builder.execute = AsyncMock(return_value=mock_result)
        
        session = await vault.sessions.refresh_session("refresh_token")
        
        assert session is not None
        assert session.access_token == "new_access_token"

