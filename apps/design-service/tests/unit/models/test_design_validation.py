"""Unit tests for DesignValidation model."""
import pytest
from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError

from src.models.design import Design
from src.models.design_validation import DesignValidation
from tests.factories import DesignFactory


class TestDesignValidationModel:
    """Test suite for DesignValidation model."""

    def test_create_design_validation_with_required_fields(self, db_session):
        """Test creating a DesignValidation with all required fields."""
        # Arrange
        design = DesignFactory.create(db_session=db_session)
        db_session.commit()

        # Act
        validation = DesignValidation(
            design_id=design.id,
            validation_type="building_code",
            rule_set="Kenya_Building_Code_2020",
            is_compliant=True,
            validated_by=1
        )
        db_session.add(validation)
        db_session.commit()
        db_session.refresh(validation)

        # Assert
        assert validation.id is not None
        assert validation.design_id == design.id
        assert validation.validation_type == "building_code"
        assert validation.rule_set == "Kenya_Building_Code_2020"
        assert validation.is_compliant is True
        assert validation.validated_by == 1
        assert validation.validated_at is not None
        assert isinstance(validation.validated_at, datetime)

    def test_create_design_validation_with_design_relationship(self, db_session):
        """Test creating a DesignValidation with proper design relationship."""
        # Arrange
        design = DesignFactory.create(db_session=db_session)
        db_session.commit()

        # Act
        validation = DesignValidation(
            design_id=design.id,
            validation_type="structural",
            rule_set="Kenya_Building_Code_2020",
            is_compliant=False,
            validated_by=1
        )
        db_session.add(validation)
        db_session.commit()
        db_session.refresh(validation)

        # Assert
        assert validation.design is not None
        assert validation.design.id == design.id
        assert validation.design.name == design.name
        assert validation in design.validations

    def test_cascade_delete_design_deletes_validations(self, db_session):
        """Test that deleting a design cascades to delete its validations."""
        # Arrange
        design = DesignFactory.create(db_session=db_session)
        db_session.commit()

        validation1 = DesignValidation(
            design_id=design.id,
            validation_type="building_code",
            rule_set="Kenya_Building_Code_2020",
            is_compliant=True,
            validated_by=1
        )
        validation2 = DesignValidation(
            design_id=design.id,
            validation_type="structural",
            rule_set="Kenya_Building_Code_2020",
            is_compliant=False,
            validated_by=1
        )
        db_session.add_all([validation1, validation2])
        db_session.commit()

        validation1_id = validation1.id
        validation2_id = validation2.id

        # Act - Delete the design
        db_session.delete(design)
        db_session.commit()

        # Assert - Validations should be deleted
        assert db_session.query(DesignValidation).filter_by(id=validation1_id).first() is None
        assert db_session.query(DesignValidation).filter_by(id=validation2_id).first() is None

    def test_violations_json_field_storage(self, db_session):
        """Test storing and retrieving violations as JSON."""
        # Arrange
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
            },
            {
                "code": "HEIGHT_VIOLATION",
                "severity": "critical",
                "rule": "Maximum building height is 12 meters",
                "current_value": 13.5,
                "required_value": 12.0,
                "location": "building_height"
            }
        ]

        # Act
        validation = DesignValidation(
            design_id=design.id,
            validation_type="building_code",
            rule_set="Kenya_Building_Code_2020",
            is_compliant=False,
            violations=violations,
            validated_by=1
        )
        db_session.add(validation)
        db_session.commit()
        db_session.refresh(validation)

        # Assert
        assert validation.violations is not None
        assert len(validation.violations) == 2
        assert validation.violations[0]["code"] == "SETBACK_VIOLATION"
        assert validation.violations[0]["severity"] == "critical"
        assert validation.violations[1]["code"] == "HEIGHT_VIOLATION"
        assert validation.violations[1]["current_value"] == 13.5

    def test_warnings_json_field_storage(self, db_session):
        """Test storing and retrieving warnings as JSON."""
        # Arrange
        design = DesignFactory.create(db_session=db_session)
        db_session.commit()

        warnings = [
            {
                "code": "VENTILATION_WARNING",
                "severity": "warning",
                "rule": "Recommended window area is 10% of floor area",
                "current_value": 8.5,
                "recommended_value": 10.0,
                "suggestion": "Consider increasing window area for better ventilation"
            }
        ]

        # Act
        validation = DesignValidation(
            design_id=design.id,
            validation_type="building_code",
            rule_set="Kenya_Building_Code_2020",
            is_compliant=True,
            warnings=warnings,
            validated_by=1
        )
        db_session.add(validation)
        db_session.commit()
        db_session.refresh(validation)

        # Assert
        assert validation.warnings is not None
        assert len(validation.warnings) == 1
        assert validation.warnings[0]["code"] == "VENTILATION_WARNING"
        assert validation.warnings[0]["severity"] == "warning"

    def test_empty_violations_and_warnings_default_to_empty_list(self, db_session):
        """Test that violations and warnings default to empty lists."""
        # Arrange
        design = DesignFactory.create(db_session=db_session)
        db_session.commit()

        # Act
        validation = DesignValidation(
            design_id=design.id,
            validation_type="building_code",
            rule_set="Kenya_Building_Code_2020",
            is_compliant=True,
            validated_by=1
        )
        db_session.add(validation)
        db_session.commit()
        db_session.refresh(validation)

        # Assert
        assert validation.violations == []
        assert validation.warnings == []

    def test_is_compliant_flag_true_logic(self, db_session):
        """Test is_compliant flag when design is compliant."""
        # Arrange
        design = DesignFactory.create(db_session=db_session)
        db_session.commit()

        # Act
        validation = DesignValidation(
            design_id=design.id,
            validation_type="building_code",
            rule_set="Kenya_Building_Code_2020",
            is_compliant=True,
            violations=[],
            warnings=[],
            validated_by=1
        )
        db_session.add(validation)
        db_session.commit()
        db_session.refresh(validation)

        # Assert
        assert validation.is_compliant is True
        assert len(validation.violations) == 0

    def test_is_compliant_flag_false_logic(self, db_session):
        """Test is_compliant flag when design has violations."""
        # Arrange
        design = DesignFactory.create(db_session=db_session)
        db_session.commit()

        violations = [
            {
                "code": "SETBACK_VIOLATION",
                "severity": "critical",
                "rule": "Front setback must be at least 5 meters"
            }
        ]

        # Act
        validation = DesignValidation(
            design_id=design.id,
            validation_type="building_code",
            rule_set="Kenya_Building_Code_2020",
            is_compliant=False,
            violations=violations,
            validated_by=1
        )
        db_session.add(validation)
        db_session.commit()
        db_session.refresh(validation)

        # Assert
        assert validation.is_compliant is False
        assert len(validation.violations) > 0

    def test_multiple_validations_for_same_design(self, db_session):
        """Test that a design can have multiple validations."""
        # Arrange
        design = DesignFactory.create(db_session=db_session)
        db_session.commit()

        # Act
        validation1 = DesignValidation(
            design_id=design.id,
            validation_type="building_code",
            rule_set="Kenya_Building_Code_2020",
            is_compliant=True,
            validated_by=1
        )
        validation2 = DesignValidation(
            design_id=design.id,
            validation_type="structural",
            rule_set="Kenya_Building_Code_2020",
            is_compliant=False,
            validated_by=1
        )
        validation3 = DesignValidation(
            design_id=design.id,
            validation_type="safety",
            rule_set="Kenya_Building_Code_2020",
            is_compliant=True,
            validated_by=2
        )
        db_session.add_all([validation1, validation2, validation3])
        db_session.commit()

        # Assert
        db_session.refresh(design)
        assert len(design.validations) == 3
        assert validation1 in design.validations
        assert validation2 in design.validations
        assert validation3 in design.validations

    def test_validation_type_field(self, db_session):
        """Test different validation types."""
        # Arrange
        design = DesignFactory.create(db_session=db_session)
        db_session.commit()

        validation_types = ["building_code", "structural", "safety", "sustainability"]

        # Act & Assert
        for vtype in validation_types:
            validation = DesignValidation(
                design_id=design.id,
                validation_type=vtype,
                rule_set="Kenya_Building_Code_2020",
                is_compliant=True,
                validated_by=1
            )
            db_session.add(validation)
            db_session.commit()
            db_session.refresh(validation)

            assert validation.validation_type == vtype

    def test_rule_set_field(self, db_session):
        """Test different rule sets."""
        # Arrange
        design = DesignFactory.create(db_session=db_session)
        db_session.commit()

        rule_sets = [
            "Kenya_Building_Code_2020",
            "Uganda_Building_Code_2019",
            "Tanzania_Building_Code_2018"
        ]

        # Act & Assert
        for rule_set in rule_sets:
            validation = DesignValidation(
                design_id=design.id,
                validation_type="building_code",
                rule_set=rule_set,
                is_compliant=True,
                validated_by=1
            )
            db_session.add(validation)
            db_session.commit()
            db_session.refresh(validation)

            assert validation.rule_set == rule_set

    def test_validated_by_field(self, db_session):
        """Test validated_by field stores user ID."""
        # Arrange
        design = DesignFactory.create(db_session=db_session)
        db_session.commit()

        # Act
        validation = DesignValidation(
            design_id=design.id,
            validation_type="building_code",
            rule_set="Kenya_Building_Code_2020",
            is_compliant=True,
            validated_by=42
        )
        db_session.add(validation)
        db_session.commit()
        db_session.refresh(validation)

        # Assert
        assert validation.validated_by == 42

    def test_validated_at_timestamp_auto_generated(self, db_session):
        """Test that validated_at timestamp is automatically generated."""
        # Arrange
        design = DesignFactory.create(db_session=db_session)
        db_session.commit()

        before_creation = datetime.now(timezone.utc)

        # Act
        validation = DesignValidation(
            design_id=design.id,
            validation_type="building_code",
            rule_set="Kenya_Building_Code_2020",
            is_compliant=True,
            validated_by=1
        )
        db_session.add(validation)
        db_session.commit()
        db_session.refresh(validation)

        after_creation = datetime.now(timezone.utc)

        # Assert
        assert validation.validated_at is not None
        # Convert to timezone-aware if needed for comparison
        validated_at = validation.validated_at
        if validated_at.tzinfo is None:
            validated_at = validated_at.replace(tzinfo=timezone.utc)
        assert before_creation <= validated_at <= after_creation

    def test_missing_required_field_design_id_raises_error(self, db_session):
        """Test that missing design_id raises an error."""
        # Act & Assert
        with pytest.raises(IntegrityError):
            validation = DesignValidation(
                validation_type="building_code",
                rule_set="Kenya_Building_Code_2020",
                is_compliant=True,
                validated_by=1
            )
            db_session.add(validation)
            db_session.commit()

    def test_missing_required_field_validation_type_raises_error(self, db_session):
        """Test that missing validation_type raises an error."""
        # Arrange
        design = DesignFactory.create(db_session=db_session)
        db_session.commit()

        # Act & Assert
        with pytest.raises(IntegrityError):
            validation = DesignValidation(
                design_id=design.id,
                rule_set="Kenya_Building_Code_2020",
                is_compliant=True,
                validated_by=1
            )
            db_session.add(validation)
            db_session.commit()

    def test_missing_required_field_rule_set_raises_error(self, db_session):
        """Test that missing rule_set raises an error."""
        # Arrange
        design = DesignFactory.create(db_session=db_session)
        db_session.commit()

        # Act & Assert
        with pytest.raises(IntegrityError):
            validation = DesignValidation(
                design_id=design.id,
                validation_type="building_code",
                is_compliant=True,
                validated_by=1
            )
            db_session.add(validation)
            db_session.commit()

    def test_missing_required_field_is_compliant_raises_error(self, db_session):
        """Test that missing is_compliant raises an error."""
        # Arrange
        design = DesignFactory.create(db_session=db_session)
        db_session.commit()

        # Act & Assert
        with pytest.raises(IntegrityError):
            validation = DesignValidation(
                design_id=design.id,
                validation_type="building_code",
                rule_set="Kenya_Building_Code_2020",
                validated_by=1
            )
            db_session.add(validation)
            db_session.commit()

    def test_missing_required_field_validated_by_raises_error(self, db_session):
        """Test that missing validated_by raises an error."""
        # Arrange
        design = DesignFactory.create(db_session=db_session)
        db_session.commit()

        # Act & Assert
        with pytest.raises(IntegrityError):
            validation = DesignValidation(
                design_id=design.id,
                validation_type="building_code",
                rule_set="Kenya_Building_Code_2020",
                is_compliant=True
            )
            db_session.add(validation)
            db_session.commit()
