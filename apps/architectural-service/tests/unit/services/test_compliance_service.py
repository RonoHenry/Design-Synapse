"""Unit tests for ComplianceService."""

from datetime import datetime
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from src.api.v1.schemas.analysis import ComplianceCheckRequest
from src.api.v1.schemas.enums import ComplianceCheckType
from src.core.exceptions import NotFoundError, ValidationError
from src.infrastructure.knowledge_service_client import (
    CodeStandard, KnowledgeServiceClient)
from src.models.compliance_check import ComplianceCheck
from src.models.design import Design
from src.repositories.compliance_check_repository import \
    ComplianceCheckRepository
from src.repositories.design_repository import DesignRepository
from src.services.compliance_service import ComplianceService


class TestComplianceService:
    """Unit tests for ComplianceService."""

    @pytest.fixture
    def mock_compliance_repo(self):
        """Mock compliance check repository."""
        return AsyncMock(spec=ComplianceCheckRepository)

    @pytest.fixture
    def mock_design_repo(self):
        """Mock design repository."""
        return AsyncMock(spec=DesignRepository)

    @pytest.fixture
    def mock_knowledge_client(self):
        """Mock knowledge service client."""
        return AsyncMock(spec=KnowledgeServiceClient)

    @pytest.fixture
    def compliance_service(
        self, mock_compliance_repo, mock_design_repo, mock_knowledge_client
    ):
        """ComplianceService instance with mocked dependencies."""
        return ComplianceService(
            mock_compliance_repo, mock_design_repo, mock_knowledge_client
        )

    @pytest.fixture
    def sample_design(self):
        """Sample design for testing."""
        return Design(
            id=str(uuid4()),
            project_id=str(uuid4()),
            name="Test Commercial Building",
            description="A test commercial building",
            building_type="commercial",
            location_data={
                "address": "123 Main St",
                "city": "San Francisco",
                "state": "California",
                "country": "USA",
                "postal_code": "94102",
                "latitude": 37.7749,
                "longitude": -122.4194,
                "jurisdiction": "City and County of San Francisco",
            },
            current_version="1.0",
            version_number=1,
            status="draft",
            metadata={},
            created_by=str(uuid4()),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            is_deleted=False,
        )

    @pytest.fixture
    def sample_request(self):
        """Sample compliance check request."""
        return ComplianceCheckRequest(
            code_standards=["IBC-2021", "ADA"],
            jurisdiction="City and County of San Francisco",
            check_types=[ComplianceCheckType.BUILDING_CODE],
        )

    @pytest.mark.asyncio
    async def test_check_compliance_design_not_found(
        self, compliance_service, mock_design_repo, sample_request
    ):
        """Test compliance check with non-existent design."""
        # Setup
        design_id = uuid4()
        mock_design_repo.get.return_value = None

        # Execute & Verify
        with pytest.raises(NotFoundError) as exc_info:
            await compliance_service.check_compliance(design_id, sample_request)

        assert f"Design {design_id} not found" in str(exc_info.value)
        mock_design_repo.get.assert_called_once_with(str(design_id))

    @pytest.mark.asyncio
    async def test_check_compliance_deleted_design(
        self, compliance_service, mock_design_repo, sample_design, sample_request
    ):
        """Test compliance check with deleted design."""
        # Setup
        sample_design.is_deleted = True
        mock_design_repo.get.return_value = sample_design

        # Execute & Verify
        with pytest.raises(ValidationError) as exc_info:
            await compliance_service.check_compliance(
                UUID(sample_design.id), sample_request
            )

        assert "Cannot check compliance for deleted design" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_check_compliance_success(
        self,
        compliance_service,
        mock_compliance_repo,
        mock_design_repo,
        mock_knowledge_client,
        sample_design,
        sample_request,
    ):
        """Test successful compliance check initiation."""
        # Setup
        mock_design_repo.get.return_value = sample_design

        def create_side_effect(compliance_check):
            compliance_check.id = str(uuid4())
            return compliance_check

        mock_compliance_repo.create.side_effect = create_side_effect
        mock_compliance_repo.update = AsyncMock()

        mock_knowledge_client.get_applicable_codes.return_value = [
            CodeStandard(
                code_id="IBC-2021",
                name="International Building Code 2021",
                edition="2021",
                jurisdiction="General",
                applicable_building_types=["commercial"],
            )
        ]

        # Execute
        response = await compliance_service.check_compliance(
            UUID(sample_design.id), sample_request
        )

        # Verify
        assert response.design_id == UUID(sample_design.id)
        assert response.design_version == sample_design.current_version
        assert response.code_standards == sample_request.code_standards
        assert response.jurisdiction == sample_request.jurisdiction
        assert response.started_at is not None

        mock_design_repo.get.assert_called_once_with(sample_design.id)
        mock_compliance_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_against_code_commercial_building(
        self, compliance_service, mock_knowledge_client, sample_design
    ):
        """Test code validation for commercial building with specific violations."""
        # Setup
        sample_design.building_type = "commercial"
        mock_knowledge_client.get_applicable_codes.return_value = [
            CodeStandard(
                code_id="IBC-2021",
                name="International Building Code 2021",
                edition="2021",
                jurisdiction="General",
                applicable_building_types=["commercial"],
            )
        ]

        # Execute
        violations, warnings = await compliance_service.validate_against_code(
            sample_design, "IBC-2021", "San Francisco"
        )

        # Verify
        assert len(violations) > 0, "Commercial buildings should have violations"

        # Check for egress width violation
        egress_violation = next(
            (v for v in violations if "egress width" in v.description.lower()), None
        )
        assert egress_violation is not None, "Should have egress width violation"
        assert egress_violation.code_section == "IBC 1005.1"
        assert egress_violation.severity == "major"
        assert egress_violation.remediation is not None

        # Verify warnings
        assert len(warnings) > 0, "Should have warnings"
        ventilation_warning = next(
            (w for w in warnings if "ventilation" in w.description.lower()), None
        )
        assert ventilation_warning is not None, "Should have ventilation warning"

    @pytest.mark.asyncio
    async def test_validate_against_code_residential_building(
        self, compliance_service, mock_knowledge_client, sample_design
    ):
        """Test code validation for residential building."""
        # Setup
        sample_design.building_type = "residential"
        mock_knowledge_client.get_applicable_codes.return_value = [
            CodeStandard(
                code_id="IBC-2021",
                name="International Building Code 2021",
                edition="2021",
                jurisdiction="General",
                applicable_building_types=["residential"],
            )
        ]

        # Execute
        violations, warnings = await compliance_service.validate_against_code(
            sample_design, "IBC-2021"
        )

        # Verify
        assert len(violations) > 0, "Residential buildings should have violations"

        # Check for fire separation violation
        fire_violation = next(
            (v for v in violations if "fire separation" in v.description.lower()), None
        )
        assert fire_violation is not None, "Should have fire separation violation"
        assert fire_violation.code_section == "IBC 706.3"
        assert fire_violation.severity == "critical"

    @pytest.mark.asyncio
    async def test_validate_against_code_mixed_use_building(
        self, compliance_service, mock_knowledge_client, sample_design
    ):
        """Test code validation for mixed-use building."""
        # Setup
        sample_design.building_type = "mixed_use"
        mock_knowledge_client.get_applicable_codes.return_value = [
            CodeStandard(
                code_id="IBC-2021",
                name="International Building Code 2021",
                edition="2021",
                jurisdiction="General",
                applicable_building_types=["mixed_use"],
            )
        ]

        # Execute
        violations, warnings = await compliance_service.validate_against_code(
            sample_design, "IBC-2021"
        )

        # Verify
        assert len(violations) > 0, "Mixed-use buildings should have violations"

        # Check for fire separation violation (mixed-use should trigger this)
        fire_violation = next(
            (v for v in violations if "fire separation" in v.description.lower()), None
        )
        assert fire_violation is not None, "Should have fire separation violation"

    @pytest.mark.asyncio
    async def test_validate_against_code_ada_accessibility(
        self, compliance_service, mock_knowledge_client, sample_design
    ):
        """Test ADA accessibility code validation."""
        # Setup
        mock_knowledge_client.get_applicable_codes.return_value = [
            CodeStandard(
                code_id="ADA",
                name="Americans with Disabilities Act",
                edition="2010",
                jurisdiction="Federal",
                applicable_building_types=["commercial"],
            )
        ]

        # Execute
        violations, warnings = await compliance_service.validate_against_code(
            sample_design, "ADA"
        )

        # Verify
        assert len(violations) > 0, "ADA validation should find violations"

        # Check for door opening force violation
        door_violation = next(
            (v for v in violations if "door opening force" in v.description.lower()),
            None,
        )
        assert door_violation is not None, "Should have door opening force violation"
        assert door_violation.code_section == "ADA 404.2.3"
        assert door_violation.severity == "major"

    @pytest.mark.asyncio
    async def test_validate_against_code_no_applicable_codes(
        self, compliance_service, mock_knowledge_client, sample_design
    ):
        """Test validation when no applicable codes are found."""
        # Setup
        mock_knowledge_client.get_applicable_codes.return_value = []

        # Execute
        violations, warnings = await compliance_service.validate_against_code(
            sample_design, "UNKNOWN-CODE"
        )

        # Verify
        assert len(violations) == 0, "No violations should be found"
        assert len(warnings) == 0, "No warnings should be found"

    @pytest.mark.asyncio
    async def test_validate_against_code_jurisdiction_specific(
        self, compliance_service, mock_knowledge_client, sample_design
    ):
        """Test validation with jurisdiction-specific requirements."""
        # Setup
        jurisdiction = "City and County of San Francisco"
        mock_knowledge_client.get_applicable_codes.return_value = [
            CodeStandard(
                code_id="IBC-2021",
                name="International Building Code 2021",
                edition="2021",
                jurisdiction=jurisdiction,
                applicable_building_types=["commercial"],
            )
        ]

        # Execute
        violations, warnings = await compliance_service.validate_against_code(
            sample_design, "IBC-2021", jurisdiction
        )

        # Verify knowledge client was called with correct parameters
        mock_knowledge_client.get_applicable_codes.assert_called_once()
        call_args = mock_knowledge_client.get_applicable_codes.call_args
        # The location should contain the extracted location string from design
        location_arg = call_args[1]["location"]
        assert "San Francisco" in location_arg  # Should contain city from design
        assert call_args[1]["building_type"] == sample_design.building_type

    @pytest.mark.asyncio
    async def test_get_check_results_not_found(
        self, compliance_service, mock_compliance_repo
    ):
        """Test getting results for non-existent compliance check."""
        # Setup
        check_id = uuid4()
        mock_compliance_repo.get.return_value = None

        # Execute & Verify
        with pytest.raises(NotFoundError) as exc_info:
            await compliance_service.get_check_results(check_id)

        assert f"Compliance check {check_id} not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_check_results_success(
        self, compliance_service, mock_compliance_repo
    ):
        """Test successful retrieval of compliance check results."""
        # Setup
        check_id = uuid4()
        compliance_check = ComplianceCheck(
            id=str(check_id),
            design_id=str(uuid4()),
            design_version="1.0",
            code_standards=["IBC-2021"],
            jurisdiction="San Francisco",
            status="completed",
            passed=True,
            violations=[],
            warnings=[],
            recommendations=[],
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
        )
        mock_compliance_repo.get.return_value = compliance_check

        # Execute
        response = await compliance_service.get_check_results(check_id)

        # Verify
        assert response.id == check_id
        assert response.status == "completed"  # status is a string, not enum
        assert response.passed is True
        assert len(response.violations) == 0
        assert len(response.warnings) == 0

    @pytest.mark.asyncio
    async def test_generate_compliance_report_not_found(
        self, compliance_service, mock_compliance_repo
    ):
        """Test report generation for non-existent compliance check."""
        # Setup
        check_id = uuid4()
        mock_compliance_repo.get.return_value = None

        # Execute & Verify
        with pytest.raises(NotFoundError) as exc_info:
            await compliance_service.generate_compliance_report(check_id)

        assert f"Compliance check {check_id} not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_generate_compliance_report_not_completed(
        self, compliance_service, mock_compliance_repo
    ):
        """Test report generation for incomplete compliance check."""
        # Setup
        check_id = uuid4()
        compliance_check = ComplianceCheck(
            id=str(check_id),
            design_id=str(uuid4()),
            design_version="1.0",
            code_standards=["IBC-2021"],
            status="pending",  # Not completed
            violations=[],
            warnings=[],
            recommendations=[],
            started_at=datetime.utcnow(),
        )
        mock_compliance_repo.get.return_value = compliance_check

        # Execute & Verify
        with pytest.raises(ValidationError) as exc_info:
            await compliance_service.generate_compliance_report(check_id)

        assert "Cannot generate report for incomplete check" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_generate_compliance_report_success(
        self, compliance_service, mock_compliance_repo
    ):
        """Test successful compliance report generation."""
        # Setup
        check_id = uuid4()
        compliance_check = ComplianceCheck(
            id=str(check_id),
            design_id=str(uuid4()),
            design_version="1.0",
            code_standards=["IBC-2021"],
            status="completed",
            passed=False,
            violations=[
                {
                    "code_section": "IBC 1005.1",
                    "description": "Test violation",
                    "severity": "major",
                }
            ],
            warnings=[],
            recommendations=["Fix violations"],
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
        )
        mock_compliance_repo.get.return_value = compliance_check
        mock_compliance_repo.update = AsyncMock()

        # Execute
        report_url = await compliance_service.generate_compliance_report(check_id)

        # Verify
        assert report_url is not None
        assert str(check_id) in report_url
        assert report_url.endswith(".pdf")

        # Verify repository update was called
        mock_compliance_repo.update.assert_called_once()
        update_call = mock_compliance_repo.update.call_args
        assert update_call[0][0] == str(check_id)
        assert "report_url" in update_call[1]

    def test_generate_recommendations_no_violations(self, compliance_service):
        """Test recommendation generation with no violations."""
        # Execute
        recommendations = compliance_service._generate_recommendations([])

        # Verify
        assert len(recommendations) == 0, "No recommendations for no violations"

    def test_generate_recommendations_with_violations(self, compliance_service):
        """Test recommendation generation with violations."""
        # Setup
        from src.api.v1.schemas.analysis import ViolationDetail

        violations = [
            ViolationDetail(
                code_section="IBC 1005.1",
                description="Test violation",
                severity="major",
            ),
            ViolationDetail(
                code_section="IBC 706.3",
                description="Critical violation",
                severity="critical",
            ),
        ]

        # Execute
        recommendations = compliance_service._generate_recommendations(violations)

        # Verify
        assert len(recommendations) > 0, "Should have recommendations for violations"
        assert any(
            "licensed architect" in rec.lower() for rec in recommendations
        ), "Should recommend architect review"
        assert any(
            "building department" in rec.lower() for rec in recommendations
        ), "Should recommend building department consultation"
        assert any(
            "critical violations" in rec.lower() for rec in recommendations
        ), "Should address critical violations"

    def test_extract_location_string_complete_data(
        self, compliance_service, sample_design
    ):
        """Test location string extraction with complete location data."""
        # Execute
        location = compliance_service._extract_location_string(sample_design)

        # Verify
        assert location is not None
        assert "San Francisco" in location
        assert "California" in location
        assert "USA" in location

    def test_extract_location_string_partial_data(
        self, compliance_service, sample_design
    ):
        """Test location string extraction with partial location data."""
        # Setup
        sample_design.location_data = {"city": "San Francisco", "state": "California"}

        # Execute
        location = compliance_service._extract_location_string(sample_design)

        # Verify
        assert location == "San Francisco, California"

    def test_extract_location_string_no_data(self, compliance_service, sample_design):
        """Test location string extraction with no location data."""
        # Setup
        sample_design.location_data = None

        # Execute
        location = compliance_service._extract_location_string(sample_design)

        # Verify
        assert location is None

    def test_extract_location_string_empty_data(
        self, compliance_service, sample_design
    ):
        """Test location string extraction with empty location data."""
        # Setup
        sample_design.location_data = {}

        # Execute
        location = compliance_service._extract_location_string(sample_design)

        # Verify
        assert location is None
