"""
Tests for vault.audit module.
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid4

from vault.audit.logger import AuditLogger
from vault.audit.models import AuditAction, ResourceType


class TestAuditLogger:
    """Tests for AuditLogger class."""

    @pytest.mark.asyncio
    async def test_log_audit_event(self, vault, sample_user_id, sample_org_id):
        """Test logging an audit event."""
        from tests.conftest import setup_table_mock
        
        audit_data = {
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
        
        mock_result = Mock()
        mock_result.data = [audit_data]
        setup_table_mock(vault, "vault_audit_log", mock_result)
        
        entry = await vault.audit.log(
            action=AuditAction.USER_CREATED,
            user_id=sample_user_id,
            organization_id=sample_org_id,
            resource_type=ResourceType.USER,
            resource_id=uuid4(),
            metadata={"email": "test@example.com"},
            ip_address="127.0.0.1",
            user_agent="test-agent"
        )
        
        assert entry.action == "user.created"
        assert entry.user_id == sample_user_id

    @pytest.mark.asyncio
    async def test_log_audit_event_disabled(self, vault):
        """Test logging when audit is disabled."""
        vault.audit.disable()
        
        entry = await vault.audit.log(
            action=AuditAction.USER_CREATED,
            user_id=uuid4()
        )
        
        # Should return dummy entry
        assert entry.id == UUID("00000000-0000-0000-0000-000000000000")
        
        vault.audit.enable()

    @pytest.mark.asyncio
    async def test_log_user_action(self, vault, sample_user_id, sample_org_id):
        """Test logging a user action."""
        from tests.conftest import setup_table_mock
        
        audit_data = {
            "id": str(uuid4()),
            "action": "user.created",
            "user_id": str(sample_user_id),
            "organization_id": str(sample_org_id),
            "resource_type": "user",
            "resource_id": str(sample_user_id),
            "metadata": {},
            "ip_address": None,
            "user_agent": None,
            "created_at": datetime.utcnow().isoformat(),
        }
        
        mock_result = Mock()
        mock_result.data = [audit_data]
        setup_table_mock(vault, "vault_audit_log", mock_result)
        
        entry = await vault.audit.log_user_action(
            action=AuditAction.USER_CREATED,
            user_id=sample_user_id,
            organization_id=sample_org_id
        )
        
        assert entry.action == "user.created"
        assert entry.resource_type == "user"

    @pytest.mark.asyncio
    async def test_log_org_action(self, vault, sample_user_id, sample_org_id):
        """Test logging an organization action."""
        from tests.conftest import setup_table_mock
        
        audit_data = {
            "id": str(uuid4()),
            "action": "org.created",
            "user_id": str(sample_user_id),
            "organization_id": str(sample_org_id),
            "resource_type": "organization",
            "resource_id": str(sample_org_id),
            "metadata": {},
            "ip_address": None,
            "user_agent": None,
            "created_at": datetime.utcnow().isoformat(),
        }
        
        mock_result = Mock()
        mock_result.data = [audit_data]
        setup_table_mock(vault, "vault_audit_log", mock_result)
        
        entry = await vault.audit.log_org_action(
            action=AuditAction.ORG_CREATED,
            user_id=sample_user_id,
            organization_id=sample_org_id
        )
        
        assert entry.action == "org.created"
        assert entry.resource_type == "organization"

    @pytest.mark.asyncio
    async def test_get_audit_entry(self, vault, sample_audit_log_data):
        """Test getting an audit entry by ID."""
        entry_id = UUID(sample_audit_log_data["id"])
        
        mock_result = Mock()
        mock_result.data = [sample_audit_log_data]
        
        query_builder = vault.client.table("vault_audit_log")
        query_builder.select.return_value = query_builder
        query_builder.eq.return_value = query_builder
        query_builder.execute = AsyncMock(return_value=mock_result)
        
        entry = await vault.audit.get(entry_id)
        
        assert entry is not None
        assert entry.action == sample_audit_log_data["action"]

    @pytest.mark.asyncio
    async def test_list_audit_by_organization(self, vault, sample_audit_log_data, sample_org_id):
        """Test listing audit entries by organization."""
        mock_result = Mock()
        mock_result.data = [sample_audit_log_data]
        
        query_builder = vault.client.table("vault_audit_log")
        query_builder.select.return_value = query_builder
        query_builder.eq.return_value = query_builder
        query_builder.limit.return_value = query_builder
        query_builder.offset.return_value = query_builder
        query_builder.order.return_value = query_builder
        query_builder.execute = AsyncMock(return_value=mock_result)
        
        entries = await vault.audit.list_by_organization(
            organization_id=sample_org_id,
            limit=10,
            offset=0
        )
        
        assert len(entries) == 1
        assert entries[0].organization_id == sample_org_id

    @pytest.mark.asyncio
    async def test_list_audit_by_user(self, vault, sample_audit_log_data, sample_user_id):
        """Test listing audit entries by user."""
        mock_result = Mock()
        mock_result.data = [sample_audit_log_data]
        
        query_builder = vault.client.table("vault_audit_log")
        query_builder.select.return_value = query_builder
        query_builder.eq.return_value = query_builder
        query_builder.limit.return_value = query_builder
        query_builder.offset.return_value = query_builder
        query_builder.order.return_value = query_builder
        query_builder.execute = AsyncMock(return_value=mock_result)
        
        entries = await vault.audit.list_by_user(
            user_id=sample_user_id,
            limit=10,
            offset=0
        )
        
        assert len(entries) == 1
        assert entries[0].user_id == sample_user_id

    @pytest.mark.asyncio
    async def test_list_audit_by_resource(self, vault, sample_audit_log_data):
        """Test listing audit entries by resource."""
        resource_id = UUID(sample_audit_log_data["resource_id"])
        
        mock_result = Mock()
        mock_result.data = [sample_audit_log_data]
        
        query_builder = vault.client.table("vault_audit_log")
        query_builder.select.return_value = query_builder
        query_builder.eq.return_value = query_builder
        query_builder.limit.return_value = query_builder
        query_builder.offset.return_value = query_builder
        query_builder.order.return_value = query_builder
        query_builder.execute = AsyncMock(return_value=mock_result)
        
        entries = await vault.audit.list_by_resource(
            resource_type=ResourceType.USER,
            resource_id=resource_id,
            limit=10,
            offset=0
        )
        
        assert len(entries) == 1
        assert entries[0].resource_id == resource_id

    @pytest.mark.asyncio
    async def test_count_audit_by_organization(self, vault, sample_org_id):
        """Test counting audit entries by organization."""
        mock_result = Mock()
        mock_result.count = 10
        
        query_builder = vault.client.table("vault_audit_log")
        query_builder.select.return_value = query_builder
        query_builder.eq.return_value = query_builder
        query_builder.execute = AsyncMock(return_value=mock_result)
        
        count = await vault.audit.count_by_organization(sample_org_id)
        
        assert count == 10

    @pytest.mark.asyncio
    async def test_cleanup_old_entries(self, vault, sample_org_id):
        """Test cleaning up old audit entries."""
        from tests.conftest import setup_table_mock
        
        before = datetime.utcnow()
        
        # Mock count - first call returns count, second call is delete
        mock_count_result = Mock()
        mock_count_result.count = 5
        
        query_builder = vault.client._client.table("vault_audit_log")
        query_builder.execute = AsyncMock(side_effect=[
            mock_count_result,  # Count query
            Mock(data=[{}])  # Delete query
        ])
        
        deleted = await vault.audit.cleanup_old_entries(
            before=before,
            organization_id=sample_org_id
        )
        
        assert deleted == 5

    @pytest.mark.asyncio
    async def test_audit_enable_disable(self, vault):
        """Test enabling and disabling audit logging."""
        assert vault.audit.is_enabled is True
        
        vault.audit.disable()
        assert vault.audit.is_enabled is False
        
        vault.audit.enable()
        assert vault.audit.is_enabled is True

