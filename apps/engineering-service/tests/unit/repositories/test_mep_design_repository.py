"""Unit tests for MEPDesignRepository."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from src.repositories.mep_design_repository import MEPDesignRepository


@pytest.mark.asyncio
class TestMEPDesignRepository:
    """Test suite for MEPDesignRepository."""

    async def test_get_by_project_id(self, test_db_session: AsyncSession):
        """Test retrieving MEP designs by project ID."""
        repo = MEPDesignRepository(test_db_session)

        # Create designs for different projects
        await repo.create(
            {
                "project_id": "project-1",
                "title": "Project 1 HVAC",
                "system_type": "hvac",
                "loads": {"heating": 100, "cooling": 150},
                "equipment": {"type": "rooftop"},
                "distribution": {"ductwork": "sheet_metal"},
                "sizing_results": {"capacity": 10},
                "created_by": "user-123",
            }
        )
        await repo.create(
            {
                "project_id": "project-2",
                "title": "Project 2 Electrical",
                "system_type": "electrical",
                "loads": {"total": 200},
                "equipment": {"panel": "main"},
                "distribution": {"conduit": "EMT"},
                "sizing_results": {"amperage": 400},
                "created_by": "user-123",
            }
        )

        # Get designs for project-1
        results = await repo.get_by_project_id("project-1")

        assert len(results) >= 1
        assert all(r.project_id == "project-1" for r in results)

    async def test_get_by_system_type(self, test_db_session: AsyncSession):
        """Test retrieving designs by system type."""
        repo = MEPDesignRepository(test_db_session)

        # Create designs of different types
        await repo.create(
            {
                "project_id": "project-1",
                "title": "HVAC Design",
                "system_type": "hvac",
                "loads": {},
                "equipment": {},
                "distribution": {},
                "sizing_results": {},
                "created_by": "user-123",
            }
        )
        await repo.create(
            {
                "project_id": "project-1",
                "title": "Electrical Design",
                "system_type": "electrical",
                "loads": {},
                "equipment": {},
                "distribution": {},
                "sizing_results": {},
                "created_by": "user-123",
            }
        )

        # Get HVAC designs
        results = await repo.get_by_system_type("hvac")

        assert len(results) >= 1
        assert all(r.system_type == "hvac" for r in results)

    async def test_get_by_project_and_system(self, test_db_session: AsyncSession):
        """Test retrieving designs by project and system type."""
        repo = MEPDesignRepository(test_db_session)

        # Create designs
        await repo.create(
            {
                "project_id": "project-1",
                "title": "P1 HVAC",
                "system_type": "hvac",
                "loads": {},
                "equipment": {},
                "distribution": {},
                "sizing_results": {},
                "created_by": "user-123",
            }
        )
        await repo.create(
            {
                "project_id": "project-1",
                "title": "P1 Electrical",
                "system_type": "electrical",
                "loads": {},
                "equipment": {},
                "distribution": {},
                "sizing_results": {},
                "created_by": "user-123",
            }
        )
        await repo.create(
            {
                "project_id": "project-2",
                "title": "P2 HVAC",
                "system_type": "hvac",
                "loads": {},
                "equipment": {},
                "distribution": {},
                "sizing_results": {},
                "created_by": "user-123",
            }
        )

        # Get project-1 HVAC designs
        results = await repo.get_by_project_and_system("project-1", "hvac")

        assert len(results) >= 1
        assert all(
            r.project_id == "project-1" and r.system_type == "hvac" for r in results
        )

    async def test_get_by_calculation_sheet_id(self, test_db_session: AsyncSession):
        """Test retrieving designs by calculation sheet ID."""
        repo = MEPDesignRepository(test_db_session)

        # Create designs linked to different sheets
        await repo.create(
            {
                "project_id": "project-1",
                "title": "Design 1",
                "system_type": "hvac",
                "calculation_sheet_id": 1,
                "loads": {},
                "equipment": {},
                "distribution": {},
                "sizing_results": {},
                "created_by": "user-123",
            }
        )
        await repo.create(
            {
                "project_id": "project-1",
                "title": "Design 2",
                "system_type": "electrical",
                "calculation_sheet_id": 2,
                "loads": {},
                "equipment": {},
                "distribution": {},
                "sizing_results": {},
                "created_by": "user-123",
            }
        )

        # Get designs for sheet 1
        results = await repo.get_by_calculation_sheet_id(1)

        assert len(results) >= 1
        assert all(r.calculation_sheet_id == 1 for r in results)

    async def test_get_by_status(self, test_db_session: AsyncSession):
        """Test retrieving designs by status."""
        repo = MEPDesignRepository(test_db_session)

        # Create designs with different statuses
        await repo.create(
            {
                "project_id": "project-1",
                "title": "Draft Design",
                "system_type": "hvac",
                "loads": {},
                "equipment": {},
                "distribution": {},
                "sizing_results": {},
                "created_by": "user-123",
                "status": "draft",
            }
        )
        await repo.create(
            {
                "project_id": "project-1",
                "title": "Approved Design",
                "system_type": "electrical",
                "loads": {},
                "equipment": {},
                "distribution": {},
                "sizing_results": {},
                "created_by": "user-123",
                "status": "approved",
            }
        )

        # Get draft designs
        results = await repo.get_by_status("draft")

        assert len(results) >= 1
        assert all(r.status == "draft" for r in results)

    async def test_get_by_created_by(self, test_db_session: AsyncSession):
        """Test retrieving designs by creator."""
        repo = MEPDesignRepository(test_db_session)

        # Create designs by different users
        await repo.create(
            {
                "project_id": "project-1",
                "title": "User 1 Design",
                "system_type": "hvac",
                "loads": {},
                "equipment": {},
                "distribution": {},
                "sizing_results": {},
                "created_by": "user-1",
            }
        )
        await repo.create(
            {
                "project_id": "project-1",
                "title": "User 2 Design",
                "system_type": "electrical",
                "loads": {},
                "equipment": {},
                "distribution": {},
                "sizing_results": {},
                "created_by": "user-2",
            }
        )

        # Get designs by user-1
        results = await repo.get_by_created_by("user-1")

        assert len(results) >= 1
        assert all(r.created_by == "user-1" for r in results)

    async def test_search_by_title(self, test_db_session: AsyncSession):
        """Test searching designs by title."""
        repo = MEPDesignRepository(test_db_session)

        # Create designs with different titles
        await repo.create(
            {
                "project_id": "project-1",
                "title": "Main HVAC System",
                "system_type": "hvac",
                "loads": {},
                "equipment": {},
                "distribution": {},
                "sizing_results": {},
                "created_by": "user-123",
            }
        )
        await repo.create(
            {
                "project_id": "project-1",
                "title": "Electrical Distribution",
                "system_type": "electrical",
                "loads": {},
                "equipment": {},
                "distribution": {},
                "sizing_results": {},
                "created_by": "user-123",
            }
        )

        # Search for "HVAC"
        results = await repo.search_by_title("HVAC")

        assert len(results) >= 1
        assert any("HVAC" in r.title for r in results)

    async def test_get_recent(self, test_db_session: AsyncSession):
        """Test retrieving recent designs."""
        repo = MEPDesignRepository(test_db_session)

        # Create designs
        for i in range(5):
            await repo.create(
                {
                    "project_id": "project-1",
                    "title": f"Design {i}",
                    "system_type": "hvac",
                    "loads": {},
                    "equipment": {},
                    "distribution": {},
                    "sizing_results": {},
                    "created_by": "user-123",
                }
            )

        # Get 3 most recent
        results = await repo.get_recent(limit=3)

        assert len(results) == 3
        # Should be ordered by created_at desc
        for i in range(len(results) - 1):
            assert results[i].created_at >= results[i + 1].created_at
