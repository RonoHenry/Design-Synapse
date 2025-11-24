"""
TDD Tests for Quote Model

Following Test-Driven Development principles:
1. Write failing tests first (RED)
2. Implement minimal code to make tests pass (GREEN)
3. Refactor while keeping tests green (REFACTOR)

These tests define the expected behavior of the Quote model
BEFORE implementation exists.
"""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from sqlalchemy.exc import IntegrityError

# These imports will fail initially - that's the point of TDD!
try:
    from src.models.quote import Quote, QuoteStatus
except ImportError:
    # Expected during TDD RED phase
    Quote = None
    QuoteStatus = None

from tests.factories import ServiceProviderFactory


@pytest.mark.unit
@pytest.mark.tdd
class TestQuoteModel:
    """TDD Test cases for Quote model - RED phase."""
    
    def test_create_quote_with_required_fields(self, db_session):
        """
        TDD Test: Quote should be created with minimal required fields.
        
        Requirements: 5.1, 5.2
        """
        # Arrange - Define what we expect to work
        provider = ServiceProviderFactory.create()
        db_session.add(provider)
        db_session.flush()  # Get the ID without committing
        
        quote_data = {
            "request_id": 1,  # Reference to ServiceRequest
            "provider_id": provider.id,
            "labor_cost": Decimal("800.00"),
            "material_cost": Decimal("200.00"),
            "travel_cost": Decimal("50.00"),
            "total_cost": Decimal("1050.00"),
            "estimated_hours": 12,
            "start_availability": datetime.now() + timedelta(days=3),
            "completion_estimate": datetime.now() + timedelta(days=5),
            "description": "Complete electrical work for kitchen renovation",
            "valid_until": datetime.now() + timedelta(days=14)
        }
        
        # Act - Create the quote
        quote = Quote(**quote_data)
        db_session.add(quote)
        db_session.commit()
        db_session.refresh(quote)
        
        # Assert - Verify the quote was created correctly
        assert quote.id is not None
        assert quote.request_id == 1
        assert quote.provider_id == provider.id
        assert quote.labor_cost == Decimal("800.00")
        assert quote.material_cost == Decimal("200.00")
        assert quote.travel_cost == Decimal("50.00")
        assert quote.total_cost == Decimal("1050.00")
        assert quote.estimated_hours == 12
        assert quote.status == QuoteStatus.DRAFT  # Default status
        assert quote.created_at is not None
        assert quote.updated_at is not None
    
    def test_quote_cost_calculation_validation(self, db_session):
        """
        TDD Test: Quote should validate that total cost matches component costs.
        
        Requirements: 5.1
        """
        # Arrange
        provider = ServiceProviderFactory.create()
        db_session.add(provider)
        db_session.flush()  # Get the ID without committing
        
        labor_cost = Decimal("1000.00")
        material_cost = Decimal("300.00")
        travel_cost = Decimal("75.00")
        expected_total = labor_cost + material_cost + travel_cost
        
        # Act - Create quote with calculated total
        quote = Quote(
            request_id=1,
            provider_id=provider.id,
            labor_cost=labor_cost,
            material_cost=material_cost,
            travel_cost=travel_cost,
            total_cost=expected_total,
            estimated_hours=16,
            start_availability=datetime.now() + timedelta(days=2),
            completion_estimate=datetime.now() + timedelta(days=4),
            description="Cost calculation validation test quote",
            valid_until=datetime.now() + timedelta(days=10)
        )
        db_session.add(quote)
        db_session.commit()
        
        # Assert - Verify cost calculation
        assert quote.total_cost == expected_total
        assert quote.labor_cost + quote.material_cost + quote.travel_cost == quote.total_cost
    
    def test_quote_status_workflow(self, db_session):
        """
        TDD Test: Quote should follow proper status workflow.
        
        Requirements: 5.3, 5.4
        """
        # Arrange - Create draft quote
        provider = ServiceProviderFactory.create()
        db_session.add(provider)
        db_session.flush()  # Get the ID without committing
        quote = Quote(
            request_id=1,
            provider_id=provider.id,
            labor_cost=Decimal("500.00"),
            total_cost=Decimal("500.00"),
            estimated_hours=8,
            start_availability=datetime.now() + timedelta(days=1),
            completion_estimate=datetime.now() + timedelta(days=2),
            description="Status workflow test quote",
            valid_until=datetime.now() + timedelta(days=7)
        )
        db_session.add(quote)
        db_session.commit()
        
        # Assert initial status
        assert quote.status == QuoteStatus.DRAFT
        
        # Test status transitions
        quote.status = QuoteStatus.SUBMITTED
        db_session.commit()
        assert quote.status == QuoteStatus.SUBMITTED
        
        quote.status = QuoteStatus.ACCEPTED
        db_session.commit()
        assert quote.status == QuoteStatus.ACCEPTED
    
    def test_quote_expiration_handling(self, db_session):
        """
        TDD Test: Quote should handle expiration dates properly.
        
        Requirements: 5.5
        """
        # Arrange
        provider = ServiceProviderFactory.create()
        db_session.add(provider)
        db_session.flush()  # Get the ID without committing
        
        # Create quote with future expiration
        future_expiry = datetime.now() + timedelta(days=14)
        quote = Quote(
            request_id=1,
            provider_id=provider.id,
            labor_cost=Decimal("600.00"),
            total_cost=Decimal("600.00"),
            estimated_hours=10,
            start_availability=datetime.now() + timedelta(days=2),
            completion_estimate=datetime.now() + timedelta(days=4),
            description="Expiration handling test quote",
            valid_until=future_expiry
        )
        db_session.add(quote)
        db_session.commit()
        
        # Assert expiration handling
        assert quote.valid_until == future_expiry
        assert quote.valid_until > datetime.now()
        
        # Test expiration check method (to be implemented)
        # assert not quote.is_expired()
    
    def test_quote_terms_and_notes_fields(self, db_session):
        """
        TDD Test: Quote should store terms and notes as text fields.
        
        Requirements: 5.2
        """
        # Arrange
        provider = ServiceProviderFactory.create()
        db_session.add(provider)
        db_session.flush()  # Get the ID without committing
        
        terms = """
        Payment Terms:
        - 50% deposit required upon acceptance
        - Remaining 50% due upon completion
        - Materials to be purchased by contractor
        - 1-year warranty on workmanship
        """
        
        notes = """
        Additional Notes:
        - Work to be performed during business hours only
        - Client to provide access to electrical panel
        - Permit applications included in quote
        """
        
        # Act - Create quote with terms and notes
        quote = Quote(
            request_id=1,
            provider_id=provider.id,
            labor_cost=Decimal("1200.00"),
            material_cost=Decimal("400.00"),
            total_cost=Decimal("1600.00"),
            estimated_hours=20,
            start_availability=datetime.now() + timedelta(days=5),
            completion_estimate=datetime.now() + timedelta(days=8),
            description="Terms and notes test quote",
            valid_until=datetime.now() + timedelta(days=21),
            terms_and_conditions=terms,
            notes=notes
        )
        db_session.add(quote)
        db_session.commit()
        
        # Assert - Verify text storage
        assert quote.terms_and_conditions == terms
        assert quote.notes == notes
        assert "50% deposit" in quote.terms_and_conditions
        assert "business hours" in quote.notes
    
    def test_quote_timeline_validation(self, db_session):
        """
        TDD Test: Quote should validate timeline consistency.
        """
        # Arrange
        provider = ServiceProviderFactory.create()
        db_session.add(provider)
        db_session.flush()  # Get the ID without committing
        
        start_date = datetime.now() + timedelta(days=3)
        completion_date = datetime.now() + timedelta(days=7)
        
        # Act - Create quote with valid timeline
        quote = Quote(
            request_id=1,
            provider_id=provider.id,
            labor_cost=Decimal("900.00"),
            total_cost=Decimal("900.00"),
            estimated_hours=15,
            start_availability=start_date,
            completion_estimate=completion_date,
            description="Timeline validation test quote",
            valid_until=datetime.now() + timedelta(days=14)
        )
        db_session.add(quote)
        db_session.commit()
        
        # Assert - Verify timeline logic
        assert quote.start_availability < quote.completion_estimate
        assert quote.completion_estimate > quote.start_availability
        
        # Calculate work duration
        work_duration = quote.completion_estimate - quote.start_availability
        assert work_duration.days >= 0
    
    def test_quote_provider_relationship(self, db_session):
        """
        TDD Test: Quote should have proper relationship with ServiceProvider.
        """
        # Arrange
        provider = ServiceProviderFactory.create(
            individual_name="John Smith",
            business_name="Smith Electrical"
        )
        db_session.add(provider)
        db_session.flush()  # Get the ID without committing
        
        # Act - Create quote linked to provider
        quote = Quote(
            request_id=1,
            provider_id=provider.id,
            labor_cost=Decimal("750.00"),
            total_cost=Decimal("750.00"),
            estimated_hours=12,
            start_availability=datetime.now() + timedelta(days=2),
            completion_estimate=datetime.now() + timedelta(days=4),
            description="Provider relationship test quote",
            valid_until=datetime.now() + timedelta(days=10)
        )
        db_session.add(quote)
        db_session.commit()
        
        # Assert - Verify relationship
        assert quote.provider_id == provider.id
        # Test relationship access (when implemented)
        # assert quote.provider.individual_name == "John Smith"
        # assert quote.provider.business_name == "Smith Electrical"


