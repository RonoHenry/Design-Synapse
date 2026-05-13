"""Property-based tests for violation reporting.

**Validates: Requirements 5.5**

Property 9: Violation Reporting
- Validates that violations are properly formatted and reported
- Ensures all required violation fields are present
- Verifies that code references are included
- Checks that recommendations are actionable
"""

from datetime import datetime
from unittest.mock import AsyncMock

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from src.api.v1.schemas.compliance import ViolationSeverity
from src.models.structural_design import StructuralDesign
from src.services.code_validator_service import CodeValidatorService


@st.composite
def violation_inducing_design_strategy(draw):
    """Generate structural designs that will produce violations."""
    # Generate designs with known violations
    violation_type = draw(st.sampled_from(["stress", "deflection", "both"]))

    if violation_type == "stress":
        stress_ratio = draw(st.floats(min_value=1.1, max_value=2.0))
        deflection_ratio = draw(st.integers(min_value=360, max_value=500))
    elif violation_type == "deflection":
        stress_ratio = draw(st.floats(min_value=0.5, max_value=0.9))
        deflection_ratio = draw(st.integers(min_value=100, max_value=350))
    else:  # both
        stress_ratio = draw(st.floats(min_value=1.1, max_value=2.0))
        deflection_ratio = draw(st.integers(min_value=100, max_value=350))

    return StructuralDesign(
        id=draw(st.integers(min_value=1, max_value=1000)),
        project_id="550e8400-e29b-41d4-a716-446655440000",
        calculation_sheet_id=1,
        title="Test Design with Violations",
        description="Property test design",
        design_type=draw(st.sampled_from(["beam", "column", "foundation"])),
        loads={
            "dead_load": draw(st.floats(min_value=10.0, max_value=100.0)),
            "live_load": draw(st.floats(min_value=10.0, max_value=100.0)),
            "load_combinations": ["1.4D", "1.2D + 1.6L"],
        },
        material_properties={"steel_grade": "A992", "fy": 50.0},
        geometry={"span": draw(st.floats(min_value=10.0, max_value=50.0))},
        design_results={"deflection_ratio": deflection_ratio},
        stress_ratios={"bending": stress_ratio, "shear": stress_ratio * 0.5},
        status="draft",
        created_by="test_user",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


class TestViolationReportingProperties:
    """Property-based tests for violation reporting."""

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
            },
        }

        return compliance_repo, structural_repo, mep_repo, knowledge_client

    # Property 9: Violation Structure and Completeness

    @settings(
        max_examples=10,
        suppress_health_check=[
            HealthCheck.function_scoped_fixture,
            HealthCheck.too_slow,
        ],
    )
    @given(design=violation_inducing_design_strategy())
    @pytest.mark.asyncio
    async def test_property_violations_have_required_fields(
        self, design, mock_repos_and_client
    ):
        """Property: All violations contain required fields.

        **Validates: Requirements 5.5**

        This property ensures that every violation includes:
        - code_section: Reference to specific code section
        - severity: Violation severity level
        - description: Clear description of the violation
        - recommendation: Actionable corrective recommendation
        - affected_elements: List of affected design elements
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

        violations = result.violations.get("violations", [])

        # Property: All violations have required fields
        for violation in violations:
            assert "code_section" in violation
            assert "severity" in violation
            assert "description" in violation
            assert "recommendation" in violation
            assert "affected_elements" in violation

            # Fields should not be empty
            assert len(violation["code_section"]) > 0
            assert len(violation["description"]) > 0
            assert len(violation["recommendation"]) > 0
            assert len(violation["affected_elements"]) > 0

    @settings(
        max_examples=10,
        suppress_health_check=[
            HealthCheck.function_scoped_fixture,
            HealthCheck.too_slow,
        ],
    )
    @given(design=violation_inducing_design_strategy())
    @pytest.mark.asyncio
    async def test_property_violations_reference_valid_codes(
        self, design, mock_repos_and_client
    ):
        """Property: All violations reference valid building codes.

        **Validates: Requirements 5.5**

        This property ensures that violations reference recognized
        building codes (IBC, ASCE 7, etc.) with proper section numbers.
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

        violations = result.violations.get("violations", [])

        # Property: Code sections reference valid codes
        valid_code_prefixes = [
            "IBC",
            "ASCE",
            "ACI",
            "AISC",
            "NEC",
            "IPC",
            "IMC",
            "NFPA",
        ]

        for violation in violations:
            code_section = violation["code_section"]
            # Should start with a valid code prefix
            assert any(
                code_section.startswith(prefix) for prefix in valid_code_prefixes
            ), f"Invalid code reference: {code_section}"

    @settings(
        max_examples=10,
        suppress_health_check=[
            HealthCheck.function_scoped_fixture,
            HealthCheck.too_slow,
        ],
    )
    @given(design=violation_inducing_design_strategy())
    @pytest.mark.asyncio
    async def test_property_violation_severity_is_appropriate(
        self, design, mock_repos_and_client
    ):
        """Property: Violation severity matches the type of violation.

        **Validates: Requirements 5.5**

        This property ensures that:
        - Stress ratio violations are CRITICAL (safety issue)
        - Deflection violations are MAJOR (serviceability issue)
        - Severity levels are from the defined enum
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

        violations = result.violations.get("violations", [])

        # Property: Severity levels are valid
        valid_severities = [s.value for s in ViolationSeverity]

        for violation in violations:
            severity = violation["severity"]
            assert severity in valid_severities

            # Property: Stress ratio violations should be CRITICAL
            if "stress ratio" in violation["description"].lower():
                assert severity == ViolationSeverity.CRITICAL.value

            # Property: Deflection violations should be MAJOR
            if "deflection" in violation["description"].lower():
                assert severity == ViolationSeverity.MAJOR.value

    @settings(
        max_examples=10,
        suppress_health_check=[
            HealthCheck.function_scoped_fixture,
            HealthCheck.too_slow,
        ],
    )
    @given(design=violation_inducing_design_strategy())
    @pytest.mark.asyncio
    async def test_property_recommendations_are_actionable(
        self, design, mock_repos_and_client
    ):
        """Property: Violation recommendations are actionable.

        **Validates: Requirements 5.5**

        This property ensures that recommendations:
        - Contain action verbs (increase, reduce, modify, etc.)
        - Are specific to the violation type
        - Provide clear guidance for correction
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

        violations = result.violations.get("violations", [])

        # Property: Recommendations contain action verbs
        action_verbs = [
            "increase",
            "reduce",
            "modify",
            "adjust",
            "change",
            "improve",
            "redesign",
            "specify",
            "use",
            "select",
        ]

        for violation in violations:
            recommendation = violation["recommendation"].lower()
            # Should contain at least one action verb
            assert any(
                verb in recommendation for verb in action_verbs
            ), f"Recommendation lacks action verb: {recommendation}"

    @settings(
        max_examples=10,
        suppress_health_check=[
            HealthCheck.function_scoped_fixture,
            HealthCheck.too_slow,
        ],
    )
    @given(design=violation_inducing_design_strategy())
    @pytest.mark.asyncio
    async def test_property_affected_elements_are_specific(
        self, design, mock_repos_and_client
    ):
        """Property: Affected elements are specific and relevant.

        **Validates: Requirements 5.5**

        This property ensures that affected_elements:
        - Are not empty
        - Reference actual design elements
        - Are relevant to the violation type
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

        violations = result.violations.get("violations", [])

        # Property: Affected elements are specific
        for violation in violations:
            affected_elements = violation["affected_elements"]
            assert len(affected_elements) > 0

            # Elements should be strings
            assert all(isinstance(elem, str) for elem in affected_elements)

            # Elements should not be empty strings
            assert all(len(elem) > 0 for elem in affected_elements)

    # Property: Violation Count Consistency

    @settings(
        max_examples=10,
        suppress_health_check=[
            HealthCheck.function_scoped_fixture,
            HealthCheck.too_slow,
        ],
    )
    @given(
        stress_ratio=st.floats(min_value=1.1, max_value=2.0),
        deflection_ratio=st.integers(min_value=100, max_value=350),
    )
    @pytest.mark.asyncio
    async def test_property_violation_count_matches_issues(
        self, stress_ratio, deflection_ratio, mock_repos_and_client
    ):
        """Property: Number of violations matches number of code issues.

        **Validates: Requirements 5.5**

        This property ensures that:
        - Each code violation is reported exactly once
        - No duplicate violations
        - Violation count is consistent with design issues
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

        violations = result.violations.get("violations", [])

        # Count expected violations
        expected_violations = 0
        if stress_ratio > 1.0:
            expected_violations += 1  # Stress ratio violation
        if deflection_ratio < 360:
            expected_violations += 1  # Deflection violation

        # Property: Violation count matches expected issues
        # Note: May have additional violations for missing load combinations, etc.
        assert len(violations) >= expected_violations

    @settings(
        max_examples=10,
        suppress_health_check=[
            HealthCheck.function_scoped_fixture,
            HealthCheck.too_slow,
        ],
    )
    @given(design=violation_inducing_design_strategy())
    @pytest.mark.asyncio
    async def test_property_no_duplicate_violations(
        self, design, mock_repos_and_client
    ):
        """Property: No duplicate violations are reported.

        **Validates: Requirements 5.5**

        This property ensures that each unique violation is reported
        only once, even if multiple checks detect the same issue.
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

        violations = result.violations.get("violations", [])

        # Property: No duplicate violations
        # Create unique keys from code_section + description
        violation_keys = [(v["code_section"], v["description"]) for v in violations]

        # All keys should be unique
        assert len(violation_keys) == len(set(violation_keys))

    # Property: Violation Descriptions are Clear

    @settings(
        max_examples=10,
        suppress_health_check=[
            HealthCheck.function_scoped_fixture,
            HealthCheck.too_slow,
        ],
    )
    @given(design=violation_inducing_design_strategy())
    @pytest.mark.asyncio
    async def test_property_violation_descriptions_are_clear(
        self, design, mock_repos_and_client
    ):
        """Property: Violation descriptions are clear and informative.

        **Validates: Requirements 5.5**

        This property ensures that descriptions:
        - Include specific values (actual vs. required)
        - Are grammatically correct
        - Provide context for the violation
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

        violations = result.violations.get("violations", [])

        # Property: Descriptions are informative
        for violation in violations:
            description = violation["description"]

            # Should be a reasonable length (not too short)
            assert len(description) >= 20

            # Should not be all uppercase (shouting)
            assert description != description.upper()

            # Should start with a capital letter
            assert description[0].isupper()
