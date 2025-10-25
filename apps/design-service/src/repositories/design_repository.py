"""Repository for Design model CRUD operations."""

from typing import List, Optional
from sqlalchemy import desc
from sqlalchemy.orm import Session

from ..models.design import Design


class DesignRepository:
    """Repository for managing Design entities."""

    def __init__(self, db_session: Session):
        """
        Initialize the repository with a database session.

        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session

    def create_design(self, **kwargs) -> Design:
        """
        Create a new design.

        Args:
            **kwargs: Design attributes (project_id, name, specification, etc.)

        Returns:
            Created Design instance

        Raises:
            ValueError: If validation fails
        """
        design = Design(**kwargs)
        self.db.add(design)
        self.db.commit()
        self.db.refresh(design)
        return design

    def get_design_by_id(
        self, design_id: int, include_archived: bool = False
    ) -> Optional[Design]:
        """
        Get a design by its ID.

        Args:
            design_id: ID of the design to retrieve
            include_archived: Whether to include archived designs (default: False)

        Returns:
            Design instance if found, None otherwise
        """
        query = self.db.query(Design).filter(Design.id == design_id)

        if not include_archived:
            query = query.filter(Design.is_archived == False)

        return query.first()

    def update_design(self, design_id: int, **kwargs) -> Optional[Design]:
        """
        Update a design with the provided fields.

        Args:
            design_id: ID of the design to update
            **kwargs: Fields to update

        Returns:
            Updated Design instance if found, None otherwise
        """
        design = self.get_design_by_id(design_id, include_archived=True)
        if not design:
            return None

        # Update provided fields
        for key, value in kwargs.items():
            if hasattr(design, key):
                setattr(design, key, value)

        self.db.commit()
        self.db.refresh(design)
        return design

    def delete_design(self, design_id: int) -> bool:
        """
        Soft delete a design by setting is_archived=True.

        Args:
            design_id: ID of the design to delete

        Returns:
            True if design was deleted, False if not found
        """
        design = self.get_design_by_id(design_id, include_archived=True)
        if not design:
            return False

        design.is_archived = True
        self.db.commit()
        return True

    def list_designs(
        self,
        project_id: Optional[int] = None,
        building_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[Design]:
        """
        List designs with optional filtering and pagination.

        Args:
            project_id: Filter by project ID
            building_type: Filter by building type
            status: Filter by status
            limit: Maximum number of results to return
            offset: Number of results to skip

        Returns:
            List of Design instances matching the criteria
        """
        query = self.db.query(Design).filter(Design.is_archived == False)

        # Apply filters
        if project_id is not None:
            query = query.filter(Design.project_id == project_id)
        if building_type is not None:
            query = query.filter(Design.building_type == building_type)
        if status is not None:
            query = query.filter(Design.status == status)

        # Order by created_at descending (newest first)
        query = query.order_by(desc(Design.created_at))

        # Apply pagination
        if offset is not None:
            query = query.offset(offset)
        if limit is not None:
            query = query.limit(limit)

        return query.all()

    def get_design_versions(self, design_id: int) -> List[Design]:
        """
        Get all versions of a design, including the current one and all ancestors.

        Args:
            design_id: ID of the design to get versions for

        Returns:
            List of Design instances representing all versions, ordered by version descending
        """
        # Get the starting design
        current_design = self.get_design_by_id(design_id, include_archived=False)
        if not current_design:
            return []

        versions = [current_design]

        # Traverse up the parent chain
        parent_id = current_design.parent_design_id
        while parent_id is not None:
            parent = self.get_design_by_id(parent_id, include_archived=False)
            if not parent:
                break
            versions.append(parent)
            parent_id = parent.parent_design_id

        # Sort by version descending (newest first)
        versions.sort(key=lambda d: d.version, reverse=True)

        return versions