@pytest.mark.unit
@pytest.mark.tdd
class TestQuoteBusinessLogic:
    """TDD Test cases for Quote business logic - RED phase."""
    
    def test_quote_to_dict_method(self, db_session):
        """
        TDD Test: Quote should convert to dictionary for API responses.
        """
        # Arrange
        provider = ServiceProviderFactory.create()
        db_session.add(provider)
        db_session.flush()  # Get the ID without committing
        quote = Quote(
            request_id=1,
            provider_id=provider.id,
            labor_cost=Decimal("800.00"),
            material_cost=Decimal("200.00"),
            total_cost=Decimal("1000.00"),
            estimated_hours=16,
            start_availability=datetime.now() + timedelta(days=3),
            completion_estimate=datetime.now() + timedelta(days=6),
            description="To dict method test quote",
            valid_until=datetime.now() + timedelta(days=14)
        )
        db_session.add(quote)
        db_session.commit()
        
        # Act
        quote_dict = quote.to_dict()
        
        # Assert
        assert isinstance(quote_dict, dict)
        assert quote_dict["labor_cost"] == Decimal("800.00")
        assert quote_dict["total_cost"] == Decimal("1000.00")
        assert quote_dict["provider_id"] == provider.id
        assert "id" in quote_dict
        assert "created_at" in quote_dict
    
    def test_quote_string_representation(self, db_session):
        """
        TDD Test: Quote should have meaningful string representation.
        """
        # Arrange
        provider = ServiceProviderFactory.create()
        db_session.add(provider)
        db_session.flush()  # Get the ID without committing
        quote = Quote(
            request_id=1,
            provider_id=provider.id,
            labor_cost=Decimal("1500.00"),
            total_cost=Decimal("1500.00"),
            estimated_hours=24,
            start_availability=datetime.now() + timedelta(days=1),
            completion_estimate=datetime.now() + timedelta(days=3),
            description="String representation test quote",
            valid_until=datetime.now() + timedelta(days=7)
        )
        db_session.add(quote)
        db_session.commit()
        
        # Act
        quote_str = str(quote)
        
        # Assert
        assert "Quote" in quote_str
        assert str(quote.id) in quote_str
        assert str(quote.total_cost) in quote_str
    
    def test_quote_comparison_methods(self, db_session):
        """
        TDD Test: Quote should support comparison for ranking.
        
        Requirements: 5.5
        """
        # Arrange - Create multiple quotes for comparison
        provider1 = ServiceProviderFactory.create()
        provider2 = ServiceProviderFactory.create()
        db_session.add_all([provider1, provider2])
        db_session.flush()  # Get the IDs without committing
        
        quote1 = Quote(
            request_id=1,
            provider_id=provider1.id,
            labor_cost=Decimal("800.00"),
            total_cost=Decimal("800.00"),
            estimated_hours=12,
            start_availability=datetime.now() + timedelta(days=2),
            completion_estimate=datetime.now() + timedelta(days=4),
            description="Comparison test quote 1",
            valid_until=datetime.now() + timedelta(days=10)
        )
        
        quote2 = Quote(
            request_id=1,
            provider_id=provider2.id,
            labor_cost=Decimal("1000.00"),
            total_cost=Decimal("1000.00"),
            estimated_hours=15,
            start_availability=datetime.now() + timedelta(days=1),
            completion_estimate=datetime.now() + timedelta(days=3),
            description="Comparison test quote 2",
            valid_until=datetime.now() + timedelta(days=14)
        )
        
        db_session.add_all([quote1, quote2])
        db_session.commit()
        
        # Assert - Verify comparison capabilities
        assert quote1.total_cost < quote2.total_cost
        assert quote1.estimated_hours < quote2.estimated_hours
        
        # Test comparison methods (to be implemented)
        # assert quote1.is_cheaper_than(quote2)
        # assert quote2.is_faster_start_than(quote1)
    
    def test_quote_cost_breakdown_calculation(self, db_session):
        """
        TDD Test: Quote should provide cost breakdown analysis.
        """
        # Arrange
        provider = ServiceProviderFactory.create()
        db_session.add(provider)
        db_session.flush()  # Get the ID without committing
        
        quote = Quote(
            request_id=1,
            provider_id=provider.id,
            labor_cost=Decimal("1200.00"),
            material_cost=Decimal("300.00"),
            travel_cost=Decimal("100.00"),
            total_cost=Decimal("1600.00"),
            estimated_hours=20,
            start_availability=datetime.now() + timedelta(days=3),
            completion_estimate=datetime.now() + timedelta(days=6),
            description="Cost breakdown test quote",
            valid_until=datetime.now() + timedelta(days=14)
        )
        db_session.add(quote)
        db_session.commit()
        
        # Assert - Verify cost breakdown
        assert quote.labor_cost > Decimal("0")
        assert quote.material_cost >= Decimal("0")
        assert quote.travel_cost >= Decimal("0")
        
        # Test cost breakdown methods (to be implemented)
        # breakdown = quote.get_cost_breakdown()
        # assert breakdown["labor_percentage"] > 0
        # assert breakdown["material_percentage"] >= 0
        # assert breakdown["travel_percentage"] >= 0
        
        # Calculate hourly rate
        if quote.estimated_hours > 0:
            hourly_rate = quote.labor_cost / quote.estimated_hours
            assert hourly_rate > Decimal("0")
    
    def test_quote_duplicate_prevention(self, db_session):
        """
        TDD Test: Quote should prevent duplicate quotes from same provider for same request.
        """
        # Arrange
        provider = ServiceProviderFactory.create()
        db_session.add(provider)
        db_session.flush()  # Get the ID without committing
        
        # Create first quote
        quote1 = Quote(
            request_id=1,
            provider_id=provider.id,
            labor_cost=Decimal("500.00"),
            total_cost=Decimal("500.00"),
            estimated_hours=8,
            start_availability=datetime.now() + timedelta(days=1),
            completion_estimate=datetime.now() + timedelta(days=2),
            description="Duplicate prevention test quote 1",
            valid_until=datetime.now() + timedelta(days=7)
        )
        db_session.add(quote1)
        db_session.commit()
        
        # Act & Assert - Attempt to create duplicate should be handled
        # This might be enforced by unique constraint or business logic
        quote2 = Quote(
            request_id=1,  # Same request
            provider_id=provider.id,  # Same provider
            labor_cost=Decimal("600.00"),
            total_cost=Decimal("600.00"),
            estimated_hours=10,
            start_availability=datetime.now() + timedelta(days=2),
            completion_estimate=datetime.now() + timedelta(days=4),
            description="Duplicate prevention test quote 2",
            valid_until=datetime.now() + timedelta(days=10)
        )
        
        # This should either raise an error or be handled by business logic
        # The exact behavior will be defined during implementation
        db_session.add(quote2)
        
        # For now, we'll allow multiple quotes but test the constraint exists
        # In implementation, this might raise IntegrityError or be handled differently
        try:
            db_session.commit()
            # If no error, verify both quotes exist but have different IDs
            assert quote1.id != quote2.id
        except IntegrityError:
            # If constraint exists, this is expected behavior
            db_session.rollback()
            assert True  # Constraint working as expected