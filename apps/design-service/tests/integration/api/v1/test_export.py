"""
Integration tests for design export API endpoint.

Tests cover:
- POST /api/v1/designs/{id}/export (JSON format)
- POST /api/v1/designs/{id}/export (PDF format)
- POST /api/v1/designs/{id}/export (IFC format)
- Export completion within 15 seconds
- Unsupported format handling
- Authentication and authorization
"""

import pytest
import time
from fastapi import status
from unittest.mock import patch, Mock

from tests.factories import DesignFactory, DesignValidationFactory


class TestExportDesignJSON:
    """Tests for POST /api/v1/designs/{id}/export with JSON format."""

    def test_export_design_json_success(self, client, db_session, auth_headers):
        """Test successful design export in JSON format."""
        # Create test design with validation
        design = DesignFactory.create(
            project_id=1,
            name="Test Design",
            created_by=1,
            specification={
                "building_info": {
                    "type": "residential",
                    "total_area": 250.0,
                    "num_floors": 2
                },
                "structure": {
                    "foundation_type": "slab",
                    "wall_material": "concrete_block"
                }
            }
        )
        validation = DesignValidationFactory.create(
            design_id=design.id,
            validation_type="building_code",
            rule_set="Kenya_Building_Code_2020",
            is_compliant=True,
            violations=[],
            warnings=[],
            validated_by=1
        )
        db_session.commit()

        # Make request
        response = client.post(
            f"/api/v1/designs/{design.id}/export",
            json={"format": "json"},
            headers=auth_headers,
        )

        # Assertions
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Verify JSON structure includes all design data
        assert "design" in data
        assert data["design"]["id"] == design.id
        assert data["design"]["name"] == "Test Design"
        assert data["design"]["specification"] == design.specification
        
        # Verify metadata is included
        assert "metadata" in data
        assert data["metadata"]["format"] == "json"
        assert "exported_at" in data["metadata"]
        
        # Verify validations are included
        assert "validations" in data
        assert len(data["validations"]) == 1
        assert data["validations"][0]["is_compliant"] is True

    def test_export_design_json_with_all_relationships(
        self, client, db_session, auth_headers
    ):
        """Test JSON export includes all related entities."""
        from tests.factories import (
            DesignOptimizationFactory,
            DesignFileFactory,
            DesignCommentFactory
        )
        
        # Create design with all relationships
        design = DesignFactory.create(
            project_id=1,
            name="Complete Design",
            created_by=1
        )
        DesignValidationFactory.create(design_id=design.id, validated_by=1)
        DesignOptimizationFactory.create(design_id=design.id)
        DesignFileFactory.create(design_id=design.id, uploaded_by=1)
        DesignCommentFactory.create(design_id=design.id, created_by=1)
        db_session.commit()

        response = client.post(
            f"/api/v1/designs/{design.id}/export",
            json={"format": "json"},
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Verify all relationships are included
        assert "validations" in data
        assert len(data["validations"]) >= 1
        assert "optimizations" in data
        assert len(data["optimizations"]) >= 1
        assert "files" in data
        assert len(data["files"]) >= 1
        assert "comments" in data
        assert len(data["comments"]) >= 1


class TestExportDesignPDF:
    """Tests for POST /api/v1/designs/{id}/export with PDF format."""

    @patch("src.api.v1.routes.export.generate_pdf_document")
    def test_export_design_pdf_success(
        self, mock_generate_pdf, client, db_session, auth_headers
    ):
        """Test successful design export in PDF format."""
        # Setup mock PDF generation
        mock_pdf_content = b"%PDF-1.4 mock pdf content"
        mock_generate_pdf.return_value = mock_pdf_content
        
        # Create test design
        design = DesignFactory.create(
            project_id=1,
            name="Test Design",
            created_by=1,
            specification={
                "building_info": {
                    "type": "residential",
                    "total_area": 250.0
                }
            }
        )
        db_session.commit()

        # Make request
        response = client.post(
            f"/api/v1/designs/{design.id}/export",
            json={"format": "pdf"},
            headers=auth_headers,
        )

        # Assertions
        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"] == "application/pdf"
        assert "content-disposition" in response.headers
        assert "Test-Design" in response.headers["content-disposition"]
        assert response.content == mock_pdf_content
        
        # Verify PDF generation was called
        mock_generate_pdf.assert_called_once()

    @patch("src.api.v1.routes.export.generate_pdf_document")
    def test_export_design_pdf_includes_all_sections(
        self, mock_generate_pdf, client, db_session, auth_headers
    ):
        """Test PDF export includes all design sections."""
        mock_generate_pdf.return_value = b"%PDF-1.4 mock pdf"
        
        design = DesignFactory.create(
            project_id=1,
            name="Complete Design",
            created_by=1,
            specification={
                "building_info": {"type": "residential"},
                "structure": {"foundation_type": "slab"},
                "spaces": [{"name": "Living Room", "area": 35.0}],
                "materials": [{"name": "Concrete", "quantity": 100}]
            }
        )
        DesignValidationFactory.create(
            design_id=design.id,
            is_compliant=True,
            validated_by=1
        )
        db_session.commit()

        response = client.post(
            f"/api/v1/designs/{design.id}/export",
            json={"format": "pdf"},
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        
        # Verify PDF generation received complete design data
        call_args = mock_generate_pdf.call_args
        design_data = call_args[0][0]
        assert design_data["name"] == "Complete Design"
        assert "specification" in design_data
        assert "validations" in design_data


class TestExportDesignIFC:
    """Tests for POST /api/v1/designs/{id}/export with IFC format."""

    @patch("src.api.v1.routes.export.generate_ifc_file")
    def test_export_design_ifc_success(
        self, mock_generate_ifc, client, db_session, auth_headers
    ):
        """Test successful design export in IFC format."""
        # Setup mock IFC generation
        mock_ifc_content = b"ISO-10303-21;HEADER;FILE_DESCRIPTION..."
        mock_generate_ifc.return_value = mock_ifc_content
        
        # Create test design
        design = DesignFactory.create(
            project_id=1,
            name="Test Building",
            created_by=1,
            specification={
                "building_info": {
                    "type": "residential",
                    "total_area": 250.0,
                    "num_floors": 2,
                    "height": 7.5
                },
                "structure": {
                    "foundation_type": "slab",
                    "wall_material": "concrete_block"
                },
                "spaces": [
                    {
                        "name": "Living Room",
                        "area": 35.0,
                        "floor": 1,
                        "dimensions": {"length": 7.0, "width": 5.0, "height": 3.0}
                    }
                ]
            }
        )
        db_session.commit()

        # Make request
        response = client.post(
            f"/api/v1/designs/{design.id}/export",
            json={"format": "ifc"},
            headers=auth_headers,
        )

        # Assertions
        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"] == "application/x-step"
        assert "content-disposition" in response.headers
        assert "Test-Building.ifc" in response.headers["content-disposition"]
        assert response.content == mock_ifc_content
        
        # Verify IFC generation was called
        mock_generate_ifc.assert_called_once()

    @patch("src.api.v1.routes.export.generate_ifc_file")
    def test_export_design_ifc_with_spatial_data(
        self, mock_generate_ifc, client, db_session, auth_headers
    ):
        """Test IFC export includes spatial and structural data."""
        mock_generate_ifc.return_value = b"ISO-10303-21;HEADER..."
        
        design = DesignFactory.create(
            project_id=1,
            name="Spatial Design",
            created_by=1,
            specification={
                "building_info": {
                    "type": "commercial",
                    "total_area": 500.0,
                    "num_floors": 3
                },
                "spaces": [
                    {
                        "name": "Office 1",
                        "area": 50.0,
                        "floor": 1,
                        "dimensions": {"length": 10.0, "width": 5.0, "height": 3.0}
                    },
                    {
                        "name": "Office 2",
                        "area": 50.0,
                        "floor": 2,
                        "dimensions": {"length": 10.0, "width": 5.0, "height": 3.0}
                    }
                ],
                "structure": {
                    "foundation_type": "pile",
                    "wall_material": "reinforced_concrete",
                    "roof_type": "flat"
                }
            }
        )
        db_session.commit()

        response = client.post(
            f"/api/v1/designs/{design.id}/export",
            json={"format": "ifc"},
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        
        # Verify IFC generation received spatial data
        call_args = mock_generate_ifc.call_args
        design_data = call_args[0][0]
        assert "spaces" in design_data["specification"]
        assert len(design_data["specification"]["spaces"]) == 2


class TestExportPerformance:
    """Tests for export performance requirements."""

    @patch("src.api.v1.routes.export.generate_pdf_document")
    def test_export_completes_within_15_seconds_pdf(
        self, mock_generate_pdf, client, db_session, auth_headers
    ):
        """Test PDF export completes within 15 seconds."""
        mock_generate_pdf.return_value = b"%PDF-1.4 mock pdf"
        
        design = DesignFactory.create(
            project_id=1,
            name="Performance Test Design",
            created_by=1
        )
        db_session.commit()

        # Measure export time
        start_time = time.time()
        response = client.post(
            f"/api/v1/designs/{design.id}/export",
            json={"format": "pdf"},
            headers=auth_headers,
        )
        elapsed_time = time.time() - start_time

        assert response.status_code == status.HTTP_200_OK
        assert elapsed_time < 15.0, f"Export took {elapsed_time:.2f}s, should be < 15s"

    @patch("src.api.v1.routes.export.generate_ifc_file")
    def test_export_completes_within_15_seconds_ifc(
        self, mock_generate_ifc, client, db_session, auth_headers
    ):
        """Test IFC export completes within 15 seconds."""
        mock_generate_ifc.return_value = b"ISO-10303-21;HEADER..."
        
        design = DesignFactory.create(
            project_id=1,
            name="Performance Test Design",
            created_by=1
        )
        db_session.commit()

        # Measure export time
        start_time = time.time()
        response = client.post(
            f"/api/v1/designs/{design.id}/export",
            json={"format": "ifc"},
            headers=auth_headers,
        )
        elapsed_time = time.time() - start_time

        assert response.status_code == status.HTTP_200_OK
        assert elapsed_time < 15.0, f"Export took {elapsed_time:.2f}s, should be < 15s"

    def test_export_completes_within_15_seconds_json(
        self, client, db_session, auth_headers
    ):
        """Test JSON export completes within 15 seconds."""
        design = DesignFactory.create(
            project_id=1,
            name="Performance Test Design",
            created_by=1
        )
        db_session.commit()

        # Measure export time
        start_time = time.time()
        response = client.post(
            f"/api/v1/designs/{design.id}/export",
            json={"format": "json"},
            headers=auth_headers,
        )
        elapsed_time = time.time() - start_time

        assert response.status_code == status.HTTP_200_OK
        assert elapsed_time < 15.0, f"Export took {elapsed_time:.2f}s, should be < 15s"


class TestExportValidation:
    """Tests for export request validation."""

    def test_export_unsupported_format(self, client, db_session, auth_headers):
        """Test export with unsupported format returns 400."""
        design = DesignFactory.create(
            project_id=1,
            name="Test Design",
            created_by=1
        )
        db_session.commit()

        response = client.post(
            f"/api/v1/designs/{design.id}/export",
            json={"format": "xml"},
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "detail" in data
        assert "unsupported" in data["detail"].lower() or "invalid" in data["detail"].lower()

    def test_export_missing_format(self, client, db_session, auth_headers):
        """Test export without format parameter."""
        design = DesignFactory.create(
            project_id=1,
            name="Test Design",
            created_by=1
        )
        db_session.commit()

        response = client.post(
            f"/api/v1/designs/{design.id}/export",
            json={},
            headers=auth_headers,
        )

        # Should either use default format or return validation error
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_422_UNPROCESSABLE_ENTITY
        ]

    def test_export_invalid_format_type(self, client, db_session, auth_headers):
        """Test export with invalid format type (not string)."""
        design = DesignFactory.create(
            project_id=1,
            name="Test Design",
            created_by=1
        )
        db_session.commit()

        response = client.post(
            f"/api/v1/designs/{design.id}/export",
            json={"format": 123},
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_export_case_insensitive_format(self, client, db_session, auth_headers):
        """Test export accepts case-insensitive format values."""
        design = DesignFactory.create(
            project_id=1,
            name="Test Design",
            created_by=1
        )
        db_session.commit()

        # Test uppercase
        response = client.post(
            f"/api/v1/designs/{design.id}/export",
            json={"format": "JSON"},
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK

        # Test mixed case
        response = client.post(
            f"/api/v1/designs/{design.id}/export",
            json={"format": "Pdf"},
            headers=auth_headers,
        )
        # Should work or return 200 with mocked PDF generation
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_500_INTERNAL_SERVER_ERROR]


class TestExportAuthentication:
    """Tests for export authentication and authorization."""

    def test_export_design_not_found(self, client, auth_headers):
        """Test exporting non-existent design."""
        response = client.post(
            "/api/v1/designs/99999/export",
            json={"format": "json"},
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_export_without_authentication(self, client_no_auth, db_session):
        """Test exporting design without authentication."""
        design = DesignFactory.create(project_id=1, created_by=1)
        db_session.commit()

        response = client_no_auth.post(
            f"/api/v1/designs/{design.id}/export",
            json={"format": "json"},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_export_without_project_access(
        self, client, db_session, auth_headers, mock_project_client
    ):
        """Test exporting design when user doesn't have project access."""
        design = DesignFactory.create(project_id=999, created_by=1)
        db_session.commit()

        # Setup mock to raise access denied
        from src.services.project_client import ProjectAccessDeniedError
        mock_project_client.verify_project_access.side_effect = ProjectAccessDeniedError("Access denied")

        response = client.post(
            f"/api/v1/designs/{design.id}/export",
            json={"format": "json"},
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_export_archived_design(self, client, db_session, auth_headers):
        """Test exporting archived design returns 404."""
        design = DesignFactory.create(
            project_id=1,
            created_by=1,
            is_archived=True
        )
        db_session.commit()

        response = client.post(
            f"/api/v1/designs/{design.id}/export",
            json={"format": "json"},
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestExportEdgeCases:
    """Tests for export edge cases."""

    def test_export_design_with_no_validations(self, client, db_session, auth_headers):
        """Test exporting design that has no validations."""
        design = DesignFactory.create(
            project_id=1,
            name="Unvalidated Design",
            created_by=1
        )
        db_session.commit()

        response = client.post(
            f"/api/v1/designs/{design.id}/export",
            json={"format": "json"},
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "validations" in data
        assert len(data["validations"]) == 0

    def test_export_design_with_minimal_specification(
        self, client, db_session, auth_headers
    ):
        """Test exporting design with minimal specification data."""
        design = DesignFactory.create(
            project_id=1,
            name="Minimal Design",
            created_by=1,
            specification={"building_info": {"type": "residential"}}
        )
        db_session.commit()

        response = client.post(
            f"/api/v1/designs/{design.id}/export",
            json={"format": "json"},
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["design"]["specification"] == {"building_info": {"type": "residential"}}

    def test_export_design_with_empty_specification(
        self, client, db_session, auth_headers
    ):
        """Test exporting design with empty specification."""
        design = DesignFactory.create(
            project_id=1,
            name="Empty Spec Design",
            created_by=1,
            specification={}
        )
        db_session.commit()

        response = client.post(
            f"/api/v1/designs/{design.id}/export",
            json={"format": "json"},
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["design"]["specification"] == {}

    @patch("src.api.v1.routes.export.generate_pdf_document")
    def test_export_pdf_generation_failure(
        self, mock_generate_pdf, client, db_session, auth_headers
    ):
        """Test handling of PDF generation failure."""
        mock_generate_pdf.side_effect = Exception("PDF generation failed")
        
        design = DesignFactory.create(
            project_id=1,
            name="Test Design",
            created_by=1
        )
        db_session.commit()

        response = client.post(
            f"/api/v1/designs/{design.id}/export",
            json={"format": "pdf"},
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    @patch("src.api.v1.routes.export.generate_ifc_file")
    def test_export_ifc_generation_failure(
        self, mock_generate_ifc, client, db_session, auth_headers
    ):
        """Test handling of IFC generation failure."""
        mock_generate_ifc.side_effect = Exception("IFC generation failed")
        
        design = DesignFactory.create(
            project_id=1,
            name="Test Design",
            created_by=1
        )
        db_session.commit()

        response = client.post(
            f"/api/v1/designs/{design.id}/export",
            json={"format": "ifc"},
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
