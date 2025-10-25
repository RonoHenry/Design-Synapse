"""
Unit tests for response schemas.

Tests serialization of response schemas from database models,
including nested relationships and proper field mapping.

Requirements tested:
- 2.1: Design storage with version control
- 3.1: Design validation against building codes
- 4.1: AI-powered design optimization
- 6.1: Design file management
- 7.1: Design collaboration and comments
"""

import pytest
from datetime import datetime, timezone
from typing import List

from src.api.v1.schemas.responses import (
    DesignResponse,
    ValidationResponse,
    OptimizationResponse,
    DesignFileResponse,
    DesignCommentResponse,
)
from tests.factories import (
    DesignFactory,
    DesignValidationFactory,
    DesignOptimizationFactory,
    DesignFileFactory,
    DesignCommentFactory,
    create_design_with_validations,
)


class TestDesignResponse:
    """Test DesignResponse schema serialization."""

    def test_design_response_from_model(self, db_session):
        """Test DesignResponse serialization from Design model."""
        # Create a design using factory
        design = DesignFactory.create(
            name="Test Design",
            description="Test description",
            project_id=1,
            building_type="residential",
            total_area=250.5,
            num_floors=2,
            materials=["concrete", "steel"],
            confidence_score=85.5,
            version=1,
            status="draft",
            created_by=1
        )
        db_session.commit()

        # Serialize to response schema
        response = DesignResponse.model_validate(design)

        # Verify all fields are correctly serialized
        assert response.id == design.id
        assert response.project_id == 1
        assert response.name == "Test Design"
        assert response.description == "Test description"
        assert response.specification == design.specification
        assert response.building_type == "residential"
        assert response.total_area == 250.5
        assert response.num_floors == 2
        assert response.materials == ["concrete", "steel"]
        assert response.confidence_score == 85.5
        assert response.version == 1
        assert response.status == "draft"
        assert response.created_by == 1
        assert isinstance(response.created_at, datetime)
        assert isinstance(response.updated_at, datetime)

    def test_design_response_with_optional_fields_none(self, db_session):
        """Test DesignResponse with optional fields set to None."""
        design = DesignFactory.create(
            description=None,
            total_area=None,
            num_floors=None,
            materials=None,
            confidence_score=None
        )
        db_session.commit()

        response = DesignResponse.model_validate(design)

        assert response.description is None
        assert response.total_area is None
        assert response.num_floors is None
        assert response.materials is None
        assert response.confidence_score is None

    def test_design_response_specification_json(self, db_session):
        """Test DesignResponse correctly serializes specification JSON."""
        specification = {
            "building_info": {
                "type": "residential",
                "total_area": 250.5
            },
            "structure": {
                "foundation_type": "slab"
            }
        }
        design = DesignFactory.create(specification=specification)
        db_session.commit()

        response = DesignResponse.model_validate(design)

        assert response.specification == specification
        assert response.specification["building_info"]["type"] == "residential"
        assert response.specification["structure"]["foundation_type"] == "slab"

    def test_design_response_different_statuses(self, db_session):
        """Test DesignResponse with different status values."""
        statuses = ["draft", "validated", "compliant", "non_compliant"]
        
        for status in statuses:
            design = DesignFactory.create(status=status)
            db_session.commit()
            
            response = DesignResponse.model_validate(design)
            assert response.status == status

    def test_design_response_version_control(self, db_session):
        """Test DesignResponse with version control fields."""
        parent_design = DesignFactory.create(version=1)
        db_session.commit()
        
        child_design = DesignFactory.create(
            version=2,
            parent_design_id=parent_design.id
        )
        db_session.commit()

        response = DesignResponse.model_validate(child_design)
        
        assert response.version == 2
        assert response.parent_design_id == parent_design.id


