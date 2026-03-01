"""Unit tests for code compliance validation schemas."""

import pytest
from pydantic import ValidationError
from src.api.v1.schemas.compliance import (CodeRequirementsRequest,
                                           CodeRequirementsResponse, CodeType,
                                           CodeValidationRequest,
                                           CodeValidationResponse,
                                           ComplianceStatus, ViolationSchema,
                                           ViolationSeverity)


class TestCodeType:
    """Tests for CodeType enum."""

    def test_code_type_values(self):
        """Test CodeType enum has correct values."""
        assert CodeType.STRUCTURAL == "structural"
        assert CodeType.MEP == "mep"
        assert CodeType.ENERGY == "energy"
        assert CodeType.FIRE == "fire"
        assert CodeType.ACCESSIBILITY == "accessibility"


class TestComplianceStatus:
    """Tests for ComplianceStatus enum."""

    def test_compliance_status_values(self):
        """Test ComplianceStatus enum has correct values."""
        assert ComplianceStatus.COMPLIANT == "compliant"
        assert ComplianceStatus.NON_COMPLIANT == "non_compliant"
        assert ComplianceStatus.REVIEW_REQUIRED == "review_required"


class TestViolationSeverity:
    """Tests for ViolationSeverity enum."""

    def test_violation_severity_values(self):
        """Test ViolationSeverity enum has correct values."""
        assert ViolationSeverity.CRITICAL == "critical"
        assert ViolationSeverity.MAJOR == "major"
        assert ViolationSeverity.MINOR == "minor"
        assert ViolationSeverity.WARNING == "warning"


class TestCodeValidationRequest:
    """Tests for CodeValidationRequest schema."""

    def test_valid_code_validation_request(self):
        """Test creating valid code validation request."""
        data = {
            "design_id": "123e4567-e89b-12d3-a456-426614174000",
            "code_type": "structural",
            "jurisdiction": "California",
            "code_version": "IBC 2021",
        }
        request = CodeValidationRequest(**data)
        assert str(request.design_id) == "123e4567-e89b-12d3-a456-426614174000"
        assert request.code_type == CodeType.STRUCTURAL
        assert request.jurisdiction == "California"

    def test_code_validation_request_missing_required_fields(self):
        """Test validation fails when required fields are missing."""
        data = {"design_id": "123e4567-e89b-12d3-a456-426614174000"}
        with pytest.raises(ValidationError):
            CodeValidationRequest(**data)

    def test_code_validation_request_invalid_design_id(self):
        """Test validation fails for invalid design_id."""
        data = {
            "design_id": "invalid-uuid",
            "code_type": "structural",
            "jurisdiction": "California",
            "code_version": "IBC 2021",
        }
        with pytest.raises(ValidationError):
            CodeValidationRequest(**data)


class TestViolationSchema:
    """Tests for ViolationSchema."""

    def test_valid_violation_schema(self):
        """Test creating valid violation schema."""
        data = {
            "code_section": "IBC 1604.3",
            "severity": "major",
            "description": "Load combinations not properly applied",
            "recommendation": "Apply ASCE 7 load combinations",
            "affected_elements": ["beam-1", "column-2"],
        }
        violation = ViolationSchema(**data)
        assert violation.code_section == "IBC 1604.3"
        assert violation.severity == ViolationSeverity.MAJOR
        assert len(violation.affected_elements) == 2

    def test_violation_schema_missing_required_fields(self):
        """Test validation fails when required fields are missing."""
        data = {
            "code_section": "IBC 1604.3",
            "severity": "major",
        }
        with pytest.raises(ValidationError):
            ViolationSchema(**data)


class TestCodeValidationResponse:
    """Tests for CodeValidationResponse schema."""

    def test_valid_code_validation_response(self):
        """Test creating valid code validation response."""
        data = {
            "report_id": "123e4567-e89b-12d3-a456-426614174000",
            "design_id": "223e4567-e89b-12d3-a456-426614174000",
            "code_type": "structural",
            "jurisdiction": "California",
            "code_version": "IBC 2021",
            "overall_status": "non_compliant",
            "checks_performed": [
                "Load combinations",
                "Deflection limits",
                "Stress ratios",
            ],
            "violations": [
                {
                    "code_section": "IBC 1604.3",
                    "severity": "major",
                    "description": "Load combinations not properly applied",
                    "recommendation": "Apply ASCE 7 load combinations",
                    "affected_elements": ["beam-1"],
                }
            ],
            "recommendations": [
                "Review structural calculations",
                "Update load combinations",
            ],
        }
        response = CodeValidationResponse(**data)
        assert response.overall_status == ComplianceStatus.NON_COMPLIANT
        assert len(response.violations) == 1
        assert len(response.checks_performed) == 3

    def test_code_validation_response_compliant(self):
        """Test response for compliant design."""
        data = {
            "report_id": "123e4567-e89b-12d3-a456-426614174000",
            "design_id": "223e4567-e89b-12d3-a456-426614174000",
            "code_type": "structural",
            "jurisdiction": "California",
            "code_version": "IBC 2021",
            "overall_status": "compliant",
            "checks_performed": ["Load combinations", "Deflection limits"],
            "violations": [],
            "recommendations": [],
        }
        response = CodeValidationResponse(**data)
        assert response.overall_status == ComplianceStatus.COMPLIANT
        assert len(response.violations) == 0


class TestCodeRequirementsRequest:
    """Tests for CodeRequirementsRequest schema."""

    def test_valid_code_requirements_request(self):
        """Test creating valid code requirements request."""
        data = {
            "code_type": "mep",
            "jurisdiction": "New York",
            "code_version": "NEC 2020",
        }
        request = CodeRequirementsRequest(**data)
        assert request.code_type == CodeType.MEP
        assert request.jurisdiction == "New York"

    def test_code_requirements_request_missing_required_fields(self):
        """Test validation fails when required fields are missing."""
        data = {"code_type": "mep"}
        with pytest.raises(ValidationError):
            CodeRequirementsRequest(**data)


class TestCodeRequirementsResponse:
    """Tests for CodeRequirementsResponse schema."""

    def test_valid_code_requirements_response(self):
        """Test creating valid code requirements response."""
        data = {
            "code_type": "energy",
            "jurisdiction": "California",
            "code_version": "Title 24 2022",
            "requirements": {
                "envelope": {
                    "wall_r_value": 13,
                    "roof_r_value": 30,
                },
                "hvac": {
                    "min_efficiency": 14,
                },
            },
            "references": [
                "ASHRAE 90.1-2019",
                "California Title 24 Part 6",
            ],
        }
        response = CodeRequirementsResponse(**data)
        assert response.code_type == CodeType.ENERGY
        assert response.requirements["envelope"]["wall_r_value"] == 13
        assert len(response.references) == 2
