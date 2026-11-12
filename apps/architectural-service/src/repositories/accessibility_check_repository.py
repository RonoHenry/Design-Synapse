"""AccessibilityCheck repository for accessibility compliance."""

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.accessibility_check import AccessibilityCheck
from src.repositories.base_repository import BaseRepository


class AccessibilityCheckRepository(BaseRepository[AccessibilityCheck]):
    """
    Repository for AccessibilityCheck model with accessibility-specific operations.

    Extends BaseRepository with methods for querying accessibility checks
    by design and retrieving latest checks.
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize AccessibilityCheckRepository.

        Args:
            session: Async database session
        """
        super().__init__(AccessibilityCheck, session)

    async def list_by_design(
        self, design_id: str, status: Optional[str] = None
    ) -> List[AccessibilityCheck]:
        """
        List all accessibility checks for a design, optionally filtered by status.

        Args:
            design_id: Design ID (UUID as string)
            status: Optional status filter (pending, in_progress, completed, failed)

        Returns:
            List of AccessibilityCheck instances

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            query = select(AccessibilityCheck).where(
                AccessibilityCheck.design_id == design_id
            )

            if status:
                query = query.where(AccessibilityCheck.status == status)

            query = query.order_by(AccessibilityCheck.started_at.desc())

            result = await self.session.execute(query)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            raise e

    async def get_latest(self, design_id: str) -> Optional[AccessibilityCheck]:
        """
        Get the most recent accessibility check for a design.

        Args:
            design_id: Design ID (UUID as string)

        Returns:
            Most recent AccessibilityCheck instance or None

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            query = (
                select(AccessibilityCheck)
                .where(AccessibilityCheck.design_id == design_id)
                .order_by(AccessibilityCheck.started_at.desc())
                .limit(1)
            )

            result = await self.session.execute(query)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            raise e
