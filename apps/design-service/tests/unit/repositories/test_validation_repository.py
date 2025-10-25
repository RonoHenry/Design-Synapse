"""Unit tests for ValidationRepository."""
import pytest
from datetime import datetime
from sqlalchemy.orm import Session

from src.models.design_validation import DesignValidation
from src.repositories.validation_repository import ValidationRepository
from tests.factories import DesignFactory, DesignValidationFactory


class TestValidationRepository:
    """Test suite for ValidationRepository."""

    @pytest.fixture
    def repository(self, db_session: Session):
        """Create a ValidationRepository instance."""
        return ValidationRepository(db_session)

    def test_create_validation(self, repository: ValidationRepository, db_session: Session):
        """Test creating a validation."""
        # Create a design first
        design = DesignFactory.create(db_session=db_session)
        db_session.commit()

        validation_data = {
            "design_id": design.id,
            "validation_type": "building_code",
            "rule_set": "Kenya_Building_Code_2020",
            "is_compliant": True,
            "violations": [],
            "warnings": [],
            "validated_by": 1,
        }

        validation = repository.create_validation(**validation_data)

        assert validation.id is not None
        assert validation.design_id == design.id
        assert validation.validation_type == "building_code"
        assert validation.rule_set == "Kenya_Building_Code_2020"
        assert validation.is_compliant is True
        assert validation.violations == []
        assert validation.warnings == []
        assert validation.validated_by == 1
        assert validation.validated_at is not None

        # Verify it's in the database
        db_validation = db_session.query(DesignValidation).filter_by(id=validation.id).first()
        assert db_validation is not None
        assert db_validation.design_id == design.id

    def test_create_validation_with_violations(
        self, repository: ValidationRepository, db_session: Session
    ):
        """Test creating a validation with violations."""
        design = DesignFactory.create(db_session=db_session)
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

        validation_data = {
            "design_id": design.id,
            "validation_type": "building_code",
            "rule_set": "Kenya_Building_Code_2020",
            "is_compliant": False,
            "violations": violations,
            "warnings": [],
            "validated_by": 1,
        }

        validation = repository.create_validation(**validation_data)

        assert validation.is_compliant is False
        assert len(validation.violations) == 1
        assert validation.violations[0]["code"] == "SETBACK_VIOLATION"
        assert validation.violations[0]["severity"] == "critical"

    def test_create_validation_with_warnings(
        self, repository: ValidationRepository, db_session: Session
    ):
        """Test creating a validation with warnings."""
        design = DesignFactory.create(db_session=db_session)
        db_session.commit()

        warnings = [
            {
                "code": "MATERIAL_WARNING",
                "severity": "warning",
                "message": "Consider using locally sourced materials for cost efficiency"
            }
        ]

        validation_data = {
            "design_id": design.id,
            "validation_type": "structural",
            "rule_set": "Kenya_Building_Code_2020",
            "is_compliant": True,
            "violations": [],
            "warnings": warnings,
            "validated_by": 1,
        }

        validation = repository.create_validation(**validation_data)

        assert validation.is_compliant is True
        assert len(validation.warnings) == 1
        assert validation.warnings[0]["code"] == "MATERIAL_WARNING"

    def test_get_validations_by_design_id(
        self, repository: ValidationRepository, db_session: Session
    ):
        """Test getting all validations for a design."""
        design = DesignFactory.create(db_session=db_session)
        db_session.commit()

        # Create multiple validations for the design
        DesignValidationFactory.create(
            design_id=design.id,
            validation_type="building_code"
        )
        DesignValidationFactory.create(
            design_id=design.id,
            validation_type="structural"
        )
        DesignValidationFactory.create(
            design_id=design.id,
            validation_type="safety"
        )
        db_session.commit()

        validations = repository.get_validations_by_design_id(design.id)

        assert len(validations) == 3
        assert all(v.design_id == design.id for v in validations)

    def test_get_validations_by_design_id_empty(
        self, repository: ValidationRepository, db_session: Session
    ):
        """Test getting validations for a design with no validations."""
        design = DesignFactory.create(db_session=db_session)
        db_session.commit()

        validations = repository.get_validations_by_design_id(design.id)

        assert validations == []

    def test_get_validations_by_design_id_ordered_by_date(
        self, repository: ValidationRepository, db_session: Session
    ):
        """Test that validations are ordered by validated_at descending (newest first)."""
        design = DesignFactory.create(db_session=db_session)
        db_session.commit()

        # Create validations (they will have different timestamps)
        val1 = DesignValidationFactory.create(
            db_session=db_session,
            design_id=design.id,
            validation_type="building_code"
        )
        db_session.commit()
        db_session.refresh(val1)

        val2 = DesignValidationFactory.create(
            db_session=db_session,
            design_id=design.id,
            validation_type="structural"
        )
        db_session.commit()
        db_session.refresh(val2)

        val3 = DesignValidationFactory.create(
            db_session=db_session,
            design_id=design.id,
            validation_type="safety"
        )
        db_session.commit()
        db_session.refresh(val3)

        validations = repository.get_validations_by_design_id(design.id)

        # Newest should be first
        assert len(validations) == 3
        assert validations[0].id == val3.id
        assert validations[1].id == val2.id
        assert validations[2].id == val1.id

    def test_get_validations_by_design_id_filters_other_designs(
        self, repository: ValidationRepository, db_session: Session
    ):
        """Test that only validations for the specified design are returned."""
        design1 = DesignFactory.create(db_session=db_session)
        design2 = DesignFactory.create(db_session=db_session)
        db_session.commit()

        # Create validations for both designs
        DesignValidationFactory.create_batch(2, db_session=db_session, design_id=design1.id)
        DesignValidationFactory.create_batch(3, db_session=db_session, design_id=design2.id)
        db_session.commit()

        validations = repository.get_validations_by_design_id(design1.id)

        assert len(validations) == 2
        assert all(v.design_id == design1.id for v in validations)

    def test_get_latest_validation(
        self, repository: ValidationRepository, db_session: Session
    ):
        """Test getting the latest validation for a design."""
        design = DesignFactory.create(db_session=db_session)
        db_session.commit()

        # Create multiple validations
        val1 = DesignValidationFactory.create(
            db_session=db_session,
            design_id=design.id,
            validation_type="building_code"
        )
        db_session.commit()
        db_session.refresh(val1)

        val2 = DesignValidationFactory.create(
            db_session=db_session,
            design_id=design.id,
            validation_type="structural"
        )
        db_session.commit()
        db_session.refresh(val2)

        val3 = DesignValidationFactory.create(
            db_session=db_session,
            design_id=design.id,
            validation_type="safety"
        )
        db_session.commit()
        db_session.refresh(val3)

        latest = repository.get_latest_validation(design.id)

        assert latest is not None
        assert latest.id == val3.id  # Should be the most recent one

    def test_get_latest_validation_no_validations(
        self, repository: ValidationRepository, db_session: Session
    ):
        """Test getting latest validation when there are no validations."""
        design = DesignFactory.create(db_session=db_session)
        db_session.commit()

        latest = repository.get_latest_validation(design.id)

        assert latest is None

    def test_get_latest_validation_single_validation(
        self, repository: ValidationRepository, db_session: Session
    ):
        """Test getting latest validation when there's only one validation."""
        design = DesignFactory.create(db_session=db_session)
        db_session.commit()

        validation = DesignValidationFactory.create(
            db_session=db_session,
            design_id=design.id
        )
        db_session.commit()

        latest = repository.get_latest_validation(design.id)

        assert latest is not None
        assert latest.id == validation.id

    def test_get_latest_validation_filters_by_design(
        self, repository: ValidationRepository, db_session: Session
    ):
        """Test that latest validation is specific to the design."""
        design1 = DesignFactory.create(db_session=db_session)
        design2 = DesignFactory.create(db_session=db_session)
        db_session.commit()

        # Create validations for both designs
        val1 = DesignValidationFactory.create(
            db_session=db_session,
            design_id=design1.id
        )
        db_session.commit()
        db_session.refresh(val1)

        val2 = DesignValidationFactory.create(
            db_session=db_session,
            design_id=design2.id
        )
        db_session.commit()
        db_session.refresh(val2)

        latest1 = repository.get_latest_validation(design1.id)
        latest2 = repository.get_latest_validation(design2.id)

        assert latest1.id == val1.id
        assert latest2.id == val2.id
        assert latest1.id != latest2.id
