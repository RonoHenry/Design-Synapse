"""Unit tests for OptimizationRepository."""
import pytest
from datetime import datetime
from sqlalchemy.orm import Session

from src.models.design_optimization import DesignOptimization
from src.repositories.optimization_repository import OptimizationRepository
from tests.factories import DesignFactory, DesignOptimizationFactory


class TestOptimizationRepository:
    """Test suite for OptimizationRepository."""

    @pytest.fixture
    def repository(self, db_session: Session):
        """Create an OptimizationRepository instance."""
        return OptimizationRepository(db_session)

    def test_create_optimization(self, repository: OptimizationRepository, db_session: Session):
        """Test creating an optimization."""
        # Create a design first
        design = DesignFactory.create(db_session=db_session)
        db_session.commit()

        optimization_data = {
            "design_id": design.id,
            "optimization_type": "cost",
            "title": "Reduce material costs",
            "description": "Use locally sourced materials to reduce costs by 15%",
            "estimated_cost_impact": -15.0,
            "implementation_difficulty": "easy",
            "priority": "high",
        }

        optimization = repository.create_optimization(**optimization_data)

        assert optimization.id is not None
        assert optimization.design_id == design.id
        assert optimization.optimization_type == "cost"
        assert optimization.title == "Reduce material costs"
        assert optimization.description == "Use locally sourced materials to reduce costs by 15%"
        assert optimization.estimated_cost_impact == -15.0
        assert optimization.implementation_difficulty == "easy"
        assert optimization.priority == "high"
        assert optimization.status == "suggested"
        assert optimization.applied_at is None
        assert optimization.applied_by is None
        assert optimization.created_at is not None

        # Verify it's in the database
        db_optimization = db_session.query(DesignOptimization).filter_by(id=optimization.id).first()
        assert db_optimization is not None
        assert db_optimization.design_id == design.id

    def test_create_optimization_with_defaults(
        self, repository: OptimizationRepository, db_session: Session
    ):
        """Test creating an optimization with default values."""
        design = DesignFactory.create(db_session=db_session)
        db_session.commit()

        optimization_data = {
            "design_id": design.id,
            "optimization_type": "structural",
            "title": "Improve structural integrity",
            "description": "Add reinforcement to load-bearing walls",
            "implementation_difficulty": "medium",
        }

        optimization = repository.create_optimization(**optimization_data)

        # Check defaults
        assert optimization.status == "suggested"
        assert optimization.priority == "medium"
        assert optimization.estimated_cost_impact is None
        assert optimization.applied_at is None
        assert optimization.applied_by is None

    def test_create_optimization_sustainability_type(
        self, repository: OptimizationRepository, db_session: Session
    ):
        """Test creating a sustainability optimization."""
        design = DesignFactory.create(db_session=db_session)
        db_session.commit()

        optimization_data = {
            "design_id": design.id,
            "optimization_type": "sustainability",
            "title": "Install solar panels",
            "description": "Add solar panels to reduce energy consumption",
            "estimated_cost_impact": 10.0,  # Positive = cost increase
            "implementation_difficulty": "hard",
            "priority": "low",
        }

        optimization = repository.create_optimization(**optimization_data)

        assert optimization.optimization_type == "sustainability"
        assert optimization.estimated_cost_impact == 10.0
        assert optimization.implementation_difficulty == "hard"
        assert optimization.priority == "low"

    def test_get_optimizations_by_design_id(
        self, repository: OptimizationRepository, db_session: Session
    ):
        """Test getting all optimizations for a design."""
        design = DesignFactory.create(db_session=db_session)
        db_session.commit()

        # Create multiple optimizations for the design
        DesignOptimizationFactory.create(
            db_session=db_session,
            design_id=design.id,
            optimization_type="cost"
        )
        DesignOptimizationFactory.create(
            db_session=db_session,
            design_id=design.id,
            optimization_type="structural"
        )
        DesignOptimizationFactory.create(
            db_session=db_session,
            design_id=design.id,
            optimization_type="sustainability"
        )
        db_session.commit()

        optimizations = repository.get_optimizations_by_design_id(design.id)

        assert len(optimizations) == 3
        assert all(o.design_id == design.id for o in optimizations)

    def test_get_optimizations_by_design_id_empty(
        self, repository: OptimizationRepository, db_session: Session
    ):
        """Test getting optimizations for a design with no optimizations."""
        design = DesignFactory.create(db_session=db_session)
        db_session.commit()

        optimizations = repository.get_optimizations_by_design_id(design.id)

        assert optimizations == []

    def test_get_optimizations_by_design_id_ordered_by_date(
        self, repository: OptimizationRepository, db_session: Session
    ):
        """Test that optimizations are ordered by created_at descending (newest first)."""
        design = DesignFactory.create(db_session=db_session)
        db_session.commit()

        # Create optimizations (they will have different timestamps)
        opt1 = DesignOptimizationFactory.create(
            db_session=db_session,
            design_id=design.id,
            optimization_type="cost"
        )
        db_session.commit()
        db_session.refresh(opt1)

        opt2 = DesignOptimizationFactory.create(
            db_session=db_session,
            design_id=design.id,
            optimization_type="structural"
        )
        db_session.commit()
        db_session.refresh(opt2)

        opt3 = DesignOptimizationFactory.create(
            db_session=db_session,
            design_id=design.id,
            optimization_type="sustainability"
        )
        db_session.commit()
        db_session.refresh(opt3)

        optimizations = repository.get_optimizations_by_design_id(design.id)

        # Newest should be first
        assert len(optimizations) == 3
        assert optimizations[0].id == opt3.id
        assert optimizations[1].id == opt2.id
        assert optimizations[2].id == opt1.id

    def test_get_optimizations_by_design_id_filters_other_designs(
        self, repository: OptimizationRepository, db_session: Session
    ):
        """Test that only optimizations for the specified design are returned."""
        design1 = DesignFactory.create(db_session=db_session)
        design2 = DesignFactory.create(db_session=db_session)
        db_session.commit()

        # Create optimizations for both designs
        DesignOptimizationFactory.create_batch(2, db_session=db_session, design_id=design1.id)
        DesignOptimizationFactory.create_batch(3, db_session=db_session, design_id=design2.id)
        db_session.commit()

        optimizations = repository.get_optimizations_by_design_id(design1.id)

        assert len(optimizations) == 2
        assert all(o.design_id == design1.id for o in optimizations)

    def test_update_optimization_status_apply(
        self, repository: OptimizationRepository, db_session: Session
    ):
        """Test applying an optimization (updating status to 'applied')."""
        design = DesignFactory.create(db_session=db_session)
        db_session.commit()

        optimization = DesignOptimizationFactory.create(
            db_session=db_session,
            design_id=design.id,
            status="suggested"
        )
        db_session.commit()

        user_id = 42
        updated_optimization = repository.update_optimization_status(
            optimization.id,
            status="applied",
            user_id=user_id
        )

        assert updated_optimization is not None
        assert updated_optimization.status == "applied"
        assert updated_optimization.applied_by == user_id
        assert updated_optimization.applied_at is not None
        assert isinstance(updated_optimization.applied_at, datetime)

        # Verify in database
        db_optimization = db_session.query(DesignOptimization).filter_by(id=optimization.id).first()
        assert db_optimization.status == "applied"
        assert db_optimization.applied_by == user_id
        assert db_optimization.applied_at is not None

    def test_update_optimization_status_reject(
        self, repository: OptimizationRepository, db_session: Session
    ):
        """Test rejecting an optimization (updating status to 'rejected')."""
        design = DesignFactory.create(db_session=db_session)
        db_session.commit()

        optimization = DesignOptimizationFactory.create(
            db_session=db_session,
            design_id=design.id,
            status="suggested"
        )
        db_session.commit()

        updated_optimization = repository.update_optimization_status(
            optimization.id,
            status="rejected"
        )

        assert updated_optimization is not None
        assert updated_optimization.status == "rejected"
        # applied_by and applied_at should remain None for rejected status
        assert updated_optimization.applied_by is None
        assert updated_optimization.applied_at is None

        # Verify in database
        db_optimization = db_session.query(DesignOptimization).filter_by(id=optimization.id).first()
        assert db_optimization.status == "rejected"

    def test_update_optimization_status_not_found(
        self, repository: OptimizationRepository
    ):
        """Test updating status of a non-existent optimization."""
        updated_optimization = repository.update_optimization_status(
            99999,
            status="applied",
            user_id=1
        )

        assert updated_optimization is None

    def test_update_optimization_status_from_applied_to_rejected(
        self, repository: OptimizationRepository, db_session: Session
    ):
        """Test changing status from applied to rejected."""
        design = DesignFactory.create(db_session=db_session)
        db_session.commit()

        optimization = DesignOptimizationFactory.create(
            db_session=db_session,
            design_id=design.id,
            status="applied",
            applied_by=10,
            applied_at=datetime.now()
        )
        db_session.commit()

        updated_optimization = repository.update_optimization_status(
            optimization.id,
            status="rejected"
        )

        assert updated_optimization.status == "rejected"
        # applied_by and applied_at should be cleared when rejecting
        assert updated_optimization.applied_by is None
        assert updated_optimization.applied_at is None

    def test_update_optimization_status_preserves_other_fields(
        self, repository: OptimizationRepository, db_session: Session
    ):
        """Test that updating status doesn't modify other fields."""
        design = DesignFactory.create(db_session=db_session)
        db_session.commit()

        optimization = DesignOptimizationFactory.create(
            db_session=db_session,
            design_id=design.id,
            optimization_type="cost",
            title="Original Title",
            description="Original Description",
            estimated_cost_impact=-20.0,
            implementation_difficulty="easy",
            priority="high"
        )
        db_session.commit()

        # Store original values
        original_type = optimization.optimization_type
        original_title = optimization.title
        original_description = optimization.description
        original_impact = optimization.estimated_cost_impact
        original_difficulty = optimization.implementation_difficulty
        original_priority = optimization.priority

        # Update status
        updated_optimization = repository.update_optimization_status(
            optimization.id,
            status="applied",
            user_id=1
        )

        # Verify other fields remain unchanged
        assert updated_optimization.optimization_type == original_type
        assert updated_optimization.title == original_title
        assert updated_optimization.description == original_description
        assert updated_optimization.estimated_cost_impact == original_impact
        assert updated_optimization.implementation_difficulty == original_difficulty
        assert updated_optimization.priority == original_priority

    def test_get_optimizations_by_design_id_includes_all_statuses(
        self, repository: OptimizationRepository, db_session: Session
    ):
        """Test that get_optimizations_by_design_id returns optimizations with all statuses."""
        design = DesignFactory.create(db_session=db_session)
        db_session.commit()

        # Create optimizations with different statuses
        DesignOptimizationFactory.create(
            db_session=db_session,
            design_id=design.id,
            status="suggested"
        )
        DesignOptimizationFactory.create(
            db_session=db_session,
            design_id=design.id,
            status="applied"
        )
        DesignOptimizationFactory.create(
            db_session=db_session,
            design_id=design.id,
            status="rejected"
        )
        db_session.commit()

        optimizations = repository.get_optimizations_by_design_id(design.id)

        assert len(optimizations) == 3
        statuses = {o.status for o in optimizations}
        assert statuses == {"suggested", "applied", "rejected"}
