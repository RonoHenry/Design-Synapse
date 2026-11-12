"""Unit tests for BaseRepository."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.calculation_sheet import CalculationSheet
from src.repositories.base_repository import BaseRepository


@pytest.mark.asyncio
class TestBaseRepository:
    """Test suite for BaseRepository CRUD operations."""

    async def test_create(self, test_db_session: AsyncSession):
        """Test creating a new record."""
        repo = BaseRepository(CalculationSheet, test_db_session)

        data = {
            "project_id": "test-project-123",
            "title": "Test Calculation",
            "calculation_type": "structural",
            "inputs": {"load": 100},
            "outputs": {"result": 200},
            "created_by": "user-123",
        }

        result = await repo.create(data)

        assert result.id is not None
        assert result.project_id == "test-project-123"
        assert result.title == "Test Calculation"
        assert result.calculation_type == "structural"

    async def test_get_by_id(self, test_db_session: AsyncSession):
        """Test retrieving a record by ID."""
        repo = BaseRepository(CalculationSheet, test_db_session)

        # Create a record first
        data = {
            "project_id": "test-project-123",
            "title": "Test Calculation",
            "calculation_type": "structural",
            "inputs": {"load": 100},
            "outputs": {"result": 200},
            "created_by": "user-123",
        }
        created = await repo.create(data)

        # Retrieve it
        result = await repo.get_by_id(created.id)

        assert result is not None
        assert result.id == created.id
        assert result.title == "Test Calculation"

    async def test_get_by_id_not_found(self, test_db_session: AsyncSession):
        """Test retrieving a non-existent record."""
        repo = BaseRepository(CalculationSheet, test_db_session)

        result = await repo.get_by_id(99999)

        assert result is None

    async def test_list_all(self, test_db_session: AsyncSession):
        """Test listing all records with pagination."""
        repo = BaseRepository(CalculationSheet, test_db_session)

        # Create multiple records
        for i in range(5):
            await repo.create(
                {
                    "project_id": f"project-{i}",
                    "title": f"Calculation {i}",
                    "calculation_type": "structural",
                    "inputs": {},
                    "outputs": {},
                    "created_by": "user-123",
                }
            )

        # List all
        results = await repo.list_all(limit=10, offset=0)

        assert len(results) >= 5

    async def test_list_all_with_pagination(self, test_db_session: AsyncSession):
        """Test pagination in list_all."""
        repo = BaseRepository(CalculationSheet, test_db_session)

        # Create records
        for i in range(5):
            await repo.create(
                {
                    "project_id": f"project-{i}",
                    "title": f"Calculation {i}",
                    "calculation_type": "structural",
                    "inputs": {},
                    "outputs": {},
                    "created_by": "user-123",
                }
            )

        # Get first page
        page1 = await repo.list_all(limit=2, offset=0)
        # Get second page
        page2 = await repo.list_all(limit=2, offset=2)

        assert len(page1) == 2
        assert len(page2) == 2
        assert page1[0].id != page2[0].id

    async def test_update(self, test_db_session: AsyncSession):
        """Test updating a record."""
        repo = BaseRepository(CalculationSheet, test_db_session)

        # Create a record
        data = {
            "project_id": "test-project-123",
            "title": "Original Title",
            "calculation_type": "structural",
            "inputs": {},
            "outputs": {},
            "created_by": "user-123",
        }
        created = await repo.create(data)

        # Update it
        updates = {"title": "Updated Title"}
        result = await repo.update(created.id, updates)

        assert result is not None
        assert result.id == created.id
        assert result.title == "Updated Title"

    async def test_update_not_found(self, test_db_session: AsyncSession):
        """Test updating a non-existent record."""
        repo = BaseRepository(CalculationSheet, test_db_session)

        result = await repo.update(99999, {"title": "New Title"})

        assert result is None

    async def test_delete(self, test_db_session: AsyncSession):
        """Test deleting a record (soft delete)."""
        repo = BaseRepository(CalculationSheet, test_db_session)

        # Create a record
        data = {
            "project_id": "test-project-123",
            "title": "To Delete",
            "calculation_type": "structural",
            "inputs": {},
            "outputs": {},
            "created_by": "user-123",
        }
        created = await repo.create(data)

        # Delete it
        success = await repo.delete(created.id)

        assert success is True

        # Verify soft delete
        deleted = await repo.get_by_id(created.id, include_deleted=True)
        assert deleted is not None
        assert deleted.deleted_at is not None

    async def test_delete_not_found(self, test_db_session: AsyncSession):
        """Test deleting a non-existent record."""
        repo = BaseRepository(CalculationSheet, test_db_session)

        success = await repo.delete(99999)

        assert success is False

    async def test_count(self, test_db_session: AsyncSession):
        """Test counting records."""
        repo = BaseRepository(CalculationSheet, test_db_session)

        initial_count = await repo.count()

        # Create records
        for i in range(3):
            await repo.create(
                {
                    "project_id": f"project-{i}",
                    "title": f"Calculation {i}",
                    "calculation_type": "structural",
                    "inputs": {},
                    "outputs": {},
                    "created_by": "user-123",
                }
            )

        final_count = await repo.count()

        assert final_count == initial_count + 3

    async def test_filter_by(self, test_db_session: AsyncSession):
        """Test filtering records."""
        repo = BaseRepository(CalculationSheet, test_db_session)

        # Create records with different types
        await repo.create(
            {
                "project_id": "project-1",
                "title": "Structural Calc",
                "calculation_type": "structural",
                "inputs": {},
                "outputs": {},
                "created_by": "user-123",
            }
        )
        await repo.create(
            {
                "project_id": "project-1",
                "title": "MEP Calc",
                "calculation_type": "mep",
                "inputs": {},
                "outputs": {},
                "created_by": "user-123",
            }
        )

        # Filter by calculation_type
        results = await repo.filter_by(calculation_type="structural")

        assert len(results) >= 1
        assert all(r.calculation_type == "structural" for r in results)

    async def test_filter_by_multiple_criteria(self, test_db_session: AsyncSession):
        """Test filtering with multiple criteria."""
        repo = BaseRepository(CalculationSheet, test_db_session)

        # Create records
        await repo.create(
            {
                "project_id": "project-1",
                "title": "Calc 1",
                "calculation_type": "structural",
                "inputs": {},
                "outputs": {},
                "created_by": "user-123",
            }
        )
        await repo.create(
            {
                "project_id": "project-2",
                "title": "Calc 2",
                "calculation_type": "structural",
                "inputs": {},
                "outputs": {},
                "created_by": "user-123",
            }
        )

        # Filter by project_id and calculation_type
        results = await repo.filter_by(
            project_id="project-1", calculation_type="structural"
        )

        assert len(results) >= 1
        assert all(
            r.project_id == "project-1" and r.calculation_type == "structural"
            for r in results
        )
