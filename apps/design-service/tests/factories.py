"""
Factory classes for creating test data in the design service.

This module provides factory_boy factories for all design service models,
following the established patterns from other services.
"""

import os
import sys
from datetime import datetime, timezone
from typing import Optional

import factory

# Add packages to path for shared testing infrastructure
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "..", "packages"))

from common.testing.base_factory import BaseFactory, FakerMixin, TimestampMixin
# Import models
from src.models.design import Design
from src.models.design_comment import DesignComment
from src.models.design_file import DesignFile
from src.models.design_optimization import DesignOptimization
from src.models.design_validation import DesignValidation


class DesignFactory(BaseFactory):
    """Factory for creating Design instances."""

    class Meta:
        model = Design
        sqlalchemy_session_persistence = "commit"
        exclude = (
            "created_at",
            "updated_at",
            "db_session",
        )  # Exclude timestamp fields and session

    # Basic fields
    name = factory.Sequence(lambda n: f"Design {n}")
    description = factory.Faker("text", max_nb_chars=500)
    project_id = factory.Sequence(lambda n: n)

    # Design specification (structured JSON)
    specification = factory.LazyFunction(
        lambda: {
            "building_info": {
                "type": "residential",
                "subtype": "single_family",
                "total_area": 250.5,
                "num_floors": 2,
                "height": 7.5,
            },
            "structure": {
                "foundation_type": "slab",
                "wall_material": "concrete_block",
                "roof_type": "pitched",
                "roof_material": "clay_tiles",
            },
            "spaces": [
                {
                    "name": "Living Room",
                    "area": 35.0,
                    "floor": 1,
                    "dimensions": {"length": 7.0, "width": 5.0, "height": 3.0},
                }
            ],
            "materials": [
                {
                    "name": "Concrete Blocks",
                    "quantity": 5000,
                    "unit": "pieces",
                    "estimated_cost": 150000,
                }
            ],
            "compliance": {
                "building_code": "Kenya_Building_Code_2020",
                "zoning": "residential_low_density",
                "setbacks": {"front": 5.0, "rear": 3.0, "side": 2.0},
            },
        }
    )

    # Metadata
    building_type = "residential"
    total_area = 250.5
    num_floors = 2
    materials = factory.LazyFunction(lambda: ["concrete_block", "clay_tiles", "steel"])

    # AI generation metadata
    generation_prompt = factory.Faker("text", max_nb_chars=200)
    confidence_score = 85.5
    ai_model_version = "gpt-4"

    # Version control
    version = 1
    parent_design_id = None

    # Status and compliance
    status = "draft"
    is_archived = False

    # Audit fields
    created_by = factory.Sequence(lambda n: n)

    # Visual output fields
    floor_plan_url = None
    rendering_url = None
    model_file_url = None
    visual_generation_status = "not_requested"
    visual_generation_error = None
    visual_generated_at = None

    class Params:
        """Traits for different design types."""

        residential = factory.Trait(
            building_type="residential", total_area=250.5, num_floors=2
        )

        commercial = factory.Trait(
            building_type="commercial", total_area=500.0, num_floors=3
        )

        industrial = factory.Trait(
            building_type="industrial", total_area=1000.0, num_floors=1
        )

        validated = factory.Trait(status="validated")

        compliant = factory.Trait(status="compliant")

        archived = factory.Trait(is_archived=True)

        # Visual output traits
        with_visuals = factory.Trait(
            floor_plan_url=factory.Faker("url"),
            rendering_url=factory.Faker("url"),
            model_file_url=factory.Faker("url"),
            visual_generation_status="completed",
            visual_generated_at=factory.LazyFunction(
                lambda: datetime.now(timezone.utc)
            ),
        )

        without_visuals = factory.Trait(
            floor_plan_url=None,
            rendering_url=None,
            model_file_url=None,
            visual_generation_status="pending",
            visual_generation_error=None,
            visual_generated_at=None,
        )

        processing_visuals = factory.Trait(
            floor_plan_url=None,
            rendering_url=None,
            model_file_url=None,
            visual_generation_status="processing",
            visual_generation_error=None,
            visual_generated_at=None,
        )

        failed_visuals = factory.Trait(
            floor_plan_url=None,
            rendering_url=None,
            model_file_url=None,
            visual_generation_status="failed",
            visual_generation_error=factory.Faker("sentence"),
            visual_generated_at=None,
        )


