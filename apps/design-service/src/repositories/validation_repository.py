"""Repository for DesignValidation model CRUD operations."""

from typing import List, Optional
from sqlalchemy import desc
from sqlalchemy.orm import Session

from ..models.design_validation import DesignValidation


class ValidationRepository:
    """Repository for managing DesignValidation entities."""

    def __init__(self, db_session: Session):
        """
        Initialize the repository with a database session.

        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session

    def create_validation(self, **kwargs) -> DesignValidation:
        """
        Create a new design validation.

        Args:
            **kwargs: DesignValidation attributes (design_id, validation_type, 
                     rule_set, is_compliant, violations, warnings, validated_by)

        Returns:
            Created DesignValidation instance

        Raises:
            ValueError: If validation fails
        """
        validation = DesignValidation(**kwargs)
        self.db.add(validation)
        self.db.commit()
        self.db.refresh(validation)
        return validation

    def get_validations_by_design_id(self, design_id: int) -> List[DesignValidation]:
        """
        Get all validations for a specific design.

        Args:
            design_id: ID of the design to get validations for

        Returns:
            List of DesignValidation instances for the design, 
            ordered by validated_at descending (newest first)
        """
        query = (
            self.db.query(DesignValidation)
            .filter(DesignValidation.design_id == design_id)
            .order_by(desc(DesignValidation.validated_at))
        )

        return query.all()

    def get_latest_validation(self, design_id: int) -> Optional[DesignValidation]:
        """
        Get the most recent validation for a design.

        Args:
            design_id: ID of the design to get the latest validation for

        Returns:
            Most recent DesignValidation instance if found, None otherwise
        """
        query = (
            self.db.query(DesignValidation)
            .filter(DesignValidation.design_id == design_id)
            .order_by(desc(DesignValidation.validated_at))
            .limit(1)
        )

        return query.first()
