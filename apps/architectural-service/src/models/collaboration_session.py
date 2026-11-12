"""CollaborationSession model for real-time collaboration."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import uuid4

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Index
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.orm import Mapped, relationship
from src.core.database import Base

if TYPE_CHECKING:
    from src.models.design import Design


def generate_uuid() -> str:
    """Generate UUID as string for TiDB/MySQL compatibility."""
    return str(uuid4())


class CollaborationSession(Base):
    """
    Real-time collaboration sessions.

    Tracks active collaboration sessions for design documents,
    including active users and session state.
    """

    __tablename__ = "collaboration_sessions"

    # Primary key
    id = Column(CHAR(36), primary_key=True, default=generate_uuid, nullable=False)

    # Foreign key to design
    design_id = Column(
        CHAR(36),
        ForeignKey("designs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Associated design ID",
    )

    # Session state
    active_users = Column(
        JSON,
        nullable=False,
        default=list,
        comment="List of currently active user IDs in the session",
    )
    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        comment="Whether the session is currently active",
    )

    # Timestamps
    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        comment="Session creation timestamp",
    )
    ended_at = Column(DateTime, nullable=True, comment="Session end timestamp")

    # Table arguments for indexes
    __table_args__ = (
        Index("idx_active_sessions", "design_id", "is_active"),
        Index("idx_session_created", "created_at"),
        {"comment": "Real-time collaboration sessions"},
    )

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<CollaborationSession(id={self.id}, design_id={self.design_id}, "
            f"is_active={self.is_active}, users={len(self.active_users)})>"
        )
