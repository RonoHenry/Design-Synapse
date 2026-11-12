"""Unit tests for ComplianceReportRepository."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from src.repositories.compliance_report_repository import \
    ComplianceReportRepository


@pytest.mark.asyncio
class TestComplianceReportRepository:
    """Test suite for ComplianceReportRepository."""

    async def test_get_by_project_id(self, test_db_session: AsyncSession):
        """Test retrieving compliance reports by project ID."""
        repo = ComplianceReportRepository(test_db_session)

        await repo.create(
            {
                "project_id": "project-1",
                "title": "Structural Compliance",
                "code_type": "structural",
                "jurisdiction": "California",
                "code_version": "2021",
                "checks_performed": {"check1": "pass"},
                "violations": {},
                "overall_status": "compliant",
                "generated_by": "user-123",
            }
        )

        results = await repo.get_by_project_id("project-1")

        assert len(results) >= 1
        assert all(r.project_id == "project-1" for r in results)

    async def test_get_by_code_type(self, test_db_session: AsyncSession):
        """Test retrieving reports by code type."""
        repo = ComplianceReportRepository(test_db_session)

        await repo.create(
            {
                "project_id": "project-1",
                "title": "Structural Report",
                "code_type": "structural",
                "jurisdiction": "California",
                "code_version": "2021",
                "checks_performed": {},
                "violations": {},
                "overall_status": "compliant",
                "generated_by": "user-123",
            }
        )
        await repo.create(
            {
                "project_id": "project-1",
                "title": "MEP Report",
                "code_type": "mep",
                "jurisdiction": "California",
                "code_version": "2021",
                "checks_performed": {},
                "violations": {},
                "overall_status": "compliant",
                "generated_by": "user-123",
            }
        )

        results = await repo.get_by_code_type("structural")

        assert len(results) >= 1
        assert all(r.code_type == "structural" for r in results)

    async def test_get_by_project_and_code_type(self, test_db_session: AsyncSession):
        """Test retrieving reports by project and code type."""
        repo = ComplianceReportRepository(test_db_session)

        await repo.create(
            {
                "project_id": "project-1",
                "title": "P1 Structural",
                "code_type": "structural",
                "jurisdiction": "California",
                "code_version": "2021",
                "checks_performed": {},
                "violations": {},
                "overall_status": "compliant",
                "generated_by": "user-123",
            }
        )
        await repo.create(
            {
                "project_id": "project-2",
                "title": "P2 Structural",
                "code_type": "structural",
                "jurisdiction": "California",
                "code_version": "2021",
                "checks_performed": {},
                "violations": {},
                "overall_status": "compliant",
                "generated_by": "user-123",
            }
        )

        results = await repo.get_by_project_and_code_type("project-1", "structural")

        assert len(results) >= 1
        assert all(
            r.project_id == "project-1" and r.code_type == "structural" for r in results
        )

    async def test_get_by_overall_status(self, test_db_session: AsyncSession):
        """Test retrieving reports by status."""
        repo = ComplianceReportRepository(test_db_session)

        await repo.create(
            {
                "project_id": "project-1",
                "title": "Compliant Report",
                "code_type": "structural",
                "jurisdiction": "California",
                "code_version": "2021",
                "checks_performed": {},
                "violations": {},
                "overall_status": "compliant",
                "generated_by": "user-123",
            }
        )
        await repo.create(
            {
                "project_id": "project-1",
                "title": "Non-Compliant Report",
                "code_type": "mep",
                "jurisdiction": "California",
                "code_version": "2021",
                "checks_performed": {},
                "violations": {"v1": "issue"},
                "overall_status": "non_compliant",
                "generated_by": "user-123",
            }
        )

        results = await repo.get_by_overall_status("compliant")

        assert len(results) >= 1
        assert all(r.overall_status == "compliant" for r in results)

    async def test_get_non_compliant_reports(self, test_db_session: AsyncSession):
        """Test retrieving non-compliant reports."""
        repo = ComplianceReportRepository(test_db_session)

        await repo.create(
            {
                "project_id": "project-1",
                "title": "Non-Compliant",
                "code_type": "structural",
                "jurisdiction": "California",
                "code_version": "2021",
                "checks_performed": {},
                "violations": {"v1": "issue"},
                "overall_status": "non_compliant",
                "generated_by": "user-123",
            }
        )

        results = await repo.get_non_compliant_reports()

        assert len(results) >= 1
        assert all(r.overall_status == "non_compliant" for r in results)

    async def test_get_pending_review_reports(self, test_db_session: AsyncSession):
        """Test retrieving reports pending review."""
        repo = ComplianceReportRepository(test_db_session)

        await repo.create(
            {
                "project_id": "project-1",
                "title": "Pending Review",
                "code_type": "structural",
                "jurisdiction": "California",
                "code_version": "2021",
                "checks_performed": {},
                "violations": {},
                "overall_status": "review_required",
                "generated_by": "user-123",
            }
        )

        results = await repo.get_pending_review_reports()

        assert len(results) >= 1
        assert all(r.overall_status == "review_required" for r in results)

    async def test_search_by_title(self, test_db_session: AsyncSession):
        """Test searching reports by title."""
        repo = ComplianceReportRepository(test_db_session)

        await repo.create(
            {
                "project_id": "project-1",
                "title": "Structural Code Compliance",
                "code_type": "structural",
                "jurisdiction": "California",
                "code_version": "2021",
                "checks_performed": {},
                "violations": {},
                "overall_status": "compliant",
                "generated_by": "user-123",
            }
        )

        results = await repo.search_by_title("Structural")

        assert len(results) >= 1
        assert any("Structural" in r.title for r in results)

    async def test_get_recent(self, test_db_session: AsyncSession):
        """Test retrieving recent reports."""
        repo = ComplianceReportRepository(test_db_session)

        for i in range(5):
            await repo.create(
                {
                    "project_id": "project-1",
                    "title": f"Report {i}",
                    "code_type": "structural",
                    "jurisdiction": "California",
                    "code_version": "2021",
                    "checks_performed": {},
                    "violations": {},
                    "overall_status": "compliant",
                    "generated_by": "user-123",
                }
            )

        results = await repo.get_recent(limit=3)

        assert len(results) == 3
        for i in range(len(results) - 1):
            assert results[i].generated_at >= results[i + 1].generated_at
