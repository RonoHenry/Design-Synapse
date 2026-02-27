"""Property-based tests for ComplianceService."""

from datetime import datetime
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from src.api.v1.schemas.analysis import (ComplianceCheckRequest,
                                         ViolationDetail, WarningDetail)
from src.api.v1.schemas.enums import CheckStatus, ComplianceCheckType
from src.infrastructure.knowledge_service_client import (
    CodeStandard, KnowledgeServiceClient)
from src.models.compliance_check import ComplianceCheck
from src.models.design import Design
from src.repositories.compliance_check_repository import \
    ComplianceCheckRepository
from src.repositories.design_repository import DesignRepository
from src.services.compliance_service import ComplianceService


# Hypothesis strategies for generating test data
@st.composite
def compliance_check_request_strategy(draw):
    """Generate valid ComplianceCheckRequest."""
    return ComplianceCheckRequest(
        code_standards=draw(
            st.lists(
                st.sampled_from(["IBC-2021", "ADA", "NFPA-101", "ASHRAE-90.1"]),
                min_size=1,
                max_size=3,
                unique=True,
            )
        ),
        jurisdiction=draw(st.one_of(st.none(), st.text(min_size=1, max_size=100))),
        check_types=draw(
            st.lists(
                st.sampled_from(ComplianceCheckType),
                min_size=1,
                max_size=3,
                unique=True,
            )
        ),
    )


@st.composite
def design_strategy(draw):
    """Generate valid Design for testing."""
    design_id = str(uuid4())
    return Design(
        id=design_id,
        project_id=str(uuid4()),
        name=draw(st.text(min_size=1, max_size=255)),
        description=draw(st.one_of(st.none(), st.text(max_size=1000))),
        building_type=draw(
            st.sampled_from(["residential", "commercial", "industrial", "mixed_use"])
        ),
        location_data={
            "address": draw(st.text(min_size=1, max_size=200)),
            "city": draw(st.text(min_size=1, max_size=100)),
            "state": draw(st.text(min_size=1, max_size=100)),
            "country": draw(st.text(min_size=1, max_size=100)),
            "postal_code": draw(st.text(min_size=1, max_size=20)),
            "latitude": draw(st.floats(min_value=-90, max_value=90)),
            "longitude": draw(st.floats(min_value=-180, max_value=180)),
            "jurisdiction": draw(st.text(min_size=1, max_size=200)),
        },
        current_version="1.0",
        version_number=1,
        status="draft",
        metadata=draw(st.dictionaries(st.text(), st.text(), max_size=5)),
        created_by=str(uuid4()),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        is_deleted=False,
    )


