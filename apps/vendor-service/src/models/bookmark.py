"""ProductBookmark model for saving products for later."""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (DateTime, ForeignKey, Integer, String,
                        UniqueConstraint, func)
from sqlalchemy.orm import Mapped, mapped_column
from src.infrastructure.database import Base


class ProductBookmark(Base):
    """ProductBookmark model for users to save products for design staging."""

    __tablename__ = "product_bookmarks"
    __table_args__ = (
        UniqueConstraint("user_id", "product_id", name="unique_user_product_bookmark"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    product_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    notes: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __init__(
        self, user_id: int, product_id: int, notes: Optional[str] = None, **kwargs
    ):
        """Initialize a new product bookmark."""
        self.user_id = user_id
        self.product_id = product_id
        self.notes = self._validate_notes(notes) if notes else None
        self.created_at = datetime.now(timezone.utc)

    @staticmethod
    def _validate_notes(notes: str) -> str:
        """Validate bookmark notes."""
        if notes and len(notes.strip()) > 1000:
            raise ValueError("Notes cannot exceed 1000 characters")
        return notes.strip() if notes else None

    def update_notes(self, notes: Optional[str]) -> None:
        """Update bookmark notes."""
        self.notes = self._validate_notes(notes) if notes else None

    def __repr__(self) -> str:
        """String representation of bookmark."""
        return f"<ProductBookmark(id={self.id}, user_id={self.user_id}, product_id={self.product_id})>"
