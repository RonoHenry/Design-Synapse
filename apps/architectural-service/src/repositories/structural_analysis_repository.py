"""StructuralAnalysis repository for structural engineering analysis."""

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.structural_analysis import StructuralAnalysis
from src.repositories.base_repository import BaseRepository


class StructuralAnalysisRepository(BaseRepository[StructuralAnalysis]):
    """
    Repository for StructuralAnalysis model with analysis-specific operations.

    Extends BaseRepository with methods for querying structural analyses
    by design and retrieving latest analyses.
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize StructuralAnalysisRepository.

        Args:
            session: Async database session
        """
        super().__init__(StructuralAnalysis, session)

    async def list_by_design(
        self, design_id: str, status: Optional[str] = None
    ) -> List[StructuralAnalysis]:
        """
        List all structural analyses for a design, optionally filtered by status.

        Args:
            design_id: Design ID (UUID as string)
            status: Optional status filter (pending, in_progress, completed, failed)

        Returns:
            List of StructuralAnalysis instances

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            query = select(StructuralAnalysis).where(
                StructuralAnalysis.design_id == design_id
            )

            if status:
                query = query.where(StructuralAnalysis.status == status)

            query = query.order_by(StructuralAnalysis.started_at.desc())

            result = await self.session.execute(query)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            raise e

    async def get_latest(self, design_id: str) -> Optional[StructuralAnalysis]:
        """
        Get the most recent structural analysis for a design.

        Args:
            design_id: Design ID (UUID as string)

        Returns:
            Most recent StructuralAnalysis instance or None

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            query = (
                select(StructuralAnalysis)
                .where(StructuralAnalysis.design_id == design_id)
                .order_by(StructuralAnalysis.started_at.desc())
                .limit(1)
            )

            result = await self.session.execute(query)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            raise e
