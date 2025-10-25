"""Unit tests for DesignOptimization model."""

import pytest
from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError

from src.models.design import Design
from src.models.design_optimization import DesignOptimization
from tests.factories import DesignFactory


class TestDesignOptimizationModel:
    """Test suite for DesignOptimization model."""

    def test_create_design_optimization(self, db_session):
        """Test creating a DesignOptimization with required fields."""
        # Arrange
        design = DesignFactory.create(db_session=db_session)
        db_session.commit()

        # Act
        optimization = DesignOptimization(
            design_id=design.id,
            optimization_type="cost",
            title="Reduce material costs",
            description="Use locally sourced materials to reduce costs by 15%",
            implementation_difficulty="medium"
        )
        db_session.add(optimization)
        db_session.commit()
        db_session.refresh(optimization)

        # Assert
        assert optimization.id is not None
        assert optimization.design_id == design.id
        assert optimization.optimization_type == "cost"
        assert optimization.title == "Reduce material costs"
        assert optimization.description == "Use locally sourced materials to reduce costs by 15%"
        assert optimization.implementation_difficulty == "medium"
        assert optimization.status == "suggested"  # default value
        assert optimization.priority == "medium"  # default value
        assert optimization.created_at is not None
        assert isinstance(optimization.created_at, datetime)

    def test_design_optimization_relationship(self, db_session):
        """Test relationship between DesignOptimization and Design."""
        # Arrange
        design = DesignFactory.create(db_session=db_session)
        db_session.commit()

        # Act
        optimization = DesignOptimization(
            design_id=design.id,
            optimization_type="structural",
            title="Improve structural integrity",
            description="Add reinforcement to load-bearing walls",
            implementation_difficulty="hard"
        )
        db_session.add(optimization)
        db_session.commit()
        db_session.refresh(optimization)
        db_session.refresh(design)

        # Assert
        assert optimization.design == design
        assert optimization in design.optimizations
        assert len(design.optimizations) == 1

    def test_cascade_delete_optimization_with_design(self, db_session):
        """Test that deleting a design cascades to delete optimizations."""
        # Arrange
        design = DesignFactory.create(db_session=db_session)
        db_session.commit()

        optimization1 = DesignOptimization(
            design_id=design.id,
            optimization_type="cost",
            title="Cost optimization",
            description="Reduce costs",
            implementation_difficulty="easy"
        )
        optimization2 = DesignOptimization(
            design_id=design.id,
            optimization_type="sustainability",
            title="Sustainability optimization",
            description="Improve sustainability",
            implementation_difficulty="medium"
        )
        db_session.add_all([optimization1, optimization2])
        db_session.commit()

        optimization1_id = optimization1.id
        optimization2_id = optimization2.id

        # Act - Delete the design
        db_session.delete(design)
        db_session.commit()

        # Assert - Optimizations should be deleted
        assert db_session.get(DesignOptimization, optimization1_id) is None
        assert db_session.get(DesignOptimization, optimization2_id) is None

    def test_status_transition_suggested_to_applied(self, db_session):
        """Test status transition from suggested to applied."""
        # Arrange
        design = DesignFactory.create(db_session=db_session)
        db_session.commit()

        optimization = DesignOptimization(
            design_id=design.id,
            optimization_type="cost",
            title="Cost optimization",
            description="Reduce costs",
            implementation_difficulty="easy",
            status="suggested"
        )
        db_session.add(optimization)
        db_session.commit()

        # Act - Apply the optimization
        optimization.status = "applied"
        optimization.applied_at = datetime.now(timezone.utc)
        optimization.applied_by = 1
        db_session.commit()
        db_session.refresh(optimization)

        # Assert
        assert optimization.status == "applied"
        assert optimization.applied_at is not None
        assert optimization.applied_by == 1

    def test_status_transition_suggested_to_rejected(self, db_session):
        """Test status transition from suggested to rejected."""
        # Arrange
        design = DesignFactory.create(db_session=db_session)
        db_session.commit()

        optimization = DesignOptimization(
            design_id=design.id,
            optimization_type="structural",
            title="Structural optimization",
            description="Improve structure",
            implementation_difficulty="hard",
            status="suggested"
        )
        db_session.add(optimization)
        db_session.commit()

        # Act - Reject the optimization
        optimization.status = "rejected"
        db_session.commit()
        db_session.refresh(optimization)

        # Assert
        assert optimization.status == "rejected"
        assert optimization.applied_at is None
        assert optimization.applied_by is None

    def test_cost_impact_validation(self, db_session):
        """Test that cost impact can be stored and retrieved correctly."""
        # Arrange
        design = DesignFactory.create(db_session=db_session)
        db_session.commit()

        # Act
        optimization = DesignOptimization(
            design_id=design.id,
            optimization_type="cost",
            title="Material cost reduction",
            description="Switch to alternative materials",
            implementation_difficulty="medium",
            estimated_cost_impact=-15.5  # negative means cost reduction
        )
        db_session.add(optimization)
        db_session.commit()
        db_session.refresh(optimization)

        # Assert
        assert optimization.estimated_cost_impact == -15.5

    def test_cost_impact_positive_value(self, db_session):
        """Test that positive cost impact (cost increase) can be stored."""
        # Arrange
        design = DesignFactory.create(db_session=db_session)
        db_session.commit()

        # Act
        optimization = DesignOptimization(
            design_id=design.id,
            optimization_type="structural",
            title="Enhanced structural support",
            description="Add additional reinforcement",
            implementation_difficulty="hard",
            estimated_cost_impact=25.0  # positive means cost increase
        )
        db_session.add(optimization)
        db_session.commit()
        db_session.refresh(optimization)

        # Assert
        assert optimization.estimated_cost_impact == 25.0

    def test_difficulty_validation_easy(self, db_session):
        """Test that 'easy' difficulty level is valid."""
        # Arrange
        design = DesignFactory.create(db_session=db_session)
        db_session.commit()

        # Act
        optimization = DesignOptimization(
            design_id=design.id,
            optimization_type="cost",
            title="Simple optimization",
            description="Easy to implement",
            implementation_difficulty="easy"
        )
        db_session.add(optimization)
        db_session.commit()
        db_session.refresh(optimization)

        # Assert
        assert optimization.implementation_difficulty == "easy"

    def test_difficulty_validation_medium(self, db_session):
        """Test that 'medium' difficulty level is valid."""
        # Arrange
        design = DesignFactory.create(db_session=db_session)
        db_session.commit()

        # Act
        optimization = DesignOptimization(
            design_id=design.id,
            optimization_type="sustainability",
            title="Medium optimization",
            description="Moderate effort required",
            implementation_difficulty="medium"
        )
        db_session.add(optimization)
        db_session.commit()
        db_session.refresh(optimization)

        # Assert
        assert optimization.implementation_difficulty == "medium"

    def test_difficulty_validation_hard(self, db_session):
        """Test that 'hard' difficulty level is valid."""
        # Arrange
        design = DesignFactory.create(db_session=db_session)
        db_session.commit()

        # Act
        optimization = DesignOptimization(
            design_id=design.id,
            optimization_type="structural",
            title="Complex optimization",
            description="Significant effort required",
            implementation_difficulty="hard"
        )
        db_session.add(optimization)
        db_session.commit()
        db_session.refresh(optimization)

        # Assert
        assert optimization.implementation_difficulty == "hard"

    def test_priority_levels(self, db_session):
        """Test different priority levels."""
        # Arrange
        design = DesignFactory.create(db_session=db_session)
        db_session.commit()

        # Act - Create optimizations with different priorities
        opt_low = DesignOptimization(
            design_id=design.id,
            optimization_type="cost",
            title="Low priority",
            description="Minor improvement",
            implementation_difficulty="easy",
            priority="low"
        )
        opt_medium = DesignOptimization(
            design_id=design.id,
            optimization_type="cost",
            title="Medium priority",
            description="Moderate improvement",
            implementation_difficulty="medium",
            priority="medium"
        )
        opt_high = DesignOptimization(
            design_id=design.id,
            optimization_type="structural",
            title="High priority",
            description="Critical improvement",
            implementation_difficulty="hard",
            priority="high"
        )
        db_session.add_all([opt_low, opt_medium, opt_high])
        db_session.commit()

        # Assert
        assert opt_low.priority == "low"
        assert opt_medium.priority == "medium"
        assert opt_high.priority == "high"

    def test_optimization_without_cost_impact(self, db_session):
        """Test that cost impact is optional."""
        # Arrange
        design = DesignFactory.create(db_session=db_session)
        db_session.commit()

        # Act
        optimization = DesignOptimization(
            design_id=design.id,
            optimization_type="sustainability",
            title="Environmental optimization",
            description="Improve sustainability without cost data",
            implementation_difficulty="medium"
        )
        db_session.add(optimization)
        db_session.commit()
        db_session.refresh(optimization)

        # Assert
        assert optimization.estimated_cost_impact is None

    def test_multiple_optimizations_per_design(self, db_session):
        """Test that a design can have multiple optimizations."""
        # Arrange
        design = DesignFactory.create(db_session=db_session)
        db_session.commit()

        # Act
        optimizations = [
            DesignOptimization(
                design_id=design.id,
                optimization_type="cost",
                title=f"Cost optimization {i}",
                description=f"Description {i}",
                implementation_difficulty="easy"
            )
            for i in range(5)
        ]
        db_session.add_all(optimizations)
        db_session.commit()
        db_session.refresh(design)

        # Assert
        assert len(design.optimizations) == 5

    def test_optimization_requires_design_id(self, db_session):
        """Test that design_id is required."""
        # Act & Assert
        with pytest.raises(IntegrityError):
            optimization = DesignOptimization(
                optimization_type="cost",
                title="Invalid optimization",
                description="Missing design_id",
                implementation_difficulty="easy"
            )
            db_session.add(optimization)
            db_session.commit()

    def test_optimization_requires_title(self, db_session):
        """Test that title is required."""
        # Arrange
        design = DesignFactory.create(db_session=db_session)
        db_session.commit()

        # Act & Assert
        with pytest.raises(IntegrityError):
            optimization = DesignOptimization(
                design_id=design.id,
                optimization_type="cost",
                description="Missing title",
                implementation_difficulty="easy"
            )
            db_session.add(optimization)
            db_session.commit()

    def test_optimization_type_variations(self, db_session):
        """Test different optimization types."""
        # Arrange
        design = DesignFactory.create(db_session=db_session)
        db_session.commit()

        # Act
        opt_cost = DesignOptimization(
            design_id=design.id,
            optimization_type="cost",
            title="Cost optimization",
            description="Reduce costs",
            implementation_difficulty="easy"
        )
        opt_structural = DesignOptimization(
            design_id=design.id,
            optimization_type="structural",
            title="Structural optimization",
            description="Improve structure",
            implementation_difficulty="medium"
        )
        opt_sustainability = DesignOptimization(
            design_id=design.id,
            optimization_type="sustainability",
            title="Sustainability optimization",
            description="Improve sustainability",
            implementation_difficulty="hard"
        )
        db_session.add_all([opt_cost, opt_structural, opt_sustainability])
        db_session.commit()

        # Assert
        assert opt_cost.optimization_type == "cost"
        assert opt_structural.optimization_type == "structural"
        assert opt_sustainability.optimization_type == "sustainability"
