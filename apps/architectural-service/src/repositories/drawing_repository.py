"""Drawing repository for architectural drawings."""

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.drawing import Drawing
from src.repositories.base_repository import BaseRepository


class DrawingRepository(BaseRepository[Drawing]):
    """
    Repository for Drawing model with drawing-specific operations.

    Extends BaseRepository with methods for querying drawings
    by design and drawing type.
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize DrawingRepository.

        Args:
            session: Async database session
        """
        super().__init__(Drawing, session)

    async def list_by_design(
        self, design_id: str, drawing_type: Optional[str] = None
    ) -> List[Drawing]:
        """
        List all drawings for a design, optionally filtered by type.

        Args:
            design_id: Design ID (UUID as string)
            drawing_type: Optional drawing type filter

        Returns:
            List of Drawing instances

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            query = select(Drawing).where(Drawing.design_id == design_id)

            if drawing_type:
                query = query.where(Drawing.drawing_type == drawing_type)

            query = query.order_by(Drawing.created_at.desc())

            result = await self.session.execute(query)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            raise e

    async def list_by_type(
        self, drawing_type: str, limit: Optional[int] = None
    ) -> List[Drawing]:
        """
        List all drawings of a specific type across all designs.

        Args:
            drawing_type: Drawing type to filter by
            limit: Optional maximum number of results

        Returns:
            List of Drawing instances

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            query = (
                select(Drawing)
                .where(Drawing.drawing_type == drawing_type)
                .order_by(Drawing.created_at.desc())
            )

            if limit:
                query = query.limit(limit)

            result = await self.session.execute(query)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            raise e
