"""DesignValidation model for storing validation results."""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from sqlalchemy import Integer, String, Boolean, JSON, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.database import Base

if TYPE_CHECKING:
    from src.models.design import Design


class DesignValidation(Base):
    """Validation results for designs against building codes."""
    
    __tablename__ = "design_validations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    design_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("designs.id", ondelete="CASCADE"),
        nullable=False
    )

    # Validation metadata
    validation_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )  # building_code, structural, safety
    rule_set: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )  # e.g., "Kenya_Building_Code_2020"

    # Results
    is_compliant: Mapped[bool] = mapped_column(Boolean, nullable=False)
    violations: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=False
    )  # List of violation objects
    warnings: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=False
    )

    # Audit
    validated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    validated_by: Mapped[int] = mapped_column(Integer, nullable=False)

    # Relationship
    design: Mapped["Design"] = relationship(
        "Design",
        back_populates="validations"
    )

    def __init__(
        self,
        design_id: Optional[int] = None,
        validation_type: Optional[str] = None,
        rule_set: Optional[str] = None,
        is_compliant: Optional[bool] = None,
        validated_by: Optional[int] = None,
        violations: Optional[List[Dict[str, Any]]] = None,
        warnings: Optional[List[Dict[str, Any]]] = None,
    ):
        """
        Initialize a new design validation.

        Args:
            design_id: ID of the design being validated
            validation_type: Type of validation (building_code, structural, safety)
            rule_set: Building code rule set used (e.g., "Kenya_Building_Code_2020")
            is_compliant: Whether the design is compliant
            validated_by: ID of the user who performed the validation
            violations: List of violation objects (default: empty list)
            warnings: List of warning objects (default: empty list)
        """
        # Set required fields (SQLAlchemy will enforce NOT NULL constraints at commit time)
        if design_id is not None:
            self.design_id = design_id
        if validation_type is not None:
            self.validation_type = validation_type
        if rule_set is not None:
            self.rule_set = rule_set
        if is_compliant is not None:
            self.is_compliant = is_compliant
        if validated_by is not None:
            self.validated_by = validated_by
        
        # Set optional fields with defaults
        self.violations = violations if violations is not None else []
        self.warnings = warnings if warnings is not None else []
        self.validated_at = datetime.now(timezone.utc)

    def __repr__(self) -> str:
        """String representation of DesignValidation."""
        return (
            f"<DesignValidation(id={self.id}, design_id={self.design_id}, "
            f"validation_type='{self.validation_type}', is_compliant={self.is_compliant})>"
        )
