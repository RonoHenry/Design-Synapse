"""MaterialSpecification repository for construction materials."""

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.material_specification import MaterialSpecification
from src.repositories.base_repository import BaseRepository


class MaterialSpecificationRepository(BaseRepository[MaterialSpecification]):
    """
    Repository for MaterialSpecification model with material-specific operations.

    Extends BaseRepository with methods for querying materials
    by design and category.
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize MaterialSpecificationRepository.

        Args:
            session: Async database session
        """
        super().__init__(MaterialSpecification, session)

    async def list_by_design(
        self, design_id: str, category: Optional[str] = None
    ) -> List[MaterialSpecification]:
        """
        List all materials for a design, optionally filtered by category.

        Args:
            design_id: Design ID (UUID as string)
            category: Optional category filter (structural, finishes, etc.)

        Returns:
            List of MaterialSpecification instances

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            query = select(MaterialSpecification).where(
                MaterialSpecification.design_id == design_id
            )

            if category:
                query = query.where(MaterialSpecification.category == category)

            query = query.order_by(MaterialSpecification.created_at.desc())

            result = await self.session.execute(query)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            raise e

    async def get_latest(self, design_id: str) -> Optional[MaterialSpecification]:
        """
        Get the most recently added material for a design.

        Args:
            design_id: Design ID (UUID as string)

        Returns:
            Most recent MaterialSpecification instance or None

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            query = (
                select(MaterialSpecification)
                .where(MaterialSpecification.design_id == design_id)
                .order_by(MaterialSpecification.created_at.desc())
                .limit(1)
            )

            result = await self.session.execute(query)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            raise e
