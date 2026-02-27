"""Base repository with common CRUD operations."""
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session
from src.models.base import Base

T = TypeVar("T", bound=Base)


class BaseRepository(Generic[T]):
    """Base repository class with common CRUD operations."""

    def __init__(self, model: Type[T], db_session: Session):
        self.model = model
        self.db_session = db_session

    async def create(self, data: Dict[str, Any]) -> T:
        """Create a new instance."""
        instance = self.model(**data)
        self.db_session.add(instance)
        self.db_session.commit()
        self.db_session.refresh(instance)
        return instance

    async def save(self, instance: T) -> T:
        """Save a new or updated instance."""
        self.db_session.add(instance)
        self.db_session.commit()
        self.db_session.refresh(instance)
        return instance

    async def get_by_id(self, id: int) -> Optional[T]:
        """Get instance by ID."""
        return self.db_session.query(self.model).filter(self.model.id == id).first()

    def get_all(self, limit: int = 100, offset: int = 0) -> List[T]:
        """Get all instances with pagination."""
        return self.db_session.query(self.model).offset(offset).limit(limit).all()

    async def update(self, id: int, data: Dict[str, Any]) -> Optional[T]:
        """Update instance by ID."""
        instance = await self.get_by_id(id)
        if instance:
            for key, value in data.items():
                setattr(instance, key, value)
            self.db_session.commit()
            self.db_session.refresh(instance)
        return instance

    async def delete(self, id: int) -> bool:
        """Delete instance by ID."""
        instance = await self.get_by_id(id)
        if instance:
            self.db_session.delete(instance)
            self.db_session.commit()
            return True
        return False

    def filter_by(self, **kwargs) -> List[T]:
        """Filter instances by given criteria."""
        query = self.db_session.query(self.model)
        for key, value in kwargs.items():
            if hasattr(self.model, key):
                query = query.filter(getattr(self.model, key) == value)
        return query.all()

    def count(self) -> int:
        """Count total instances."""
        return self.db_session.query(self.model).count()

    async def list_with_filters(
        self,
        filters: Dict[str, Any] = None,
        sort_by: str = "id",
        order: str = "desc",
        page: int = 1,
        size: int = 10,
    ) -> Dict[str, Any]:
        """List instances with pagination and filtering"""
        if filters is None:
            filters = {}

        query = self.db_session.query(self.model)

        # Apply filters
        for key, value in filters.items():
            if hasattr(self.model, key) and value is not None:
                query = query.filter(getattr(self.model, key) == value)

        # Get total count before pagination
        total = query.count()

        # Apply sorting
        if hasattr(self.model, sort_by):
            sort_column = getattr(self.model, sort_by)
            if order.lower() == "desc":
                query = query.order_by(sort_column.desc())
            else:
                query = query.order_by(sort_column.asc())

        # Apply pagination
        offset = (page - 1) * size
        items = query.offset(offset).limit(size).all()

        return {"items": items, "total": total}