class DesignValidationFactory(BaseFactory):
    """Factory for creating DesignValidation instances."""

    class Meta:
        model = DesignValidation
        sqlalchemy_session_persistence = "commit"
        exclude = (
            "validated_at",
            "created_at",
            "updated_at",
            "design",
            "db_session",
        )  # Exclude timestamp fields, relationship, and session

    design_id = factory.Sequence(lambda n: n)
    design = factory.SubFactory(DesignFactory)

    # Validation metadata
    validation_type = "building_code"
    rule_set = "Kenya_Building_Code_2020"

    # Results
    is_compliant = True
    violations = factory.LazyFunction(list)
    warnings = factory.LazyFunction(list)

    # Audit
    validated_by = factory.Sequence(lambda n: n)

    @factory.lazy_attribute
    def design_id(self):
        """Set design_id from design relationship if not explicitly provided."""
        if self.design:
            return self.design.id
        return None

    class Params:
        """Traits for different validation scenarios."""

        compliant = factory.Trait(
            is_compliant=True,
            violations=factory.LazyFunction(list),
            warnings=factory.LazyFunction(list),
        )

        with_violations = factory.Trait(
            is_compliant=False,
            violations=factory.LazyFunction(
                lambda: [
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
            ),
        )

        with_warnings = factory.Trait(
            is_compliant=True,
            warnings=factory.LazyFunction(
                lambda: [
                    {
                        "code": "MATERIAL_WARNING",
                        "severity": "warning",
                        "message": "Consider using locally sourced materials for cost efficiency",
                    }
                ]
            ),
        )


class DesignOptimizationFactory(BaseFactory):
    """Factory for creating DesignOptimization instances."""

    class Meta:
        model = DesignOptimization
        sqlalchemy_session_persistence = "commit"
        exclude = (
            "created_at",
            "updated_at",
            "design",
            "db_session",
        )  # Exclude timestamp fields, relationship, and session

    design_id = factory.Sequence(lambda n: n)
    design = factory.SubFactory(DesignFactory)

    # Optimization details
    optimization_type = "cost"
    title = factory.Sequence(lambda n: f"Optimization {n}")
    description = factory.Faker("text", max_nb_chars=300)

    # Impact analysis
    estimated_cost_impact = -15.0
    implementation_difficulty = "medium"
    priority = "medium"

    # Application status
    status = "suggested"
    applied_at = None
    applied_by = None

    @factory.lazy_attribute
    def design_id(self):
        """Set design_id from design relationship if not explicitly provided."""
        if self.design:
            return self.design.id
        return None

    class Params:
        """Traits for different optimization types."""

        cost = factory.Trait(
            optimization_type="cost",
            title="Cost optimization suggestion",
            estimated_cost_impact=-15.0,
        )

        structural = factory.Trait(
            optimization_type="structural",
            title="Structural optimization suggestion",
            estimated_cost_impact=-8.0,
        )

        sustainability = factory.Trait(
            optimization_type="sustainability",
            title="Sustainability optimization suggestion",
            estimated_cost_impact=5.0,
        )

        applied = factory.Trait(
            status="applied", applied_by=factory.Sequence(lambda n: n)
        )

        rejected = factory.Trait(status="rejected")


class DesignFileFactory(BaseFactory):
    """Factory for creating DesignFile instances."""

    class Meta:
        model = DesignFile
        sqlalchemy_session_persistence = "commit"
        exclude = (
            "uploaded_at",
            "created_at",
            "updated_at",
            "design",
        )  # Exclude timestamp fields and relationship

    design_id = factory.Sequence(lambda n: n)
    design = factory.SubFactory(DesignFactory)

    # File metadata
    filename = factory.Sequence(lambda n: f"design_file_{n}.pdf")
    file_type = "pdf"
    file_size = 1024000  # 1MB in bytes
    storage_path = factory.LazyAttribute(lambda obj: f"/storage/designs/{obj.filename}")

    # Optional description
    description = factory.Faker("text", max_nb_chars=200)

    # Audit
    uploaded_by = factory.Sequence(lambda n: n)

    @factory.lazy_attribute
    def design_id(self):
        """Set design_id from design relationship if not explicitly provided."""
        if self.design:
            return self.design.id
        return None

    class Params:
        """Traits for different file types."""

        pdf = factory.Trait(
            filename=factory.Sequence(lambda n: f"design_{n}.pdf"),
            file_type="pdf",
            file_size=1024000,
        )

        dwg = factory.Trait(
            filename=factory.Sequence(lambda n: f"design_{n}.dwg"),
            file_type="dwg",
            file_size=2048000,
        )

        image = factory.Trait(
            filename=factory.Sequence(lambda n: f"design_{n}.png"),
            file_type="png",
            file_size=512000,
        )

        large = factory.Trait(file_size=50 * 1024 * 1024)  # 50MB


class DesignCommentFactory(BaseFactory):
    """Factory for creating DesignComment instances."""

    class Meta:
        model = DesignComment
        sqlalchemy_session_persistence = "commit"
        exclude = (
            "created_at",
            "updated_at",
            "design",
        )  # Exclude timestamp fields and relationship

    design_id = factory.Sequence(lambda n: n)
    design = factory.SubFactory(DesignFactory)

    # Comment content
    content = factory.Faker("text", max_nb_chars=500)

    # Optional spatial positioning
    position_x = None
    position_y = None
    position_z = None

    # Audit
    created_by = factory.Sequence(lambda n: n)
    is_edited = False

    @factory.lazy_attribute
    def design_id(self):
        """Set design_id from design relationship if not explicitly provided."""
        if self.design:
            return self.design.id
        return None

    class Params:
        """Traits for different comment types."""

        with_position = factory.Trait(position_x=10.5, position_y=20.3, position_z=5.0)

        edited = factory.Trait(is_edited=True)


# Convenience functions for common test scenarios


def create_design_with_validations(session, num_validations: int = 2, **design_kwargs):
    """
    Create a design with a specified number of validations.

    Args:
        session: SQLAlchemy session
        num_validations: Number of validations to create
        **design_kwargs: Additional design attributes

    Returns:
        Design instance with validations
    """
    DesignFactory._meta.sqlalchemy_session = session
    DesignValidationFactory._meta.sqlalchemy_session = session

    design = DesignFactory.create(**design_kwargs)
    DesignValidationFactory.create_batch(num_validations, design=design)

    return design


def create_design_with_optimizations(
    session, num_optimizations: int = 3, **design_kwargs
):
    """
    Create a design with a specified number of optimization suggestions.

    Args:
        session: SQLAlchemy session
        num_optimizations: Number of optimizations to create
        **design_kwargs: Additional design attributes

    Returns:
        Design instance with optimizations
    """
    DesignFactory._meta.sqlalchemy_session = session
    DesignOptimizationFactory._meta.sqlalchemy_session = session

    design = DesignFactory.create(**design_kwargs)
    DesignOptimizationFactory.create_batch(num_optimizations, design=design)

    return design


def create_design_with_files(session, num_files: int = 3, **design_kwargs):
    """
    Create a design with a specified number of attached files.

    Args:
        session: SQLAlchemy session
        num_files: Number of files to create
        **design_kwargs: Additional design attributes

    Returns:
        Design instance with files
    """
    DesignFactory._meta.sqlalchemy_session = session
    DesignFileFactory._meta.sqlalchemy_session = session

    design = DesignFactory.create(**design_kwargs)
    DesignFileFactory.create_batch(num_files, design=design)

    return design


def create_design_with_comments(session, num_comments: int = 5, **design_kwargs):
    """
    Create a design with a specified number of comments.

    Args:
        session: SQLAlchemy session
        num_comments: Number of comments to create
        **design_kwargs: Additional design attributes

    Returns:
        Design instance with comments
    """
    DesignFactory._meta.sqlalchemy_session = session
    DesignCommentFactory._meta.sqlalchemy_session = session

    design = DesignFactory.create(**design_kwargs)
    DesignCommentFactory.create_batch(num_comments, design=design)

    return design


def create_complete_design(session, **design_kwargs):
    """
    Create a design with all related entities (validations, optimizations, files, comments).

    Args:
        session: SQLAlchemy session
        **design_kwargs: Additional design attributes

    Returns:
        Design instance with all relationships populated
    """
    DesignFactory._meta.sqlalchemy_session = session
    DesignValidationFactory._meta.sqlalchemy_session = session
    DesignOptimizationFactory._meta.sqlalchemy_session = session
    DesignFileFactory._meta.sqlalchemy_session = session
    DesignCommentFactory._meta.sqlalchemy_session = session

    design = DesignFactory.create(**design_kwargs)

    # Add validations
    DesignValidationFactory.create_batch(2, design=design)

    # Add optimizations
    DesignOptimizationFactory.create_batch(3, design=design)

    # Add files
    DesignFileFactory.create_batch(2, design=design)

    # Add comments
    DesignCommentFactory.create_batch(3, design=design)

    return design


def create_design_version_chain(session, num_versions: int = 3, **design_kwargs):
    """
    Create a chain of design versions.

    Args:
        session: SQLAlchemy session
        num_versions: Number of versions to create
        **design_kwargs: Additional design attributes

    Returns:
        List of design versions (oldest to newest)
    """
    DesignFactory._meta.sqlalchemy_session = session

    versions = []
    parent = None

    for i in range(num_versions):
        design = DesignFactory.create(
            version=i + 1,
            parent_design_id=parent.id if parent else None,
            **design_kwargs,
        )
        versions.append(design)
        parent = design

    return versions
