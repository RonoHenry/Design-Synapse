"""AuditLog model for tracking engineering service activities."""

from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import JSON, Column, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ..core.database import Base


class AuditLog(Base):
    """Model for storing audit logs of engineering activities.

    Audit logs track all significant actions including document creation,
    modifications, code compliance checks, and integration events.
    """

    __tablename__ = "audit_logs"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # User and project association
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    project_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, index=True
    )

    # Action details
    action_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # create, update, delete, validate, export
    entity_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # calculation, design, report, document
    entity_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # Change tracking (stored as JSON)
    changes: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON, nullable=True
    )  # before/after values

    # Additional context
    description: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Result
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="success"
    )  # success, failure, error
    error_message: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)

    # Timestamp
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, index=True
    )

    def __repr__(self) -> str:
        """String representation of AuditLog."""
        return (
            f"<AuditLog(id={self.id}, action='{self.action_type}', "
            f"entity='{self.entity_type}', user='{self.user_id}')>"
        )

    def __str__(self) -> str:
        """Human-readable string representation."""
        return (
            f"{self.action_type} {self.entity_type} "
            f"by {self.user_id} at {self.timestamp}"
        )
