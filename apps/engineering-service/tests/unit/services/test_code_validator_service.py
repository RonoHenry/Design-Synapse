"""Unit tests for CodeValidatorService."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from src.api.v1.schemas.compliance import (CodeType, ComplianceStatus,
                                           ViolationSeverity)
from src.models.compliance_report import ComplianceReport
from src.models.mep_design import MEPDesign
from src.models.structural_design import StructuralDesign
from src.services.code_validator_service import CodeValidatorService


class TestCodeValidatorService:
    """Test cases for CodeValidatorService."""

    @pytest.fixture
    def mock_compliance_repo(self):
        """Mock compliance report repository."""
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def mock_structural_repo(self):
        """Mock structural design repository."""
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def mock_mep_repo(self):
        """Mock MEP design repository."""
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def mock_knowledge_client(self):
        """Mock knowledge service client."""
        client = AsyncMock()
        return client

    @pytest.fixture
    def code_validator_service(
        self,
        mock_compliance_repo,
        mock_structural_repo,
        mock_mep_repo,
        mock_knowledge_client,
    ):
        """Create CodeValidatorService instance with mocked dependencies."""
        return CodeValidatorService(
            compliance_repo=mock_compliance_repo,
            structural_repo=mock_structural_repo,
            mep_repo=mock_mep_repo,
            knowledge_client=mock_knowledge_client,
        )

    @pytest.fixture
    def sample_structural_design(self):
        """Sample structural design for testing."""
        return StructuralDesign(
            id=1,
            project_id="550e8400-e29b-41d4-a716-446655440000",
            calculation_sheet_id=1,
            title="Beam Design",
            description="W18x50 beam design",
            design_type="beam",
            loads={
                "dead_load": 50.0,
                "live_load": 40.0,
                "load_combinations": ["1.4D", "1.2D + 1.6L"],
            },
            material_properties={"steel_grade": "A992", "fy": 50.0},
            geometry={"span": 20.0, "section": "W18x50"},
            design_results={
                "required_section": "W18x50",
                "deflection_ratio": 400,
                "seismic_design_category": "D",
            },
            stress_ratios={"bending": 0.85, "shear": 0.45},
            status="draft",
            created_by="550e8400-e29b-41d4-a716-446655440001",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

    @pytest.fixture
    def sample_mep_design_hvac(self):
        """Sample HVAC MEP design for testing."""
        return MEPDesign(
            id=1,
            project_id="550e8400-e29b-41d4-a716-446655440000",
            calculation_sheet_id=1,
            title="HVAC System Design",
            description="Building HVAC system",
            system_type="hvac",
            loads={"heating_load": 100000, "cooling_load": 120000},
            equipment={"type": "heat_pump", "efficiency": 14.0},
            distribution={"duct_type": "rectangular"},
            sizing_results={
                "equipment_size": "5_ton",
                "ventilation_rate": 20,
                "duct_velocity": 1800,
            },
            status="draft",
            created_by="550e8400-e29b-41d4-a716-446655440001",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

    @pytest.fixture
    def sample_mep_design_electrical(self):
        """Sample electrical MEP design for testing."""
        return MEPDesign(
            id=2,
            project_id="550e8400-e29b-41d4-a716-446655440000",
            calculation_sheet_id=2,
            title="Electrical System Design",
            description="Building electrical distribution",
            system_type="electrical",
            loads={"total_load": 50000, "lighting_power_density": 0.8},
            equipment={"panel_type": "main_distribution", "voltage": 480},
            distribution={"circuit_count": 20},
            sizing_results={
                "panel_size": "400A",
                "voltage_drop": 2.5,
            },
            status="draft",
            created_by="550e8400-e29b-41d4-a716-446655440001",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

    @pytest.fixture
    def sample_code_requirements_structural(self):
        """Sample structural code requirements."""
        return {
            "version": "2021",
            "jurisdiction": "California",
            "code_type": "structural",
            "requirements": {
                "max_stress_ratio": 1.0,
                "max_deflection_ratio": 360,
                "load_combinations": ["1.4D", "1.2D + 1.6L", "1.2D + 1.0L + 1.0W"],
            },
        }

    @pytest.fixture
    def sample_code_requirements_mep(self):
        """Sample MEP code requirements."""
        return {
            "version": "2021",
            "jurisdiction": "California",
            "code_type": "mep",
            "requirements": {
                "electrical": {
                    "max_voltage_drop": 3.0,
                    "min_circuit_breaker_rating": 15,
                },
                "plumbing": {"min_pipe_size": 0.5, "max_velocity": 8.0},
                "hvac": {"min_ventilation_rate": 15, "max_duct_velocity": 2000},
            },
        }

    @pytest.fixture
    def sample_code_requirements_energy(self):
        """Sample energy code requirements."""
        return {
            "version": "2021",
            "jurisdiction": "California",
            "code_type": "energy",
            "requirements": {
                "max_u_value_wall": 0.057,
                "max_u_value_roof": 0.048,
                "min_hvac_efficiency": 13.0,
                "max_lighting_power_density": 1.0,
            },
        }

    # Test validate_structural_code

    @pytest.mark.asyncio
    async def test_validate_structural_code_compliant(
        self,
        code_validator_service,
        mock_structural_repo,
        mock_knowledge_client,
        mock_compliance_repo,
        sample_structural_design,
        sample_code_requirements_structural,
    ):
        """Test structural code validation with compliant design."""
        # Arrange
        design_id = 1
        jurisdiction = "California"
        user_id = "550e8400-e29b-41d4-a716-446655440001"

        mock_structural_repo.get_by_id.return_value = sample_structural_design
        mock_knowledge_client.get_code_requirements.return_value = (
            sample_code_requirements_structural
        )

        created_report = ComplianceReport(
            id=1,
            calculation_sheet_id=1,
            project_id=sample_structural_design.project_id,
            title="Structural Code Compliance - beam",
            code_type="structural",
            jurisdiction=jurisdiction,
            code_version="2021",
            checks_performed={"checks": []},
            violations={"violations": []},
            recommendations={"recommendations": []},
            overall_status="compliant",
            generated_by=user_id,
            generated_at=datetime.utcnow(),
        )
        mock_compliance_repo.create.return_value = created_report

        # Act
        result = await code_validator_service.validate_structural_code(
            design_id, jurisdiction, user_id
        )

        # Assert
        assert result is not None
        assert result.overall_status == "compliant"
        mock_structural_repo.get_by_id.assert_called_once_with(design_id)
        mock_knowledge_client.get_code_requirements.assert_called_once_with(
            CodeType.STRUCTURAL.value, jurisdiction
        )
        mock_compliance_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_structural_code_with_violations(
        self,
        code_validator_service,
        mock_structural_repo,
        mock_knowledge_client,
        mock_compliance_repo,
        sample_code_requirements_structural,
    ):
        """Test structural code validation with violations."""
        # Arrange
        design_id = 1
        jurisdiction = "California"
        user_id = "550e8400-e29b-41d4-a716-446655440001"

        # Create design with violations (high stress ratio)
        design_with_violations = StructuralDesign(
            id=1,
            project_id="550e8400-e29b-41d4-a716-446655440000",
            calculation_sheet_id=1,
            title="Beam Design",
            design_type="beam",
            loads={"dead_load": 50.0, "live_load": 40.0},
            material_properties={"steel_grade": "A992"},
            geometry={"span": 20.0},
            design_results={"deflection_ratio": 300},  # Below 360 limit
            stress_ratios={"bending": 1.2},  # Exceeds 1.0 limit
            status="draft",
            created_by=user_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        mock_structural_repo.get_by_id.return_value = design_with_violations
        mock_knowledge_client.get_code_requirements.return_value = (
            sample_code_requirements_structural
        )

        created_report = ComplianceReport(
            id=1,
            calculation_sheet_id=1,
            project_id=design_with_violations.project_id,
            title="Structural Code Compliance - beam",
            code_type="structural",
            jurisdiction=jurisdiction,
            code_version="2021",
            checks_performed={"checks": []},
            violations={"violations": []},
            recommendations={"recommendations": []},
            overall_status="non_compliant",
            generated_by=user_id,
            generated_at=datetime.utcnow(),
        )
        mock_compliance_repo.create.return_value = created_report

        # Act
        result = await code_validator_service.validate_structural_code(
            design_id, jurisdiction, user_id
        )

        # Assert
        assert result is not None
        assert result.overall_status == "non_compliant"
        mock_compliance_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_structural_code_design_not_found(
        self,
        code_validator_service,
        mock_structural_repo,
    ):
        """Test structural code validation with non-existent design."""
        # Arrange
        design_id = 999
        jurisdiction = "California"
        user_id = "550e8400-e29b-41d4-a716-446655440001"

        mock_structural_repo.get_by_id.return_value = None

        # Act & Assert
        with pytest.raises(ValueError, match="Structural design 999 not found"):
            await code_validator_service.validate_structural_code(
                design_id, jurisdiction, user_id
            )

    # Test validate_mep_code

    @pytest.mark.asyncio
    async def test_validate_mep_code_hvac_compliant(
        self,
        code_validator_service,
        mock_mep_repo,
        mock_knowledge_client,
        mock_compliance_repo,
        sample_mep_design_hvac,
        sample_code_requirements_mep,
    ):
        """Test MEP code validation for compliant HVAC system."""
        # Arrange
        design_id = 1
        jurisdiction = "California"
        user_id = "550e8400-e29b-41d4-a716-446655440001"

        mock_mep_repo.get_by_id.return_value = sample_mep_design_hvac
        mock_knowledge_client.get_code_requirements.return_value = (
            sample_code_requirements_mep
        )

        created_report = ComplianceReport(
            id=1,
            calculation_sheet_id=1,
            project_id=sample_mep_design_hvac.project_id,
            title="MEP Code Compliance - HVAC",
            code_type="mep",
            jurisdiction=jurisdiction,
            code_version="2021",
            checks_performed={"checks": []},
            violations={"violations": []},
            recommendations={"recommendations": []},
            overall_status="compliant",
            generated_by=user_id,
            generated_at=datetime.utcnow(),
        )
        mock_compliance_repo.create.return_value = created_report

        # Act
        result = await code_validator_service.validate_mep_code(
            design_id, jurisdiction, user_id
        )

        # Assert
        assert result is not None
        assert result.code_type == "mep"
        mock_mep_repo.get_by_id.assert_called_once_with(design_id)
        mock_knowledge_client.get_code_requirements.assert_called_once_with(
            CodeType.MEP.value, jurisdiction
        )

    @pytest.mark.asyncio
    async def test_validate_mep_code_electrical_with_violations(
        self,
        code_validator_service,
        mock_mep_repo,
        mock_knowledge_client,
        mock_compliance_repo,
        sample_code_requirements_mep,
    ):
        """Test MEP code validation for electrical system with violations."""
        # Arrange
        design_id = 2
        jurisdiction = "California"
        user_id = "550e8400-e29b-41d4-a716-446655440001"

        # Create electrical design with high voltage drop
        electrical_design = MEPDesign(
            id=2,
            project_id="550e8400-e29b-41d4-a716-446655440000",
            calculation_sheet_id=2,
            title="Electrical System",
            system_type="electrical",
            loads={"total_load": 50000},
            equipment={"panel_type": "main"},
            distribution={},
            sizing_results={"voltage_drop": 4.5},  # Exceeds 3.0% limit
            status="draft",
            created_by=user_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        mock_mep_repo.get_by_id.return_value = electrical_design
        mock_knowledge_client.get_code_requirements.return_value = (
            sample_code_requirements_mep
        )

        created_report = ComplianceReport(
            id=1,
            calculation_sheet_id=2,
            project_id=electrical_design.project_id,
            title="MEP Code Compliance - ELECTRICAL",
            code_type="mep",
            jurisdiction=jurisdiction,
            code_version="2021",
            checks_performed={"checks": []},
            violations={"violations": []},
            recommendations={"recommendations": []},
            overall_status="review_required",
            generated_by=user_id,
            generated_at=datetime.utcnow(),
        )
        mock_compliance_repo.create.return_value = created_report

        # Act
        result = await code_validator_service.validate_mep_code(
            design_id, jurisdiction, user_id
        )

        # Assert
        assert result is not None
        mock_compliance_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_mep_code_design_not_found(
        self,
        code_validator_service,
        mock_mep_repo,
    ):
        """Test MEP code validation with non-existent design."""
        # Arrange
        design_id = 999
        jurisdiction = "California"
        user_id = "550e8400-e29b-41d4-a716-446655440001"

        mock_mep_repo.get_by_id.return_value = None

        # Act & Assert
        with pytest.raises(ValueError, match="MEP design 999 not found"):
            await code_validator_service.validate_mep_code(
                design_id, jurisdiction, user_id
            )

    # Test validate_energy_code

    @pytest.mark.asyncio
    async def test_validate_energy_code_mep_compliant(
        self,
        code_validator_service,
        mock_mep_repo,
        mock_knowledge_client,
        mock_compliance_repo,
        sample_mep_design_hvac,
        sample_code_requirements_energy,
    ):
        """Test energy code validation for compliant MEP design."""
        # Arrange
        design_id = 1
        jurisdiction = "California"
        user_id = "550e8400-e29b-41d4-a716-446655440001"
        design_type = "mep"

        mock_mep_repo.get_by_id.return_value = sample_mep_design_hvac
        mock_knowledge_client.get_code_requirements.return_value = (
            sample_code_requirements_energy
        )

        created_report = ComplianceReport(
            id=1,
            calculation_sheet_id=1,
            project_id=sample_mep_design_hvac.project_id,
            title="Energy Code Compliance - Mep",
            code_type="energy",
            jurisdiction=jurisdiction,
            code_version="2021",
            checks_performed={"checks": []},
            violations={"violations": []},
            recommendations={"recommendations": []},
            overall_status="compliant",
            generated_by=user_id,
            generated_at=datetime.utcnow(),
        )
        mock_compliance_repo.create.return_value = created_report

        # Act
        result = await code_validator_service.validate_energy_code(
            design_id, jurisdiction, user_id, design_type
        )

        # Assert
        assert result is not None
        assert result.code_type == "energy"
        mock_mep_repo.get_by_id.assert_called_once_with(design_id)

    @pytest.mark.asyncio
    async def test_validate_energy_code_invalid_design_type(
        self,
        code_validator_service,
    ):
        """Test energy code validation with invalid design type."""
        # Arrange
        design_id = 1
        jurisdiction = "California"
        user_id = "550e8400-e29b-41d4-a716-446655440001"
        design_type = "invalid"

        # Act & Assert
        with pytest.raises(ValueError, match="Invalid design type: invalid"):
            await code_validator_service.validate_energy_code(
                design_id, jurisdiction, user_id, design_type
            )

    # Test get_code_requirements

    @pytest.mark.asyncio
    async def test_get_code_requirements_from_service(
        self,
        code_validator_service,
        mock_knowledge_client,
        sample_code_requirements_structural,
    ):
        """Test retrieving code requirements from Knowledge Service."""
        # Arrange
        code_type = CodeType.STRUCTURAL
        jurisdiction = "California"

        mock_knowledge_client.get_code_requirements.return_value = (
            sample_code_requirements_structural
        )

        # Act
        result = await code_validator_service.get_code_requirements(
            code_type, jurisdiction
        )

        # Assert
        assert result == sample_code_requirements_structural
        mock_knowledge_client.get_code_requirements.assert_called_once_with(
            code_type.value, jurisdiction
        )

    @pytest.mark.asyncio
    async def test_get_code_requirements_with_caching(
        self,
        code_validator_service,
        mock_knowledge_client,
        sample_code_requirements_structural,
    ):
        """Test code requirements caching."""
        # Arrange
        code_type = CodeType.STRUCTURAL
        jurisdiction = "California"

        mock_knowledge_client.get_code_requirements.return_value = (
            sample_code_requirements_structural
        )

        # Act - First call
        result1 = await code_validator_service.get_code_requirements(
            code_type, jurisdiction
        )

        # Act - Second call (should use cache)
        result2 = await code_validator_service.get_code_requirements(
            code_type, jurisdiction
        )

        # Assert
        assert result1 == result2
        # Should only call knowledge service once due to caching
        mock_knowledge_client.get_code_requirements.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_code_requirements_fallback_on_error(
        self,
        code_validator_service,
        mock_knowledge_client,
    ):
        """Test fallback to default requirements when service fails."""
        # Arrange
        code_type = CodeType.STRUCTURAL
        jurisdiction = "California"

        mock_knowledge_client.get_code_requirements.side_effect = Exception(
            "Service unavailable"
        )

        # Act
        result = await code_validator_service.get_code_requirements(
            code_type, jurisdiction
        )

        # Assert
        assert result is not None
        assert result["version"] == "2021"
        assert result["code_type"] == "structural"
        assert "requirements" in result

    # Test helper methods

    def test_determine_compliance_status_compliant(self, code_validator_service):
        """Test compliance status determination with no violations."""
        # Arrange
        violations = []

        # Act
        status = code_validator_service._determine_compliance_status(violations)

        # Assert
        assert status == ComplianceStatus.COMPLIANT

    def test_determine_compliance_status_non_compliant(self, code_validator_service):
        """Test compliance status determination with critical violations."""
        # Arrange
        from src.api.v1.schemas.compliance import ViolationSchema

        violations = [
            ViolationSchema(
                code_section="IBC 1605",
                severity=ViolationSeverity.CRITICAL,
                description="Critical violation",
                recommendation="Fix immediately",
                affected_elements=["beam"],
            )
        ]

        # Act
        status = code_validator_service._determine_compliance_status(violations)

        # Assert
        assert status == ComplianceStatus.NON_COMPLIANT

    def test_determine_compliance_status_review_required(self, code_validator_service):
        """Test compliance status determination with major violations."""
        # Arrange
        from src.api.v1.schemas.compliance import ViolationSchema

        violations = [
            ViolationSchema(
                code_section="IBC 1604",
                severity=ViolationSeverity.MAJOR,
                description="Major violation",
                recommendation="Review and fix",
                affected_elements=["column"],
            )
        ]

        # Act
        status = code_validator_service._determine_compliance_status(violations)

        # Assert
        assert status == ComplianceStatus.REVIEW_REQUIRED

    def test_generate_recommendations_no_violations(self, code_validator_service):
        """Test recommendation generation with no violations."""
        # Arrange
        violations = []

        # Act
        recommendations = code_validator_service._generate_recommendations(violations)

        # Assert
        assert len(recommendations) == 1
        assert "meets all code requirements" in recommendations[0]

    def test_generate_recommendations_with_violations(self, code_validator_service):
        """Test recommendation generation with violations."""
        # Arrange
        from src.api.v1.schemas.compliance import ViolationSchema

        violations = [
            ViolationSchema(
                code_section="IBC 1605",
                severity=ViolationSeverity.CRITICAL,
                description="Critical violation",
                recommendation="Fix immediately",
                affected_elements=["beam"],
            ),
            ViolationSchema(
                code_section="IBC 1604",
                severity=ViolationSeverity.MAJOR,
                description="Major violation",
                recommendation="Review",
                affected_elements=["column"],
            ),
        ]

        # Act
        recommendations = code_validator_service._generate_recommendations(violations)

        # Assert
        assert len(recommendations) > 0
        assert any("critical" in rec.lower() for rec in recommendations)
        assert any("major" in rec.lower() for rec in recommendations)
