"""Design repository for architectural design documents."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.pagination import (PaginatedResponse, PaginationHelper,
                                 PaginationParams)
from src.models.design import Design
from src.models.design_version import DesignVersion
from src.repositories.base_repository import BaseRepository


class DesignRepository(BaseRepository[Design]):
    """
    Repository for Design model with version control support.

    Extends BaseRepository with design-specific methods including
    version management, soft delete, and optimistic locking.
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize design repository.

        Args:
            session: Async database session
        """
        super().__init__(Design, session)

    async def get_by_version(self, design_id: str, version: str) -> Optional[Design]:
        """
        Get a design at a specific version.

        Retrieves the design and reconstructs its state from the version snapshot.

        Args:
            design_id: Design ID (UUID as string)
            version: Version string (e.g., "1.0", "2.0")

        Returns:
            Design instance with data from specified version, or None if not found

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            # Get the design version
            result = await self.session.execute(
                select(DesignVersion)
                .where(DesignVersion.design_id == design_id)
                .where(DesignVersion.version == version)
            )
            design_version = result.scalar_one_or_none()

            if design_version is None:
                return None

            # Get the current design
            design = await self.get(design_id)
            if design is None:
                return None

            # Reconstruct the design from the version snapshot
            design_data = design_version.design_data

            # Apply snapshot data to design fields
            if "name" in design_data:
                design.name = design_data["name"]
            if "description" in design_data:
                design.description = design_data["description"]
            if "building_type" in design_data:
                design.building_type = design_data["building_type"]
            if "location_data" in design_data:
                design.location_data = design_data["location_data"]
            if "design_metadata" in design_data:
                design.metadata = design_data["design_metadata"]
            if "status" in design_data:
                design.status = design_data["status"]

            # Set version information
            design.current_version = design_version.version
            design.version_number = design_version.version_number

            return design
        except SQLAlchemyError as e:
            raise e

    async def list_versions(self, design_id: str) -> List[DesignVersion]:
        """
        List all versions of a design.

        Args:
            design_id: Design ID (UUID as string)

        Returns:
            List of DesignVersion instances ordered by version_number

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            result = await self.session.execute(
                select(DesignVersion)
                .where(DesignVersion.design_id == design_id)
                .order_by(DesignVersion.version_number)
            )
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            raise e

    async def create_version(
        self,
        design_id: str,
        version: str,
        version_number: int,
        design_data: dict,
        created_by: str,
        change_summary: Optional[str] = None,
    ) -> DesignVersion:
        """
        Create a new version snapshot for a design.

        Args:
            design_id: Design ID (UUID as string)
            version: Version string (e.g., "2.0")
            version_number: Numeric version number
            design_data: Complete snapshot of design data
            created_by: User ID who created this version
            change_summary: Optional summary of changes

        Returns:
            Created DesignVersion instance

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            design_version = DesignVersion(
                design_id=design_id,
                version=version,
                version_number=version_number,
                design_data=design_data,
                change_summary=change_summary,
                created_by=created_by,
                created_at=datetime.utcnow(),
            )
            self.session.add(design_version)
            await self.session.flush()
            await self.session.refresh(design_version)
            return design_version
        except SQLAlchemyError as e:
            await self.session.rollback()
            raise e

    async def soft_delete(self, design_id: str) -> Optional[Design]:
        """
        Soft delete a design document.

        Sets is_deleted=True and deleted_at timestamp without removing the record.

        Args:
            design_id: Design ID (UUID as string)

        Returns:
            Updated Design instance or None if not found

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            design = await self.get(design_id)
            if design is None:
                return None

            design.is_deleted = True
            design.deleted_at = datetime.utcnow()
            design.status = "archived"

            await self.session.flush()
            await self.session.refresh(design)
            return design
        except SQLAlchemyError as e:
            await self.session.rollback()
            raise e

    async def update_with_version_check(
        self, design_id: str, expected_version_number: int, **kwargs
    ) -> Optional[Design]:
        """
        Update a design with optimistic locking.

        Checks that the version_number matches expected value before updating.
        This prevents concurrent modification conflicts.

        Args:
            design_id: Design ID (UUID as string)
            expected_version_number: Expected current version number
            **kwargs: Fields to update

        Returns:
            Updated Design instance or None if version mismatch or not found

        Raises:
            SQLAlchemyError: If database operation fails
            ValueError: If version number doesn't match (optimistic lock failure)
        """
        try:
            design = await self.get(design_id)
            if design is None:
                return None

            # Check version number for optimistic locking
            if design.version_number != expected_version_number:
                raise ValueError(
                    f"Version conflict: expected {expected_version_number}, "
                    f"got {design.version_number}"
                )

            # Update fields
            for key, value in kwargs.items():
                if hasattr(design, key):
                    setattr(design, key, value)

            # Increment version number
            design.version_number += 1
            design.current_version = f"{design.version_number}.0"
            design.updated_at = datetime.utcnow()

            await self.session.flush()
            await self.session.refresh(design)
            return design
        except SQLAlchemyError as e:
            await self.session.rollback()
            raise e

    async def list_by_project(
        self,
        project_id: str,
        include_deleted: bool = False,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[Design]:
        """
        List all designs for a project.

        Args:
            project_id: Project ID (UUID as string)
            include_deleted: Whether to include soft-deleted designs
            limit: Maximum number of records to return
            offset: Number of records to skip

        Returns:
            List of Design instances

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            query = select(Design).where(Design.project_id == project_id)

            if not include_deleted:
                query = query.where(Design.is_deleted == False)

            query = query.order_by(Design.created_at.desc())

            if offset is not None:
                query = query.offset(offset)
            if limit is not None:
                query = query.limit(limit)

            result = await self.session.execute(query)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            raise e

    async def get_latest_version_number(self, design_id: str) -> Optional[int]:
        """
        Get the latest version number for a design.

        Args:
            design_id: Design ID (UUID as string)

        Returns:
            Latest version number or None if design not found

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            from sqlalchemy import func

            result = await self.session.execute(
                select(func.max(DesignVersion.version_number)).where(
                    DesignVersion.design_id == design_id
                )
            )
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            raise e

    async def list_designs(
        self,
        params: PaginationParams,
        project_id: Optional[UUID] = None,
        include_deleted: bool = False,
        include_total: bool = False,
    ) -> PaginatedResponse:
        """
        List designs with cursor-based pagination.

        Args:
            params: Pagination parameters (cursor, limit, sort)
            project_id: Optional project ID to filter by
            include_deleted: Whether to include soft-deleted designs
            include_total: Whether to include total count

        Returns:
            Paginated response with Design instances

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            # Build base query
            query = select(Design)

            # Apply filters
            if project_id is not None:
                query = query.where(Design.project_id == str(project_id))

            if not include_deleted:
                query = query.where(Design.is_deleted == False)

            # Use pagination helper
            pagination_helper = PaginationHelper(
                session=self.session, model=Design, default_sort_field="created_at"
            )

            return await pagination_helper.paginate(
                query=query, params=params, include_total=include_total
            )

        except SQLAlchemyError as e:
            raise e
