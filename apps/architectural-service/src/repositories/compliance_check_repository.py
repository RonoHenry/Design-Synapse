"""ComplianceCheck repository for building code compliance."""

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.compliance_check import ComplianceCheck
from src.repositories.base_repository import BaseRepository


class ComplianceCheckRepository(BaseRepository[ComplianceCheck]):
    """
    Repository for ComplianceCheck model with compliance-specific operations.

    Extends BaseRepository with methods for querying compliance checks
    by design and retrieving latest checks.
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize ComplianceCheckRepository.

        Args:
            session: Async database session
        """
        super().__init__(ComplianceCheck, session)

    async def list_by_design(
        self, design_id: str, status: Optional[str] = None
    ) -> List[ComplianceCheck]:
        """
        List all compliance checks for a design, optionally filtered by status.

        Args:
            design_id: Design ID (UUID as string)
            status: Optional status filter (pending, in_progress, completed, failed)

        Returns:
            List of ComplianceCheck instances

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            query = select(ComplianceCheck).where(
                ComplianceCheck.design_id == design_id
            )

            if status:
                query = query.where(ComplianceCheck.status == status)

            query = query.order_by(ComplianceCheck.started_at.desc())

            result = await self.session.execute(query)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            raise e

    async def get_latest(self, design_id: str) -> Optional[ComplianceCheck]:
        """
        Get the most recent compliance check for a design.

        Args:
            design_id: Design ID (UUID as string)

        Returns:
            Most recent ComplianceCheck instance or None

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            query = (
                select(ComplianceCheck)
                .where(ComplianceCheck.design_id == design_id)
                .order_by(ComplianceCheck.started_at.desc())
                .limit(1)
            )

            result = await self.session.execute(query)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            raise e
