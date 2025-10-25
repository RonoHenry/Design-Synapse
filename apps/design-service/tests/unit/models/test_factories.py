"""
Tests for factory classes to verify they create valid model instances.

This test module ensures all factories in tests/factories.py can successfully
create valid model instances that pass model validation.
"""

import pytest
from sqlalchemy.orm import Session

from tests.factories import (
    DesignFactory,
    DesignValidationFactory,
    DesignOptimizationFactory,
    DesignFileFactory,
    DesignCommentFactory,
    create_design_with_validations,
    create_design_with_optimizations,
    create_design_with_files,
    create_design_with_comments,
    create_complete_design,
    create_design_version_chain,
)
from src.models.design import Design
from src.models.design_validation import DesignValidation
from src.models.design_optimization import DesignOptimization
from src.models.design_file import DesignFile
from src.models.design_comment import DesignComment


class TestDesignFactory:
    """Tests for DesignFactory."""

    def test_create_design(self, db_session: Session):
        """Test that DesignFactory creates a valid Design instance."""
        DesignFactory._meta.sqlalchemy_session = db_session
        
        design = DesignFactory.create()
        
        assert design.id is not None
        assert design.name is not None
        assert design.project_id is not None
        assert design.building_type == "residential"
        assert design.specification is not None
        assert isinstance(design.specification, dict)
        assert design.status == "draft"
        assert design.version == 1
        assert design.created_by is not None

    def test_create_design_with_custom_values(self, db_session: Session):
        """Test creating a design with custom values."""
        DesignFactory._meta.sqlalchemy_session = db_session
        
        design = DesignFactory.create(
            name="Custom Design",
            building_type="commercial",
            status="validated"
        )
        
        assert design.name == "Custom Design"
        assert design.building_type == "commercial"
        assert design.status == "validated"

    def test_create_design_with_traits(self, db_session: Session):
        """Test creating designs with different traits."""
        DesignFactory._meta.sqlalchemy_session = db_session
        
        # Test commercial trait
        commercial = DesignFactory.create(commercial=True)
        assert commercial.building_type == "commercial"
        assert commercial.total_area == 500.0
        assert commercial.num_floors == 3
        
        # Test industrial trait
        industrial = DesignFactory.create(industrial=True)
        assert industrial.building_type == "industrial"
        assert industrial.total_area == 1000.0
        assert industrial.num_floors == 1
        
        # Test validated trait
        validated = DesignFactory.create(validated=True)
        assert validated.status == "validated"
        
        # Test archived trait
        archived = DesignFactory.create(archived=True)
        assert archived.is_archived is True

    def test_create_design_batch(self, db_session: Session):
        """Test creating multiple designs at once."""
        DesignFactory._meta.sqlalchemy_session = db_session
        
        designs = DesignFactory.create_batch(5)
        
        assert len(designs) == 5
        assert all(isinstance(d, Design) for d in designs)
        assert all(d.id is not None for d in designs)


class TestDesignValidationFactory:
    """Tests for DesignValidationFactory."""

    def test_create_validation(self, db_session: Session):
        """Test that DesignValidationFactory creates a valid instance."""
        DesignFactory._meta.sqlalchemy_session = db_session
        DesignValidationFactory._meta.sqlalchemy_session = db_session
        
        design = DesignFactory.create()
        validation = DesignValidationFactory.create(design=design)
        
        assert validation.id is not None
        assert validation.design_id == design.id
        assert validation.validation_type == "building_code"
        assert validation.rule_set == "Kenya_Building_Code_2020"
        assert validation.is_compliant is True
        assert isinstance(validation.violations, list)
        assert isinstance(validation.warnings, list)

    def test_create_validation_with_violations(self, db_session: Session):
        """Test creating a validation with violations."""
        DesignFactory._meta.sqlalchemy_session = db_session
        DesignValidationFactory._meta.sqlalchemy_session = db_session
        
        design = DesignFactory.create()
        validation = DesignValidationFactory.create(
            design=design,
            with_violations=True
        )
        
        assert validation.is_compliant is False
        assert len(validation.violations) > 0
        assert validation.violations[0]["code"] == "SETBACK_VIOLATION"

    def test_create_validation_with_warnings(self, db_session: Session):
        """Test creating a validation with warnings."""
        DesignFactory._meta.sqlalchemy_session = db_session
        DesignValidationFactory._meta.sqlalchemy_session = db_session
        
        design = DesignFactory.create()
        validation = DesignValidationFactory.create(
            design=design,
            with_warnings=True
        )
        
        assert validation.is_compliant is True
        assert len(validation.warnings) > 0


class TestDesignOptimizationFactory:
    """Tests for DesignOptimizationFactory."""

    def test_create_optimization(self, db_session: Session):
        """Test that DesignOptimizationFactory creates a valid instance."""
        DesignFactory._meta.sqlalchemy_session = db_session
        DesignOptimizationFactory._meta.sqlalchemy_session = db_session
        
        design = DesignFactory.create()
        optimization = DesignOptimizationFactory.create(design=design)
        
        assert optimization.id is not None
        assert optimization.design_id == design.id
        assert optimization.optimization_type == "cost"
        assert optimization.title is not None
        assert optimization.description is not None
        assert optimization.implementation_difficulty == "medium"
        assert optimization.status == "suggested"

    def test_create_optimization_with_traits(self, db_session: Session):
        """Test creating optimizations with different traits."""
        DesignFactory._meta.sqlalchemy_session = db_session
        DesignOptimizationFactory._meta.sqlalchemy_session = db_session
        
        design = DesignFactory.create()
        
        # Test structural trait
        structural = DesignOptimizationFactory.create(
            design=design,
            structural=True
        )
        assert structural.optimization_type == "structural"
        
        # Test sustainability trait
        sustainability = DesignOptimizationFactory.create(
            design=design,
            sustainability=True
        )
        assert sustainability.optimization_type == "sustainability"
        
        # Test applied trait
        applied = DesignOptimizationFactory.create(
            design=design,
            applied=True
        )
        assert applied.status == "applied"
        assert applied.applied_by is not None


