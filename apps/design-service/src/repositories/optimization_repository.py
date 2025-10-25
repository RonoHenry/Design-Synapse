"""Repository for DesignOptimization model CRUD operations."""

from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import desc
from sqlalchemy.orm import Session

from ..models.design_optimization import DesignOptimization


class OptimizationRepository:
    """Repository for managing DesignOptimization entities."""

    def __init__(self, db_session: Session):
        """
        Initialize the repository with a database session.

        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session

    def create_optimization(self, **kwargs) -> DesignOptimization:
        """
        Create a new design optimization.

        Args:
            **kwargs: DesignOptimization attributes (design_id, optimization_type,
                     title, description, estimated_cost_impact, implementation_difficulty,
                     priority, etc.)

        Returns:
            Created DesignOptimization instance

        Raises:
            ValueError: If validation fails
        """
        optimization = DesignOptimization(**kwargs)
        self.db.add(optimization)
        self.db.commit()
        self.db.refresh(optimization)
        return optimization

    def get_optimizations_by_design_id(self, design_id: int) -> List[DesignOptimization]:
        """
        Get all optimizations for a specific design.

        Args:
            design_id: ID of the design to get optimizations for

        Returns:
            List of DesignOptimization instances for the design,
            ordered by created_at descending (newest first)
        """
        query = (
            self.db.query(DesignOptimization)
            .filter(DesignOptimization.design_id == design_id)
            .order_by(desc(DesignOptimization.created_at))
        )

        return query.all()

    def update_optimization_status(
        self,
        optimization_id: int,
        status: str,
        user_id: Optional[int] = None
    ) -> Optional[DesignOptimization]:
        """
        Update the status of an optimization.

        When status is set to 'applied', sets applied_at and applied_by.
        When status is set to 'rejected', clears applied_at and applied_by.

        Args:
            optimization_id: ID of the optimization to update
            status: New status ('suggested', 'applied', 'rejected')
            user_id: ID of the user applying/rejecting the optimization (optional)

        Returns:
            Updated DesignOptimization instance if found, None otherwise
        """
        optimization = self.db.query(DesignOptimization).filter(
            DesignOptimization.id == optimization_id
        ).first()

        if optimization is None:
            return None

        # Update status
        optimization.status = status

        # Set applied_at and applied_by when status is 'applied'
        if status == "applied":
            optimization.applied_at = datetime.now(timezone.utc)
            optimization.applied_by = user_id
        else:
            # Clear applied_at and applied_by for other statuses
            optimization.applied_at = None
            optimization.applied_by = None

        self.db.commit()
        self.db.refresh(optimization)
        return optimization