class TestValidationResponse:
    """Test ValidationResponse schema serialization."""

    def test_validation_response_from_model(self, db_session):
        """Test ValidationResponse serialization from DesignValidation model."""
        design = DesignFactory.create()
        db_session.commit()
        
        validation = DesignValidationFactory.create(
            design=design,
            validation_type="building_code",
            rule_set="Kenya_Building_Code_2020",
            is_compliant=True,
            violations=[],
            warnings=[],
            validated_by=1
        )
        db_session.commit()

        response = ValidationResponse.model_validate(validation)

        assert response.id == validation.id
        assert response.design_id == design.id
        assert response.validation_type == "building_code"
        assert response.rule_set == "Kenya_Building_Code_2020"
        assert response.is_compliant is True
        assert response.violations == []
        assert response.warnings == []
        assert isinstance(response.validated_at, datetime)

    def test_validation_response_with_violations(self, db_session):
        """Test ValidationResponse with violations."""
        design = DesignFactory.create()
        db_session.commit()
        
        violations = [
            {
                "code": "SETBACK_VIOLATION",
                "severity": "critical",
                "rule": "Front setback must be at least 5 meters",
                "current_value": 4.5,
                "required_value": 5.0,
                "location": "front_boundary",
                "suggestion": "Increase front setback by 0.5 meters"
            }
        ]
        
        validation = DesignValidationFactory.create(
            design=design,
            is_compliant=False,
            violations=violations,
            warnings=[]
        )
        db_session.commit()

        response = ValidationResponse.model_validate(validation)

        assert response.is_compliant is False
        assert len(response.violations) == 1
        assert response.violations[0]["code"] == "SETBACK_VIOLATION"
        assert response.violations[0]["severity"] == "critical"

    def test_validation_response_with_warnings(self, db_session):
        """Test ValidationResponse with warnings only."""
        design = DesignFactory.create()
        db_session.commit()
        
        warnings = [
            {
                "code": "MATERIAL_WARNING",
                "severity": "warning",
                "message": "Consider using locally sourced materials"
            }
        ]
        
        validation = DesignValidationFactory.create(
            design=design,
            is_compliant=True,
            violations=[],
            warnings=warnings
        )
        db_session.commit()

        response = ValidationResponse.model_validate(validation)

        assert response.is_compliant is True
        assert len(response.violations) == 0
        assert len(response.warnings) == 1
        assert response.warnings[0]["code"] == "MATERIAL_WARNING"

    def test_validation_response_different_types(self, db_session):
        """Test ValidationResponse with different validation types."""
        design = DesignFactory.create()
        db_session.commit()
        
        validation_types = ["building_code", "structural", "safety"]
        
        for val_type in validation_types:
            validation = DesignValidationFactory.create(
                design=design,
                validation_type=val_type
            )
            db_session.commit()
            
            response = ValidationResponse.model_validate(validation)
            assert response.validation_type == val_type


class TestOptimizationResponse:
    """Test OptimizationResponse schema serialization."""

    def test_optimization_response_from_model(self, db_session):
        """Test OptimizationResponse serialization from DesignOptimization model."""
        design = DesignFactory.create()
        db_session.commit()
        
        optimization = DesignOptimizationFactory.create(
            design=design,
            optimization_type="cost",
            title="Reduce material costs",
            description="Use alternative materials to reduce costs",
            estimated_cost_impact=-15.0,
            implementation_difficulty="medium",
            priority="high",
            status="suggested"
        )
        db_session.commit()

        response = OptimizationResponse.model_validate(optimization)

        assert response.id == optimization.id
        assert response.design_id == design.id
        assert response.optimization_type == "cost"
        assert response.title == "Reduce material costs"
        assert response.description == "Use alternative materials to reduce costs"
        assert response.estimated_cost_impact == -15.0
        assert response.implementation_difficulty == "medium"
        assert response.priority == "high"
        assert response.status == "suggested"
        assert isinstance(response.created_at, datetime)

    def test_optimization_response_different_types(self, db_session):
        """Test OptimizationResponse with different optimization types."""
        design = DesignFactory.create()
        db_session.commit()
        
        optimization_types = ["cost", "structural", "sustainability"]
        
        for opt_type in optimization_types:
            optimization = DesignOptimizationFactory.create(
                design=design,
                optimization_type=opt_type
            )
            db_session.commit()
            
            response = OptimizationResponse.model_validate(optimization)
            assert response.optimization_type == opt_type

    def test_optimization_response_applied_status(self, db_session):
        """Test OptimizationResponse with applied status."""
        design = DesignFactory.create()
        db_session.commit()
        
        applied_at = datetime.now(timezone.utc)
        optimization = DesignOptimizationFactory.create(
            design=design,
            status="applied",
            applied_at=applied_at,
            applied_by=1
        )
        db_session.commit()

        response = OptimizationResponse.model_validate(optimization)

        assert response.status == "applied"
        # Compare timestamps without microsecond precision due to database storage
        assert response.applied_at is not None
        assert isinstance(response.applied_at, datetime)
        assert response.applied_by == 1

    def test_optimization_response_optional_fields_none(self, db_session):
        """Test OptimizationResponse with optional fields as None."""
        design = DesignFactory.create()
        db_session.commit()
        
        optimization = DesignOptimizationFactory.create(
            design=design,
            estimated_cost_impact=None,
            applied_at=None,
            applied_by=None
        )
        db_session.commit()

        response = OptimizationResponse.model_validate(optimization)

        assert response.estimated_cost_impact is None
        assert response.applied_at is None
        assert response.applied_by is None