class TestDesignFileFactory:
    """Tests for DesignFileFactory."""

    def test_create_file(self, db_session: Session):
        """Test that DesignFileFactory creates a valid instance."""
        DesignFactory._meta.sqlalchemy_session = db_session
        DesignFileFactory._meta.sqlalchemy_session = db_session
        
        design = DesignFactory.create()
        file = DesignFileFactory.create(design=design)
        
        assert file.id is not None
        assert file.design_id == design.id
        assert file.filename is not None
        assert file.file_type == "pdf"
        assert file.file_size == 1024000
        assert file.storage_path is not None
        assert file.uploaded_by is not None

    def test_create_file_with_traits(self, db_session: Session):
        """Test creating files with different traits."""
        DesignFactory._meta.sqlalchemy_session = db_session
        DesignFileFactory._meta.sqlalchemy_session = db_session
        
        design = DesignFactory.create()
        
        # Test DWG trait
        dwg = DesignFileFactory.create(design=design, dwg=True)
        assert dwg.file_type == "dwg"
        assert dwg.file_size == 2048000
        
        # Test image trait
        image = DesignFileFactory.create(design=design, image=True)
        assert image.file_type == "png"
        
        # Test large file trait
        large = DesignFileFactory.create(design=design, large=True)
        assert large.file_size == 50 * 1024 * 1024


class TestDesignCommentFactory:
    """Tests for DesignCommentFactory."""

    def test_create_comment(self, db_session: Session):
        """Test that DesignCommentFactory creates a valid instance."""
        DesignFactory._meta.sqlalchemy_session = db_session
        DesignCommentFactory._meta.sqlalchemy_session = db_session
        
        design = DesignFactory.create()
        comment = DesignCommentFactory.create(design=design)
        
        assert comment.id is not None
        assert comment.design_id == design.id
        assert comment.content is not None
        assert comment.created_by is not None
        assert comment.is_edited is False
        assert comment.position_x is None
        assert comment.position_y is None
        assert comment.position_z is None

    def test_create_comment_with_position(self, db_session: Session):
        """Test creating a comment with spatial positioning."""
        DesignFactory._meta.sqlalchemy_session = db_session
        DesignCommentFactory._meta.sqlalchemy_session = db_session
        
        design = DesignFactory.create()
        comment = DesignCommentFactory.create(
            design=design,
            with_position=True
        )
        
        assert comment.position_x == 10.5
        assert comment.position_y == 20.3
        assert comment.position_z == 5.0

    def test_create_edited_comment(self, db_session: Session):
        """Test creating an edited comment."""
        DesignFactory._meta.sqlalchemy_session = db_session
        DesignCommentFactory._meta.sqlalchemy_session = db_session
        
        design = DesignFactory.create()
        comment = DesignCommentFactory.create(
            design=design,
            edited=True
        )
        
        assert comment.is_edited is True


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_create_design_with_validations(self, db_session: Session):
        """Test creating a design with validations."""
        design = create_design_with_validations(db_session, num_validations=3)
        
        assert design.id is not None
        assert len(design.validations) == 3
        assert all(isinstance(v, DesignValidation) for v in design.validations)

    def test_create_design_with_optimizations(self, db_session: Session):
        """Test creating a design with optimizations."""
        design = create_design_with_optimizations(db_session, num_optimizations=4)
        
        assert design.id is not None
        assert len(design.optimizations) == 4
        assert all(isinstance(o, DesignOptimization) for o in design.optimizations)

    def test_create_design_with_files(self, db_session: Session):
        """Test creating a design with files."""
        design = create_design_with_files(db_session, num_files=2)
        
        assert design.id is not None
        assert len(design.files) == 2
        assert all(isinstance(f, DesignFile) for f in design.files)

    def test_create_design_with_comments(self, db_session: Session):
        """Test creating a design with comments."""
        design = create_design_with_comments(db_session, num_comments=5)
        
        assert design.id is not None
        assert len(design.comments) == 5
        assert all(isinstance(c, DesignComment) for c in design.comments)

    def test_create_complete_design(self, db_session: Session):
        """Test creating a design with all relationships."""
        design = create_complete_design(db_session)
        
        assert design.id is not None
        assert len(design.validations) == 2
        assert len(design.optimizations) == 3
        assert len(design.files) == 2
        assert len(design.comments) == 3

    def test_create_design_version_chain(self, db_session: Session):
        """Test creating a chain of design versions."""
        versions = create_design_version_chain(db_session, num_versions=4)
        
        assert len(versions) == 4
        assert versions[0].version == 1
        assert versions[0].parent_design_id is None
        assert versions[1].version == 2
        assert versions[1].parent_design_id == versions[0].id
        assert versions[2].version == 3
        assert versions[2].parent_design_id == versions[1].id
        assert versions[3].version == 4
        assert versions[3].parent_design_id == versions[2].id
