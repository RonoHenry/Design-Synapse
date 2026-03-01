"""Unit tests for CivilDesignRepository."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from src.repositories.civil_design_repository import CivilDesignRepository


@pytest.mark.asyncio
class TestCivilDesignRepository:
    """Test suite for CivilDesignRepository."""

    async def test_get_by_project_id(self, test_db_session: AsyncSession):
        """Test retrieving civil designs by project ID."""
        repo = CivilDesignRepository(test_db_session)

        await repo.create(
            {
                "project_id": "project-1",
                "title": "Site Grading",
                "design_type": "grading",
                "site_parameters": {"area": 5000},
                "design_criteria": {"slope": 2},
                "design_results": {"cut": 100, "fill": 150},
                "created_by": "user-123",
            }
        )

        results = await repo.get_by_project_id("project-1")

        assert len(results) >= 1
        assert all(r.project_id == "project-1" for r in results)

    async def test_get_by_design_type(self, test_db_session: AsyncSession):
        """Test retrieving designs by type."""
        repo = CivilDesignRepository(test_db_session)

        await repo.create(
            {
                "project_id": "project-1",
                "title": "Grading Design",
                "design_type": "grading",
                "site_parameters": {},
                "design_criteria": {},
                "design_results": {},
                "created_by": "user-123",
            }
        )
        await repo.create(
            {
                "project_id": "project-1",
                "title": "Stormwater Design",
                "design_type": "stormwater",
                "site_parameters": {},
                "design_criteria": {},
                "design_results": {},
                "created_by": "user-123",
            }
        )

        results = await repo.get_by_design_type("grading")

        assert len(results) >= 1
        assert all(r.design_type == "grading" for r in results)

    async def test_get_by_project_and_type(self, test_db_session: AsyncSession):
        """Test retrieving designs by project and type."""
        repo = CivilDesignRepository(test_db_session)

        await repo.create(
            {
                "project_id": "project-1",
                "title": "P1 Grading",
                "design_type": "grading",
                "site_parameters": {},
                "design_criteria": {},
                "design_results": {},
                "created_by": "user-123",
            }
        )
        await repo.create(
            {
                "project_id": "project-2",
                "title": "P2 Grading",
                "design_type": "grading",
                "site_parameters": {},
                "design_criteria": {},
                "design_results": {},
                "created_by": "user-123",
            }
        )

        results = await repo.get_by_project_and_type("project-1", "grading")

        assert len(results) >= 1
        assert all(
            r.project_id == "project-1" and r.design_type == "grading" for r in results
        )

    async def test_search_by_title(self, test_db_session: AsyncSession):
        """Test searching designs by title."""
        repo = CivilDesignRepository(test_db_session)

        await repo.create(
            {
                "project_id": "project-1",
                "title": "Site Grading Plan",
                "design_type": "grading",
                "site_parameters": {},
                "design_criteria": {},
                "design_results": {},
                "created_by": "user-123",
            }
        )

        results = await repo.search_by_title("Grading")

        assert len(results) >= 1
        assert any("Grading" in r.title for r in results)

    async def test_get_recent(self, test_db_session: AsyncSession):
        """Test retrieving recent designs."""
        repo = CivilDesignRepository(test_db_session)

        for i in range(5):
            await repo.create(
                {
                    "project_id": "project-1",
                    "title": f"Design {i}",
                    "design_type": "grading",
                    "site_parameters": {},
                    "design_criteria": {},
                    "design_results": {},
                    "created_by": "user-123",
                }
            )

        results = await repo.get_recent(limit=3)

        assert len(results) == 3
        for i in range(len(results) - 1):
            assert results[i].created_at >= results[i + 1].created_at