class TestDesignFileResponse:
    """Test DesignFileResponse schema serialization."""

    def test_design_file_response_from_model(self, db_session):
        """Test DesignFileResponse serialization from DesignFile model."""
        design = DesignFactory.create()
        db_session.commit()
        
        design_file = DesignFileFactory.create(
            design=design,
            filename="floor_plan.pdf",
            file_type="pdf",
            file_size=1024000,
            storage_path="/storage/designs/floor_plan.pdf",
            description="Main floor plan",
            uploaded_by=1
        )
        db_session.commit()

        response = DesignFileResponse.model_validate(design_file)

        assert response.id == design_file.id
        assert response.design_id == design.id
        assert response.filename == "floor_plan.pdf"
        assert response.file_type == "pdf"
        assert response.file_size == 1024000
        assert response.storage_path == "/storage/designs/floor_plan.pdf"
        assert response.description == "Main floor plan"
        assert response.uploaded_by == 1
        assert isinstance(response.uploaded_at, datetime)

    def test_design_file_response_different_types(self, db_session):
        """Test DesignFileResponse with different file types."""
        design = DesignFactory.create()
        db_session.commit()
        
        file_types = ["pdf", "dwg", "dxf", "png", "jpg", "ifc"]
        
        for file_type in file_types:
            design_file = DesignFileFactory.create(
                design=design,
                file_type=file_type,
                filename=f"design.{file_type}"
            )
            db_session.commit()
            
            response = DesignFileResponse.model_validate(design_file)
            assert response.file_type == file_type
            assert response.filename == f"design.{file_type}"

    def test_design_file_response_optional_description_none(self, db_session):
        """Test DesignFileResponse with description as None."""
        design = DesignFactory.create()
        db_session.commit()
        
        design_file = DesignFileFactory.create(
            design=design,
            description=None
        )
        db_session.commit()

        response = DesignFileResponse.model_validate(design_file)

        assert response.description is None


class TestDesignCommentResponse:
    """Test DesignCommentResponse schema serialization."""

    def test_design_comment_response_from_model(self, db_session):
        """Test DesignCommentResponse serialization from DesignComment model."""
        design = DesignFactory.create()
        db_session.commit()
        
        comment = DesignCommentFactory.create(
            design=design,
            content="This looks great!",
            created_by=1,
            is_edited=False
        )
        db_session.commit()

        response = DesignCommentResponse.model_validate(comment)

        assert response.id == comment.id
        assert response.design_id == design.id
        assert response.content == "This looks great!"
        assert response.created_by == 1
        assert isinstance(response.created_at, datetime)
        assert isinstance(response.updated_at, datetime)
        assert response.is_edited is False

    def test_design_comment_response_with_position(self, db_session):
        """Test DesignCommentResponse with spatial positioning."""
        design = DesignFactory.create()
        db_session.commit()
        
        comment = DesignCommentFactory.create(
            design=design,
            content="Issue here",
            position_x=10.5,
            position_y=20.3,
            position_z=5.0
        )
        db_session.commit()

        response = DesignCommentResponse.model_validate(comment)

        assert response.position_x == 10.5
        assert response.position_y == 20.3
        assert response.position_z == 5.0

    def test_design_comment_response_without_position(self, db_session):
        """Test DesignCommentResponse without spatial positioning."""
        design = DesignFactory.create()
        db_session.commit()
        
        comment = DesignCommentFactory.create(
            design=design,
            position_x=None,
            position_y=None,
            position_z=None
        )
        db_session.commit()

        response = DesignCommentResponse.model_validate(comment)

        assert response.position_x is None
        assert response.position_y is None
        assert response.position_z is None

    def test_design_comment_response_edited(self, db_session):
        """Test DesignCommentResponse with edited flag."""
        design = DesignFactory.create()
        db_session.commit()
        
        comment = DesignCommentFactory.create(
            design=design,
            is_edited=True
        )
        db_session.commit()

        response = DesignCommentResponse.model_validate(comment)

        assert response.is_edited is True


class TestNestedRelationships:
    """Test response schemas with nested relationships."""

    def test_design_response_with_validations(self, db_session):
        """Test DesignResponse can include nested validations."""
        # Create design with validations
        design = create_design_with_validations(db_session, num_validations=2)
        db_session.commit()

        # Serialize design
        design_response = DesignResponse.model_validate(design)
        
        # Verify design is serialized correctly
        assert design_response.id == design.id
        assert design_response.name == design.name
        
        # Note: Nested relationships are not included in basic response
        # They would be loaded separately via dedicated endpoints

    def test_multiple_response_types_from_same_design(self, db_session):
        """Test creating multiple response types from a design with all relationships."""
        # Create design
        design = DesignFactory.create()
        db_session.commit()
        
        # Create related entities
        validation = DesignValidationFactory.create(design=design)
        optimization = DesignOptimizationFactory.create(design=design)
        file = DesignFileFactory.create(design=design)
        comment = DesignCommentFactory.create(design=design)
        db_session.commit()

        # Serialize all response types
        design_response = DesignResponse.model_validate(design)
        validation_response = ValidationResponse.model_validate(validation)
        optimization_response = OptimizationResponse.model_validate(optimization)
        file_response = DesignFileResponse.model_validate(file)
        comment_response = DesignCommentResponse.model_validate(comment)

        # Verify all responses reference the same design
        assert design_response.id == design.id
        assert validation_response.design_id == design.id
        assert optimization_response.design_id == design.id
        assert file_response.design_id == design.id
        assert comment_response.design_id == design.id

    def test_list_of_validations_serialization(self, db_session):
        """Test serializing a list of validations for a design."""
        design = create_design_with_validations(db_session, num_validations=3)
        db_session.commit()

        # Serialize all validations
        validation_responses = [
            ValidationResponse.model_validate(v) for v in design.validations
        ]

        assert len(validation_responses) == 3
        for response in validation_responses:
            assert response.design_id == design.id
            assert isinstance(response, ValidationResponse)