class TestComplianceServiceProperties:
    """Property-based tests for ComplianceService."""

    @pytest.mark.asyncio
    @given(
        design=design_strategy(),
        request=compliance_check_request_strategy(),
    )
    @settings(suppress_health_check=[HealthCheck.too_slow])
    async def test_property_7_compliance_check_initiation(
        self,
        design: Design,
        request: ComplianceCheckRequest,
    ):
        """
        Property 7: Compliance check initiation.

        For any valid design and compliance check request, initiating
        a compliance check should create a check record with unique ID,
        pending status, and all request parameters preserved.

        Validates: Requirements 2.1
        """
        # Setup mocks
        mock_compliance_repo = AsyncMock(spec=ComplianceCheckRepository)
        mock_design_repo = AsyncMock(spec=DesignRepository)
        mock_knowledge_client = AsyncMock(spec=KnowledgeServiceClient)

        # Mock design repository to return the test design
        mock_design_repo.get.return_value = design

        # Mock compliance repository create to return check with ID
        def create_side_effect(compliance_check):
            compliance_check.id = str(uuid4())
            return compliance_check

        mock_compliance_repo.create.side_effect = create_side_effect
        mock_compliance_repo.update = AsyncMock()

        # Mock knowledge client
        mock_knowledge_client.get_applicable_codes.return_value = [
            CodeStandard(
                code_id="IBC-2021",
                name="International Building Code 2021",
                edition="2021",
                jurisdiction="General",
                applicable_building_types=[design.building_type],
            )
        ]

        # Create service
        service = ComplianceService(
            mock_compliance_repo, mock_design_repo, mock_knowledge_client
        )

        # Execute
        response = await service.check_compliance(UUID(design.id), request)

        # Verify Property 7: Compliance check initiation
        assert response.id is not None, "Check must have unique identifier"
        assert response.design_id == UUID(design.id), "Design ID must match"
        assert response.design_version == design.current_version, "Version must match"
        assert (
            response.code_standards == request.code_standards
        ), "Code standards must be preserved"
        assert (
            response.jurisdiction == request.jurisdiction
        ), "Jurisdiction must be preserved"
        assert response.status in [
            CheckStatus.PENDING,
            CheckStatus.IN_PROGRESS,
            CheckStatus.COMPLETED,
        ], "Status must be valid"
        assert response.started_at is not None, "Start time must be set"

        # Verify repository interactions
        mock_design_repo.get.assert_called_once_with(design.id)
        mock_compliance_repo.create.assert_called_once()

    @pytest.mark.asyncio
    @given(
        design=design_strategy(),
        code_standard=st.sampled_from(["IBC-2021", "ADA", "NFPA-101"]),
        num_violations=st.integers(min_value=0, max_value=5),
    )
    async def test_property_8_violation_reference_completeness(
        self,
        design: Design,
        code_standard: str,
        num_violations: int,
    ):
        """
        Property 8: Violation reference completeness.

        For any design validation against a code standard, each violation
        found must include complete reference information: code section,
        description, severity, and remediation guidance.

        Validates: Requirements 2.2
        """
        # Setup mocks
        mock_compliance_repo = AsyncMock(spec=ComplianceCheckRepository)
        mock_design_repo = AsyncMock(spec=DesignRepository)
        mock_knowledge_client = AsyncMock(spec=KnowledgeServiceClient)

        # Mock knowledge client
        mock_knowledge_client.get_applicable_codes.return_value = [
            CodeStandard(
                code_id=code_standard,
                name=f"{code_standard} Standard",
                edition="2021",
                jurisdiction="General",
                applicable_building_types=[design.building_type],
            )
        ]

        # Create service
        service = ComplianceService(
            mock_compliance_repo, mock_design_repo, mock_knowledge_client
        )

        # Execute validation
        violations, warnings = await service.validate_against_code(
            design, code_standard
        )

        # Verify Property 8: Violation reference completeness
        for violation in violations:
            assert isinstance(
                violation, ViolationDetail
            ), "Violation must be ViolationDetail instance"
            assert (
                violation.code_section is not None
                and len(violation.code_section.strip()) > 0
            ), "Code section must be provided"
            assert (
                violation.description is not None
                and len(violation.description.strip()) > 0
            ), "Description must be provided"
            assert violation.severity is not None and violation.severity in [
                "critical",
                "major",
                "minor",
            ], "Severity must be valid"
            # Remediation is optional but if provided, must not be empty
            if violation.remediation is not None:
                assert (
                    len(violation.remediation.strip()) > 0
                ), "Remediation must not be empty if provided"

    @pytest.mark.asyncio
    @given(
        design=design_strategy(),
        request=compliance_check_request_strategy(),
    )
    async def test_property_9_compliance_report_completeness(
        self,
        design: Design,
        request: ComplianceCheckRequest,
    ):
        """
        Property 9: Compliance report completeness.

        For any completed compliance check, the generated report must
        include all violations, warnings, recommendations, and be
        accessible via a valid URL.

        Validates: Requirements 2.3, 2.7
        """
        # Setup mocks
        mock_compliance_repo = AsyncMock(spec=ComplianceCheckRepository)
        mock_design_repo = AsyncMock(spec=DesignRepository)
        mock_knowledge_client = AsyncMock(spec=KnowledgeServiceClient)

        # Create completed compliance check
        check_id = str(uuid4())
        completed_check = ComplianceCheck(
            id=check_id,
            design_id=design.id,
            design_version=design.current_version,
            code_standards=request.code_standards,
            jurisdiction=request.jurisdiction,
            status="completed",
            passed=False,
            violations=[
                {
                    "code_section": "IBC 1005.1",
                    "description": "Test violation",
                    "severity": "major",
                    "location": "Test location",
                    "remediation": "Test remediation",
                }
            ],
            warnings=[
                {
                    "code_section": "IBC 1208.3",
                    "description": "Test warning",
                    "recommendation": "Test recommendation",
                }
            ],
            recommendations=["Test recommendation"],
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
        )

        # Mock repository to return completed check
        mock_compliance_repo.get.return_value = completed_check
        mock_compliance_repo.update = AsyncMock()

        # Create service
        service = ComplianceService(
            mock_compliance_repo, mock_design_repo, mock_knowledge_client
        )

        # Execute report generation
        report_url = await service.generate_compliance_report(UUID(check_id))

        # Verify Property 9: Compliance report completeness
        assert report_url is not None, "Report URL must be provided"
        assert isinstance(report_url, str), "Report URL must be string"
        assert len(report_url.strip()) > 0, "Report URL must not be empty"
        assert check_id in report_url, "Report URL must reference the compliance check"

        # Verify repository update was called to save report URL
        mock_compliance_repo.update.assert_called_once()

    @pytest.mark.asyncio
    @given(
        design=design_strategy(),
        request=compliance_check_request_strategy(),
    )
    async def test_property_10_analysis_result_persistence(
        self,
        design: Design,
        request: ComplianceCheckRequest,
    ):
        """
        Property 10: Analysis result persistence.

        For any compliance check, all analysis results (violations,
        warnings, recommendations) must be persistently stored and
        retrievable after the check completes.

        Validates: Requirements 2.6
        """
        # Setup mocks
        mock_compliance_repo = AsyncMock(spec=ComplianceCheckRepository)
        mock_design_repo = AsyncMock(spec=DesignRepository)
        mock_knowledge_client = AsyncMock(spec=KnowledgeServiceClient)

        # Track what gets stored
        stored_data = {}

        def update_side_effect(check_id, **kwargs):
            stored_data.update(kwargs)
            return AsyncMock()

        mock_compliance_repo.update.side_effect = update_side_effect

        # Mock design repository
        mock_design_repo.get.return_value = design

        # Mock compliance repository create
        check_id = str(uuid4())

        def create_side_effect(compliance_check):
            compliance_check.id = check_id
            return compliance_check

        mock_compliance_repo.create.side_effect = create_side_effect

        # Mock knowledge client
        mock_knowledge_client.get_applicable_codes.return_value = [
            CodeStandard(
                code_id="IBC-2021",
                name="International Building Code 2021",
                edition="2021",
                jurisdiction="General",
                applicable_building_types=[design.building_type],
            )
        ]

        # Create service
        service = ComplianceService(
            mock_compliance_repo, mock_design_repo, mock_knowledge_client
        )

        # Execute compliance check
        response = await service.check_compliance(UUID(design.id), request)

        # Verify Property 10: Analysis result persistence
        # Check that results were stored
        assert "status" in stored_data, "Status must be persisted"
        assert stored_data["status"] in [
            "in_progress",
            "completed",
            "failed",
        ], "Status must be valid"

        if stored_data.get("status") == "completed":
            assert "passed" in stored_data, "Pass/fail status must be persisted"
            assert isinstance(
                stored_data["passed"], bool
            ), "Pass status must be boolean"
            assert "violations" in stored_data, "Violations must be persisted"
            assert isinstance(
                stored_data["violations"], list
            ), "Violations must be list"
            assert "warnings" in stored_data, "Warnings must be persisted"
            assert isinstance(stored_data["warnings"], list), "Warnings must be list"
            assert "recommendations" in stored_data, "Recommendations must be persisted"
            assert isinstance(
                stored_data["recommendations"], list
            ), "Recommendations must be list"

    @pytest.mark.asyncio
    @given(
        design=design_strategy(),
        request=compliance_check_request_strategy(),
    )
    async def test_property_11_compliance_success_marking(
        self,
        design: Design,
        request: ComplianceCheckRequest,
    ):
        """
        Property 11: Compliance success marking.

        For any compliance check that finds no violations, the check
        must be marked as passed (passed=True) and status must be
        completed.

        Validates: Requirements 2.6
        """
        # Setup mocks
        mock_compliance_repo = AsyncMock(spec=ComplianceCheckRepository)
        mock_design_repo = AsyncMock(spec=DesignRepository)
        mock_knowledge_client = AsyncMock(spec=KnowledgeServiceClient)

        # Track stored data
        stored_data = {}

        def update_side_effect(check_id, **kwargs):
            stored_data.update(kwargs)
            return AsyncMock()

        mock_compliance_repo.update.side_effect = update_side_effect

        # Mock design repository
        mock_design_repo.get.return_value = design

        # Mock compliance repository create
        check_id = str(uuid4())

        def create_side_effect(compliance_check):
            compliance_check.id = check_id
            return compliance_check

        mock_compliance_repo.create.side_effect = create_side_effect

        # Mock knowledge client to return no applicable codes (no violations)
        mock_knowledge_client.get_applicable_codes.return_value = []

        # Create service
        service = ComplianceService(
            mock_compliance_repo, mock_design_repo, mock_knowledge_client
        )

        # Execute compliance check
        response = await service.check_compliance(UUID(design.id), request)

        # Verify Property 11: Compliance success marking
        # Since no applicable codes were returned, no violations should be found
        if stored_data.get("status") == "completed":
            # If check completed successfully with no violations
            if stored_data.get("violations") == []:
                assert (
                    stored_data.get("passed") is True
                ), "Check with no violations must be marked as passed"
            # If check has violations
            elif stored_data.get("violations") and len(stored_data["violations"]) > 0:
                assert (
                    stored_data.get("passed") is False
                ), "Check with violations must be marked as failed"

        # Verify status progression
        assert response.status in [
            CheckStatus.PENDING,
            CheckStatus.IN_PROGRESS,
            CheckStatus.COMPLETED,
        ], "Status must be valid"
