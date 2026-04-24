"""Unit tests for CalculationSheetRepository."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from src.repositories.calculation_sheet_repository import \
    CalculationSheetRepository


@pytest.mark.asyncio
class TestCalculationSheetRepository:
    """Test suite for CalculationSheetRepository."""

    async def test_get_by_project_id(self, test_db_session: AsyncSession):
        """Test retrieving calculation sheets by project ID."""
        repo = CalculationSheetRepository(test_db_session)

        # Create sheets for different projects
        await repo.create(
            {
                "project_id": "project-1",
                "title": "Project 1 Calc",
                "calculation_type": "structural",
                "inputs": {},
                "outputs": {},
                "created_by": "user-123",
            }
        )
        await repo.create(
            {
                "project_id": "project-2",
                "title": "Project 2 Calc",
                "calculation_type": "mep",
                "inputs": {},
                "outputs": {},
                "created_by": "user-123",
            }
        )

        # Get sheets for project-1
        results = await repo.get_by_project_id("project-1")

        assert len(results) >= 1
        assert all(r.project_id == "project-1" for r in results)

    async def test_get_by_calculation_type(self, test_db_session: AsyncSession):
        """Test retrieving sheets by calculation type."""
        repo = CalculationSheetRepository(test_db_session)

        # Create sheets of different types
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

        # Get structural sheets
        results = await repo.get_by_calculation_type("structural")

        assert len(results) >= 1
        assert all(r.calculation_type == "structural" for r in results)

    async def test_get_by_project_and_type(self, test_db_session: AsyncSession):
        """Test retrieving sheets by project and type."""
        repo = CalculationSheetRepository(test_db_session)

        # Create sheets
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
        await repo.create(
            {
                "project_id": "project-2",
                "title": "Structural Calc",
                "calculation_type": "structural",
                "inputs": {},
                "outputs": {},
                "created_by": "user-123",
            }
        )

        # Get project-1 structural sheets
        results = await repo.get_by_project_and_type("project-1", "structural")

        assert len(results) >= 1
        assert all(
            r.project_id == "project-1" and r.calculation_type == "structural"
            for r in results
        )

    async def test_get_version_history(self, test_db_session: AsyncSession):
        """Test retrieving version history for a sheet."""
        repo = CalculationSheetRepository(test_db_session)

        # Create original sheet
        original = await repo.create(
            {
                "project_id": "project-1",
                "title": "Original Calc",
                "calculation_type": "structural",
                "inputs": {"load": 100},
                "outputs": {"result": 200},
                "created_by": "user-123",
                "version": 1,
            }
        )

        # Create version 2
        await repo.create(
            {
                "project_id": "project-1",
                "title": "Original Calc",
                "calculation_type": "structural",
                "inputs": {"load": 150},
                "outputs": {"result": 300},
                "created_by": "user-123",
                "version": 2,
                "parent_id": original.id,
            }
        )

        # Get version history
        history = await repo.get_version_history(original.id)

        assert len(history) >= 1
        assert any(h.version == 2 for h in history)

    async def test_get_latest_version(self, test_db_session: AsyncSession):
        """Test retrieving the latest version of a sheet."""
        repo = CalculationSheetRepository(test_db_session)

        # Create original sheet
        original = await repo.create(
            {
                "project_id": "project-1",
                "title": "Calc Sheet",
                "calculation_type": "structural",
                "inputs": {},
                "outputs": {},
                "created_by": "user-123",
                "version": 1,
            }
        )

        # Create newer versions
        v2 = await repo.create(
            {
                "project_id": "project-1",
                "title": "Calc Sheet",
                "calculation_type": "structural",
                "inputs": {},
                "outputs": {},
                "created_by": "user-123",
                "version": 2,
                "parent_id": original.id,
            }
        )

        # Get latest version
        latest = await repo.get_latest_version(original.id)

        assert latest is not None
        assert latest.version == 2
        assert latest.id == v2.id

    async def test_search_by_title(self, test_db_session: AsyncSession):
        """Test searching sheets by title."""
        repo = CalculationSheetRepository(test_db_session)

        # Create sheets with different titles
        await repo.create(
            {
                "project_id": "project-1",
                "title": "Beam Design Calculation",
                "calculation_type": "structural",
                "inputs": {},
                "outputs": {},
                "created_by": "user-123",
            }
        )
        await repo.create(
            {
                "project_id": "project-1",
                "title": "Column Design Calculation",
                "calculation_type": "structural",
                "inputs": {},
                "outputs": {},
                "created_by": "user-123",
            }
        )

        # Search for "Beam"
        results = await repo.search_by_title("Beam")

        assert len(results) >= 1
        assert any("Beam" in r.title for r in results)

    async def test_get_by_status(self, test_db_session: AsyncSession):
        """Test retrieving sheets by status."""
        repo = CalculationSheetRepository(test_db_session)

        # Create sheets with different statuses
        await repo.create(
            {
                "project_id": "project-1",
                "title": "Draft Calc",
                "calculation_type": "structural",
                "inputs": {},
                "outputs": {},
                "created_by": "user-123",
                "status": "draft",
            }
        )
        await repo.create(
            {
                "project_id": "project-1",
                "title": "Approved Calc",
                "calculation_type": "structural",
                "inputs": {},
                "outputs": {},
                "created_by": "user-123",
                "status": "approved",
            }
        )

        # Get draft sheets
        results = await repo.get_by_status("draft")

        assert len(results) >= 1
        assert all(r.status == "draft" for r in results)

    async def test_get_by_created_by(self, test_db_session: AsyncSession):
        """Test retrieving sheets by creator."""
        repo = CalculationSheetRepository(test_db_session)

        # Create sheets by different users
        await repo.create(
            {
                "project_id": "project-1",
                "title": "User 1 Calc",
                "calculation_type": "structural",
                "inputs": {},
                "outputs": {},
                "created_by": "user-1",
            }
        )
        await repo.create(
            {
                "project_id": "project-1",
                "title": "User 2 Calc",
                "calculation_type": "structural",
                "inputs": {},
                "outputs": {},
                "created_by": "user-2",
            }
        )

        # Get sheets by user-1
        results = await repo.get_by_created_by("user-1")

        assert len(results) >= 1
        assert all(r.created_by == "user-1" for r in results)

    async def test_get_recent(self, test_db_session: AsyncSession):
        """Test retrieving recent sheets."""
        repo = CalculationSheetRepository(test_db_session)

        # Create sheets
        for i in range(5):
            await repo.create(
                {
                    "project_id": "project-1",
                    "title": f"Calc {i}",
                    "calculation_type": "structural",
                    "inputs": {},
                    "outputs": {},
                    "created_by": "user-123",
                }
            )

        # Get 3 most recent
        results = await repo.get_recent(limit=3)

        assert len(results) == 3
        # Should be ordered by created_at desc
        for i in range(len(results) - 1):
            assert results[i].created_at >= results[i + 1].created_at
