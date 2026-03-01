"""Unit tests for document management schemas."""

import pytest
from pydantic import ValidationError
from src.api.v1.schemas.document import (CalculationSheetCreateRequest,
                                         CalculationSheetResponse,
                                         CalculationSheetUpdateRequest,
                                         DocumentHistoryResponse,
                                         DocumentSearchRequest,
                                         DocumentSearchResponse,
                                         DocumentStatus, DocumentType,
                                         DocumentVersionSchema,
                                         SpecificationFormat,
                                         SpecificationGenerateRequest,
                                         SpecificationResponse)


class TestDocumentType:
    """Tests for DocumentType enum."""

    def test_document_type_values(self):
        """Test DocumentType enum has correct values."""
        assert DocumentType.CALCULATION_SHEET == "calculation_sheet"
        assert DocumentType.SPECIFICATION == "specification"
        assert DocumentType.REPORT == "report"
        assert DocumentType.DRAWING == "drawing"


class TestDocumentStatus:
    """Tests for DocumentStatus enum."""

    def test_document_status_values(self):
        """Test DocumentStatus enum has correct values."""
        assert DocumentStatus.DRAFT == "draft"
        assert DocumentStatus.REVIEW == "review"
        assert DocumentStatus.APPROVED == "approved"
        assert DocumentStatus.REJECTED == "rejected"
        assert DocumentStatus.ARCHIVED == "archived"


class TestSpecificationFormat:
    """Tests for SpecificationFormat enum."""

    def test_specification_format_values(self):
        """Test SpecificationFormat enum has correct values."""
        assert SpecificationFormat.CSI_MASTERFORMAT == "csi_masterformat"
        assert SpecificationFormat.UNIFORMAT == "uniformat"


class TestCalculationSheetCreateRequest:
    """Tests for CalculationSheetCreateRequest schema."""

    def test_valid_calculation_sheet_create_request(self):
        """Test creating valid calculation sheet create request."""
        data = {
            "project_id": "123e4567-e89b-12d3-a456-426614174000",
            "discipline": "structural",
            "calculation_type": "beam_design",
            "inputs": {
                "span": 20.0,
                "load": 1000.0,
            },
            "results": {
                "section": "W18x50",
                "deflection": 0.75,
            },
            "formulas": {
                "deflection": "5wL^4/384EI",
            },
            "unit_system": "imperial",
        }
        request = CalculationSheetCreateRequest(**data)
        assert str(request.project_id) == "123e4567-e89b-12d3-a456-426614174000"
        assert request.discipline == "structural"
        assert request.inputs["span"] == 20.0

    def test_calculation_sheet_create_request_missing_required_fields(self):
        """Test validation fails when required fields are missing."""
        data = {
            "project_id": "123e4567-e89b-12d3-a456-426614174000",
            "discipline": "structural",
        }
        with pytest.raises(ValidationError):
            CalculationSheetCreateRequest(**data)


class TestCalculationSheetUpdateRequest:
    """Tests for CalculationSheetUpdateRequest schema."""

    def test_valid_calculation_sheet_update_request(self):
        """Test creating valid calculation sheet update request."""
        data = {
            "inputs": {"span": 25.0},
            "results": {"section": "W21x62"},
        }
        request = CalculationSheetUpdateRequest(**data)
        assert request.inputs["span"] == 25.0
        assert request.results["section"] == "W21x62"

    def test_calculation_sheet_update_request_all_optional(self):
        """Test all fields are optional in update request."""
        data = {}
        request = CalculationSheetUpdateRequest(**data)
        assert request.inputs is None
        assert request.results is None
        assert request.formulas is None


class TestCalculationSheetResponse:
    """Tests for CalculationSheetResponse schema."""

    def test_valid_calculation_sheet_response(self):
        """Test creating valid calculation sheet response."""
        data = {
            "id": "123e4567-e89b-12d3-a456-426614174000",
            "project_id": "223e4567-e89b-12d3-a456-426614174000",
            "discipline": "structural",
            "calculation_type": "beam_design",
            "version": 1,
            "inputs": {"span": 20.0},
            "results": {"section": "W18x50"},
            "formulas": {"deflection": "5wL^4/384EI"},
            "unit_system": "imperial",
            "created_by": "323e4567-e89b-12d3-a456-426614174000",
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00",
        }
        response = CalculationSheetResponse(**data)
        assert response.version == 1
        assert response.discipline == "structural"


