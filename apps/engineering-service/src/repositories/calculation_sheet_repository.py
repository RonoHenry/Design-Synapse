"""Repository for CalculationSheet model."""

from typing import List, Optional

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.calculation_sheet import CalculationSheet
from .base_repository import BaseRepository


class CalculationSheetRepository(BaseRepository[CalculationSheet]):
    """Repository for managing calculation sheets.

    Provides CRUD operations and specialized queries for calculation sheets
    including version history, project filtering, and search capabilities.
    """

    def __init__(self, db_session: AsyncSession):
        """Initialize repository with session.

        Args:
            db_session: Async database session
        """
        super().__init__(CalculationSheet, db_session)

    async def get_by_project_id(
        self, project_id: str, include_deleted: bool = False
    ) -> List[CalculationSheet]:
        """Get all calculation sheets for a project.

        Args:
            project_id: Project identifier
            include_deleted: Whether to include soft-deleted records

        Returns:
            List of calculation sheets
        """
        return await self.filter_by(
            project_id=project_id, include_deleted=include_deleted
        )

    async def get_by_calculation_type(
        self, calculation_type: str, include_deleted: bool = False
    ) -> List[CalculationSheet]:
        """Get calculation sheets by type.

        Args:
            calculation_type: Type of calculation (structural, mep, civil)
            include_deleted: Whether to include soft-deleted records

        Returns:
            List of calculation sheets
        """
        return await self.filter_by(
            calculation_type=calculation_type, include_deleted=include_deleted
        )

    async def get_by_project_and_type(
        self, project_id: str, calculation_type: str, include_deleted: bool = False
    ) -> List[CalculationSheet]:
        """Get calculation sheets by project and type.

        Args:
            project_id: Project identifier
            calculation_type: Type of calculation
            include_deleted: Whether to include soft-deleted records

        Returns:
            List of calculation sheets
        """
        return await self.filter_by(
            project_id=project_id,
            calculation_type=calculation_type,
            include_deleted=include_deleted,
        )

    async def get_version_history(self, sheet_id: int) -> List[CalculationSheet]:
        """Get version history for a calculation sheet.

        Args:
            sheet_id: ID of the original sheet

        Returns:
            List of sheet versions ordered by version number
        """
        query = (
            select(CalculationSheet)
            .where(
                or_(
                    CalculationSheet.id == sheet_id,
                    CalculationSheet.parent_id == sheet_id,
                )
            )
            .order_by(CalculationSheet.version.asc())
        )

        result = await self.db_session.execute(query)
        return list(result.scalars().all())

    async def get_latest_version(self, sheet_id: int) -> Optional[CalculationSheet]:
        """Get the latest version of a calculation sheet.

        Args:
            sheet_id: ID of the original sheet

        Returns:
            Latest version of the sheet or None
        """
        query = (
            select(CalculationSheet)
            .where(
                or_(
                    CalculationSheet.id == sheet_id,
                    CalculationSheet.parent_id == sheet_id,
                )
            )
            .order_by(CalculationSheet.version.desc())
            .limit(1)
        )

        result = await self.db_session.execute(query)
        return result.scalar_one_or_none()

    async def search_by_title(
        self, search_term: str, include_deleted: bool = False
    ) -> List[CalculationSheet]:
        """Search calculation sheets by title.

        Args:
            search_term: Search term to match in title
            include_deleted: Whether to include soft-deleted records

        Returns:
            List of matching calculation sheets
        """
        query = select(CalculationSheet).where(
            CalculationSheet.title.ilike(f"%{search_term}%")
        )

        if not include_deleted:
            query = query.where(CalculationSheet.deleted_at.is_(None))

        result = await self.db_session.execute(query)
        return list(result.scalars().all())

    async def get_by_status(
        self, status: str, include_deleted: bool = False
    ) -> List[CalculationSheet]:
        """Get calculation sheets by status.

        Args:
            status: Sheet status (draft, approved, archived)
            include_deleted: Whether to include soft-deleted records

        Returns:
            List of calculation sheets
        """
        return await self.filter_by(status=status, include_deleted=include_deleted)

    async def get_by_created_by(
        self, user_id: str, include_deleted: bool = False
    ) -> List[CalculationSheet]:
        """Get calculation sheets created by a user.

        Args:
            user_id: User identifier
            include_deleted: Whether to include soft-deleted records

        Returns:
            List of calculation sheets
        """
        return await self.filter_by(created_by=user_id, include_deleted=include_deleted)

    async def get_recent(
        self, limit: int = 10, include_deleted: bool = False
    ) -> List[CalculationSheet]:
        """Get most recent calculation sheets.

        Args:
            limit: Maximum number of sheets to return
            include_deleted: Whether to include soft-deleted records

        Returns:
            List of recent calculation sheets
        """
        query = select(CalculationSheet)

        if not include_deleted:
            query = query.where(CalculationSheet.deleted_at.is_(None))

        query = query.order_by(CalculationSheet.created_at.desc()).limit(limit)

        result = await self.db_session.execute(query)
        return list(result.scalars().all())
