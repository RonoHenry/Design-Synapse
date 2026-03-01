"""Unit tests for StructuralDesignRepository."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from src.repositories.structural_design_repository import \
    StructuralDesignRepository


@pytest.mark.asyncio
class TestStructuralDesignRepository:
    """Test suite for StructuralDesignRepository."""

    async def test_get_by_project_id(self, test_db_session: AsyncSession):
        """Test retrieving structural designs by project ID."""
        repo = StructuralDesignRepository(test_db_session)

        # Create designs for different projects
        await repo.create(
            {
                "project_id": "project-1",
                "title": "Project 1 Beam",
                "design_type": "beam",
                "loads": {"dead": 100, "live": 50},
                "material_properties": {"type": "steel"},
                "geometry": {"length": 20},
                "design_results": {"section": "W12x26"},
                "stress_ratios": {"bending": 0.85},
                "created_by": "user-123",
            }
        )
        await repo.create(
            {
                "project_id": "project-2",
                "title": "Project 2 Column",
                "design_type": "column",
                "loads": {"axial": 200},
                "material_properties": {"type": "concrete"},
                "geometry": {"height": 12},
                "design_results": {"section": "12x12"},
                "stress_ratios": {"axial": 0.75},
                "created_by": "user-123",
            }
        )

        # Get designs for project-1
        results = await repo.get_by_project_id("project-1")

        assert len(results) >= 1
        assert all(r.project_id == "project-1" for r in results)

    async def test_get_by_design_type(self, test_db_session: AsyncSession):
        """Test retrieving designs by type."""
        repo = StructuralDesignRepository(test_db_session)

        # Create designs of different types
        await repo.create(
            {
                "project_id": "project-1",
                "title": "Beam Design",
                "design_type": "beam",
                "loads": {},
                "material_properties": {},
                "geometry": {},
                "design_results": {},
                "stress_ratios": {},
                "created_by": "user-123",
            }
        )
        await repo.create(
            {
                "project_id": "project-1",
                "title": "Column Design",
                "design_type": "column",
                "loads": {},
                "material_properties": {},
                "geometry": {},
                "design_results": {},
                "stress_ratios": {},
                "created_by": "user-123",
            }
        )

        # Get beam designs
        results = await repo.get_by_design_type("beam")

        assert len(results) >= 1
        assert all(r.design_type == "beam" for r in results)

    async def test_get_by_project_and_type(self, test_db_session: AsyncSession):
        """Test retrieving designs by project and type."""
        repo = StructuralDesignRepository(test_db_session)

        # Create designs
        await repo.create(
            {
                "project_id": "project-1",
                "title": "P1 Beam",
                "design_type": "beam",
                "loads": {},
                "material_properties": {},
                "geometry": {},
                "design_results": {},
                "stress_ratios": {},
                "created_by": "user-123",
            }
        )
        await repo.create(
            {
                "project_id": "project-1",
                "title": "P1 Column",
                "design_type": "column",
                "loads": {},
                "material_properties": {},
                "geometry": {},
                "design_results": {},
                "stress_ratios": {},
                "created_by": "user-123",
            }
        )
        await repo.create(
            {
                "project_id": "project-2",
                "title": "P2 Beam",
                "design_type": "beam",
                "loads": {},
                "material_properties": {},
                "geometry": {},
                "design_results": {},
                "stress_ratios": {},
                "created_by": "user-123",
            }
        )

        # Get project-1 beam designs
        results = await repo.get_by_project_and_type("project-1", "beam")

        assert len(results) >= 1
        assert all(
            r.project_id == "project-1" and r.design_type == "beam" for r in results
        )

    async def test_get_by_calculation_sheet_id(self, test_db_session: AsyncSession):
        """Test retrieving designs by calculation sheet ID."""
        repo = StructuralDesignRepository(test_db_session)

        # Create designs linked to different sheets
        await repo.create(
            {
                "project_id": "project-1",
                "title": "Design 1",
                "design_type": "beam",
                "calculation_sheet_id": 1,
                "loads": {},
                "material_properties": {},
                "geometry": {},
                "design_results": {},
                "stress_ratios": {},
                "created_by": "user-123",
            }
        )
        await repo.create(
            {
                "project_id": "project-1",
                "title": "Design 2",
                "design_type": "column",
                "calculation_sheet_id": 2,
                "loads": {},
                "material_properties": {},
                "geometry": {},
                "design_results": {},
                "stress_ratios": {},
                "created_by": "user-123",
            }
        )

        # Get designs for sheet 1
        results = await repo.get_by_calculation_sheet_id(1)

        assert len(results) >= 1
        assert all(r.calculation_sheet_id == 1 for r in results)

    async def test_get_by_status(self, test_db_session: AsyncSession):
        """Test retrieving designs by status."""
        repo = StructuralDesignRepository(test_db_session)

        # Create designs with different statuses
        await repo.create(
            {
                "project_id": "project-1",
                "title": "Draft Design",
                "design_type": "beam",
                "loads": {},
                "material_properties": {},
                "geometry": {},
                "design_results": {},
                "stress_ratios": {},
                "created_by": "user-123",
                "status": "draft",
            }
        )
        await repo.create(
            {
                "project_id": "project-1",
                "title": "Approved Design",
                "design_type": "column",
                "loads": {},
                "material_properties": {},
                "geometry": {},
                "design_results": {},
                "stress_ratios": {},
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
        repo = StructuralDesignRepository(test_db_session)

        # Create designs by different users
        await repo.create(
            {
                "project_id": "project-1",
                "title": "User 1 Design",
                "design_type": "beam",
                "loads": {},
                "material_properties": {},
                "geometry": {},
                "design_results": {},
                "stress_ratios": {},
                "created_by": "user-1",
            }
        )
        await repo.create(
            {
                "project_id": "project-1",
                "title": "User 2 Design",
                "design_type": "column",
                "loads": {},
                "material_properties": {},
                "geometry": {},
                "design_results": {},
                "stress_ratios": {},
                "created_by": "user-2",
            }
        )

        # Get designs by user-1
        results = await repo.get_by_created_by("user-1")

        assert len(results) >= 1
        assert all(r.created_by == "user-1" for r in results)

    async def test_search_by_title(self, test_db_session: AsyncSession):
        """Test searching designs by title."""
        repo = StructuralDesignRepository(test_db_session)

        # Create designs with different titles
        await repo.create(
            {
                "project_id": "project-1",
                "title": "Main Beam Design",
                "design_type": "beam",
                "loads": {},
                "material_properties": {},
                "geometry": {},
                "design_results": {},
                "stress_ratios": {},
                "created_by": "user-123",
            }
        )
        await repo.create(
            {
                "project_id": "project-1",
                "title": "Support Column Design",
                "design_type": "column",
                "loads": {},
                "material_properties": {},
                "geometry": {},
                "design_results": {},
                "stress_ratios": {},
                "created_by": "user-123",
            }
        )

        # Search for "Beam"
        results = await repo.search_by_title("Beam")

        assert len(results) >= 1
        assert any("Beam" in r.title for r in results)

    async def test_get_recent(self, test_db_session: AsyncSession):
        """Test retrieving recent designs."""
        repo = StructuralDesignRepository(test_db_session)

        # Create designs
        for i in range(5):
            await repo.create(
                {
                    "project_id": "project-1",
                    "title": f"Design {i}",
                    "design_type": "beam",
                    "loads": {},
                    "material_properties": {},
                    "geometry": {},
                    "design_results": {},
                    "stress_ratios": {},
                    "created_by": "user-123",
                }
            )

        # Get 3 most recent
        results = await repo.get_recent(limit=3)

        assert len(results) == 3
        # Should be ordered by created_at desc
        for i in range(len(results) - 1):
            assert results[i].created_at >= results[i + 1].created_at
