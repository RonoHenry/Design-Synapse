"""Unit tests for DesignRepository."""

from datetime import datetime
from uuid import uuid4

import pytest
from src.repositories.design_repository import DesignRepository


@pytest.mark.asyncio
class TestDesignRepository:
    """Unit tests for DesignRepository."""

    async def test_create_design(self, test_session):
        """Test creating a design."""
        # Arrange
        repo = DesignRepository(test_session)
        data = {
            "project_id": str(uuid4()),
            "name": "Test Design",
            "description": "Test description",
            "building_type": "residential",
            "location_data": {
                "address": "123 Main St",
                "city": "Test City",
                "state": "CA",
                "zip_code": "12345",
                "latitude": 37.7749,
                "longitude": -122.4194,
            },
            "design_metadata": {"key": "value"},
            "created_by": str(uuid4()),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }

        # Act
        design = await repo.create(**data)
        await test_session.commit()

        # Assert
        assert design.id is not None
        assert design.current_version == "1.0"
        assert design.version_number == 1
        assert design.name == data["name"]
        assert design.status == "draft"
        assert design.is_deleted == False

    async def test_get_design(self, test_session):
        """Test retrieving a design by ID."""
        # Arrange
        repo = DesignRepository(test_session)
        data = {
            "project_id": str(uuid4()),
            "name": "Test Design",
            "building_type": "commercial",
            "location_data": {"address": "456 Oak Ave"},
            "created_by": str(uuid4()),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        created_design = await repo.create(**data)
        await test_session.commit()

        # Act
        retrieved_design = await repo.get(created_design.id)

        # Assert
        assert retrieved_design is not None
        assert retrieved_design.id == created_design.id
        assert retrieved_design.name == data["name"]

    async def test_soft_delete(self, test_session):
        """Test soft deleting a design."""
        # Arrange
        repo = DesignRepository(test_session)
        data = {
            "project_id": str(uuid4()),
            "name": "Test Design",
            "building_type": "industrial",
            "location_data": {"address": "789 Pine Rd"},
            "created_by": str(uuid4()),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        created_design = await repo.create(**data)
        await test_session.commit()

        # Act
        deleted_design = await repo.soft_delete(created_design.id)
        await test_session.commit()

        # Assert
        assert deleted_design is not None
        assert deleted_design.is_deleted == True
        assert deleted_design.deleted_at is not None
        assert deleted_design.status == "archived"

    async def test_soft_delete_nonexistent_design(self, test_session):
        """Test soft deleting a design that doesn't exist."""
        # Arrange
        repo = DesignRepository(test_session)
        nonexistent_id = uuid4()

        # Act
        result = await repo.soft_delete(str(nonexistent_id))

        # Assert
        assert result is None

    async def test_optimistic_locking_conflict(self, test_session):
        """Test optimistic locking detects version conflicts."""
        # Arrange
        repo = DesignRepository(test_session)
        data = {
            "project_id": str(uuid4()),
            "name": "Test Design",
            "building_type": "residential",
            "location_data": {"address": "123 Main St"},
            "created_by": str(uuid4()),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        design = await repo.create(**data)
        await test_session.commit()

        # Act & Assert
        with pytest.raises(ValueError, match="Version conflict"):
            await repo.update_with_version_check(
                design.id,
                expected_version_number=999,  # Wrong version
                name="Updated Name",
            )

    async def test_get_by_version_not_found(self, test_session):
        """Test retrieving a non-existent version."""
        # Arrange
        repo = DesignRepository(test_session)
        data = {
            "project_id": str(uuid4()),
            "name": "Test Design",
            "building_type": "commercial",
            "location_data": {"address": "456 Oak Ave"},
            "created_by": str(uuid4()),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        design = await repo.create(**data)
        await test_session.commit()

        # Act
        result = await repo.get_by_version(design.id, "99.0")

        # Assert
        assert result is None

    async def test_list_by_project_excludes_deleted(self, test_session):
        """Test listing designs excludes soft-deleted by default."""
        # Arrange
        repo = DesignRepository(test_session)
        project_id = str(uuid4())
        created_by = str(uuid4())

        # Create two designs
        design1 = await repo.create(
            project_id=project_id,
            name="Design 1",
            building_type="residential",
            location_data={"address": "123 Main St"},
            created_by=created_by,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        design2 = await repo.create(
            project_id=project_id,
            name="Design 2",
            building_type="commercial",
            location_data={"address": "456 Oak Ave"},
            created_by=created_by,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        await test_session.commit()

        # Soft delete one design
        await repo.soft_delete(design1.id)
        await test_session.commit()

        # Act
        designs = await repo.list_by_project(project_id)

        # Assert
        assert len(designs) == 1
        assert designs[0].id == design2.id

    async def test_list_by_project_includes_deleted_when_requested(self, test_session):
        """Test listing designs includes soft-deleted when requested."""
        # Arrange
        repo = DesignRepository(test_session)
        project_id = str(uuid4())
        created_by = str(uuid4())

        # Create two designs
        design1 = await repo.create(
            project_id=project_id,
            name="Design 1",
            building_type="residential",
            location_data={"address": "123 Main St"},
            created_by=created_by,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        design2 = await repo.create(
            project_id=project_id,
            name="Design 2",
            building_type="commercial",
            location_data={"address": "456 Oak Ave"},
            created_by=created_by,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        await test_session.commit()

        # Soft delete one design
        await repo.soft_delete(design1.id)
        await test_session.commit()

        # Act
        designs = await repo.list_by_project(project_id, include_deleted=True)

        # Assert
        assert len(designs) == 2
