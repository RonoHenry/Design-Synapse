"""SpacePlanning repository for space planning analysis."""

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.space_planning import SpacePlanning
from src.repositories.base_repository import BaseRepository


class SpacePlanningRepository(BaseRepository[SpacePlanning]):
    """
    Repository for SpacePlanning model with planning-specific operations.

    Extends BaseRepository with methods for querying space planning
    analyses by design.
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize SpacePlanningRepository.

        Args:
            session: Async database session
        """
        super().__init__(SpacePlanning, session)

    async def list_by_design(
        self, design_id: str, status: Optional[str] = None
    ) -> List[SpacePlanning]:
        """
        List all space planning analyses for a design, optionally filtered by status.

        Args:
            design_id: Design ID (UUID as string)
            status: Optional status filter (pending, in_progress, completed, failed)

        Returns:
            List of SpacePlanning instances

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            query = select(SpacePlanning).where(SpacePlanning.design_id == design_id)

            if status:
                query = query.where(SpacePlanning.status == status)

            query = query.order_by(SpacePlanning.started_at.desc())

            result = await self.session.execute(query)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            raise e

    async def get_latest(self, design_id: str) -> Optional[SpacePlanning]:
        """
        Get the most recent space planning analysis for a design.

        Args:
            design_id: Design ID (UUID as string)

        Returns:
            Most recent SpacePlanning instance or None

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            query = (
                select(SpacePlanning)
                .where(SpacePlanning.design_id == design_id)
                .order_by(SpacePlanning.started_at.desc())
                .limit(1)
            )

            result = await self.session.execute(query)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            raise e
