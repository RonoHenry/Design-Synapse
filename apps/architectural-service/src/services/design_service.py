"""Design service for architectural design management."""

import logging
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from src.api.v1.schemas.design import CreateDesignRequest, UpdateDesignRequest
from src.core.exceptions import ConflictError, NotFoundError, ValidationError
from src.infrastructure.project_service_client import (ActivityLog,
                                                       ProjectServiceClient)
from src.models.design import Design
from src.models.design_version import DesignVersion
from src.repositories.design_repository import DesignRepository

logger = logging.getLogger(__name__)


class DesignService:
    """
    Service for managing architectural design documents.

    Handles design creation, updates, version management, and soft deletion
    with project validation and activity logging.
    """

    def __init__(
        self,
        design_repository: DesignRepository,
        project_client: ProjectServiceClient,
    ):
        """
        Initialize DesignService.

        Args:
            design_repository: Repository for design data access
            project_client: Client for project service integration
        """
        self.design_repository = design_repository
        self.project_client = project_client

    async def create_design(
        self,
        project_id: UUID,
        user_id: UUID,
        data: CreateDesignRequest,
    ) -> Design:
        """
        Create a new architectural design document.

        Validates project exists and user has access before creating design.
        Initializes design with version 1.0 and creates initial version snapshot.

        Args:
            project_id: Project ID to associate design with
            user_id: User ID creating the design
            data: Design creation request data

        Returns:
            Created Design instance with version 1.0

        Raises:
            ValidationError: If project validation fails
            NotFoundError: If project doesn't exist
        """
        # Validate project exists and user has access
        validation = await self.project_client.validate_project(project_id, user_id)

        if not validation.exists:
            raise NotFoundError(
                f"Project {project_id} not found",
                details={"project_id": str(project_id)},
            )

        if not validation.user_has_access:
            raise ValidationError(
                f"User {user_id} does not have access to project {project_id}",
                details={"user_id": str(user_id), "project_id": str(project_id)},
            )

        # Create design with version 1.0
        # Handle both enum and string values for building_type
        building_type_value = (
            data.building_type.value
            if hasattr(data.building_type, "value")
            else data.building_type
        )

        design = Design(
            id=str(uuid4()),
            project_id=str(project_id),
            name=data.name,
            description=data.description,
            building_type=building_type_value,
            location_data=data.location.model_dump(),
            current_version="1.0",
            version_number=1,
            status="draft",
            metadata=data.metadata,
            created_by=str(user_id),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            is_deleted=False,
        )

        # Save design
        design = await self.design_repository.create(design)

        # Create initial version snapshot
        design_data = {
            "name": design.name,
            "description": design.description,
            "building_type": design.building_type,
            "location_data": design.location_data,
            "design_metadata": design.metadata,
            "status": design.status,
        }

        await self.design_repository.create_version(
            design_id=design.id,
            version="1.0",
            version_number=1,
            design_data=design_data,
            created_by=str(user_id),
            change_summary="Initial design creation",
        )

        # Log activity to project service (fire-and-forget)
        try:
            activity = ActivityLog(
                project_id=project_id,
                user_id=user_id,
                activity_type="design_created",
                description=f"Created design: {design.name}",
                metadata={
                    "design_id": design.id,
                    "design_name": design.name,
                    "building_type": design.building_type,
                },
                timestamp=datetime.utcnow(),
            )
            await self.project_client.log_activity(project_id, activity)
        except Exception as e:
            logger.warning(f"Failed to log design creation activity: {e}")

        logger.info(
            f"Created design {design.id} for project {project_id} " f"by user {user_id}"
        )

        return design

    async def update_design(
        self,
        design_id: UUID,
        user_id: UUID,
        data: UpdateDesignRequest,
    ) -> Design:
        """
        Update a design document and create new version.

        Increments version number and creates version snapshot.
        Uses optimistic locking to prevent concurrent modification conflicts.

        Args:
            design_id: Design ID to update
            user_id: User ID performing the update
            data: Design update request data

        Returns:
            Updated Design instance with incremented version

        Raises:
            NotFoundError: If design doesn't exist
            ConflictError: If concurrent modification detected
        """
        # Get current design
        design = await self.design_repository.get(str(design_id))
        if design is None:
            raise NotFoundError(
                f"Design {design_id} not found", details={"design_id": str(design_id)}
            )

        # Check if design is deleted
        if design.is_deleted:
            raise ValidationError(
                f"Cannot update deleted design {design_id}",
                details={"design_id": str(design_id)},
            )

        # Store current version number for optimistic locking
        current_version_number = design.version_number

        # Update fields
        update_data = {}
        if data.name is not None:
            update_data["name"] = data.name
        if data.description is not None:
            update_data["description"] = data.description
        if data.building_type is not None:
            # Handle both enum and string values
            update_data["building_type"] = (
                data.building_type.value
                if hasattr(data.building_type, "value")
                else data.building_type
            )
        if data.location is not None:
            update_data["location_data"] = data.location.model_dump()
        if data.status is not None:
            # Handle both enum and string values
            update_data["status"] = (
                data.status.value if hasattr(data.status, "value") else data.status
            )
        if data.metadata is not None:
            update_data["metadata"] = data.metadata

        # Update with version check
        try:
            design = await self.design_repository.update_with_version_check(
                design_id=str(design_id),
                expected_version_number=current_version_number,
                **update_data,
            )
        except ValueError as e:
            raise ConflictError(
                f"Concurrent modification detected for design {design_id}",
                details={"design_id": str(design_id), "error": str(e)},
            )

        if design is None:
            raise NotFoundError(
                f"Design {design_id} not found during update",
                details={"design_id": str(design_id)},
            )

        # Create version snapshot
        design_data = {
            "name": design.name,
            "description": design.description,
            "building_type": design.building_type,
            "location_data": design.location_data,
            "design_metadata": design.metadata,
            "status": design.status,
        }

        await self.design_repository.create_version(
            design_id=design.id,
            version=design.current_version,
            version_number=design.version_number,
            design_data=design_data,
            created_by=str(user_id),
            change_summary="Design updated",
        )

        # Log activity to project service (fire-and-forget)
        try:
            activity = ActivityLog(
                project_id=UUID(design.project_id),
                user_id=user_id,
                activity_type="design_updated",
                description=f"Updated design: {design.name}",
                metadata={
                    "design_id": design.id,
                    "design_name": design.name,
                    "version": design.current_version,
                },
                timestamp=datetime.utcnow(),
            )
            await self.project_client.log_activity(UUID(design.project_id), activity)
        except Exception as e:
            logger.warning(f"Failed to log design update activity: {e}")

        logger.info(
            f"Updated design {design.id} to version {design.current_version} "
            f"by user {user_id}"
        )

        return design

    async def get_design(
        self,
        design_id: UUID,
        version: Optional[str] = None,
    ) -> Design:
        """
        Retrieve a design document, optionally at a specific version.

        Args:
            design_id: Design ID to retrieve
            version: Optional version string (e.g., "1.0", "2.0")

        Returns:
            Design instance (current or historical version)

        Raises:
            NotFoundError: If design or version doesn't exist
        """
        if version is not None:
            # Get specific version
            design = await self.design_repository.get_by_version(
                str(design_id), version
            )
            if design is None:
                raise NotFoundError(
                    f"Design {design_id} version {version} not found",
                    details={"design_id": str(design_id), "version": version},
                )
        else:
            # Get current version
            design = await self.design_repository.get(str(design_id))
            if design is None:
                raise NotFoundError(
                    f"Design {design_id} not found",
                    details={"design_id": str(design_id)},
                )

        return design

    async def list_versions(
        self,
        design_id: UUID,
    ) -> list[DesignVersion]:
        """
        List all versions of a design document.

        Args:
            design_id: Design ID to list versions for

        Returns:
            List of DesignVersion instances ordered by version number

        Raises:
            NotFoundError: If design doesn't exist
        """
        # Verify design exists
        design = await self.design_repository.get(str(design_id))
        if design is None:
            raise NotFoundError(
                f"Design {design_id} not found", details={"design_id": str(design_id)}
            )

        # Get all versions
        versions = await self.design_repository.list_versions(str(design_id))

        return versions

    async def soft_delete(
        self,
        design_id: UUID,
        user_id: UUID,
    ) -> None:
        """
        Soft delete a design document.

        Sets is_deleted=True and deleted_at timestamp without removing record.
        All design data remains accessible for audit purposes.

        Args:
            design_id: Design ID to delete
            user_id: User ID performing the deletion

        Raises:
            NotFoundError: If design doesn't exist
        """
        # Verify design exists
        design = await self.design_repository.get(str(design_id))
        if design is None:
            raise NotFoundError(
                f"Design {design_id} not found", details={"design_id": str(design_id)}
            )

        # Check if already deleted
        if design.is_deleted:
            logger.warning(f"Design {design_id} is already deleted")
            return

        # Soft delete
        design = await self.design_repository.soft_delete(str(design_id))

        # Log activity to project service (fire-and-forget)
        try:
            activity = ActivityLog(
                project_id=UUID(design.project_id),
                user_id=user_id,
                activity_type="design_deleted",
                description=f"Deleted design: {design.name}",
                metadata={
                    "design_id": design.id,
                    "design_name": design.name,
                },
                timestamp=datetime.utcnow(),
            )
            await self.project_client.log_activity(UUID(design.project_id), activity)
        except Exception as e:
            logger.warning(f"Failed to log design deletion activity: {e}")

        logger.info(f"Soft deleted design {design_id} by user {user_id}")
