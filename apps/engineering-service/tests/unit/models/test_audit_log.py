"""Unit tests for AuditLog model."""

from datetime import datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.audit_log import AuditLog


class TestAuditLogModel:
    """Test suite for AuditLog model."""

    @pytest.mark.asyncio
    async def test_create_audit_log(self, test_db_session: AsyncSession):
        """Test creating an audit log entry."""
        log = AuditLog(
            user_id="user_123",
            project_id="proj_123",
            action_type="create",
            entity_type="calculation",
            entity_id="calc_456",
            description="Created new beam calculation",
            ip_address="192.168.1.100",
            user_agent="Mozilla/5.0",
            status="success",
        )

        test_db_session.add(log)
        await test_db_session.commit()
        await test_db_session.refresh(log)

        assert log.id is not None
        assert log.user_id == "user_123"
        assert log.action_type == "create"
        assert log.entity_type == "calculation"
        assert log.status == "success"
        assert isinstance(log.timestamp, datetime)

    @pytest.mark.asyncio
    async def test_audit_log_action_types(self, test_db_session: AsyncSession):
        """Test different action types."""
        action_types = ["create", "update", "delete", "validate", "export"]

        for action_type in action_types:
            log = AuditLog(
                user_id="user_123",
                action_type=action_type,
                entity_type="design",
                entity_id="design_789",
                status="success",
            )

            test_db_session.add(log)
            await test_db_session.commit()
            await test_db_session.refresh(log)

            assert log.action_type == action_type
            await test_db_session.rollback()

    @pytest.mark.asyncio
    async def test_audit_log_entity_types(self, test_db_session: AsyncSession):
        """Test different entity types."""
        entity_types = ["calculation", "design", "report", "document"]

        for entity_type in entity_types:
            log = AuditLog(
                user_id="user_123",
                action_type="update",
                entity_type=entity_type,
                entity_id=f"{entity_type}_001",
                status="success",
            )

            test_db_session.add(log)
            await test_db_session.commit()
            await test_db_session.refresh(log)

            assert log.entity_type == entity_type
            await test_db_session.rollback()

    @pytest.mark.asyncio
    async def test_audit_log_with_changes(self, test_db_session: AsyncSession):
        """Test audit log with change tracking."""
        log = AuditLog(
            user_id="user_123",
            project_id="proj_123",
            action_type="update",
            entity_type="calculation",
            entity_id="calc_456",
            changes={
                "before": {
                    "span": 20,
                    "load": 100,
                },
                "after": {
                    "span": 25,
                    "load": 150,
                },
            },
            description="Updated beam span and load",
            status="success",
        )

        test_db_session.add(log)
        await test_db_session.commit()
        await test_db_session.refresh(log)

        assert log.changes is not None
        assert log.changes["before"]["span"] == 20
        assert log.changes["after"]["span"] == 25

    @pytest.mark.asyncio
    async def test_audit_log_failure(self, test_db_session: AsyncSession):
        """Test audit log for failed operations."""
        log = AuditLog(
            user_id="user_123",
            project_id="proj_123",
            action_type="validate",
            entity_type="design",
            entity_id="design_789",
            description="Code compliance validation failed",
            status="failure",
            error_message="Design does not meet IBC requirements",
        )

        test_db_session.add(log)
        await test_db_session.commit()
        await test_db_session.refresh(log)

        assert log.status == "failure"
        assert log.error_message is not None
        assert "IBC" in log.error_message

    @pytest.mark.asyncio
    async def test_audit_log_without_project(self, test_db_session: AsyncSession):
        """Test audit log for non-project actions."""
        log = AuditLog(
            user_id="user_123",
            project_id=None,
            action_type="export",
            entity_type="report",
            entity_id="report_001",
            description="Exported compliance report",
            status="success",
        )

        test_db_session.add(log)
        await test_db_session.commit()
        await test_db_session.refresh(log)

        assert log.project_id is None
        assert log.action_type == "export"

    @pytest.mark.asyncio
    async def test_audit_log_string_representation(self, test_db_session: AsyncSession):
        """Test string representation."""
        log = AuditLog(
            user_id="user_123",
            action_type="create",
            entity_type="calculation",
            entity_id="calc_456",
            status="success",
        )

        test_db_session.add(log)
        await test_db_session.commit()
        await test_db_session.refresh(log)

        str_repr = str(log)
        assert "create" in str_repr
        assert "calculation" in str_repr
        assert "user_123" in str_repr

    @pytest.mark.asyncio
    async def test_audit_log_timestamp_indexing(self, test_db_session: AsyncSession):
        """Test that timestamp is properly indexed for queries."""
        # Create multiple logs
        for i in range(5):
            log = AuditLog(
                user_id=f"user_{i}",
                action_type="create",
                entity_type="calculation",
                entity_id=f"calc_{i}",
                status="success",
            )
            test_db_session.add(log)

        await test_db_session.commit()

        # Query should work efficiently with timestamp index
        from sqlalchemy import select

        result = await test_db_session.execute(
            select(AuditLog).order_by(AuditLog.timestamp.desc()).limit(3)
        )
        logs = result.scalars().all()

        assert len(logs) == 3
        # Verify descending order
        assert logs[0].timestamp >= logs[1].timestamp
        assert logs[1].timestamp >= logs[2].timestamp
