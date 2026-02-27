"""Quote repository with specialized query methods."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, asc, desc, func, or_
from sqlalchemy.orm import Session, joinedload
from src.models.quote import Quote, QuoteStatus

from .base_repository import BaseRepository


class QuoteRepository(BaseRepository[Quote]):
    """Repository for Quote with specialized query methods."""

    def __init__(self, db_session: Session):
        super().__init__(Quote, db_session)

    def find_by_status(self, status: QuoteStatus) -> List[Quote]:
        """Find quotes by status."""
        return self.db_session.query(Quote).filter(Quote.status == status).all()

    def find_by_request_id(self, request_id: int) -> List[Quote]:
        """Find all quotes for a specific service request."""
        return (
            self.db_session.query(Quote)
            .filter(Quote.request_id == request_id)
            .order_by(asc(Quote.total_cost))
            .all()
        )

    def find_by_provider_id(self, provider_id: int) -> List[Quote]:
        """Find all quotes submitted by a specific provider."""
        return (
            self.db_session.query(Quote)
            .filter(Quote.provider_id == provider_id)
            .order_by(desc(Quote.created_at))
            .all()
        )

    def find_by_cost_range(self, min_cost: float, max_cost: float) -> List[Quote]:
        """Find quotes within cost range."""
        return (
            self.db_session.query(Quote)
            .filter(and_(Quote.total_cost >= min_cost, Quote.total_cost <= max_cost))
            .all()
        )

    def find_pending_quotes(self) -> List[Quote]:
        """Find quotes that are pending review."""
        return (
            self.db_session.query(Quote)
            .filter(Quote.status == QuoteStatus.SUBMITTED)
            .order_by(asc(Quote.created_at))
            .all()
        )

    def find_expired_quotes(self) -> List[Quote]:
        """Find quotes that have expired."""
        current_time = datetime.now(timezone.utc)
        return (
            self.db_session.query(Quote)
            .filter(
                and_(
                    Quote.valid_until < current_time,
                    Quote.status.in_([QuoteStatus.SUBMITTED, QuoteStatus.DRAFT]),
                )
            )
            .all()
        )

    def find_expiring_soon(self, hours: int = 24) -> List[Quote]:
        """Find quotes expiring within specified hours."""
        expiry_threshold = datetime.now(timezone.utc) + timedelta(hours=hours)
        return (
            self.db_session.query(Quote)
            .filter(
                and_(
                    Quote.valid_until <= expiry_threshold,
                    Quote.valid_until > datetime.now(timezone.utc),
                    Quote.status == QuoteStatus.SUBMITTED,
                )
            )
            .order_by(asc(Quote.valid_until))
            .all()
        )

    def find_competitive_quotes(
        self, request_id: int, exclude_quote_id: int = None
    ) -> List[Quote]:
        """Find competitive quotes for comparison."""
        query = self.db_session.query(Quote).filter(
            and_(Quote.request_id == request_id, Quote.status == QuoteStatus.SUBMITTED)
        )

        if exclude_quote_id:
            query = query.filter(Quote.id != exclude_quote_id)

        return query.order_by(asc(Quote.total_cost)).all()

    def get_quote_statistics(self, request_id: int) -> Dict[str, Any]:
        """Get statistics for quotes on a specific request."""
        quotes = (
            self.db_session.query(Quote)
            .filter(
                and_(
                    Quote.request_id == request_id,
                    Quote.status == QuoteStatus.SUBMITTED,
                )
            )
            .all()
        )

        if not quotes:
            return {
                "request_id": request_id,
                "quote_count": 0,
                "avg_cost": 0.0,
                "min_cost": 0.0,
                "max_cost": 0.0,
                "avg_hours": 0.0,
            }

        costs = [float(quote.total_cost) for quote in quotes]
        hours = [quote.estimated_hours for quote in quotes if quote.estimated_hours]

        return {
            "request_id": request_id,
            "quote_count": len(quotes),
            "avg_cost": sum(costs) / len(costs),
            "min_cost": min(costs),
            "max_cost": max(costs),
            "avg_hours": sum(hours) / len(hours) if hours else 0.0,
        }

    def find_provider_quote_history(
        self, provider_id: int, limit: int = 50
    ) -> List[Quote]:
        """Find recent quote history for a provider."""
        return (
            self.db_session.query(Quote)
            .filter(Quote.provider_id == provider_id)
            .order_by(desc(Quote.created_at))
            .limit(limit)
            .all()
        )

    def find_accepted_quotes_by_provider(self, provider_id: int) -> List[Quote]:
        """Find accepted quotes for a provider."""
        return (
            self.db_session.query(Quote)
            .filter(
                and_(
                    Quote.provider_id == provider_id,
                    Quote.status == QuoteStatus.ACCEPTED,
                )
            )
            .order_by(desc(Quote.updated_at))
            .all()
        )

    def get_provider_quote_stats(self, provider_id: int) -> Dict[str, Any]:
        """Get quote statistics for a specific provider."""
        all_quotes = (
            self.db_session.query(Quote).filter(Quote.provider_id == provider_id).all()
        )

        if not all_quotes:
            return {
                "provider_id": provider_id,
                "total_quotes": 0,
                "accepted_quotes": 0,
                "acceptance_rate": 0.0,
                "avg_quote_value": 0.0,
                "avg_response_time": 0.0,
            }

        accepted_quotes = [q for q in all_quotes if q.status == QuoteStatus.ACCEPTED]
        quote_values = [float(q.total_cost) for q in all_quotes]

        # Calculate response times (simplified - would need request creation time in real scenario)
        response_times = []
        for quote in all_quotes:
            if quote.submitted_at and quote.created_at:
                response_time = (
                    quote.submitted_at - quote.created_at
                ).total_seconds() / 3600  # hours
                response_times.append(response_time)

        return {
            "provider_id": provider_id,
            "total_quotes": len(all_quotes),
            "accepted_quotes": len(accepted_quotes),
            "acceptance_rate": len(accepted_quotes) / len(all_quotes) * 100,
            "avg_quote_value": sum(quote_values) / len(quote_values),
            "avg_response_time": sum(response_times) / len(response_times)
            if response_times
            else 0.0,
        }

    def find_quotes_by_date_range(
        self, start_date: datetime, end_date: datetime
    ) -> List[Quote]:
        """Find quotes created within date range."""
        return (
            self.db_session.query(Quote)
            .filter(and_(Quote.created_at >= start_date, Quote.created_at <= end_date))
            .order_by(desc(Quote.created_at))
            .all()
        )

    def update_expired_quotes(self) -> int:
        """Update expired quotes to EXPIRED status."""
        current_time = datetime.now(timezone.utc)
        updated_count = (
            self.db_session.query(Quote)
            .filter(
                and_(
                    Quote.valid_until < current_time,
                    Quote.status.in_([QuoteStatus.SUBMITTED, QuoteStatus.DRAFT]),
                )
            )
            .update({"status": QuoteStatus.EXPIRED}, synchronize_session=False)
        )

        self.db_session.commit()
        return updated_count

    def find_best_quotes_for_request(
        self, request_id: int, limit: int = 5
    ) -> List[Quote]:
        """Find best quotes for a request based on cost and provider rating."""
        # This would typically involve a more complex scoring algorithm
        # For now, we'll sort by cost and limit results
        return (
            self.db_session.query(Quote)
            .filter(
                and_(
                    Quote.request_id == request_id,
                    Quote.status == QuoteStatus.SUBMITTED,
                )
            )
            .order_by(asc(Quote.total_cost))
            .limit(limit)
            .all()
        )

    async def bulk_update_status(
        self, quote_ids: List[int], status: QuoteStatus
    ) -> int:
        """Bulk update status for multiple quotes."""
        updated_count = (
            self.db_session.query(Quote)
            .filter(Quote.id.in_(quote_ids))
            .update({"status": status}, synchronize_session=False)
        )

        self.db_session.commit()
        return updated_count

    def get_multiple_by_ids(self, quote_ids: List[int]) -> List[Quote]:
        """Get multiple quotes by their IDs."""
        return self.db_session.query(Quote).filter(Quote.id.in_(quote_ids)).all()

    async def get_by_request_id(self, request_id: int) -> List[Quote]:
        """Get quotes by request ID (alias for find_by_request_id for service compatibility)."""
        return self.find_by_request_id(request_id)

    def get_by_provider_id(self, provider_id: int) -> List[Quote]:
        """Get quotes by provider ID (alias for find_by_provider_id for service compatibility)."""
        return self.find_by_provider_id(provider_id)

    async def get_by_request_and_provider(
        self, request_id: int, provider_id: int
    ) -> Optional[Quote]:
        """Get quote by request ID and provider ID."""
        return (
            self.db_session.query(Quote)
            .filter(Quote.request_id == request_id, Quote.provider_id == provider_id)
            .first()
        )

    async def get_analytics(self, quote_id: int) -> Dict[str, Any]:
        """Get analytics for a specific quote."""
        quote = await self.get_by_id(quote_id)
        if not quote:
            return {
                "views": 0,
                "responses": 0,
                "acceptance_rate": 0.0,
                "average_response_time": 0,
                "response_time": 0,
                "competitive_position": "average",
            }

        # Mock analytics data for now
        return {
            "views": 0,
            "responses": 0,
            "acceptance_rate": 0.0,
            "average_response_time": 0,
            "response_time": 0,
            "competitive_position": "average",
        }

    async def expire_quotes_before(self, cutoff_date: datetime) -> int:
        """Expire quotes older than cutoff date."""
        updated_count = (
            self.db_session.query(Quote)
            .filter(
                and_(
                    Quote.created_at < cutoff_date,
                    Quote.status.in_([QuoteStatus.SUBMITTED, QuoteStatus.DRAFT]),
                )
            )
            .update({"status": QuoteStatus.EXPIRED}, synchronize_session=False)
        )

        self.db_session.commit()
        return updated_count

    async def get_provider_stats(self, provider_id: int) -> Dict[str, Any]:
        """Get quote statistics for a provider."""
        return self.get_provider_quote_stats(provider_id)

    async def get_provider_statistics(self, provider_id: int) -> Dict[str, Any]:
        """Get quote statistics for a provider (alias)."""
        return self.get_provider_quote_stats(provider_id)

    async def list_with_filters(
        self,
        filters: Dict[str, Any] = None,
        sort_by: str = "created_at",
        order: str = "desc",
        page: int = 1,
        size: int = 10,
    ) -> Dict[str, Any]:
        """List quotes with pagination and filtering."""
        if filters is None:
            filters = {}

        query = self.db_session.query(Quote)

        # Apply filters
        if "status" in filters:
            query = query.filter(Quote.status == filters["status"])
        if "provider_id" in filters:
            query = query.filter(Quote.provider_id == filters["provider_id"])
        if "request_id" in filters:
            query = query.filter(Quote.request_id == filters["request_id"])

        # Apply sorting
        if sort_by == "created_at":
            if order == "desc":
                query = query.order_by(desc(Quote.created_at))
            else:
                query = query.order_by(asc(Quote.created_at))
        elif sort_by == "total_cost":
            if order == "desc":
                query = query.order_by(desc(Quote.total_cost))
            else:
                query = query.order_by(asc(Quote.total_cost))

        # Get total count
        total = query.count()

        # Apply pagination
        offset = (page - 1) * size
        items = query.offset(offset).limit(size).all()

        return {
            "items": items,
            "total": total,
            "page": page,
            "size": size,
            "pages": (total + size - 1) // size,
        }
