"""CalculationDependency model for tracking dependencies between calculations."""

from datetime import datetime
from typing import Optional

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.database import Base


class CalculationDependency(Base):
    """Model for tracking dependencies between calculation sheets.

    When calculation A depends on calculation B, changing B should trigger
    recalculation of A. This model tracks these relationships to enable
    automatic recalculation cascades.
    """

    __tablename__ = "calculation_dependencies"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Source calculation (the one that depends on another)
    source_calculation_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("calculation_sheets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Target calculation (the one being depended upon)
    target_calculation_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("calculation_sheets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Dependency type (e.g., "load_input", "material_property", "geometry")
    dependency_type: Mapped[str] = mapped_column(String(100), nullable=False)

    # Field path in the source calculation that depends on the target
    # e.g., "inputs.loads.dead_load"
    dependent_field: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Field path in the target calculation that is depended upon
    # e.g., "outputs.total_load"
    source_field: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Audit fields
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)

    def __repr__(self) -> str:
        """String representation of CalculationDependency."""
        return (
            f"<CalculationDependency(id={self.id}, "
            f"source={self.source_calculation_id}, "
            f"target={self.target_calculation_id}, "
            f"type='{self.dependency_type}')>"
        )

    def __str__(self) -> str:
        """Human-readable string representation."""
        return (
            f"Calculation {self.source_calculation_id} depends on "
            f"Calculation {self.target_calculation_id} ({self.dependency_type})"
        )
