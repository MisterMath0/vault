"""
Tests for vault.rbac module.
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid4

from vault.rbac.roles import RoleManager
from vault.rbac.permissions import PermissionManager
from vault.rbac.models import check_permission, check_permissions, VaultPermission


class TestRoleManager:
    """Tests for RoleManager class."""

    @pytest.mark.asyncio
    async def test_create_role(self, vault, sample_role_data, sample_org_id):
        """Test creating a role."""
        # Create a custom mock for insert that properly chains
        insert_result = Mock()
        insert_result.data = [sample_role_data]

        query_builder = vault.client.table("vault_roles")
        # Set up insert to return self for chaining, then execute
        query_builder.insert.return_value = query_builder
        query_builder.execute = AsyncMock(return_value=insert_result)

        # Mock _unset_default_role (update path)
        query_builder.update.return_value = query_builder
        query_builder.eq.return_value = query_builder

        role = await vault.roles.create(
            organization_id=sample_org_id,
            name="Editor",
            permissions=["posts:read", "posts:write"]
        )

        assert role.name == "Editor"
        assert "posts:read" in role.permissions
        assert "posts:write" in role.permissions

    @pytest.mark.asyncio
    async def test_create_system_roles(self, vault, sample_org_id):
        """Test creating system roles."""
        system_roles_data = [
            {
                "id": str(uuid4()),
                "organization_id": str(sample_org_id),
                "name": "Owner",
                "description": "Full access",
                "permissions": ["*:*"],
                "is_default": False,
                "is_system": True,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            },
            {
                "id": str(uuid4()),
                "organization_id": str(sample_org_id),
                "name": "Admin",
                "description": "Admin access",
                "permissions": ["admin:*"],
                "is_default": False,
                "is_system": True,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            },
        ]
        
        mock_result = Mock()
        mock_result.data = system_roles_data
        
        query_builder = vault.client.table("vault_roles")
        query_builder.insert.return_value = query_builder
        query_builder.execute = AsyncMock(return_value=mock_result)
        
        roles = await vault.roles.create_system_roles(sample_org_id)
        
        assert len(roles) == 2
        assert any(r.name == "Owner" for r in roles)
        assert any(r.name == "Admin" for r in roles)

    @pytest.mark.asyncio
    async def test_get_role(self, vault, sample_role_data):
        """Test getting a role by ID."""
        role_id = UUID(sample_role_data["id"])
        
        mock_result = Mock()
        mock_result.data = [sample_role_data]
        
        query_builder = vault.client.table("vault_roles")
        query_builder.select.return_value = query_builder
        query_builder.eq.return_value = query_builder
        query_builder.execute = AsyncMock(return_value=mock_result)
        
        role = await vault.roles.get(role_id)
        
        assert role is not None
        assert role.name == sample_role_data["name"]

    @pytest.mark.asyncio
    async def test_get_role_by_name(self, vault, sample_role_data, sample_org_id):
        """Test getting a role by name."""
        mock_result = Mock()
        mock_result.data = [sample_role_data]
        
        query_builder = vault.client.table("vault_roles")
        query_builder.select.return_value = query_builder
        query_builder.eq.return_value = query_builder
        query_builder.execute = AsyncMock(return_value=mock_result)
        
        role = await vault.roles.get_by_name(sample_org_id, "Editor")
        
        assert role is not None
        assert role.name == "Editor"

    @pytest.mark.asyncio
    async def test_get_default_role(self, vault, sample_role_data, sample_org_id):
        """Test getting default role."""
        default_role_data = sample_role_data.copy()
        default_role_data["is_default"] = True
        
        mock_result = Mock()
        mock_result.data = [default_role_data]
        
        query_builder = vault.client.table("vault_roles")
        query_builder.select.return_value = query_builder
        query_builder.eq.return_value = query_builder
        query_builder.execute = AsyncMock(return_value=mock_result)
        
        role = await vault.roles.get_default_role(sample_org_id)
        
        assert role is not None
        assert role.is_default is True

    @pytest.mark.asyncio
    async def test_list_roles_by_organization(self, vault, sample_role_data, sample_org_id):
        """Test listing roles by organization."""
        mock_result = Mock()
        mock_result.data = [sample_role_data]
        
        query_builder = vault.client.table("vault_roles")
        query_builder.select.return_value = query_builder
        query_builder.eq.return_value = query_builder
        query_builder.range.return_value = query_builder
        query_builder.order.return_value = query_builder
        query_builder.execute = AsyncMock(return_value=mock_result)
        
        roles = await vault.roles.list_by_organization(
            organization_id=sample_org_id,
            limit=10,
            offset=0
        )
        
        assert len(roles) == 1
        assert roles[0].organization_id == sample_org_id

    @pytest.mark.asyncio
    async def test_update_role(self, vault, sample_role_data):
        """Test updating a role."""
        role_id = UUID(sample_role_data["id"])
        
        updated_data = sample_role_data.copy()
        updated_data["permissions"] = ["posts:read", "posts:write", "posts:delete"]
        updated_data["updated_at"] = datetime.utcnow().isoformat()
        
        # Mock get
        mock_get_result = Mock()
        mock_get_result.data = [sample_role_data]
        
        query_builder = vault.client.table("vault_roles")
        query_builder.select.return_value = query_builder
        query_builder.eq.return_value = query_builder
        query_builder.execute = AsyncMock(return_value=mock_get_result)
        
        # Mock update
        mock_update_result = Mock()
        mock_update_result.data = [updated_data]
        
        query_builder.update.return_value = query_builder
        query_builder.execute = AsyncMock(return_value=mock_update_result)
        
        role = await vault.roles.update(
            role_id=role_id,
            permissions=["posts:read", "posts:write", "posts:delete"]
        )
        
        assert len(role.permissions) == 3
        assert "posts:delete" in role.permissions

    @pytest.mark.asyncio
    async def test_update_system_role_permissions_fails(self, vault, sample_role_data):
        """Test that updating system role permissions fails."""
        role_id = UUID(sample_role_data["id"])
        system_role_data = sample_role_data.copy()
        system_role_data["is_system"] = True
        
        # Mock get
        mock_get_result = Mock()
        mock_get_result.data = [system_role_data]
        
        query_builder = vault.client.table("vault_roles")
        query_builder.select.return_value = query_builder
        query_builder.eq.return_value = query_builder
        query_builder.execute = AsyncMock(return_value=mock_get_result)
        
        with pytest.raises(ValueError, match="Cannot modify permissions of system roles"):
            await vault.roles.update(
                role_id=role_id,
                permissions=["new:permission"]
            )

    @pytest.mark.asyncio
    async def test_delete_role(self, vault, sample_role_data):
        """Test deleting a role."""
        role_id = UUID(sample_role_data["id"])
        
        # Mock get
        mock_get_result = Mock()
        mock_get_result.data = [sample_role_data]
        
        query_builder = vault.client.table("vault_roles")
        query_builder.select.return_value = query_builder
        query_builder.eq.return_value = query_builder
        query_builder.execute = AsyncMock(return_value=mock_get_result)
        
        # Mock delete
        mock_delete_result = Mock()
        mock_delete_result.data = [sample_role_data]
        
        query_builder.delete.return_value = query_builder
        query_builder.execute = AsyncMock(return_value=mock_delete_result)
        
        await vault.roles.delete(role_id)
        
        query_builder.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_system_role_fails(self, vault, sample_role_data):
        """Test that deleting system role fails."""
        role_id = UUID(sample_role_data["id"])
        system_role_data = sample_role_data.copy()
        system_role_data["is_system"] = True
        
        # Mock get
        mock_get_result = Mock()
        mock_get_result.data = [system_role_data]
        
        query_builder = vault.client.table("vault_roles")
        query_builder.select.return_value = query_builder
        query_builder.eq.return_value = query_builder
        query_builder.execute = AsyncMock(return_value=mock_get_result)
        
        with pytest.raises(ValueError, match="Cannot delete system roles"):
            await vault.roles.delete(role_id)

    @pytest.mark.asyncio
    async def test_add_permissions(self, vault, sample_role_data):
        """Test adding permissions to a role."""
        role_id = UUID(sample_role_data["id"])
        
        # Mock get
        mock_get_result = Mock()
        mock_get_result.data = [sample_role_data]
        
        query_builder = vault.client.table("vault_roles")
        query_builder.select.return_value = query_builder
        query_builder.eq.return_value = query_builder
        query_builder.execute = AsyncMock(return_value=mock_get_result)
        
        # Mock update
        updated_data = sample_role_data.copy()
        updated_data["permissions"] = ["posts:read", "posts:write", "comments:read"]
        updated_data["updated_at"] = datetime.utcnow().isoformat()
        
        mock_update_result = Mock()
        mock_update_result.data = [updated_data]
        
        query_builder.update.return_value = query_builder
        query_builder.execute = AsyncMock(return_value=mock_update_result)
        
        role = await vault.roles.add_permissions(
            role_id=role_id,
            permissions=["comments:read"]
        )
        
        assert "comments:read" in role.permissions

    @pytest.mark.asyncio
    async def test_remove_permissions(self, vault, sample_role_data):
        """Test removing permissions from a role."""
        role_id = UUID(sample_role_data["id"])
        
        # Mock get
        mock_get_result = Mock()
        mock_get_result.data = [sample_role_data]
        
        query_builder = vault.client.table("vault_roles")
        query_builder.select.return_value = query_builder
        query_builder.eq.return_value = query_builder
        query_builder.execute = AsyncMock(return_value=mock_get_result)
        
        # Mock update
        updated_data = sample_role_data.copy()
        updated_data["permissions"] = ["posts:write"]
        updated_data["updated_at"] = datetime.utcnow().isoformat()
        
        mock_update_result = Mock()
        mock_update_result.data = [updated_data]
        
        query_builder.update.return_value = query_builder
        query_builder.execute = AsyncMock(return_value=mock_update_result)
        
        role = await vault.roles.remove_permissions(
            role_id=role_id,
            permissions=["posts:read"]
        )
        
        assert "posts:read" not in role.permissions
        assert "posts:write" in role.permissions

    @pytest.mark.asyncio
    async def test_count_roles(self, vault, sample_org_id):
        """Test counting roles."""
        mock_result = Mock()
        mock_result.count = 3
        
        query_builder = vault.client.table("vault_roles")
        query_builder.select.return_value = query_builder
        query_builder.eq.return_value = query_builder
        query_builder.execute = AsyncMock(return_value=mock_result)
        
        count = await vault.roles.count(sample_org_id)
        
        assert count == 3


class TestPermissionManager:
    """Tests for PermissionManager class."""

    @pytest.mark.asyncio
    async def test_get_user_permissions(self, vault, sample_user_id, sample_org_id, sample_role_id, sample_role_data, sample_membership_data):
        """Test getting user permissions."""
        # Mock membership
        mock_membership_result = Mock()
        mock_membership_result.data = [sample_membership_data]
        
        query_builder = vault.client.table("vault_memberships")
        query_builder.select.return_value = query_builder
        query_builder.eq.return_value = query_builder
        query_builder.execute = AsyncMock(return_value=mock_membership_result)
        
        # Mock role
        mock_role_result = Mock()
        mock_role_result.data = [sample_role_data]
        
        query_builder = vault.client.table("vault_roles")
        query_builder.select.return_value = query_builder
        query_builder.eq.return_value = query_builder
        query_builder.execute = AsyncMock(return_value=mock_role_result)
        
        permissions = await vault.permissions.get_user_permissions(
            user_id=sample_user_id,
            organization_id=sample_org_id
        )
        
        assert len(permissions) == 2
        assert "posts:read" in permissions
        assert "posts:write" in permissions

    @pytest.mark.asyncio
    async def test_check_permission(self, vault, sample_user_id, sample_org_id, sample_role_id, sample_role_data, sample_membership_data):
        """Test checking a permission."""
        # Mock membership
        mock_membership_result = Mock()
        mock_membership_result.data = [sample_membership_data]
        
        query_builder = vault.client.table("vault_memberships")
        query_builder.select.return_value = query_builder
        query_builder.eq.return_value = query_builder
        query_builder.execute = AsyncMock(return_value=mock_membership_result)
        
        # Mock role
        mock_role_result = Mock()
        mock_role_result.data = [sample_role_data]
        
        query_builder = vault.client.table("vault_roles")
        query_builder.select.return_value = query_builder
        query_builder.eq.return_value = query_builder
        query_builder.execute = AsyncMock(return_value=mock_role_result)
        
        has_permission = await vault.permissions.check(
            user_id=sample_user_id,
            organization_id=sample_org_id,
            permission="posts:write"
        )
        
        assert has_permission is True

    @pytest.mark.asyncio
    async def test_check_all_permissions(self, vault, sample_user_id, sample_org_id, sample_role_id, sample_role_data, sample_membership_data):
        """Test checking all permissions."""
        # Mock membership
        mock_membership_result = Mock()
        mock_membership_result.data = [sample_membership_data]
        
        query_builder = vault.client.table("vault_memberships")
        query_builder.select.return_value = query_builder
        query_builder.eq.return_value = query_builder
        query_builder.execute = AsyncMock(return_value=mock_membership_result)
        
        # Mock role
        mock_role_result = Mock()
        mock_role_result.data = [sample_role_data]
        
        query_builder = vault.client.table("vault_roles")
        query_builder.select.return_value = query_builder
        query_builder.eq.return_value = query_builder
        query_builder.execute = AsyncMock(return_value=mock_role_result)
        
        has_all = await vault.permissions.check_all(
            user_id=sample_user_id,
            organization_id=sample_org_id,
            permissions=["posts:read", "posts:write"]
        )
        
        assert has_all is True

    @pytest.mark.asyncio
    async def test_check_any_permission(self, vault, sample_user_id, sample_org_id, sample_role_id, sample_role_data, sample_membership_data):
        """Test checking any permission."""
        # Mock membership
        mock_membership_result = Mock()
        mock_membership_result.data = [sample_membership_data]
        
        query_builder = vault.client.table("vault_memberships")
        query_builder.select.return_value = query_builder
        query_builder.eq.return_value = query_builder
        query_builder.execute = AsyncMock(return_value=mock_membership_result)
        
        # Mock role
        mock_role_result = Mock()
        mock_role_result.data = [sample_role_data]
        
        query_builder = vault.client.table("vault_roles")
        query_builder.select.return_value = query_builder
        query_builder.eq.return_value = query_builder
        query_builder.execute = AsyncMock(return_value=mock_role_result)
        
        has_any = await vault.permissions.check_any(
            user_id=sample_user_id,
            organization_id=sample_org_id,
            permissions=["posts:read", "admin:*"]
        )
        
        assert has_any is True

    @pytest.mark.asyncio
    async def test_check_role(self, vault, sample_user_id, sample_org_id, sample_role_id, sample_role_data, sample_membership_data):
        """Test checking if user has a role."""
        # Mock membership
        mock_membership_result = Mock()
        mock_membership_result.data = [sample_membership_data]
        
        query_builder = vault.client.table("vault_memberships")
        query_builder.select.return_value = query_builder
        query_builder.eq.return_value = query_builder
        query_builder.execute = AsyncMock(return_value=mock_membership_result)
        
        # Mock role
        mock_role_result = Mock()
        mock_role_result.data = [sample_role_data]
        
        query_builder = vault.client.table("vault_roles")
        query_builder.select.return_value = query_builder
        query_builder.eq.return_value = query_builder
        query_builder.execute = AsyncMock(return_value=mock_role_result)
        
        has_role = await vault.permissions.check_role(
            user_id=sample_user_id,
            organization_id=sample_org_id,
            role_name="Editor"
        )
        
        assert has_role is True

    @pytest.mark.asyncio
    async def test_is_member(self, vault, sample_user_id, sample_org_id, sample_membership_data):
        """Test checking if user is a member."""
        mock_result = Mock()
        mock_result.data = [sample_membership_data]
        
        query_builder = vault.client.table("vault_memberships")
        query_builder.select.return_value = query_builder
        query_builder.eq.return_value = query_builder
        query_builder.execute = AsyncMock(return_value=mock_result)
        
        is_member = await vault.permissions.is_member(
            user_id=sample_user_id,
            organization_id=sample_org_id
        )
        
        assert is_member is True


class TestPermissionModels:
    """Tests for permission utility functions."""

    def test_check_permission_exact_match(self):
        """Test permission check with exact match."""
        granted = ["posts:read", "posts:write"]
        assert check_permission(granted, "posts:read") is True
        assert check_permission(granted, "posts:write") is True
        assert check_permission(granted, "posts:delete") is False

    def test_check_permission_wildcard(self):
        """Test permission check with wildcards."""
        granted = ["posts:*"]
        assert check_permission(granted, "posts:read") is True
        assert check_permission(granted, "posts:write") is True
        assert check_permission(granted, "posts:delete") is True
        
        granted = ["*:read"]
        assert check_permission(granted, "posts:read") is True
        assert check_permission(granted, "users:read") is True
        assert check_permission(granted, "posts:write") is False
        
        granted = ["*:*"]
        assert check_permission(granted, "posts:read") is True
        assert check_permission(granted, "anything:anything") is True

    def test_check_permissions_all(self):
        """Test checking all permissions."""
        granted = ["posts:read", "posts:write", "users:read"]
        required = ["posts:read", "posts:write"]
        assert check_permissions(granted, required, require_all=True) is True
        
        required = ["posts:read", "users:delete"]
        assert check_permissions(granted, required, require_all=True) is False

    def test_check_permissions_any(self):
        """Test checking any permission."""
        granted = ["posts:read", "posts:write"]
        required = ["posts:read", "users:delete"]
        assert check_permissions(granted, required, require_all=False) is True
        
        required = ["users:delete", "admin:*"]
        assert check_permissions(granted, required, require_all=False) is False

    def test_vault_permission_from_string(self):
        """Test creating VaultPermission from string."""
        perm = VaultPermission.from_string("posts:read")
        assert perm.resource == "posts"
        assert perm.action == "read"

    def test_vault_permission_to_string(self):
        """Test converting VaultPermission to string."""
        perm = VaultPermission(resource="posts", action="read")
        assert perm.to_string() == "posts:read"

    def test_vault_permission_matches(self):
        """Test permission matching."""
        perm = VaultPermission(resource="posts", action="*")
        required = VaultPermission(resource="posts", action="read")
        assert perm.matches(required) is True
        
        perm = VaultPermission(resource="*", action="read")
        required = VaultPermission(resource="posts", action="read")
        assert perm.matches(required) is True

