"""Repository for AuditLog model."""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.audit_log import AuditLog
from .base_repository import BaseRepository


class AuditLogRepository(BaseRepository[AuditLog]):
    """Repository for managing audit logs.

    Provides query operations for audit logs including filtering by user,
    action type, entity, and time range. Note: Audit logs are typically
    not updated or deleted, only created and queried.
    """

    def __init__(self, db_session: AsyncSession):
        """Initialize repository with session.

        Args:
            db_session: Async database session
        """
        super().__init__(AuditLog, db_session)

    async def get_by_user_id(self, user_id: str, limit: int = 100) -> List[AuditLog]:
        """Get audit logs for a user.

        Args:
            user_id: User identifier
            limit: Maximum number of logs to return

        Returns:
            List of audit logs ordered by timestamp desc
        """
        query = (
            select(AuditLog)
            .where(AuditLog.user_id == user_id)
            .order_by(AuditLog.timestamp.desc())
            .limit(limit)
        )

        result = await self.db_session.execute(query)
        return list(result.scalars().all())

    async def get_by_project_id(
        self, project_id: str, limit: int = 100
    ) -> List[AuditLog]:
        """Get audit logs for a project.

        Args:
            project_id: Project identifier
            limit: Maximum number of logs to return

        Returns:
            List of audit logs ordered by timestamp desc
        """
        query = (
            select(AuditLog)
            .where(AuditLog.project_id == project_id)
            .order_by(AuditLog.timestamp.desc())
            .limit(limit)
        )

        result = await self.db_session.execute(query)
        return list(result.scalars().all())

    async def get_by_action_type(
        self, action_type: str, limit: int = 100
    ) -> List[AuditLog]:
        """Get audit logs by action type.

        Args:
            action_type: Action type (create, update, delete, validate, export)
            limit: Maximum number of logs to return

        Returns:
            List of audit logs ordered by timestamp desc
        """
        return await self.filter_by(action_type=action_type)

    async def get_by_entity_type(
        self, entity_type: str, limit: int = 100
    ) -> List[AuditLog]:
        """Get audit logs by entity type.

        Args:
            entity_type: Entity type (calculation, design, report, document)
            limit: Maximum number of logs to return

        Returns:
            List of audit logs ordered by timestamp desc
        """
        query = (
            select(AuditLog)
            .where(AuditLog.entity_type == entity_type)
            .order_by(AuditLog.timestamp.desc())
            .limit(limit)
        )

        result = await self.db_session.execute(query)
        return list(result.scalars().all())

    async def get_by_entity(
        self, entity_type: str, entity_id: str, limit: int = 100
    ) -> List[AuditLog]:
        """Get audit logs for a specific entity.

        Args:
            entity_type: Entity type
            entity_id: Entity identifier
            limit: Maximum number of logs to return

        Returns:
            List of audit logs ordered by timestamp desc
        """
        query = (
            select(AuditLog)
            .where(
                and_(
                    AuditLog.entity_type == entity_type, AuditLog.entity_id == entity_id
                )
            )
            .order_by(AuditLog.timestamp.desc())
            .limit(limit)
        )

        result = await self.db_session.execute(query)
        return list(result.scalars().all())

    async def get_by_date_range(
        self, start_date: datetime, end_date: datetime, limit: int = 1000
    ) -> List[AuditLog]:
        """Get audit logs within a date range.

        Args:
            start_date: Start of date range
            end_date: End of date range
            limit: Maximum number of logs to return

        Returns:
            List of audit logs ordered by timestamp desc
        """
        query = (
            select(AuditLog)
            .where(
                and_(AuditLog.timestamp >= start_date, AuditLog.timestamp <= end_date)
            )
            .order_by(AuditLog.timestamp.desc())
            .limit(limit)
        )

        result = await self.db_session.execute(query)
        return list(result.scalars().all())

    async def get_by_status(self, status: str, limit: int = 100) -> List[AuditLog]:
        """Get audit logs by status.

        Args:
            status: Status (success, failure, error)
            limit: Maximum number of logs to return

        Returns:
            List of audit logs ordered by timestamp desc
        """
        query = (
            select(AuditLog)
            .where(AuditLog.status == status)
            .order_by(AuditLog.timestamp.desc())
            .limit(limit)
        )

        result = await self.db_session.execute(query)
        return list(result.scalars().all())

    async def get_failed_actions(
        self, user_id: Optional[str] = None, limit: int = 100
    ) -> List[AuditLog]:
        """Get failed audit log entries.

        Args:
            user_id: Optional user identifier to filter by
            limit: Maximum number of logs to return

        Returns:
            List of failed audit logs ordered by timestamp desc
        """
        query = select(AuditLog).where(AuditLog.status.in_(["failure", "error"]))

        if user_id:
            query = query.where(AuditLog.user_id == user_id)

        query = query.order_by(AuditLog.timestamp.desc()).limit(limit)

        result = await self.db_session.execute(query)
        return list(result.scalars().all())

    async def get_recent(self, limit: int = 50) -> List[AuditLog]:
        """Get most recent audit logs.

        Args:
            limit: Maximum number of logs to return

        Returns:
            List of recent audit logs ordered by timestamp desc
        """
        query = select(AuditLog).order_by(AuditLog.timestamp.desc()).limit(limit)

        result = await self.db_session.execute(query)
        return list(result.scalars().all())

    async def search_logs(
        self,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        action_type: Optional[str] = None,
        entity_type: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[AuditLog]:
        """Search audit logs with multiple filters.

        Args:
            user_id: Optional user identifier
            project_id: Optional project identifier
            action_type: Optional action type
            entity_type: Optional entity type
            status: Optional status
            start_date: Optional start date
            end_date: Optional end date
            limit: Maximum number of logs to return

        Returns:
            List of matching audit logs ordered by timestamp desc
        """
        query = select(AuditLog)
        conditions = []

        if user_id:
            conditions.append(AuditLog.user_id == user_id)
        if project_id:
            conditions.append(AuditLog.project_id == project_id)
        if action_type:
            conditions.append(AuditLog.action_type == action_type)
        if entity_type:
            conditions.append(AuditLog.entity_type == entity_type)
        if status:
            conditions.append(AuditLog.status == status)
        if start_date:
            conditions.append(AuditLog.timestamp >= start_date)
        if end_date:
            conditions.append(AuditLog.timestamp <= end_date)

        if conditions:
            query = query.where(and_(*conditions))

        query = query.order_by(AuditLog.timestamp.desc()).limit(limit)

        result = await self.db_session.execute(query)
        return list(result.scalars().all())