class TestDocumentVersionSchema:
    """Tests for DocumentVersionSchema."""

    def test_valid_document_version_schema(self):
        """Test creating valid document version schema."""
        data = {
            "version": 2,
            "changes": {
                "inputs": {"span": 25.0},
                "results": {"section": "W21x62"},
            },
            "updated_by": "123e4567-e89b-12d3-a456-426614174000",
            "updated_at": "2024-01-02T00:00:00",
        }
        version = DocumentVersionSchema(**data)
        assert version.version == 2
        assert version.changes["inputs"]["span"] == 25.0


class TestDocumentHistoryResponse:
    """Tests for DocumentHistoryResponse schema."""

    def test_valid_document_history_response(self):
        """Test creating valid document history response."""
        data = {
            "document_id": "123e4567-e89b-12d3-a456-426614174000",
            "current_version": 3,
            "versions": [
                {
                    "version": 1,
                    "changes": {"initial": True},
                    "updated_by": "223e4567-e89b-12d3-a456-426614174000",
                    "updated_at": "2024-01-01T00:00:00",
                },
                {
                    "version": 2,
                    "changes": {"inputs": {"span": 25.0}},
                    "updated_by": "223e4567-e89b-12d3-a456-426614174000",
                    "updated_at": "2024-01-02T00:00:00",
                },
            ],
        }
        response = DocumentHistoryResponse(**data)
        assert response.current_version == 3
        assert len(response.versions) == 2


class TestSpecificationGenerateRequest:
    """Tests for SpecificationGenerateRequest schema."""

    def test_valid_specification_generate_request(self):
        """Test creating valid specification generate request."""
        data = {
            "project_id": "123e4567-e89b-12d3-a456-426614174000",
            "design_ids": [
                "223e4567-e89b-12d3-a456-426614174000",
                "323e4567-e89b-12d3-a456-426614174000",
            ],
            "format": "csi_masterformat",
            "sections": ["03 30 00", "05 12 00"],
        }
        request = SpecificationGenerateRequest(**data)
        assert len(request.design_ids) == 2
        assert request.format == SpecificationFormat.CSI_MASTERFORMAT

    def test_specification_generate_request_missing_required_fields(self):
        """Test validation fails when required fields are missing."""
        data = {
            "project_id": "123e4567-e89b-12d3-a456-426614174000",
        }
        with pytest.raises(ValidationError):
            SpecificationGenerateRequest(**data)


class TestSpecificationResponse:
    """Tests for SpecificationResponse schema."""

    def test_valid_specification_response(self):
        """Test creating valid specification response."""
        data = {
            "specification_id": "123e4567-e89b-12d3-a456-426614174000",
            "project_id": "223e4567-e89b-12d3-a456-426614174000",
            "format": "csi_masterformat",
            "sections": {
                "03 30 00": {
                    "title": "Cast-in-Place Concrete",
                    "content": "Specification content...",
                },
            },
        }
        response = SpecificationResponse(**data)
        assert response.format == SpecificationFormat.CSI_MASTERFORMAT
        assert "03 30 00" in response.sections


class TestDocumentSearchRequest:
    """Tests for DocumentSearchRequest schema."""

    def test_valid_document_search_request(self):
        """Test creating valid document search request."""
        data = {
            "project_id": "123e4567-e89b-12d3-a456-426614174000",
            "discipline": "structural",
            "document_type": "calculation_sheet",
            "status": "approved",
            "search_text": "beam design",
        }
        request = DocumentSearchRequest(**data)
        assert request.discipline == "structural"
        assert request.document_type == DocumentType.CALCULATION_SHEET

    def test_document_search_request_all_optional(self):
        """Test all fields are optional in search request."""
        data = {}
        request = DocumentSearchRequest(**data)
        assert request.project_id is None
        assert request.discipline is None


class TestDocumentSearchResponse:
    """Tests for DocumentSearchResponse schema."""

    def test_valid_document_search_response(self):
        """Test creating valid document search response."""
        data = {
            "total_count": 2,
            "documents": [
                {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "project_id": "223e4567-e89b-12d3-a456-426614174000",
                    "discipline": "structural",
                    "calculation_type": "beam_design",
                    "version": 1,
                    "inputs": {},
                    "results": {},
                    "formulas": {},
                    "unit_system": "imperial",
                    "created_by": "323e4567-e89b-12d3-a456-426614174000",
                    "created_at": "2024-01-01T00:00:00",
                    "updated_at": "2024-01-01T00:00:00",
                }
            ],
        }
        response = DocumentSearchResponse(**data)
        assert response.total_count == 2
        assert len(response.documents) == 1
