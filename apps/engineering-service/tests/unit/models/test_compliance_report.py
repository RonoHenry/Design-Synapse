"""Unit tests for ComplianceReport model."""

from datetime import datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.compliance_report import ComplianceReport


class TestComplianceReportModel:
    """Test suite for ComplianceReport model."""

    @pytest.mark.asyncio
    async def test_create_compliance_report(self, test_db_session: AsyncSession):
        """Test creating a compliance report."""
        report = ComplianceReport(
            project_id="proj_123",
            title="Structural Code Compliance",
            description="IBC compliance check for beam design",
            code_type="structural",
            jurisdiction="California",
            code_version="IBC 2021",
            checks_performed={
                "strength_check": "passed",
                "deflection_check": "passed",
                "connection_check": "passed",
            },
            violations={},
            overall_status="compliant",
            generated_by="user_123",
        )

        test_db_session.add(report)
        await test_db_session.commit()
        await test_db_session.refresh(report)

        assert report.id is not None
        assert report.code_type == "structural"
        assert report.jurisdiction == "California"
        assert report.overall_status == "compliant"
        assert len(report.violations) == 0

    @pytest.mark.asyncio
    async def test_compliance_report_with_violations(
        self, test_db_session: AsyncSession
    ):
        """Test compliance report with code violations."""
        report = ComplianceReport(
            project_id="proj_123",
            title="MEP Code Compliance",
            code_type="mep",
            jurisdiction="New York",
            code_version="NEC 2020",
            checks_performed={
                "circuit_sizing": "failed",
                "grounding": "passed",
                "protection": "failed",
            },
            violations={
                "circuit_sizing": {
                    "code_section": "NEC 210.19",
                    "description": "Circuit undersized for load",
                    "severity": "critical",
                },
                "protection": {
                    "code_section": "NEC 240.4",
                    "description": "Overcurrent protection inadequate",
                    "severity": "major",
                },
            },
            recommendations={
                "circuit_sizing": "Increase conductor size to #10 AWG",
                "protection": "Install 30A breaker",
            },
            overall_status="non_compliant",
            generated_by="user_123",
        )

        test_db_session.add(report)
        await test_db_session.commit()
        await test_db_session.refresh(report)

        assert report.overall_status == "non_compliant"
        assert len(report.violations) == 2
        assert "circuit_sizing" in report.violations
        assert report.violations["circuit_sizing"]["severity"] == "critical"

    @pytest.mark.asyncio
    async def test_compliance_report_code_types(self, test_db_session: AsyncSession):
        """Test different code types."""
        code_types = ["structural", "mep", "energy", "fire"]

        for code_type in code_types:
            report = ComplianceReport(
                project_id="proj_123",
                title=f"{code_type.title()} Compliance",
                code_type=code_type,
                jurisdiction="Test Jurisdiction",
                code_version="2021",
                checks_performed={"check1": "passed"},
                violations={},
                overall_status="compliant",
                generated_by="user_123",
            )

            test_db_session.add(report)
            await test_db_session.commit()
            await test_db_session.refresh(report)

            assert report.code_type == code_type
            await test_db_session.rollback()

    @pytest.mark.asyncio
    async def test_compliance_report_review_workflow(
        self, test_db_session: AsyncSession
    ):
        """Test review workflow."""
        report = ComplianceReport(
            project_id="proj_123",
            title="Energy Code Review",
            code_type="energy",
            jurisdiction="Texas",
            code_version="IECC 2021",
            checks_performed={"insulation": "review_required"},
            violations={},
            overall_status="review_required",
            generated_by="user_123",
        )

        test_db_session.add(report)
        await test_db_session.commit()
        await test_db_session.refresh(report)

        assert report.reviewed_by is None
        assert report.reviewed_at is None

        # Simulate review
        report.reviewed_by = "reviewer_456"
        report.reviewed_at = datetime.utcnow()
        report.overall_status = "compliant"
        await test_db_session.commit()
        await test_db_session.refresh(report)

        assert report.reviewed_by == "reviewer_456"
        assert report.reviewed_at is not None
        assert report.overall_status == "compliant"

    @pytest.mark.asyncio
    async def test_compliance_report_string_representation(
        self, test_db_session: AsyncSession
    ):
        """Test string representation."""
        report = ComplianceReport(
            project_id="proj_123",
            title="Fire Code Compliance",
            code_type="fire",
            jurisdiction="Florida",
            code_version="NFPA 13 2019",
            checks_performed={"sprinkler_coverage": "passed"},
            violations={},
            overall_status="compliant",
            generated_by="user_123",
        )

        test_db_session.add(report)
        await test_db_session.commit()
        await test_db_session.refresh(report)

        str_repr = str(report)
        assert "Fire Code Compliance" in str_repr
        assert "fire" in str_repr
        assert "Florida" in str_repr
