"""Models for user bookmarks."""

from datetime import datetime
from typing import Optional
from sqlalchemy import Integer, ForeignKey, Text, DateTime, CheckConstraint, UniqueConstraint
from sqlalchemy.orm import Mapped, relationship, mapped_column

from ..infrastructure.database import Base

class Bookmark(Base):
    """Model for user bookmarks of resources."""
    
    __tablename__ = "bookmarks"
    __table_args__ = (
        CheckConstraint('user_id > 0', name='check_user_id_positive'),
        UniqueConstraint('user_id', 'resource_id', name='unique_user_resource'),
        {'extend_existing': True}
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)  # Foreign key to user service
    resource_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("resources.id", ondelete="CASCADE"),
        nullable=False
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    
    resource: Mapped["Resource"] = relationship("Resource", back_populates="bookmarks")

    def __repr__(self):
        """String representation."""
        return f"<Bookmark {self.id}: User {self.user_id} -> Resource {self.resource_id}>"