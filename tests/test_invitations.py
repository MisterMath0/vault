"""
Tests for vault.invitations module.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid4

from vault.invitations.invites import InvitationManager


class TestInvitationManager:
    """Tests for InvitationManager class."""

    @pytest.mark.asyncio
    async def test_create_invitation(self, vault, sample_org_id, sample_role_id, sample_org_data):
        """Test creating an invitation."""
        # Mock org get
        mock_org_result = Mock()
        mock_org_result.data = [sample_org_data]
        
        query_builder = vault.client.table("vault_organizations")
        query_builder.select.return_value = query_builder
        query_builder.eq.return_value = query_builder
        query_builder.execute = AsyncMock(return_value=mock_org_result)
        
        # Mock user check (no existing user)
        mock_user_result = Mock()
        mock_user_result.data = []
        
        query_builder = vault.client.table("vault_users")
        query_builder.select.return_value = query_builder
        query_builder.eq.return_value = query_builder
        query_builder.execute = AsyncMock(return_value=mock_user_result)
        
        # Mock invitation insert
        invitation_data = {
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
        
        mock_invite_result = Mock()
        mock_invite_result.data = [invitation_data]
        
        query_builder = vault.client.table("vault_invitations")
        query_builder.select.return_value = query_builder
        query_builder.eq.return_value = query_builder
        query_builder.is_.return_value = query_builder
        query_builder.execute = AsyncMock(return_value=Mock(data=[]))  # No existing invite
        query_builder.insert.return_value = query_builder
        query_builder.execute = AsyncMock(return_value=mock_invite_result)
        
        # Mock email sending
        vault.client._client.auth.admin.invite_user_by_email = AsyncMock()
        
        invite = await vault.invites.create(
            organization_id=sample_org_id,
            email="invited@example.com",
            role_id=sample_role_id
        )
        
        assert invite.email == "invited@example.com"
        assert invite.organization_id == sample_org_id
        assert invite.role_id == sample_role_id

    @pytest.mark.asyncio
    async def test_get_invitation(self, vault, sample_invitation_data):
        """Test getting an invitation by ID."""
        invitation_id = UUID(sample_invitation_data["id"])
        
        mock_result = Mock()
        mock_result.data = [sample_invitation_data]
        
        query_builder = vault.client.table("vault_invitations")
        query_builder.select.return_value = query_builder
        query_builder.eq.return_value = query_builder
        query_builder.execute = AsyncMock(return_value=mock_result)
        
        invite = await vault.invites.get(invitation_id)
        
        assert invite is not None
        assert invite.email == sample_invitation_data["email"]

    @pytest.mark.asyncio
    async def test_get_invitation_by_token(self, vault, sample_invitation_data):
        """Test getting an invitation by token."""
        mock_result = Mock()
        mock_result.data = [sample_invitation_data]
        
        query_builder = vault.client.table("vault_invitations")
        query_builder.select.return_value = query_builder
        query_builder.eq.return_value = query_builder
        query_builder.execute = AsyncMock(return_value=mock_result)
        
        invite = await vault.invites.get_by_token("test-token-123")
        
        assert invite is not None
        assert invite.token == "test-token-123"

    @pytest.mark.asyncio
    async def test_list_invitations_by_organization(self, vault, sample_invitation_data, sample_org_id):
        """Test listing invitations by organization."""
        mock_result = Mock()
        mock_result.data = [sample_invitation_data]
        
        query_builder = vault.client.table("vault_invitations")
        query_builder.select.return_value = query_builder
        query_builder.eq.return_value = query_builder
        query_builder.limit.return_value = query_builder
        query_builder.offset.return_value = query_builder
        query_builder.order.return_value = query_builder
        query_builder.execute = AsyncMock(return_value=mock_result)
        
        invites = await vault.invites.list_by_organization(
            organization_id=sample_org_id,
            limit=10,
            offset=0
        )
        
        assert len(invites) == 1
        assert invites[0].organization_id == sample_org_id

    @pytest.mark.asyncio
    async def test_accept_invitation(self, vault, sample_invitation_data, sample_user_id, sample_user_data):
        """Test accepting an invitation."""
        # Mock get_by_token (first execute call)
        mock_token_result = Mock()
        mock_token_result.data = [sample_invitation_data]

        # Mock user get
        mock_user_result = Mock()
        mock_user_result.data = [sample_user_data]

        # Mock membership check (not a member)
        mock_membership_result = Mock()
        mock_membership_result.data = []

        # Mock invitation update (returns accepted invitation)
        updated_data = sample_invitation_data.copy()
        updated_data["accepted_at"] = datetime.utcnow().isoformat()
        updated_data["accepted_by"] = str(sample_user_id)
        mock_update_result = Mock()
        mock_update_result.data = [updated_data]

        # Set up invitations table mock
        invitations_query = vault.client.table("vault_invitations")
        invitations_query.select.return_value = invitations_query
        invitations_query.eq.return_value = invitations_query
        invitations_query.update.return_value = invitations_query
        invitations_query.execute = AsyncMock(side_effect=[mock_token_result, mock_update_result])

        # Set up users table mock
        users_query = vault.client.table("vault_users")
        users_query.select.return_value = users_query
        users_query.eq.return_value = users_query
        users_query.execute = AsyncMock(return_value=mock_user_result)

        # Set up memberships table mock
        memberships_query = vault.client.table("vault_memberships")
        memberships_query.select.return_value = memberships_query
        memberships_query.eq.return_value = memberships_query
        memberships_query.execute = AsyncMock(return_value=mock_membership_result)

        # Mock membership create
        vault.memberships.create = AsyncMock(return_value=Mock(
            id=uuid4(),
            user_id=sample_user_id,
            organization_id=UUID(sample_invitation_data["organization_id"]),
            role_id=UUID(sample_invitation_data["role_id"]),
            status="active",
            metadata={},
            joined_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        ))

        invite = await vault.invites.accept(
            token="test-token-123",
            user_id=sample_user_id
        )

        assert invite.accepted_at is not None
        assert invite.accepted_by == sample_user_id

    @pytest.mark.asyncio
    async def test_accept_invitation_already_accepted(self, vault, sample_invitation_data):
        """Test accepting an already accepted invitation fails."""
        accepted_data = sample_invitation_data.copy()
        accepted_data["accepted_at"] = datetime.utcnow().isoformat()
        
        mock_result = Mock()
        mock_result.data = [accepted_data]
        
        query_builder = vault.client.table("vault_invitations")
        query_builder.select.return_value = query_builder
        query_builder.eq.return_value = query_builder
        query_builder.execute = AsyncMock(return_value=mock_result)
        
        with pytest.raises(ValueError, match="already been accepted"):
            await vault.invites.accept(
                token="test-token-123",
                user_id=uuid4()
            )

    @pytest.mark.asyncio
    async def test_accept_invitation_expired(self, vault, sample_invitation_data):
        """Test accepting an expired invitation fails."""
        expired_data = sample_invitation_data.copy()
        expired_data["expires_at"] = (datetime.utcnow() - timedelta(days=1)).isoformat()
        
        mock_result = Mock()
        mock_result.data = [expired_data]
        
        query_builder = vault.client.table("vault_invitations")
        query_builder.select.return_value = query_builder
        query_builder.eq.return_value = query_builder
        query_builder.execute = AsyncMock(return_value=mock_result)
        
        with pytest.raises(ValueError, match="expired"):
            await vault.invites.accept(
                token="test-token-123",
                user_id=uuid4()
            )

    @pytest.mark.asyncio
    async def test_revoke_invitation(self, vault, sample_invitation_data):
        """Test revoking an invitation."""
        invitation_id = UUID(sample_invitation_data["id"])

        # Mock get
        mock_get_result = Mock()
        mock_get_result.data = [sample_invitation_data]

        # Mock delete result
        mock_delete_result = Mock()
        mock_delete_result.data = []

        # Set up invitations table mock with side_effect for multiple execute calls
        query_builder = vault.client.table("vault_invitations")
        query_builder.select.return_value = query_builder
        query_builder.eq.return_value = query_builder
        query_builder.delete.return_value = query_builder
        query_builder.execute = AsyncMock(side_effect=[mock_get_result, mock_delete_result])

        await vault.invites.revoke(invitation_id)

        query_builder.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_revoke_accepted_invitation_fails(self, vault, sample_invitation_data):
        """Test revoking an accepted invitation fails."""
        invitation_id = UUID(sample_invitation_data["id"])
        accepted_data = sample_invitation_data.copy()
        accepted_data["accepted_at"] = datetime.utcnow().isoformat()
        
        mock_result = Mock()
        mock_result.data = [accepted_data]
        
        query_builder = vault.client.table("vault_invitations")
        query_builder.select.return_value = query_builder
        query_builder.eq.return_value = query_builder
        query_builder.execute = AsyncMock(return_value=mock_result)
        
        with pytest.raises(ValueError, match="Cannot revoke an accepted invitation"):
            await vault.invites.revoke(invitation_id)

    @pytest.mark.asyncio
    async def test_resend_invitation(self, vault, sample_invitation_data, sample_org_data):
        """Test resending an invitation."""
        invitation_id = UUID(sample_invitation_data["id"])
        
        # Mock get
        mock_get_result = Mock()
        mock_get_result.data = [sample_invitation_data]
        
        query_builder = vault.client.table("vault_invitations")
        query_builder.select.return_value = query_builder
        query_builder.eq.return_value = query_builder
        query_builder.execute = AsyncMock(return_value=mock_get_result)
        
        # Mock org get
        mock_org_result = Mock()
        mock_org_result.data = [sample_org_data]
        
        query_builder = vault.client.table("vault_organizations")
        query_builder.select.return_value = query_builder
        query_builder.eq.return_value = query_builder
        query_builder.execute = AsyncMock(return_value=mock_org_result)
        
        # Mock update
        updated_data = sample_invitation_data.copy()
        updated_data["token"] = "new-token-456"
        updated_data["expires_at"] = (datetime.utcnow() + timedelta(days=7)).isoformat()
        
        mock_update_result = Mock()
        mock_update_result.data = [updated_data]
        
        query_builder = vault.client.table("vault_invitations")
        query_builder.update.return_value = query_builder
        query_builder.eq.return_value = query_builder
        query_builder.execute = AsyncMock(return_value=mock_update_result)
        
        # Mock email sending
        vault.client._client.auth.admin.invite_user_by_email = AsyncMock()
        
        invite = await vault.invites.resend(invitation_id)
        
        assert invite.token == "new-token-456"

    @pytest.mark.asyncio
    async def test_count_invitations(self, vault, sample_org_id):
        """Test counting invitations."""
        mock_result = Mock()
        mock_result.count = 5
        
        query_builder = vault.client.table("vault_invitations")
        query_builder.select.return_value = query_builder
        query_builder.eq.return_value = query_builder
        query_builder.execute = AsyncMock(return_value=mock_result)
        
        count = await vault.invites.count_by_organization(sample_org_id)
        
        assert count == 5

    @pytest.mark.asyncio
    async def test_cleanup_expired_invitations(self, vault):
        """Test cleaning up expired invitations."""
        from tests.conftest import setup_table_mock
        
        # Mock count - first call returns count, second call is delete
        mock_count_result = Mock()
        mock_count_result.count = 3
        
        query_builder = vault.client._client.table("vault_invitations")
        query_builder.execute = AsyncMock(side_effect=[
            mock_count_result,  # Count query
            Mock(data=[{}])  # Delete query
        ])
        
        deleted = await vault.invites.cleanup_expired()
        
        assert deleted == 3

