"""
Base Model Classes - Optimized for Performance

Common base classes and mixins for all Labor Service models.
Optimized for TiDB compatibility and high performance.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List

from sqlalchemy import Boolean, Column, DateTime, Index, Integer
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class TimestampMixin:
    """
    Mixin for adding created_at and updated_at timestamps.
    Optimized for TiDB with proper timezone handling.
    """

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,  # Index for time-based queries
        comment="Record creation timestamp",
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        index=True,  # Index for recently updated queries
        comment="Record last update timestamp",
    )


class SoftDeleteMixin:
    """Mixin for soft delete functionality"""

    is_deleted = Column(
        Boolean, default=False, nullable=False, comment="Soft delete flag"
    )

    deleted_at = Column(
        DateTime(timezone=True), nullable=True, comment="Soft delete timestamp"
    )

    def soft_delete(self):
        """Mark record as deleted with timezone-aware timestamp"""
        self.is_deleted = True
        self.deleted_at = datetime.now(timezone.utc)

    def restore(self):
        """Restore soft deleted record"""
        self.is_deleted = False
        self.deleted_at = None


class BaseModel(Base, TimestampMixin):
    """
    Base model class with common fields and optimized methods.
    Provides consistent interface for all Labor Service models.
    """

    __abstract__ = True

    id = Column(Integer, primary_key=True, autoincrement=True, comment="Primary key")

    def to_dict(self, include_relationships: bool = False) -> Dict[str, Any]:
        """
        Convert model instance to dictionary with optional relationship data.

        Args:
            include_relationships: Whether to include relationship data

        Returns:
            Dictionary representation of the model
        """
        result = {}

        # Include column data
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            if isinstance(value, datetime):
                result[column.name] = value.isoformat()
            else:
                result[column.name] = value

        # Optionally include relationship data
        if include_relationships:
            for relationship_name in self.__mapper__.relationships.keys():
                relationship_value = getattr(self, relationship_name)
                if relationship_value is not None:
                    if hasattr(relationship_value, "__iter__") and not isinstance(
                        relationship_value, str
                    ):
                        # Collection relationship
                        result[relationship_name] = [
                            item.to_dict() if hasattr(item, "to_dict") else str(item)
                            for item in relationship_value
                        ]
                    else:
                        # Single relationship
                        result[relationship_name] = (
                            relationship_value.to_dict()
                            if hasattr(relationship_value, "to_dict")
                            else str(relationship_value)
                        )

        return result

    def update_from_dict(
        self, data: Dict[str, Any], exclude_fields: List[str] = None
    ) -> None:
        """
        Update model instance from dictionary data.

        Args:
            data: Dictionary of field values to update
            exclude_fields: List of fields to exclude from update
        """
        exclude_fields = exclude_fields or ["id", "created_at"]

        for key, value in data.items():
            if key not in exclude_fields and hasattr(self, key):
                setattr(self, key, value)

    def __repr__(self):
        """String representation of model"""
        return f"<{self.__class__.__name__}(id={self.id})>"

    def __str__(self):
        """Human-readable string representation"""
        return f"{self.__class__.__name__}(id={self.id})"
