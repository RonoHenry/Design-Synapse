"""Base repository with common CRUD operations."""

from datetime import datetime
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import Base

T = TypeVar("T", bound=Base)


class BaseRepository(Generic[T]):
    """Base repository class with common CRUD operations.

    Provides standard CRUD operations for all models with support for:
    - Async/await patterns
    - Soft deletes (deleted_at field)
    - Pagination
    - Filtering
    - Transaction management
    """

    def __init__(self, model: Type[T], db_session: AsyncSession):
        """Initialize repository with model and session.

        Args:
            model: SQLAlchemy model class
            db_session: Async database session
        """
        self.model = model
        self.db_session = db_session

    async def create(self, data: Dict[str, Any]) -> T:
        """Create a new record.

        Args:
            data: Dictionary of field values

        Returns:
            Created model instance
        """
        instance = self.model(**data)
        self.db_session.add(instance)
        await self.db_session.commit()
        await self.db_session.refresh(instance)
        return instance

    async def get_by_id(self, id: int, include_deleted: bool = False) -> Optional[T]:
        """Get a record by ID.

        Args:
            id: Record ID
            include_deleted: Whether to include soft-deleted records

        Returns:
            Model instance or None if not found
        """
        query = select(self.model).where(self.model.id == id)

        # Exclude soft-deleted records by default
        if not include_deleted and hasattr(self.model, "deleted_at"):
            query = query.where(self.model.deleted_at.is_(None))

        result = await self.db_session.execute(query)
        return result.scalar_one_or_none()

    async def list_all(
        self, limit: int = 100, offset: int = 0, include_deleted: bool = False
    ) -> List[T]:
        """List all records with pagination.

        Args:
            limit: Maximum number of records to return
            offset: Number of records to skip
            include_deleted: Whether to include soft-deleted records

        Returns:
            List of model instances
        """
        query = select(self.model)

        # Exclude soft-deleted records by default
        if not include_deleted and hasattr(self.model, "deleted_at"):
            query = query.where(self.model.deleted_at.is_(None))

        query = query.offset(offset).limit(limit)
        result = await self.db_session.execute(query)
        return list(result.scalars().all())

    async def update(self, id: int, data: Dict[str, Any]) -> Optional[T]:
        """Update a record by ID.

        Args:
            id: Record ID
            data: Dictionary of fields to update

        Returns:
            Updated model instance or None if not found
        """
        instance = await self.get_by_id(id)
        if instance is None:
            return None

        for key, value in data.items():
            if hasattr(instance, key):
                setattr(instance, key, value)

        # Update timestamp if available
        if hasattr(instance, "updated_at"):
            instance.updated_at = datetime.utcnow()

        await self.db_session.commit()
        await self.db_session.refresh(instance)
        return instance

    async def delete(self, id: int, soft: bool = True) -> bool:
        """Delete a record by ID.

        Args:
            id: Record ID
            soft: If True, perform soft delete; if False, hard delete

        Returns:
            True if deleted, False if not found
        """
        instance = await self.get_by_id(id)
        if instance is None:
            return False

        if soft and hasattr(instance, "deleted_at"):
            # Soft delete
            instance.deleted_at = datetime.utcnow()
            await self.db_session.commit()
        else:
            # Hard delete
            await self.db_session.delete(instance)
            await self.db_session.commit()

        return True

    async def count(self, include_deleted: bool = False) -> int:
        """Count total records.

        Args:
            include_deleted: Whether to include soft-deleted records

        Returns:
            Total count
        """
        query = select(func.count()).select_from(self.model)

        # Exclude soft-deleted records by default
        if not include_deleted and hasattr(self.model, "deleted_at"):
            query = query.where(self.model.deleted_at.is_(None))

        result = await self.db_session.execute(query)
        return result.scalar_one()

    async def filter_by(self, include_deleted: bool = False, **kwargs) -> List[T]:
        """Filter records by field values.

        Args:
            include_deleted: Whether to include soft-deleted records
            **kwargs: Field name and value pairs to filter by

        Returns:
            List of matching model instances
        """
        query = select(self.model)

        # Build filter conditions
        conditions = []
        for key, value in kwargs.items():
            if hasattr(self.model, key):
                conditions.append(getattr(self.model, key) == value)

        if conditions:
            query = query.where(and_(*conditions))

        # Exclude soft-deleted records by default
        if not include_deleted and hasattr(self.model, "deleted_at"):
            query = query.where(self.model.deleted_at.is_(None))

        result = await self.db_session.execute(query)
        return list(result.scalars().all())

    async def list_with_filters(
        self,
        filters: Optional[Dict[str, Any]] = None,
        sort_by: str = "id",
        order: str = "desc",
        page: int = 1,
        size: int = 10,
        include_deleted: bool = False,
    ) -> Dict[str, Any]:
        """List records with advanced filtering and pagination.

        Args:
            filters: Dictionary of field filters
            sort_by: Field name to sort by
            order: Sort order ('asc' or 'desc')
            page: Page number (1-indexed)
            size: Page size
            include_deleted: Whether to include soft-deleted records

        Returns:
            Dictionary with 'items' and 'total' keys
        """
        if filters is None:
            filters = {}

        query = select(self.model)

        # Apply filters
        conditions = []
        for key, value in filters.items():
            if hasattr(self.model, key) and value is not None:
                conditions.append(getattr(self.model, key) == value)

        if conditions:
            query = query.where(and_(*conditions))

        # Exclude soft-deleted records by default
        if not include_deleted and hasattr(self.model, "deleted_at"):
            query = query.where(self.model.deleted_at.is_(None))

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db_session.execute(count_query)
        total = total_result.scalar_one()

        # Apply sorting
        if hasattr(self.model, sort_by):
            sort_column = getattr(self.model, sort_by)
            if order.lower() == "desc":
                query = query.order_by(sort_column.desc())
            else:
                query = query.order_by(sort_column.asc())

        # Apply pagination
        offset = (page - 1) * size
        query = query.offset(offset).limit(size)

        result = await self.db_session.execute(query)
        items = list(result.scalars().all())

        return {"items": items, "total": total}
