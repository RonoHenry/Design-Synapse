"""Base repository with common CRUD operations."""

from typing import Any, Dict, Generic, List, Optional, Type, TypeVar
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.database import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """
    Base repository providing common CRUD operations.

    Uses SQLAlchemy async session for all database operations.
    Implements transaction support and error handling.
    """

    def __init__(self, model: Type[ModelType], session: AsyncSession):
        """
        Initialize repository.

        Args:
            model: SQLAlchemy model class
            session: Async database session
        """
        self.model = model
        self.session = session

    async def create(self, **kwargs: Any) -> ModelType:
        """
        Create a new record.

        Args:
            **kwargs: Model field values

        Returns:
            Created model instance

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            instance = self.model(**kwargs)
            self.session.add(instance)
            await self.session.flush()
            await self.session.refresh(instance)
            return instance
        except SQLAlchemyError as e:
            await self.session.rollback()
            raise e

    async def get(self, id: str) -> Optional[ModelType]:
        """
        Get a record by ID.

        Args:
            id: Record ID (UUID as string)

        Returns:
            Model instance or None if not found

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            result = await self.session.execute(
                select(self.model).where(self.model.id == id)
            )
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            raise e

    async def update(self, id: str, **kwargs: Any) -> Optional[ModelType]:
        """
        Update a record.

        Args:
            id: Record ID (UUID as string)
            **kwargs: Fields to update

        Returns:
            Updated model instance or None if not found

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            instance = await self.get(id)
            if instance is None:
                return None

            for key, value in kwargs.items():
                if hasattr(instance, key):
                    setattr(instance, key, value)

            await self.session.flush()
            await self.session.refresh(instance)
            return instance
        except SQLAlchemyError as e:
            await self.session.rollback()
            raise e

    async def delete(self, id: str) -> bool:
        """
        Delete a record.

        Args:
            id: Record ID (UUID as string)

        Returns:
            True if deleted, False if not found

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            instance = await self.get(id)
            if instance is None:
                return False

            await self.session.delete(instance)
            await self.session.flush()
            return True
        except SQLAlchemyError as e:
            await self.session.rollback()
            raise e

    async def list(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        order_by: Optional[str] = None,
    ) -> List[ModelType]:
        """
        List records with optional filtering and pagination.

        Args:
            filters: Dictionary of field:value filters
            limit: Maximum number of records to return
            offset: Number of records to skip
            order_by: Field name to order by

        Returns:
            List of model instances

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            query = select(self.model)

            # Apply filters
            if filters:
                for key, value in filters.items():
                    if hasattr(self.model, key):
                        query = query.where(getattr(self.model, key) == value)

            # Apply ordering
            if order_by and hasattr(self.model, order_by):
                query = query.order_by(getattr(self.model, order_by))

            # Apply pagination
            if offset is not None:
                query = query.offset(offset)
            if limit is not None:
                query = query.limit(limit)

            result = await self.session.execute(query)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            raise e

    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        Count records with optional filtering.

        Args:
            filters: Dictionary of field:value filters

        Returns:
            Number of matching records

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            from sqlalchemy import func

            query = select(func.count()).select_from(self.model)

            # Apply filters
            if filters:
                for key, value in filters.items():
                    if hasattr(self.model, key):
                        query = query.where(getattr(self.model, key) == value)

            result = await self.session.execute(query)
            return result.scalar_one()
        except SQLAlchemyError as e:
            raise e

    async def exists(self, id: str) -> bool:
        """
        Check if a record exists.

        Args:
            id: Record ID (UUID as string)

        Returns:
            True if exists, False otherwise

        Raises:
            SQLAlchemyError: If database operation fails
        """
        try:
            from sqlalchemy import exists as sql_exists

            query = select(sql_exists().where(self.model.id == id))
            result = await self.session.execute(query)
            return result.scalar_one()
        except SQLAlchemyError as e:
            raise e

    async def commit(self) -> None:
        """
        Commit the current transaction.

        Raises:
            SQLAlchemyError: If commit fails
        """
        try:
            await self.session.commit()
        except SQLAlchemyError as e:
            await self.session.rollback()
            raise e

    async def rollback(self) -> None:
        """
        Rollback the current transaction.

        Raises:
            SQLAlchemyError: If rollback fails
        """
        try:
            await self.session.rollback()
        except SQLAlchemyError as e:
            raise e
