"""Repository for MEPDesign model."""

from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.mep_design import MEPDesign
from .base_repository import BaseRepository


class MEPDesignRepository(BaseRepository[MEPDesign]):
    """Repository for managing MEP designs.

    Provides CRUD operations and specialized queries for MEP designs
    including filtering by project, system type, and status.
    """

    def __init__(self, db_session: AsyncSession):
        """Initialize repository with session.

        Args:
            db_session: Async database session
        """
        super().__init__(MEPDesign, db_session)

    async def get_by_project_id(
        self, project_id: str, include_deleted: bool = False
    ) -> List[MEPDesign]:
        """Get all MEP designs for a project.

        Args:
            project_id: Project identifier
            include_deleted: Whether to include soft-deleted records

        Returns:
            List of MEP designs
        """
        return await self.filter_by(
            project_id=project_id, include_deleted=include_deleted
        )

    async def get_by_system_type(
        self, system_type: str, include_deleted: bool = False
    ) -> List[MEPDesign]:
        """Get MEP designs by system type.

        Args:
            system_type: Type of system (hvac, electrical, plumbing, fire_protection)
            include_deleted: Whether to include soft-deleted records

        Returns:
            List of MEP designs
        """
        return await self.filter_by(
            system_type=system_type, include_deleted=include_deleted
        )

    async def get_by_project_and_system(
        self, project_id: str, system_type: str, include_deleted: bool = False
    ) -> List[MEPDesign]:
        """Get MEP designs by project and system type.

        Args:
            project_id: Project identifier
            system_type: Type of system
            include_deleted: Whether to include soft-deleted records

        Returns:
            List of MEP designs
        """
        return await self.filter_by(
            project_id=project_id,
            system_type=system_type,
            include_deleted=include_deleted,
        )

    async def get_by_calculation_sheet_id(
        self, calculation_sheet_id: int, include_deleted: bool = False
    ) -> List[MEPDesign]:
        """Get MEP designs linked to a calculation sheet.

        Args:
            calculation_sheet_id: Calculation sheet ID
            include_deleted: Whether to include soft-deleted records

        Returns:
            List of MEP designs
        """
        return await self.filter_by(
            calculation_sheet_id=calculation_sheet_id, include_deleted=include_deleted
        )

    async def get_by_status(
        self, status: str, include_deleted: bool = False
    ) -> List[MEPDesign]:
        """Get MEP designs by status.

        Args:
            status: Design status (draft, approved, rejected)
            include_deleted: Whether to include soft-deleted records

        Returns:
            List of MEP designs
        """
        return await self.filter_by(status=status, include_deleted=include_deleted)

    async def get_by_created_by(
        self, user_id: str, include_deleted: bool = False
    ) -> List[MEPDesign]:
        """Get MEP designs created by a user.

        Args:
            user_id: User identifier
            include_deleted: Whether to include soft-deleted records

        Returns:
            List of MEP designs
        """
        return await self.filter_by(created_by=user_id, include_deleted=include_deleted)

    async def search_by_title(
        self, search_term: str, include_deleted: bool = False
    ) -> List[MEPDesign]:
        """Search MEP designs by title.

        Args:
            search_term: Search term to match in title
            include_deleted: Whether to include soft-deleted records

        Returns:
            List of matching MEP designs
        """
        query = select(MEPDesign).where(MEPDesign.title.ilike(f"%{search_term}%"))

        if not include_deleted:
            query = query.where(MEPDesign.deleted_at.is_(None))

        result = await self.db_session.execute(query)
        return list(result.scalars().all())

    async def get_recent(
        self, limit: int = 10, include_deleted: bool = False
    ) -> List[MEPDesign]:
        """Get most recent MEP designs.

        Args:
            limit: Maximum number of designs to return
            include_deleted: Whether to include soft-deleted records

        Returns:
            List of recent MEP designs
        """
        query = select(MEPDesign)

        if not include_deleted:
            query = query.where(MEPDesign.deleted_at.is_(None))

        query = query.order_by(MEPDesign.created_at.desc()).limit(limit)

        result = await self.db_session.execute(query)
        return list(result.scalars().all())
