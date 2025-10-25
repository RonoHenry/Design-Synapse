"""
Integration tests for validation API endpoints.

Tests cover:
- POST /api/v1/designs/{id}/validate (validate design)
- GET /api/v1/designs/{id}/validations (get validation history)
- Validation with invalid rule set (404)
- Validation without design access (403)
"""

import pytest
from fastapi import status
from unittest.mock import patch, Mock

from tests.factories import DesignFactory, DesignValidationFactory


class TestValidateDesign:
    """Tests for POST /api/v1/designs/{id}/validate endpoint."""

    def test_validate_design_success_compliant(
        self, client, db_session, auth_headers, test_user_id
    ):
        """Test successful validation of a compliant design."""
        # Create test design
        design = DesignFactory.create(
            project_id=1,
            name="Test Design",
            created_by=test_user_id,
            specification={
                "building_info": {"type": "residential", "total_area": 250.5},
                "compliance": {"setbacks": {"front": 5.0, "rear": 3.0}},
            },
            status="draft",
        )
        db_session.commit()

        # Mock rule engine to return compliant result
        with patch(
            "src.services.validation_service.RuleEngine.load_rule_set"
        ) as mock_load:
            with patch(
                "src.services.validation_service.RuleEngine.validate"
            ) as mock_validate:
                mock_load.return_value = {"name": "Kenya_Building_Code_2020", "rules": []}
                mock_validate.return_value = {
                    "is_compliant": True,
                    "violations": [],
                    "warnings": [],
                }

                # Make request
                response = client.post(
                    f"/api/v1/designs/{design.id}/validate",
                    json={
                        "validation_type": "building_code",
                        "rule_set": "Kenya_Building_Code_2020",
                    },
                    headers=auth_headers,
                )

        # Assertions
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["design_id"] == design.id
        assert data["validation_type"] == "building_code"
        assert data["rule_set"] == "Kenya_Building_Code_2020"
        assert data["is_compliant"] is True
        assert data["violations"] == []
        assert data["warnings"] == []
        assert "validated_at" in data
        assert data["validated_by"] == test_user_id

    def test_validate_design_with_violations(
        self, client, db_session, auth_headers, test_user_id
    ):
        """Test validation of a design with violations."""
        # Create test design
        design = DesignFactory.create(
            project_id=1,
            name="Test Design",
            created_by=test_user_id,
            specification={
                "building_info": {"type": "residential"},
                "compliance": {"setbacks": {"front": 4.5, "rear": 3.0}},
            },
            status="draft",
        )
        db_session.commit()

        expected_violations = [
            {
                "code": "SETBACK_VIOLATION",
                "severity": "critical",
                "rule": "Front setback must be at least 5 meters",
                "current_value": 4.5,
                "required_value": 5.0,
                "location": "front_boundary",
                "suggestion": "Increase front setback by 0.5 meters",
            }
        ]

        # Mock rule engine to return violations
        with patch(
            "src.services.validation_service.RuleEngine.load_rule_set"
        ) as mock_load:
            with patch(
                "src.services.validation_service.RuleEngine.validate"
            ) as mock_validate:
                mock_load.return_value = {"name": "Kenya_Building_Code_2020", "rules": []}
                mock_validate.return_value = {
                    "is_compliant": False,
                    "violations": expected_violations,
                    "warnings": [],
                }

                # Make request
                response = client.post(
                    f"/api/v1/designs/{design.id}/validate",
                    json={
                        "validation_type": "building_code",
                        "rule_set": "Kenya_Building_Code_2020",
                    },
                    headers=auth_headers,
                )

        # Assertions
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["is_compliant"] is False
        assert len(data["violations"]) == 1
        assert data["violations"][0]["code"] == "SETBACK_VIOLATION"
        assert data["violations"][0]["severity"] == "critical"

    def test_validate_design_with_warnings_only(
        self, client, db_session, auth_headers, test_user_id
    ):
        """Test validation of a design with warnings but no violations."""
        # Create test design
        design = DesignFactory.create(
            project_id=1,
            created_by=test_user_id,
            specification={
                "building_info": {"type": "residential"},
                "compliance": {"setbacks": {"front": 5.0, "rear": 3.0}},
            },
            status="draft",
        )
        db_session.commit()

        expected_warnings = [
            {
                "code": "MATERIAL_WARNING",
                "severity": "warning",
                "message": "Consider using locally sourced materials",
            }
        ]

        # Mock rule engine
        with patch(
            "src.services.validation_service.RuleEngine.load_rule_set"
        ) as mock_load:
            with patch(
                "src.services.validation_service.RuleEngine.validate"
            ) as mock_validate:
                mock_load.return_value = {"name": "Kenya_Building_Code_2020", "rules": []}
                mock_validate.return_value = {
                    "is_compliant": True,
                    "violations": [],
                    "warnings": expected_warnings,
                }

                # Make request
                response = client.post(
                    f"/api/v1/designs/{design.id}/validate",
                    json={
                        "validation_type": "building_code",
                        "rule_set": "Kenya_Building_Code_2020",
                    },
                    headers=auth_headers,
                )

        # Assertions
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["is_compliant"] is True
        assert data["violations"] == []
        assert len(data["warnings"]) == 1
        assert data["warnings"][0]["code"] == "MATERIAL_WARNING"

    def test_validate_design_not_found(self, client, auth_headers):
        """Test validating a non-existent design."""
        response = client.post(
            "/api/v1/designs/99999/validate",
            json={
                "validation_type": "building_code",
                "rule_set": "Kenya_Building_Code_2020",
            },
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_validate_design_invalid_rule_set(
        self, client, db_session, auth_headers, test_user_id
    ):
        """Test validation with invalid rule set."""
        # Create test design
        design = DesignFactory.create(
            project_id=1,
            created_by=test_user_id,
            status="draft",
        )
        db_session.commit()

        # Mock rule engine to raise FileNotFoundError
        with patch(
            "src.services.validation_service.RuleEngine.load_rule_set"
        ) as mock_load:
            mock_load.side_effect = FileNotFoundError(
                "Rule set not found: Invalid_Code"
            )

            # Make request
            response = client.post(
                f"/api/v1/designs/{design.id}/validate",
                json={
                    "validation_type": "building_code",
                    "rule_set": "Invalid_Code",
                },
                headers=auth_headers,
            )

        # Assertions
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "rule set" in response.json()["detail"].lower()

    def test_validate_design_without_authentication(
        self, client_no_auth, db_session
    ):
        """Test validating design without authentication."""
        design = DesignFactory.create(project_id=1, created_by=1)
        db_session.commit()

        response = client_no_auth.post(
            f"/api/v1/designs/{design.id}/validate",
            json={
                "validation_type": "building_code",
                "rule_set": "Kenya_Building_Code_2020",
            },
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_validate_design_without_project_access(
        self, client, db_session, auth_headers, mock_project_client
    ):
        """Test validating design when user doesn't have project access."""
        # Create design
        design = DesignFactory.create(project_id=999, created_by=1)
        db_session.commit()

        # Setup mock to raise access denied
        from src.services.project_client import ProjectAccessDeniedError

        mock_project_client.verify_project_access.side_effect = (
            ProjectAccessDeniedError("Access denied")
        )

        response = client.post(
            f"/api/v1/designs/{design.id}/validate",
            json={
                "validation_type": "building_code",
                "rule_set": "Kenya_Building_Code_2020",
            },
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_validate_archived_design(
        self, client, db_session, auth_headers, test_user_id
    ):
        """Test validating an archived design returns 404."""
        design = DesignFactory.create(
            project_id=1,
            created_by=test_user_id,
            is_archived=True,
        )
        db_session.commit()

        response = client.post(
            f"/api/v1/designs/{design.id}/validate",
            json={
                "validation_type": "building_code",
                "rule_set": "Kenya_Building_Code_2020",
            },
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_validate_design_missing_required_fields(
        self, client, db_session, auth_headers, test_user_id
    ):
        """Test validation with missing required fields."""
        design = DesignFactory.create(
            project_id=1,
            created_by=test_user_id,
        )
        db_session.commit()

        # Missing validation_type
        response = client.post(
            f"/api/v1/designs/{design.id}/validate",
            json={"rule_set": "Kenya_Building_Code_2020"},
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_validate_design_updates_status(
        self, client, db_session, auth_headers, test_user_id
    ):
        """Test that validation updates the design status."""
        # Create test design
        design = DesignFactory.create(
            project_id=1,
            created_by=test_user_id,
            status="draft",
        )
        db_session.commit()

        # Mock rule engine to return compliant result
        with patch(
            "src.services.validation_service.RuleEngine.load_rule_set"
        ) as mock_load:
            with patch(
                "src.services.validation_service.RuleEngine.validate"
            ) as mock_validate:
                mock_load.return_value = {"name": "Kenya_Building_Code_2020", "rules": []}
                mock_validate.return_value = {
                    "is_compliant": True,
                    "violations": [],
                    "warnings": [],
                }

                # Make request
                response = client.post(
                    f"/api/v1/designs/{design.id}/validate",
                    json={
                        "validation_type": "building_code",
                        "rule_set": "Kenya_Building_Code_2020",
                    },
                    headers=auth_headers,
                )

        # Verify design status was updated
        assert response.status_code == status.HTTP_201_CREATED
        db_session.refresh(design)
        assert design.status == "compliant"


class TestGetValidations:
    """Tests for GET /api/v1/designs/{id}/validations endpoint."""

    def test_get_validations_success(
        self, client, db_session, auth_headers, test_user_id
    ):
        """Test successful retrieval of validation history."""
        # Create test design
        design = DesignFactory.create(
            project_id=1,
            created_by=test_user_id,
        )
        db_session.commit()

        # Create multiple validations
        validation1 = DesignValidationFactory.create(
            design_id=design.id,
            validation_type="building_code",
            rule_set="Kenya_Building_Code_2020",
            is_compliant=False,
            violations=[{"code": "TEST_VIOLATION"}],
            validated_by=test_user_id,
        )
        validation2 = DesignValidationFactory.create(
            design_id=design.id,
            validation_type="building_code",
            rule_set="Kenya_Building_Code_2020",
            is_compliant=True,
            violations=[],
            validated_by=test_user_id,
        )
        db_session.commit()

        # Make request
        response = client.get(
            f"/api/v1/designs/{design.id}/validations",
            headers=auth_headers,
        )

        # Assertions
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2
        # Should be ordered by validated_at descending (newest first)
        assert data[0]["id"] == validation2.id
        assert data[1]["id"] == validation1.id

    def test_get_validations_empty(
        self, client, db_session, auth_headers, test_user_id
    ):
        """Test getting validations when none exist."""
        # Create test design with no validations
        design = DesignFactory.create(
            project_id=1,
            created_by=test_user_id,
        )
        db_session.commit()

        # Make request
        response = client.get(
            f"/api/v1/designs/{design.id}/validations",
            headers=auth_headers,
        )

        # Assertions
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    def test_get_validations_design_not_found(self, client, auth_headers):
        """Test getting validations for non-existent design."""
        response = client.get(
            "/api/v1/designs/99999/validations",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_validations_without_authentication(
        self, client_no_auth, db_session
    ):
        """Test getting validations without authentication."""
        design = DesignFactory.create(project_id=1, created_by=1)
        db_session.commit()

        response = client_no_auth.get(f"/api/v1/designs/{design.id}/validations")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_validations_without_project_access(
        self, client, db_session, auth_headers, mock_project_client
    ):
        """Test getting validations when user doesn't have project access."""
        # Create design
        design = DesignFactory.create(project_id=999, created_by=1)
        db_session.commit()

        # Setup mock to raise access denied
        from src.services.project_client import ProjectAccessDeniedError

        mock_project_client.verify_project_access.side_effect = (
            ProjectAccessDeniedError("Access denied")
        )

        response = client.get(
            f"/api/v1/designs/{design.id}/validations",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_get_validations_archived_design(
        self, client, db_session, auth_headers, test_user_id
    ):
        """Test getting validations for archived design returns 404."""
        design = DesignFactory.create(
            project_id=1,
            created_by=test_user_id,
            is_archived=True,
        )
        db_session.commit()

        response = client.get(
            f"/api/v1/designs/{design.id}/validations",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_validations_multiple_types(
        self, client, db_session, auth_headers, test_user_id
    ):
        """Test getting validations with multiple validation types."""
        # Create test design
        design = DesignFactory.create(
            project_id=1,
            created_by=test_user_id,
        )
        db_session.commit()

        # Create validations of different types
        DesignValidationFactory.create(
            design_id=design.id,
            validation_type="building_code",
            rule_set="Kenya_Building_Code_2020",
            is_compliant=True,
            validated_by=test_user_id,
        )
        DesignValidationFactory.create(
            design_id=design.id,
            validation_type="structural",
            rule_set="Structural_Standards_2020",
            is_compliant=True,
            validated_by=test_user_id,
        )
        db_session.commit()

        # Make request
        response = client.get(
            f"/api/v1/designs/{design.id}/validations",
            headers=auth_headers,
        )

        # Assertions
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 2
        validation_types = {v["validation_type"] for v in data}
        assert "building_code" in validation_types
        assert "structural" in validation_types

    def test_get_validations_includes_all_fields(
        self, client, db_session, auth_headers, test_user_id
    ):
        """Test that validation response includes all expected fields."""
        # Create test design
        design = DesignFactory.create(
            project_id=1,
            created_by=test_user_id,
        )
        db_session.commit()

        # Create validation with all fields
        validation = DesignValidationFactory.create(
            design_id=design.id,
            validation_type="building_code",
            rule_set="Kenya_Building_Code_2020",
            is_compliant=False,
            violations=[
                {
                    "code": "TEST_VIOLATION",
                    "severity": "critical",
                    "message": "Test violation",
                }
            ],
            warnings=[
                {
                    "code": "TEST_WARNING",
                    "severity": "warning",
                    "message": "Test warning",
                }
            ],
            validated_by=test_user_id,
        )
        db_session.commit()

        # Make request
        response = client.get(
            f"/api/v1/designs/{design.id}/validations",
            headers=auth_headers,
        )

        # Assertions
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        
        validation_data = data[0]
        assert "id" in validation_data
        assert "design_id" in validation_data
        assert "validation_type" in validation_data
        assert "rule_set" in validation_data
        assert "is_compliant" in validation_data
        assert "violations" in validation_data
        assert "warnings" in validation_data
        assert "validated_at" in validation_data
        assert "validated_by" in validation_data
        
        assert validation_data["design_id"] == design.id
        assert validation_data["is_compliant"] is False
        assert len(validation_data["violations"]) == 1
        assert len(validation_data["warnings"]) == 1
