"""Repository for StructuralDesign model."""

from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.structural_design import StructuralDesign
from .base_repository import BaseRepository


class StructuralDesignRepository(BaseRepository[StructuralDesign]):
    """Repository for managing structural designs.

    Provides CRUD operations and specialized queries for structural designs
    including filtering by project, design type, and status.
    """

    def __init__(self, db_session: AsyncSession):
        """Initialize repository with session.

        Args:
            db_session: Async database session
        """
        super().__init__(StructuralDesign, db_session)

    async def get_by_project_id(
        self, project_id: str, include_deleted: bool = False
    ) -> List[StructuralDesign]:
        """Get all structural designs for a project.

        Args:
            project_id: Project identifier
            include_deleted: Whether to include soft-deleted records

        Returns:
            List of structural designs
        """
        return await self.filter_by(
            project_id=project_id, include_deleted=include_deleted
        )

    async def get_by_design_type(
        self, design_type: str, include_deleted: bool = False
    ) -> List[StructuralDesign]:
        """Get structural designs by type.

        Args:
            design_type: Type of design (beam, column, foundation, slab, wall)
            include_deleted: Whether to include soft-deleted records

        Returns:
            List of structural designs
        """
        return await self.filter_by(
            design_type=design_type, include_deleted=include_deleted
        )

    async def get_by_project_and_type(
        self, project_id: str, design_type: str, include_deleted: bool = False
    ) -> List[StructuralDesign]:
        """Get structural designs by project and type.

        Args:
            project_id: Project identifier
            design_type: Type of design
            include_deleted: Whether to include soft-deleted records

        Returns:
            List of structural designs
        """
        return await self.filter_by(
            project_id=project_id,
            design_type=design_type,
            include_deleted=include_deleted,
        )

    async def get_by_calculation_sheet_id(
        self, calculation_sheet_id: int, include_deleted: bool = False
    ) -> List[StructuralDesign]:
        """Get structural designs linked to a calculation sheet.

        Args:
            calculation_sheet_id: Calculation sheet ID
            include_deleted: Whether to include soft-deleted records

        Returns:
            List of structural designs
        """
        return await self.filter_by(
            calculation_sheet_id=calculation_sheet_id, include_deleted=include_deleted
        )

    async def get_by_status(
        self, status: str, include_deleted: bool = False
    ) -> List[StructuralDesign]:
        """Get structural designs by status.

        Args:
            status: Design status (draft, approved, rejected)
            include_deleted: Whether to include soft-deleted records

        Returns:
            List of structural designs
        """
        return await self.filter_by(status=status, include_deleted=include_deleted)

    async def get_by_created_by(
        self, user_id: str, include_deleted: bool = False
    ) -> List[StructuralDesign]:
        """Get structural designs created by a user.

        Args:
            user_id: User identifier
            include_deleted: Whether to include soft-deleted records

        Returns:
            List of structural designs
        """
        return await self.filter_by(created_by=user_id, include_deleted=include_deleted)

    async def search_by_title(
        self, search_term: str, include_deleted: bool = False
    ) -> List[StructuralDesign]:
        """Search structural designs by title.

        Args:
            search_term: Search term to match in title
            include_deleted: Whether to include soft-deleted records

        Returns:
            List of matching structural designs
        """
        query = select(StructuralDesign).where(
            StructuralDesign.title.ilike(f"%{search_term}%")
        )

        if not include_deleted:
            query = query.where(StructuralDesign.deleted_at.is_(None))

        result = await self.db_session.execute(query)
        return list(result.scalars().all())

    async def get_recent(
        self, limit: int = 10, include_deleted: bool = False
    ) -> List[StructuralDesign]:
        """Get most recent structural designs.

        Args:
            limit: Maximum number of designs to return
            include_deleted: Whether to include soft-deleted records

        Returns:
            List of recent structural designs
        """
        query = select(StructuralDesign)

        if not include_deleted:
            query = query.where(StructuralDesign.deleted_at.is_(None))

        query = query.order_by(StructuralDesign.created_at.desc()).limit(limit)

        result = await self.db_session.execute(query)
        return list(result.scalars().all())
