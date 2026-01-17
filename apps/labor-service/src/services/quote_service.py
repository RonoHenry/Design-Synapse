"""
QuoteService - GREEN Phase Implementation
Following TDD methodology - minimal implementation to make tests pass
"""
from typing import Dict, Any, List, Optional
from decimal import Decimal
from datetime import datetime, timedelta, timezone
from src.models.quote import Quote, QuoteStatus
from src.core.exceptions import QuoteNotFoundError, ValidationError, BusinessLogicError


class QuoteService:
    """Service for managing quotes - minimal TDD implementation"""
    
    def __init__(self, quote_repository, request_repository, provider_repository, notification_service):
        self.quote_repository = quote_repository
        self.request_repository = request_repository
        self.provider_repository = provider_repository
        self.notification_service = notification_service
    
    async def create_quote(self, quote_data: Dict[str, Any]) -> Quote:
        """Create a new quote"""
        # Validate quote amount
        amount = quote_data.get("amount")
        if amount and amount <= 0:
            raise ValidationError("Quote amount must be positive")
        
        # Validate timeline
        estimated_hours = quote_data.get("estimated_hours")
        if estimated_hours and estimated_hours <= 0:
            raise ValidationError("Estimated hours must be positive")
        
        # Set initial status
        quote_data["status"] = QuoteStatus.PENDING
        quote_data["created_at"] = datetime.now(timezone.utc)
        
        return await self.quote_repository.create(quote_data)
    
    async def submit_quote(self, quote_data: Dict[str, Any]) -> Quote:
        """Submit a new quote for a service request"""
        # Validate required fields
        if not quote_data.get("request_id"):
            raise ValidationError("Request ID is required")
        if not quote_data.get("provider_id"):
            raise ValidationError("Provider ID is required")
        
        # Validate that the request exists and is active
        request = await self.request_repository.get_by_id(quote_data["request_id"])
        if not request:
            raise ValidationError("Request not found")
        
        # Check if request is active (can accept quotes)
        from src.models.service_request import RequestStatus
        if request.status not in [RequestStatus.ACTIVE, RequestStatus.DRAFT]:
            raise BusinessLogicError("Cannot submit quote for inactive request")
        
        # Check for duplicate quotes from same provider
        existing_quote = await self.quote_repository.get_by_request_and_provider(
            quote_data["request_id"], quote_data["provider_id"]
        )
        if existing_quote:
            raise BusinessLogicError("Provider has already submitted a quote for this request")
        
        # Validate costs
        labor_cost = quote_data.get("labor_cost", Decimal("0"))
        material_cost = quote_data.get("material_cost", Decimal("0"))
        travel_cost = quote_data.get("travel_cost", Decimal("0"))
        
        if labor_cost < 0 or material_cost < 0 or travel_cost < 0:
            raise ValidationError("Costs cannot be negative")
        
        # Calculate total cost
        total_cost = labor_cost + material_cost + travel_cost
        quote_data["total_cost"] = total_cost
        
        # Check if quote exceeds request budget
        if request.budget_max and total_cost > request.budget_max:
            raise ValidationError("Quote exceeds maximum budget")
        
        # Set status and timestamps
        quote_data["status"] = QuoteStatus.SUBMITTED
        quote_data["created_at"] = datetime.now(timezone.utc)
        
        return await self.quote_repository.create(quote_data)
    
    async def get_quote(self, quote_id: int) -> Quote:
        """Get quote by ID"""
        quote = await self.quote_repository.get_by_id(quote_id)
        if not quote:
            raise QuoteNotFoundError(quote_id)
        return quote
    
    async def update_quote_status(self, quote_id: int, status: QuoteStatus) -> Quote:
        """Update quote status"""
        quote = await self.get_quote(quote_id)
        return await self.quote_repository.update(quote_id, {"status": status})
    
    async def accept_quote(self, quote_id: int, seeker_id: int) -> Quote:
        """Accept a quote"""
        quote = await self.get_quote(quote_id)
        
        # Verify the request exists and get the seeker
        request = await self.request_repository.get_by_id(quote.request_id)
        if not request:
            raise ValidationError("Associated request not found")
        
        # Verify only the request owner can accept quotes
        if request.seeker_id != seeker_id:
            raise BusinessLogicError("Only request owner can accept quotes")
        
        if quote.status != QuoteStatus.SUBMITTED:
            raise ValidationError("Only submitted quotes can be accepted")
        
        # Accept the quote
        updated_quote = await self.quote_repository.update(quote_id, {"status": QuoteStatus.ACCEPTED})
        
        # Reject all other quotes for this request
        other_quotes = await self.quote_repository.get_by_request_id(quote.request_id)
        other_quote_ids = [q.id for q in other_quotes if q.id != quote_id and q.status == QuoteStatus.SUBMITTED]
        
        if other_quote_ids:
            await self.quote_repository.bulk_update_status(other_quote_ids, QuoteStatus.REJECTED)
        
        # Notify provider of acceptance
        await self.notification_service.notify_quote_accepted(quote_id)
        
        return updated_quote
    
    async def update_quote(self, quote_id: int, update_data: Dict[str, Any]) -> Quote:
        """Update an existing quote"""
        quote = await self.get_quote(quote_id)
        
        # Validate that quote can be updated
        if quote.status == QuoteStatus.ACCEPTED:
            raise BusinessLogicError("Cannot update accepted quote")
        
        if quote.status == QuoteStatus.REJECTED:
            raise BusinessLogicError("Cannot update rejected quote")
        
        # Update the quote
        return await self.quote_repository.update(quote_id, update_data)
    
    async def compare_quotes(self, quote_ids: List[int]) -> Dict[str, Any]:
        """Compare multiple quotes"""
        quotes = await self.quote_repository.get_multiple_by_ids(quote_ids)
        
        if not quotes:
            return {"comparison_matrix": [], "recommendations": []}
        
        # Create comparison matrix
        comparison_matrix = []
        for quote in quotes:
            comparison_matrix.append({
                "quote_id": quote.id,
                "provider_id": quote.provider_id,
                "total_cost": float(quote.total_cost) if quote.total_cost else 0,
                "estimated_hours": quote.estimated_hours or 0,
                "hourly_rate": float(quote.total_cost / quote.estimated_hours) if quote.estimated_hours and quote.total_cost else 0
            })
        
        # Sort by cost for recommendations
        sorted_quotes = sorted(comparison_matrix, key=lambda x: x["total_cost"])
        recommendations = [f"Quote {q['quote_id']} offers best value" for q in sorted_quotes[:3]]
        
        return {
            "comparison_matrix": comparison_matrix,
            "recommendations": recommendations
        }
    
    async def rank_quotes_by_value(self, request_id: int) -> Dict[str, Any]:
        """Rank quotes by value proposition"""
        quotes = await self.quote_repository.get_by_request_id(request_id)
        
        if not quotes:
            return {"ranked_quotes": [], "analysis": "No quotes found"}
        
        # Get provider information for ranking
        provider_ids = [q.provider_id for q in quotes]
        providers = self.provider_repository.get_multiple_by_ids(provider_ids)
        provider_map = {p.id: p for p in providers}
        
        # Calculate value scores
        ranked_quotes = []
        for quote in quotes:
            provider = provider_map.get(quote.provider_id)
            
            # Simple value calculation (cost vs provider rating)
            cost_score = 1.0 / (float(quote.total_cost) / 1000) if quote.total_cost else 0
            rating_score = provider.rating if provider and provider.rating else 3.0
            value_score = (cost_score + rating_score) / 2
            
            ranked_quotes.append({
                "quote_id": quote.id,
                "provider_id": quote.provider_id,
                "total_cost": float(quote.total_cost) if quote.total_cost else 0,
                "value_score": value_score,
                "provider_rating": rating_score
            })
        
        # Sort by value score
        ranked_quotes.sort(key=lambda x: x["value_score"], reverse=True)
        
        return {
            "ranked_quotes": ranked_quotes,
            "analysis": f"Ranked {len(ranked_quotes)} quotes by value proposition"
        }
    
    async def extend_quote_validity(self, quote_id: int, new_expiry: datetime, provider_id: int) -> Quote:
        """Extend quote validity period"""
        quote = await self.get_quote(quote_id)
        
        # Verify provider authorization
        if quote.provider_id != provider_id:
            raise ValidationError("Only quote provider can extend validity")
        
        if quote.status != QuoteStatus.SUBMITTED:
            raise ValidationError("Can only extend validity of submitted quotes")
        
        # Update validity
        return await self.quote_repository.update(quote_id, {"valid_until": new_expiry})
    
    async def submit_counter_proposal(self, original_quote_id: int, counter_data: Dict[str, Any], provider_id: int) -> Quote:
        """Submit counter-proposal to existing quote"""
        original_quote = await self.get_quote(original_quote_id)
        
        # Create new quote as counter-proposal
        counter_quote_data = {
            "request_id": original_quote.request_id,
            "provider_id": original_quote.provider_id,
            "total_cost": counter_data.get("total_cost"),
            "notes": counter_data.get("notes", "Counter-proposal"),
            "status": QuoteStatus.SUBMITTED,
            "created_at": datetime.now(timezone.utc)
        }
        
        counter_quote = await self.quote_repository.create(counter_quote_data)
        
        # Notify about counter-proposal
        self.notification_service.notify_counter_proposal(counter_quote)
        
        return counter_quote
    
    async def reject_quote(self, quote_id: int, reason: str) -> Quote:
        """Reject a quote"""
        quote = await self.get_quote(quote_id)
        
        if quote.status != QuoteStatus.PENDING:
            raise ValidationError("Only pending quotes can be rejected")
        
        return await self.quote_repository.update(quote_id, {
            "status": QuoteStatus.REJECTED,
            "rejection_reason": reason
        })
    
    async def get_quotes_for_request(self, request_id: int) -> List[Quote]:
        """Get all quotes for a service request"""
        return await self.quote_repository.get_by_request_id(request_id)
    
    async def get_quotes_by_provider(self, provider_id: int) -> List[Quote]:
        """Get all quotes by a provider"""
        return await self.quote_repository.get_by_provider_id(provider_id)
    
    async def calculate_quote_competitiveness(self, quote_id: int) -> Dict[str, Any]:
        """Calculate how competitive a quote is"""
        quote = await self.get_quote(quote_id)
        competing_quotes = await self.quote_repository.get_by_request_id(quote.request_id)
        
        if len(competing_quotes) <= 1:
            return {"competitiveness": "no_competition", "rank": 1, "total_quotes": 1}
        
        # Sort by amount (ascending - lower is better)
        sorted_quotes = sorted(competing_quotes, key=lambda q: q.amount or Decimal('0'))
        
        # Find rank
        rank = next((i + 1 for i, q in enumerate(sorted_quotes) if q.id == quote_id), len(sorted_quotes))
        
        competitiveness = "high" if rank <= len(sorted_quotes) * 0.3 else "medium" if rank <= len(sorted_quotes) * 0.7 else "low"
        
        return {
            "competitiveness": competitiveness,
            "rank": rank,
            "total_quotes": len(sorted_quotes),
            "price_difference_from_lowest": float((quote.amount or Decimal('0')) - (sorted_quotes[0].amount or Decimal('0')))
        }
    
    async def get_quote_analytics(self, quote_id: int) -> Dict[str, Any]:
        """Get quote performance analytics"""
        quote = await self.get_quote(quote_id)
        return await self.quote_repository.get_analytics(quote_id)
    
    async def expire_old_quotes(self, days_old: int = 30) -> int:
        """Expire quotes older than specified days"""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_old)
        return await self.quote_repository.expire_quotes_before(cutoff_date)
    
    async def get_provider_quote_stats(self, provider_id: int) -> Dict[str, Any]:
        """Get quote statistics for a provider"""
        return await self.quote_repository.get_provider_stats(provider_id)
    
    async def get_provider_quote_statistics(self, provider_id: int) -> Dict[str, Any]:
        """Get quote statistics for a provider (alias for get_provider_quote_stats)"""
        return await self.quote_repository.get_provider_statistics(provider_id)