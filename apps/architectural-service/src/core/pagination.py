"""Cursor-based pagination utilities for the Architectural Service."""

import base64
import json
from typing import Any, Dict, Generic, List, Optional, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import asc, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.sql import Select

T = TypeVar("T")


class PaginationCursor(BaseModel):
    """Cursor for pagination containing sort field value and unique ID."""

    sort_value: Any = Field(..., description="Value of the sort field")
    id: str = Field(..., description="Unique identifier for stable ordering")

    def encode(self) -> str:
        """Encode cursor to base64 string."""
        cursor_data = {"sort_value": self.sort_value, "id": self.id}
        json_str = json.dumps(cursor_data, default=str)
        return base64.b64encode(json_str.encode()).decode()

    @classmethod
    def decode(cls, cursor: str) -> "PaginationCursor":
        """Decode cursor from base64 string."""
        try:
            json_str = base64.b64decode(cursor.encode()).decode()
            cursor_data = json.loads(json_str)
            return cls(**cursor_data)
        except (ValueError, json.JSONDecodeError, TypeError) as e:
            raise ValueError(f"Invalid cursor format: {e}")


class PaginationParams(BaseModel):
    """Parameters for pagination requests."""

    limit: int = Field(
        default=20, ge=1, le=100, description="Number of items per page (1-100)"
    )
    cursor: Optional[str] = Field(default=None, description="Cursor for pagination")
    sort_field: str = Field(default="created_at", description="Field to sort by")
    sort_direction: str = Field(
        default="desc",
        pattern="^(asc|desc)$",
        description="Sort direction (asc or desc)",
    )


class PaginatedResponse(BaseModel):
    """Paginated response with items and pagination metadata."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    items: List[Any] = Field(..., description="List of items")
    has_next: bool = Field(..., description="Whether there are more items")
    next_cursor: Optional[str] = Field(default=None, description="Cursor for next page")
    total_count: Optional[int] = Field(
        default=None, description="Total count (if requested)"
    )
    page_info: Dict[str, Any] = Field(
        default_factory=dict, description="Additional pagination metadata"
    )


class PaginationHelper:
    """Helper class for implementing cursor-based pagination."""

    def __init__(
        self,
        session: AsyncSession,
        model: type[T],
        default_sort_field: str = "created_at",
    ):
        self.session = session
        self.model = model
        self.default_sort_field = default_sort_field

    async def paginate(
        self, query: Select, params: PaginationParams, include_total: bool = False
    ) -> PaginatedResponse:
        """
        Apply cursor-based pagination to a query.

        Args:
            query: Base SQLAlchemy query
            params: Pagination parameters
            include_total: Whether to include total count

        Returns:
            Paginated response with items and metadata
        """
        # Validate sort field exists on model
        sort_field = params.sort_field or self.default_sort_field
        if not hasattr(self.model, sort_field):
            raise ValueError(f"Invalid sort field: {sort_field}")

        sort_column = getattr(self.model, sort_field)
        id_column = getattr(self.model, "id")

        # Apply sorting
        if params.sort_direction == "desc":
            query = query.order_by(desc(sort_column), desc(id_column))
        else:
            query = query.order_by(asc(sort_column), asc(id_column))

        # Apply cursor filtering if provided
        if params.cursor:
            try:
                cursor = PaginationCursor.decode(params.cursor)
                cursor_id = UUID(cursor.id)

                if params.sort_direction == "desc":
                    # For descending order: (sort_value < cursor_value) OR
                    # (sort_value = cursor_value AND id < cursor_id)
                    query = query.where(
                        (sort_column < cursor.sort_value)
                        | ((sort_column == cursor.sort_value) & (id_column < cursor_id))
                    )
                else:
                    # For ascending order: (sort_value > cursor_value) OR
                    # (sort_value = cursor_value AND id > cursor_id)
                    query = query.where(
                        (sort_column > cursor.sort_value)
                        | ((sort_column == cursor.sort_value) & (id_column > cursor_id))
                    )
            except (ValueError, TypeError) as e:
                raise ValueError(f"Invalid cursor: {e}")

        # Fetch one extra item to determine if there's a next page
        limit_query = query.limit(params.limit + 1)
        result = await self.session.execute(limit_query)
        items = result.scalars().all()

        # Determine if there are more items
        has_next = len(items) > params.limit
        if has_next:
            items = items[:-1]  # Remove the extra item

        # Generate next cursor if there are more items
        next_cursor = None
        if has_next and items:
            last_item = items[-1]
            sort_value = getattr(last_item, sort_field)
            next_cursor = PaginationCursor(
                sort_value=sort_value, id=str(last_item.id)
            ).encode()

        # Get total count if requested
        total_count = None
        if include_total:
            count_query = select(func.count()).select_from(query.subquery())
            count_result = await self.session.execute(count_query)
            total_count = count_result.scalar()

        return PaginatedResponse(
            items=items,
            has_next=has_next,
            next_cursor=next_cursor,
            total_count=total_count,
            page_info={
                "limit": params.limit,
                "sort_field": sort_field,
                "sort_direction": params.sort_direction,
                "cursor": params.cursor,
            },
        )

    async def paginate_simple(
        self,
        base_query: Select,
        limit: int = 20,
        cursor: Optional[str] = None,
        sort_field: str = None,
        sort_direction: str = "desc",
    ) -> PaginatedResponse:
        """
        Simplified pagination method with direct parameters.

        Args:
            base_query: Base SQLAlchemy query
            limit: Number of items per page
            cursor: Pagination cursor
            sort_field: Field to sort by
            sort_direction: Sort direction

        Returns:
            Paginated response
        """
        params = PaginationParams(
            limit=min(limit, 100),  # Enforce max limit
            cursor=cursor,
            sort_field=sort_field or self.default_sort_field,
            sort_direction=sort_direction,
        )

        return await self.paginate(base_query, params, include_total=False)


def create_pagination_params(
    limit: Optional[int] = None,
    cursor: Optional[str] = None,
    sort_field: Optional[str] = None,
    sort_direction: Optional[str] = None,
) -> PaginationParams:
    """
    Create pagination parameters with defaults.

    Args:
        limit: Number of items per page
        cursor: Pagination cursor
        sort_field: Field to sort by
        sort_direction: Sort direction

    Returns:
        PaginationParams instance
    """
    return PaginationParams(
        limit=limit or 20,
        cursor=cursor,
        sort_field=sort_field or "created_at",
        sort_direction=sort_direction or "desc",
    )


def encode_cursor(sort_value: Any, item_id: UUID) -> str:
    """
    Encode a cursor from sort value and item ID.

    Args:
        sort_value: Value of the sort field
        item_id: Unique identifier

    Returns:
        Encoded cursor string
    """
    cursor = PaginationCursor(sort_value=sort_value, id=str(item_id))
    return cursor.encode()


def decode_cursor(cursor: str) -> PaginationCursor:
    """
    Decode a cursor string.

    Args:
        cursor: Encoded cursor string

    Returns:
        PaginationCursor instance

    Raises:
        ValueError: If cursor format is invalid
    """
    return PaginationCursor.decode(cursor)
