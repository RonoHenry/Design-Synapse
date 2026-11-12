"""Unit tests for AuditLogRepository."""

from datetime import datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from src.repositories.audit_log_repository import AuditLogRepository


@pytest.mark.asyncio
class TestAuditLogRepository:
    """Test suite for AuditLogRepository."""

    async def test_get_by_user_id(self, test_db_session: AsyncSession):
        """Test retrieving audit logs by user ID."""
        repo = AuditLogRepository(test_db_session)

        await repo.create(
            {
                "user_id": "user-1",
                "action_type": "create",
                "entity_type": "calculation",
                "entity_id": "calc-1",
            }
        )
        await repo.create(
            {
                "user_id": "user-2",
                "action_type": "update",
                "entity_type": "design",
                "entity_id": "design-1",
            }
        )

        results = await repo.get_by_user_id("user-1")

        assert len(results) >= 1
        assert all(r.user_id == "user-1" for r in results)

    async def test_get_by_project_id(self, test_db_session: AsyncSession):
        """Test retrieving audit logs by project ID."""
        repo = AuditLogRepository(test_db_session)

        await repo.create(
            {
                "user_id": "user-1",
                "project_id": "project-1",
                "action_type": "create",
                "entity_type": "calculation",
                "entity_id": "calc-1",
            }
        )
        await repo.create(
            {
                "user_id": "user-1",
                "project_id": "project-2",
                "action_type": "update",
                "entity_type": "design",
                "entity_id": "design-1",
            }
        )

        results = await repo.get_by_project_id("project-1")

        assert len(results) >= 1
        assert all(r.project_id == "project-1" for r in results)

    async def test_get_by_action_type(self, test_db_session: AsyncSession):
        """Test retrieving logs by action type."""
        repo = AuditLogRepository(test_db_session)

        await repo.create(
            {
                "user_id": "user-1",
                "action_type": "create",
                "entity_type": "calculation",
                "entity_id": "calc-1",
            }
        )
        await repo.create(
            {
                "user_id": "user-1",
                "action_type": "update",
                "entity_type": "design",
                "entity_id": "design-1",
            }
        )

        results = await repo.get_by_action_type("create")

        assert len(results) >= 1
        assert all(r.action_type == "create" for r in results)

    async def test_get_by_entity_type(self, test_db_session: AsyncSession):
        """Test retrieving logs by entity type."""
        repo = AuditLogRepository(test_db_session)

        await repo.create(
            {
                "user_id": "user-1",
                "action_type": "create",
                "entity_type": "calculation",
                "entity_id": "calc-1",
            }
        )
        await repo.create(
            {
                "user_id": "user-1",
                "action_type": "create",
                "entity_type": "design",
                "entity_id": "design-1",
            }
        )

        results = await repo.get_by_entity_type("calculation")

        assert len(results) >= 1
        assert all(r.entity_type == "calculation" for r in results)

    async def test_get_by_entity(self, test_db_session: AsyncSession):
        """Test retrieving logs for a specific entity."""
        repo = AuditLogRepository(test_db_session)

        await repo.create(
            {
                "user_id": "user-1",
                "action_type": "create",
                "entity_type": "calculation",
                "entity_id": "calc-1",
            }
        )
        await repo.create(
            {
                "user_id": "user-1",
                "action_type": "update",
                "entity_type": "calculation",
                "entity_id": "calc-1",
            }
        )
        await repo.create(
            {
                "user_id": "user-1",
                "action_type": "create",
                "entity_type": "calculation",
                "entity_id": "calc-2",
            }
        )

        results = await repo.get_by_entity("calculation", "calc-1")

        assert len(results) >= 2
        assert all(
            r.entity_type == "calculation" and r.entity_id == "calc-1" for r in results
        )

    async def test_get_by_date_range(self, test_db_session: AsyncSession):
        """Test retrieving logs within a date range."""
        repo = AuditLogRepository(test_db_session)

        now = datetime.utcnow()
        yesterday = now - timedelta(days=1)
        tomorrow = now + timedelta(days=1)

        await repo.create(
            {
                "user_id": "user-1",
                "action_type": "create",
                "entity_type": "calculation",
                "entity_id": "calc-1",
                "timestamp": now,
            }
        )

        results = await repo.get_by_date_range(yesterday, tomorrow)

        assert len(results) >= 1
        assert all(yesterday <= r.timestamp <= tomorrow for r in results)

    async def test_get_by_status(self, test_db_session: AsyncSession):
        """Test retrieving logs by status."""
        repo = AuditLogRepository(test_db_session)

        await repo.create(
            {
                "user_id": "user-1",
                "action_type": "create",
                "entity_type": "calculation",
                "entity_id": "calc-1",
                "status": "success",
            }
        )
        await repo.create(
            {
                "user_id": "user-1",
                "action_type": "update",
                "entity_type": "design",
                "entity_id": "design-1",
                "status": "failure",
            }
        )

        results = await repo.get_by_status("success")

        assert len(results) >= 1
        assert all(r.status == "success" for r in results)

    async def test_get_failed_actions(self, test_db_session: AsyncSession):
        """Test retrieving failed actions."""
        repo = AuditLogRepository(test_db_session)

        await repo.create(
            {
                "user_id": "user-1",
                "action_type": "create",
                "entity_type": "calculation",
                "entity_id": "calc-1",
                "status": "failure",
            }
        )
        await repo.create(
            {
                "user_id": "user-1",
                "action_type": "update",
                "entity_type": "design",
                "entity_id": "design-1",
                "status": "error",
            }
        )
        await repo.create(
            {
                "user_id": "user-1",
                "action_type": "delete",
                "entity_type": "report",
                "entity_id": "report-1",
                "status": "success",
            }
        )

        results = await repo.get_failed_actions()

        assert len(results) >= 2
        assert all(r.status in ["failure", "error"] for r in results)

    async def test_get_recent(self, test_db_session: AsyncSession):
        """Test retrieving recent logs."""
        repo = AuditLogRepository(test_db_session)

        for i in range(5):
            await repo.create(
                {
                    "user_id": "user-1",
                    "action_type": "create",
                    "entity_type": "calculation",
                    "entity_id": f"calc-{i}",
                }
            )

        results = await repo.get_recent(limit=3)

        assert len(results) == 3
        for i in range(len(results) - 1):
            assert results[i].timestamp >= results[i + 1].timestamp

    async def test_search_logs(self, test_db_session: AsyncSession):
        """Test searching logs with multiple filters."""
        repo = AuditLogRepository(test_db_session)

        await repo.create(
            {
                "user_id": "user-1",
                "project_id": "project-1",
                "action_type": "create",
                "entity_type": "calculation",
                "entity_id": "calc-1",
                "status": "success",
            }
        )
        await repo.create(
            {
                "user_id": "user-2",
                "project_id": "project-1",
                "action_type": "update",
                "entity_type": "design",
                "entity_id": "design-1",
                "status": "success",
            }
        )

        results = await repo.search_logs(
            user_id="user-1", project_id="project-1", action_type="create"
        )

        assert len(results) >= 1
        assert all(
            r.user_id == "user-1"
            and r.project_id == "project-1"
            and r.action_type == "create"
            for r in results
        )
