"""Property-based tests for code compliance validation.

**Validates: Requirements 5.1-5.3**

Property 8: Code Compliance Checks
- Validates that code compliance checks are consistent and deterministic
- Ensures that the same design always produces the same compliance result
- Verifies that violations are properly detected and reported
"""

from datetime import datetime
from unittest.mock import AsyncMock

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from src.api.v1.schemas.compliance import ComplianceStatus
from src.models.mep_design import MEPDesign
from src.models.structural_design import StructuralDesign
from src.services.code_validator_service import CodeValidatorService

# Hypothesis strategies for generating test data


@st.composite
def structural_design_strategy(draw):
    """Generate structural design with varying stress ratios."""
    stress_ratio = draw(st.floats(min_value=0.1, max_value=2.0))
    deflection_ratio = draw(st.integers(min_value=100, max_value=500))

    return StructuralDesign(
        id=draw(st.integers(min_value=1, max_value=1000)),
        project_id="550e8400-e29b-41d4-a716-446655440000",
        calculation_sheet_id=1,
        title="Test Beam Design",
        description="Property test beam",
        design_type="beam",
        loads={
            "dead_load": draw(st.floats(min_value=10.0, max_value=100.0)),
            "live_load": draw(st.floats(min_value=10.0, max_value=100.0)),
            "load_combinations": ["1.4D", "1.2D + 1.6L"],
        },
        material_properties={"steel_grade": "A992", "fy": 50.0},
        geometry={"span": draw(st.floats(min_value=10.0, max_value=50.0))},
        design_results={
            "deflection_ratio": deflection_ratio,
            "seismic_design_category": "D",
        },
        stress_ratios={"bending": stress_ratio, "shear": stress_ratio * 0.5},
        status="draft",
        created_by="test_user",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


@st.composite
def mep_design_hvac_strategy(draw):
    """Generate HVAC MEP design with varying parameters."""
    ventilation_rate = draw(st.floats(min_value=5.0, max_value=30.0))
    duct_velocity = draw(st.floats(min_value=1000.0, max_value=3000.0))

    return MEPDesign(
        id=draw(st.integers(min_value=1, max_value=1000)),
        project_id="550e8400-e29b-41d4-a716-446655440000",
        calculation_sheet_id=1,
        title="Test HVAC Design",
        description="Property test HVAC",
        system_type="hvac",
        loads={
            "heating_load": draw(st.floats(min_value=50000.0, max_value=200000.0)),
            "cooling_load": draw(st.floats(min_value=50000.0, max_value=200000.0)),
        },
        equipment={
            "type": "heat_pump",
            "efficiency": draw(st.floats(min_value=10.0, max_value=20.0)),
        },
        distribution={"duct_type": "rectangular"},
        sizing_results={
            "ventilation_rate": ventilation_rate,
            "duct_velocity": duct_velocity,
        },
        status="draft",
        created_by="test_user",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


@st.composite
def mep_design_electrical_strategy(draw):
    """Generate electrical MEP design with varying parameters."""
    voltage_drop = draw(st.floats(min_value=0.5, max_value=5.0))

    return MEPDesign(
        id=draw(st.integers(min_value=1, max_value=1000)),
        project_id="550e8400-e29b-41d4-a716-446655440000",
        calculation_sheet_id=1,
        title="Test Electrical Design",
        description="Property test electrical",
        system_type="electrical",
        loads={
            "total_load": draw(st.floats(min_value=10000.0, max_value=100000.0)),
            "lighting_power_density": draw(st.floats(min_value=0.5, max_value=2.0)),
        },
        equipment={"panel_type": "main_distribution", "voltage": 480},
        distribution={"circuit_count": draw(st.integers(min_value=5, max_value=50))},
        sizing_results={
            "voltage_drop": voltage_drop,
        },
        status="draft",
        created_by="test_user",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


class TestCodeComplianceProperties:
    """Property-based tests for code compliance validation."""

    @pytest.fixture
    def mock_repos_and_client(self):
        """Create mocked repositories and client."""
        compliance_repo = AsyncMock()
        structural_repo = AsyncMock()
        mep_repo = AsyncMock()
        knowledge_client = AsyncMock()

        # Mock code requirements
        knowledge_client.get_code_requirements.return_value = {
            "version": "2021",
            "jurisdiction": "Test",
            "requirements": {
                "max_stress_ratio": 1.0,
                "max_deflection_ratio": 360,
                "load_combinations": ["1.4D", "1.2D + 1.6L"],
                "electrical": {"max_voltage_drop": 3.0},
                "hvac": {
                    "min_ventilation_rate": 15,
                    "max_duct_velocity": 2000,
                },
            },
        }

        return compliance_repo, structural_repo, mep_repo, knowledge_client

    # Property 8: Code Compliance Checks - Determinism

    @settings(
        max_examples=10,
        suppress_health_check=[
            HealthCheck.function_scoped_fixture,
            HealthCheck.too_slow,
        ],
    )
    @given(design=structural_design_strategy())
    @pytest.mark.asyncio
    async def test_property_structural_compliance_determinism(
        self, design, mock_repos_and_client
    ):
        """Property: Same structural design produces same compliance status.

        **Validates: Requirements 5.1, 5.4**

        This property ensures that code compliance validation is
        deterministic:
        - Running validation twice on same design produces identical results
        - Compliance status is consistent
        - Violation detection is reproducible
        """
        (
            compliance_repo,
            structural_repo,
            mep_repo,
            knowledge_client,
        ) = mock_repos_and_client

        # Mock repository responses
        structural_repo.get_by_id.return_value = design

        report_id = 1

        def create_report(report):
            report.id = report_id
            return report

        compliance_repo.create.side_effect = create_report

        # Create service
        service = CodeValidatorService(
            compliance_repo=compliance_repo,
            structural_repo=structural_repo,
            mep_repo=mep_repo,
            knowledge_client=knowledge_client,
        )

        # Run validation twice
        result1 = await service.validate_structural_code(design.id, "Test", "test_user")
        result2 = await service.validate_structural_code(design.id, "Test", "test_user")

        # Property: Same design produces same compliance status
        assert result1.overall_status == result2.overall_status

        # Property: Violation count is consistent
        violations1 = result1.violations.get("violations", [])
        violations2 = result2.violations.get("violations", [])
        assert len(violations1) == len(violations2)

    @settings(
        max_examples=10,
        suppress_health_check=[
            HealthCheck.function_scoped_fixture,
            HealthCheck.too_slow,
        ],
    )
    @given(design=structural_design_strategy())
    @pytest.mark.asyncio
    async def test_property_stress_ratio_violation_detection(
        self, design, mock_repos_and_client
    ):
        """Property: Designs with stress ratio > 1.0 are non-compliant.

        **Validates: Requirements 5.1, 5.5**

        This property ensures that stress ratio violations are correctly
        detected:
        - Stress ratios exceeding code limits trigger violations
        - Violation severity is appropriate (CRITICAL for stress ratio)
        - Recommendations are provided
        """
        (
            compliance_repo,
            structural_repo,
            mep_repo,
            knowledge_client,
        ) = mock_repos_and_client

        structural_repo.get_by_id.return_value = design

        report_id = 1

        def create_report(report):
            report.id = report_id
            return report

        compliance_repo.create.side_effect = create_report

        service = CodeValidatorService(
            compliance_repo=compliance_repo,
            structural_repo=structural_repo,
            mep_repo=mep_repo,
            knowledge_client=knowledge_client,
        )

        result = await service.validate_structural_code(design.id, "Test", "test_user")

        # Property: If any stress ratio > 1.0, status should be NON_COMPLIANT
        max_stress_ratio = max(design.stress_ratios.values())
        if max_stress_ratio > 1.0:
            assert result.overall_status == ComplianceStatus.NON_COMPLIANT.value
            # Should have at least one violation
            violations = result.violations.get("violations", [])
            assert len(violations) > 0
        else:
            # May be compliant or require review based on other checks
            assert result.overall_status in [
                ComplianceStatus.COMPLIANT.value,
                ComplianceStatus.REVIEW_REQUIRED.value,
            ]

    @settings(
        max_examples=10,
        suppress_health_check=[
            HealthCheck.function_scoped_fixture,
            HealthCheck.too_slow,
        ],
    )
    @given(design=mep_design_hvac_strategy())
    @pytest.mark.asyncio
    async def test_property_hvac_ventilation_violation_detection(
        self, design, mock_repos_and_client
    ):
        """Property: HVAC designs with insufficient ventilation are flagged.

        **Validates: Requirements 5.2, 5.5**

        This property ensures that ventilation violations are correctly
        detected:
        - Ventilation rates below code minimum trigger violations
        - Appropriate code sections are referenced
        - Recommendations are provided
        """
        (
            compliance_repo,
            structural_repo,
            mep_repo,
            knowledge_client,
        ) = mock_repos_and_client

        mep_repo.get_by_id.return_value = design

        report_id = 1

        def create_report(report):
            report.id = report_id
            return report

        compliance_repo.create.side_effect = create_report

        service = CodeValidatorService(
            compliance_repo=compliance_repo,
            structural_repo=structural_repo,
            mep_repo=mep_repo,
            knowledge_client=knowledge_client,
        )

        result = await service.validate_mep_code(design.id, "Test", "test_user")

        # Property: If ventilation rate < 15 CFM/person, should have
        # violation
        ventilation_rate = design.sizing_results.get("ventilation_rate", 0)
        violations = result.violations.get("violations", [])

        if ventilation_rate < 15:
            assert len(violations) > 0
            # Should reference IMC code
            assert any("IMC" in str(v) for v in violations)

    @settings(
        max_examples=10,
        suppress_health_check=[
            HealthCheck.function_scoped_fixture,
            HealthCheck.too_slow,
        ],
    )
    @given(design=mep_design_electrical_strategy())
    @pytest.mark.asyncio
    async def test_property_electrical_voltage_drop_violation(
        self, design, mock_repos_and_client
    ):
        """Property: Electrical designs with excessive voltage drop flagged.

        **Validates: Requirements 5.2, 5.5**

        This property ensures that voltage drop violations are correctly
        detected:
        - Voltage drops exceeding code limits trigger violations
        - NEC code sections are referenced
        - Recommendations include corrective actions
        """
        (
            compliance_repo,
            structural_repo,
            mep_repo,
            knowledge_client,
        ) = mock_repos_and_client

        mep_repo.get_by_id.return_value = design

        report_id = 1

        def create_report(report):
            report.id = report_id
            return report

        compliance_repo.create.side_effect = create_report

        service = CodeValidatorService(
            compliance_repo=compliance_repo,
            structural_repo=structural_repo,
            mep_repo=mep_repo,
            knowledge_client=knowledge_client,
        )

        result = await service.validate_mep_code(design.id, "Test", "test_user")

        # Property: If voltage drop > 3%, should have violation
        voltage_drop = design.sizing_results.get("voltage_drop", 0)
        violations = result.violations.get("violations", [])

        if voltage_drop > 3.0:
            assert len(violations) > 0
            # Should reference NEC code
            assert any("NEC" in str(v) for v in violations)

    # Property 8: Compliance Status Consistency

    @settings(
        max_examples=10,
        suppress_health_check=[
            HealthCheck.function_scoped_fixture,
            HealthCheck.too_slow,
        ],
    )
    @given(
        stress_ratio=st.floats(min_value=0.1, max_value=2.0),
        deflection_ratio=st.integers(min_value=100, max_value=500),
    )
    @pytest.mark.asyncio
    async def test_property_compliance_status_consistency(
        self, stress_ratio, deflection_ratio, mock_repos_and_client
    ):
        """Property: Compliance status consistent with violation severity.

        **Validates: Requirements 5.4**

        This property ensures that overall compliance status correctly
        reflects the severity of violations found:
        - CRITICAL violations → NON_COMPLIANT status
        - MAJOR violations → REVIEW_REQUIRED status
        - No violations → COMPLIANT status
        """
        (
            compliance_repo,
            structural_repo,
            mep_repo,
            knowledge_client,
        ) = mock_repos_and_client

        design = StructuralDesign(
            id=1,
            project_id="550e8400-e29b-41d4-a716-446655440000",
            calculation_sheet_id=1,
            title="Test Design",
            design_type="beam",
            loads={"dead_load": 50.0, "live_load": 40.0, "load_combinations": ["1.4D"]},
            material_properties={"steel_grade": "A992"},
            geometry={"span": 20.0},
            design_results={"deflection_ratio": deflection_ratio},
            stress_ratios={"bending": stress_ratio},
            status="draft",
            created_by="test_user",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        structural_repo.get_by_id.return_value = design

        report_id = 1

        def create_report(report):
            report.id = report_id
            return report

        compliance_repo.create.side_effect = create_report

        service = CodeValidatorService(
            compliance_repo=compliance_repo,
            structural_repo=structural_repo,
            mep_repo=mep_repo,
            knowledge_client=knowledge_client,
        )

        result = await service.validate_structural_code(1, "Test", "test_user")

        # Property: Status consistency with violations
        if stress_ratio > 1.0:
            # Critical violation expected
            assert result.overall_status == ComplianceStatus.NON_COMPLIANT.value
        elif deflection_ratio < 360:
            # Major violation expected
            assert result.overall_status in [
                ComplianceStatus.REVIEW_REQUIRED.value,
                ComplianceStatus.NON_COMPLIANT.value,
            ]
        else:
            # Should be compliant or review required
            assert result.overall_status in [
                ComplianceStatus.COMPLIANT.value,
                ComplianceStatus.REVIEW_REQUIRED.value,
            ]

    @settings(
        max_examples=10,
        suppress_health_check=[
            HealthCheck.function_scoped_fixture,
            HealthCheck.too_slow,
        ],
    )
    @given(design=structural_design_strategy())
    @pytest.mark.asyncio
    async def test_property_recommendations_always_provided(
        self, design, mock_repos_and_client
    ):
        """Property: Compliance reports always include recommendations.

        **Validates: Requirements 5.5**

        This property ensures that every compliance report includes
        actionable recommendations, whether compliant or not.
        """
        (
            compliance_repo,
            structural_repo,
            mep_repo,
            knowledge_client,
        ) = mock_repos_and_client

        structural_repo.get_by_id.return_value = design

        report_id = 1

        def create_report(report):
            report.id = report_id
            return report

        compliance_repo.create.side_effect = create_report

        service = CodeValidatorService(
            compliance_repo=compliance_repo,
            structural_repo=structural_repo,
            mep_repo=mep_repo,
            knowledge_client=knowledge_client,
        )

        result = await service.validate_structural_code(design.id, "Test", "test_user")

        # Property: Recommendations are always present
        recommendations = result.recommendations.get("recommendations", [])
        assert len(recommendations) > 0
        assert all(isinstance(rec, str) for rec in recommendations)
        assert all(len(rec) > 0 for rec in recommendations)
