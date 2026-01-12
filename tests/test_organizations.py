"""
Tests for vault.organizations module.
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, Mock
from uuid import UUID

from vault.organizations.orgs import OrganizationManager
from vault.organizations.members import MembershipManager


class TestOrganizationManager:
    """Tests for OrganizationManager class."""

    @pytest.mark.asyncio
    async def test_create_organization(self, vault, sample_org_id):
        """Test creating an organization."""
        org_data = {
            "id": str(sample_org_id),
            "name": "Test Org",
            "slug": "test-org",
            "settings": {},
            "metadata": {},
            "status": "active",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
        
        mock_result = Mock()
        mock_result.data = [org_data]
        
        query_builder = vault.client.table("vault_organizations")
        query_builder.insert.return_value = query_builder
        query_builder.execute = AsyncMock(return_value=mock_result)
        
        org = await vault.orgs.create(
            name="Test Org",
            slug="test-org"
        )
        
        assert org.name == "Test Org"
        assert org.slug == "test-org"
        assert org.id == sample_org_id

    @pytest.mark.asyncio
    async def test_get_organization(self, vault, sample_org_data, sample_org_id):
        """Test getting an organization by ID."""
        mock_result = Mock()
        mock_result.data = [sample_org_data]
        
        query_builder = vault.client.table("vault_organizations")
        query_builder.select.return_value = query_builder
        query_builder.eq.return_value = query_builder
        query_builder.execute = AsyncMock(return_value=mock_result)
        
        org = await vault.orgs.get(sample_org_id)
        
        assert org is not None
        assert org.name == sample_org_data["name"]
        assert org.slug == sample_org_data["slug"]

    @pytest.mark.asyncio
    async def test_get_organization_by_slug(self, vault, sample_org_data):
        """Test getting an organization by slug."""
        mock_result = Mock()
        mock_result.data = [sample_org_data]
        
        query_builder = vault.client.table("vault_organizations")
        query_builder.select.return_value = query_builder
        query_builder.eq.return_value = query_builder
        query_builder.execute = AsyncMock(return_value=mock_result)
        
        org = await vault.orgs.get_by_slug("test-org")
        
        assert org is not None
        assert org.slug == "test-org"

    @pytest.mark.asyncio
    async def test_list_organizations(self, vault, sample_org_data):
        """Test listing organizations."""
        mock_result = Mock()
        mock_result.data = [sample_org_data]
        
        query_builder = vault.client.table("vault_organizations")
        query_builder.select.return_value = query_builder
        query_builder.range.return_value = query_builder
        query_builder.order.return_value = query_builder
        query_builder.execute = AsyncMock(return_value=mock_result)
        
        orgs = await vault.orgs.list(limit=10, offset=0)
        
        assert len(orgs) == 1
        assert orgs[0].name == sample_org_data["name"]

    @pytest.mark.asyncio
    async def test_update_organization(self, vault, sample_org_data, sample_org_id):
        """Test updating an organization."""
        # Mock get
        mock_get_result = Mock()
        mock_get_result.data = [sample_org_data]
        
        query_builder = vault.client.table("vault_organizations")
        query_builder.select.return_value = query_builder
        query_builder.eq.return_value = query_builder
        query_builder.execute = AsyncMock(return_value=mock_get_result)
        
        # Mock update
        updated_data = sample_org_data.copy()
        updated_data["name"] = "Updated Name"
        updated_data["updated_at"] = datetime.utcnow().isoformat()
        
        mock_update_result = Mock()
        mock_update_result.data = [updated_data]
        
        query_builder.update.return_value = query_builder
        query_builder.execute = AsyncMock(return_value=mock_update_result)
        
        org = await vault.orgs.update(
            sample_org_id,
            name="Updated Name"
        )
        
        assert org.name == "Updated Name"

    @pytest.mark.asyncio
    async def test_delete_organization_soft(self, vault, sample_org_data, sample_org_id):
        """Test soft deleting an organization."""
        mock_result = Mock()
        mock_result.data = [sample_org_data]
        
        query_builder = vault.client.table("vault_organizations")
        query_builder.update.return_value = query_builder
        query_builder.eq.return_value = query_builder
        query_builder.execute = AsyncMock(return_value=mock_result)
        
        await vault.orgs.delete(sample_org_id, soft_delete=True)
        
        query_builder.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_organization_hard(self, vault, sample_org_data, sample_org_id):
        """Test hard deleting an organization."""
        mock_result = Mock()
        mock_result.data = [sample_org_data]
        
        query_builder = vault.client.table("vault_organizations")
        query_builder.delete.return_value = query_builder
        query_builder.eq.return_value = query_builder
        query_builder.execute = AsyncMock(return_value=mock_result)
        
        await vault.orgs.delete(sample_org_id, soft_delete=False)
        
        query_builder.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_count_organizations(self, vault):
        """Test counting organizations."""
        mock_result = Mock()
        mock_result.count = 3
        
        query_builder = vault.client.table("vault_organizations")
        query_builder.select.return_value = query_builder
        query_builder.eq.return_value = query_builder
        query_builder.execute = AsyncMock(return_value=mock_result)
        
        count = await vault.orgs.count()
        
        assert count == 3


class TestMembershipManager:
    """Tests for MembershipManager class."""

    @pytest.mark.asyncio
    async def test_create_membership(self, vault, sample_membership_data, sample_user_id, sample_org_id, sample_role_id):
        """Test creating a membership."""
        mock_result = Mock()
        mock_result.data = [sample_membership_data]
        
        query_builder = vault.client.table("vault_memberships")
        query_builder.insert.return_value = query_builder
        query_builder.execute = AsyncMock(return_value=mock_result)
        
        membership = await vault.memberships.create(
            user_id=sample_user_id,
            organization_id=sample_org_id,
            role_id=sample_role_id
        )
        
        assert membership.user_id == sample_user_id
        assert membership.organization_id == sample_org_id
        assert membership.role_id == sample_role_id

    @pytest.mark.asyncio
    async def test_get_membership(self, vault, sample_membership_data):
        """Test getting a membership by ID."""
        membership_id = UUID(sample_membership_data["id"])
        
        mock_result = Mock()
        mock_result.data = [sample_membership_data]
        
        query_builder = vault.client.table("vault_memberships")
        query_builder.select.return_value = query_builder
        query_builder.eq.return_value = query_builder
        query_builder.execute = AsyncMock(return_value=mock_result)
        
        membership = await vault.memberships.get(membership_id)
        
        assert membership is not None
        assert membership.id == membership_id

    @pytest.mark.asyncio
    async def test_get_membership_by_user_and_org(self, vault, sample_membership_data, sample_user_id, sample_org_id):
        """Test getting membership by user and org."""
        mock_result = Mock()
        mock_result.data = [sample_membership_data]
        
        query_builder = vault.client.table("vault_memberships")
        query_builder.select.return_value = query_builder
        query_builder.eq.return_value = query_builder
        query_builder.execute = AsyncMock(return_value=mock_result)
        
        membership = await vault.memberships.get_by_user_and_org(
            user_id=sample_user_id,
            organization_id=sample_org_id
        )
        
        assert membership is not None
        assert membership.user_id == sample_user_id
        assert membership.organization_id == sample_org_id

    @pytest.mark.asyncio
    async def test_list_memberships_by_organization(self, vault, sample_membership_data, sample_org_id):
        """Test listing memberships by organization."""
        mock_result = Mock()
        mock_result.data = [sample_membership_data]
        
        query_builder = vault.client.table("vault_memberships")
        query_builder.select.return_value = query_builder
        query_builder.eq.return_value = query_builder
        query_builder.range.return_value = query_builder
        query_builder.order.return_value = query_builder
        query_builder.execute = AsyncMock(return_value=mock_result)
        
        memberships = await vault.memberships.list_by_organization(
            organization_id=sample_org_id,
            limit=10,
            offset=0
        )
        
        assert len(memberships) == 1
        assert memberships[0].organization_id == sample_org_id

    @pytest.mark.asyncio
    async def test_list_memberships_by_user(self, vault, sample_membership_data, sample_user_id):
        """Test listing memberships by user."""
        mock_result = Mock()
        mock_result.data = [sample_membership_data]
        
        query_builder = vault.client.table("vault_memberships")
        query_builder.select.return_value = query_builder
        query_builder.eq.return_value = query_builder
        query_builder.range.return_value = query_builder
        query_builder.order.return_value = query_builder
        query_builder.execute = AsyncMock(return_value=mock_result)
        
        memberships = await vault.memberships.list_by_user(
            user_id=sample_user_id,
            limit=10,
            offset=0
        )
        
        assert len(memberships) == 1
        assert memberships[0].user_id == sample_user_id

    @pytest.mark.asyncio
    async def test_update_membership(self, vault, sample_membership_data, sample_role_id):
        """Test updating a membership."""
        membership_id = UUID(sample_membership_data["id"])
        
        updated_data = sample_membership_data.copy()
        updated_data["role_id"] = str(sample_role_id)
        updated_data["updated_at"] = datetime.utcnow().isoformat()
        
        mock_result = Mock()
        mock_result.data = [updated_data]
        
        query_builder = vault.client.table("vault_memberships")
        query_builder.update.return_value = query_builder
        query_builder.eq.return_value = query_builder
        query_builder.execute = AsyncMock(return_value=mock_result)
        
        membership = await vault.memberships.update(
            membership_id=membership_id,
            role_id=sample_role_id
        )
        
        assert membership.role_id == sample_role_id

    @pytest.mark.asyncio
    async def test_delete_membership(self, vault, sample_membership_data):
        """Test deleting a membership."""
        membership_id = UUID(sample_membership_data["id"])
        
        mock_result = Mock()
        mock_result.data = [sample_membership_data]
        
        query_builder = vault.client.table("vault_memberships")
        query_builder.delete.return_value = query_builder
        query_builder.eq.return_value = query_builder
        query_builder.execute = AsyncMock(return_value=mock_result)
        
        await vault.memberships.delete(membership_id)
        
        query_builder.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_membership_by_user_and_org(self, vault, sample_membership_data, sample_user_id, sample_org_id):
        """Test deleting membership by user and org."""
        mock_result = Mock()
        mock_result.data = [sample_membership_data]
        
        query_builder = vault.client.table("vault_memberships")
        query_builder.delete.return_value = query_builder
        query_builder.eq.return_value = query_builder
        query_builder.execute = AsyncMock(return_value=mock_result)
        
        await vault.memberships.delete_by_user_and_org(
            user_id=sample_user_id,
            organization_id=sample_org_id
        )
        
        query_builder.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_count_memberships(self, vault, sample_org_id):
        """Test counting memberships."""
        mock_result = Mock()
        mock_result.count = 5
        
        query_builder = vault.client.table("vault_memberships")
        query_builder.select.return_value = query_builder
        query_builder.eq.return_value = query_builder
        query_builder.execute = AsyncMock(return_value=mock_result)
        
        count = await vault.memberships.count_by_organization(sample_org_id)
        
        assert count == 5

