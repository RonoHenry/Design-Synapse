"""
Test Factories for Labor Services Marketplace

Factory classes for creating test data following the Factory Boy pattern.
These factories support our TDD approach by providing consistent test data.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict

import factory
import factory.alchemy
from faker import Faker

fake = Faker()

from src.models import (Booking, BookingMilestone, BookingStatus,
                        MilestoneStatus, ProficiencyLevel, ProviderSkill,
                        ProviderType, Quote, QuoteStatus, RequestStatus,
                        Review, ReviewStatus, ReviewType, ServiceArea,
                        ServiceProvider, ServiceRequest, Skill, SkillCategory,
                        SkillRequirement, UrgencyLevel, VerificationStatus)


class ServiceProviderFactory(factory.alchemy.SQLAlchemyModelFactory):
    """Factory for creating ServiceProvider test instances."""

    class Meta:
        model = ServiceProvider
        sqlalchemy_session_persistence = "flush"

    # Basic provider information (matching actual model fields)
    user_id = factory.Sequence(lambda n: n + 10000)  # Use sequence to avoid duplicates
    business_name = factory.Faker("company")
    individual_name = factory.Faker("name")
    provider_type = ProviderType.INDIVIDUAL
    description = factory.Faker("text", max_nb_chars=500)

    # Experience and qualifications
    experience_years = factory.Faker("random_int", min=1, max=30)

    # Verification and trust
    verification_status = VerificationStatus.PENDING
    verification_date = None

    # Ratings and performance (matching actual model fields)
    rating = factory.Faker(
        "pydecimal", left_digits=1, right_digits=2, min_value=0, max_value=5
    )
    total_reviews = factory.Faker("random_int", min=0, max=100)
    total_jobs_completed = factory.Faker("random_int", min=0, max=200)
    response_time_avg = factory.Faker("random_int", min=5, max=120)

    # Status
    is_active = True
    is_available = True


class SkillCategoryFactory(factory.alchemy.SQLAlchemyModelFactory):
    """Factory for creating SkillCategory test instances."""

    class Meta:
        model = SkillCategory
        sqlalchemy_session_persistence = "flush"

    name = factory.Sequence(lambda n: f"Category {n}")
    description = factory.Faker("text", max_nb_chars=200)
    sort_order = factory.Sequence(lambda n: n)
    is_active = True


class SkillFactory(factory.alchemy.SQLAlchemyModelFactory):
    """Factory for creating Skill test instances."""

    class Meta:
        model = Skill
        sqlalchemy_session_persistence = "flush"

    category = factory.SubFactory(SkillCategoryFactory)
    name = factory.Sequence(lambda n: f"Skill {n}")
    description = factory.Faker("text", max_nb_chars=200)
    requires_certification = factory.Faker("boolean")
    is_active = True


class ProviderSkillFactory(factory.alchemy.SQLAlchemyModelFactory):
    """Factory for creating ProviderSkill test instances."""

    class Meta:
        model = ProviderSkill
        sqlalchemy_session_persistence = "flush"

    provider = factory.SubFactory(ServiceProviderFactory)
    skill = factory.SubFactory(SkillFactory)
    proficiency_level = ProficiencyLevel.INTERMEDIATE
    years_experience = factory.Faker("random_int", min=1, max=15)
    hourly_rate = factory.Faker(
        "pydecimal", left_digits=3, right_digits=2, min_value=25, max_value=150
    )
    certifications = factory.LazyFunction(
        lambda: [
            {
                "name": "Sample Certification",
                "issuer": "Professional Board",
                "date_issued": "2023-01-01",
                "expiry_date": "2025-01-01",
            }
        ]
    )
    is_primary = False


class ServiceAreaFactory(factory.alchemy.SQLAlchemyModelFactory):
    """Factory for creating ServiceArea test instances."""

    class Meta:
        model = ServiceArea
        sqlalchemy_session_persistence = "flush"

    provider = factory.SubFactory(ServiceProviderFactory)
    center_latitude = factory.Faker("latitude")
    center_longitude = factory.Faker("longitude")
    radius_miles = factory.Faker("random_int", min=5, max=50)
    travel_rate = factory.Faker(
        "pydecimal", left_digits=2, right_digits=2, min_value=0.50, max_value=2.00
    )
    area_name = factory.Faker("city")
    is_primary = False
    is_active = True


class ServiceRequestFactory(factory.alchemy.SQLAlchemyModelFactory):
    """Factory for creating ServiceRequest test instances."""

    class Meta:
        model = ServiceRequest
        sqlalchemy_session_persistence = "flush"

    # Basic request information
    title = factory.Faker("sentence", nb_words=4)
    description = factory.Faker("text", max_nb_chars=1000)
    seeker_id = factory.Sequence(lambda n: n + 2000)

    # Location information
    location_address = factory.Faker("address")
    location_latitude = factory.Faker("latitude")
    location_longitude = factory.Faker("longitude")

    # Budget information
    budget_min = factory.LazyFunction(lambda: Decimal("500.00"))
    budget_max = factory.LazyAttribute(lambda obj: obj.budget_min + Decimal("1000.00"))
    budget_currency = "USD"

    # Timing and urgency
    urgency_level = factory.Faker(
        "random_element", elements=[level for level in UrgencyLevel]
    )
    preferred_start_date = factory.LazyFunction(
        lambda: datetime.now() + timedelta(days=7)
    )
    estimated_duration_hours = factory.Faker("random_int", min=4, max=80)

    # Status
    status = RequestStatus.DRAFT

    # Additional information
    requirements = factory.LazyFunction(
        lambda: {
            "tools_provided": True,
            "materials_included": False,
            "special_requirements": "Standard construction requirements",
        }
    )
    images = factory.LazyFunction(
        lambda: ["https://example.com/image_1.jpg", "https://example.com/image_2.jpg"]
    )

    # Project integration (optional)
    project_id = factory.Faker("random_int", min=1, max=100)


class SkillRequirementFactory(factory.alchemy.SQLAlchemyModelFactory):
    """Factory for creating SkillRequirement test instances."""

    class Meta:
        model = SkillRequirement
        sqlalchemy_session_persistence = "flush"

    service_request = factory.SubFactory(ServiceRequestFactory)
    skill_id = factory.Faker("random_int", min=1, max=50)
    proficiency_level = factory.Faker(
        "random_element", elements=["BEGINNER", "INTERMEDIATE", "ADVANCED", "EXPERT"]
    )
    is_required = factory.Faker("boolean")
    importance_weight = factory.Faker("random_int", min=1, max=10)
    notes = factory.Faker("sentence")


class QuoteFactory(factory.alchemy.SQLAlchemyModelFactory):
    """Factory for creating Quote test instances."""

    class Meta:
        model = Quote
        sqlalchemy_session_persistence = "flush"

    request_id = factory.Sequence(lambda n: n + 3000)
    provider_id = factory.Sequence(lambda n: n + 4000)

    # Cost breakdown
    labor_cost = factory.LazyFunction(
        lambda: Decimal(str(fake.random_int(min=200, max=2000)))
    )
    material_cost = factory.LazyFunction(
        lambda: Decimal(str(fake.random_int(min=0, max=1000)))
    )
    travel_cost = factory.LazyFunction(
        lambda: Decimal(str(fake.random_int(min=0, max=200)))
    )

    # Timeline
    start_availability = factory.LazyFunction(
        lambda: datetime.now() + timedelta(days=fake.random_int(min=1, max=14))
    )
    completion_estimate = factory.LazyAttribute(
        lambda obj: obj.start_availability
        + timedelta(days=fake.random_int(min=1, max=21))
    )
    estimated_hours = factory.Faker("random_int", min=4, max=40)

    # Quote details
    description = factory.Faker("text", max_nb_chars=1000)
    terms_and_conditions = factory.Faker("text", max_nb_chars=500)
    notes = factory.Faker("sentence")

    # Status
    status = QuoteStatus.SUBMITTED

    # Expiration (7 days from now by default)
    valid_until = factory.LazyFunction(lambda: datetime.now() + timedelta(days=7))

    @factory.post_generation
    def set_completion_estimate(self, create, extracted, **kwargs):
        """Set completion estimate based on start date and estimated hours."""
        if self.start_availability and self.estimated_hours:
            # Assume 8 hours per day
            days_needed = max(1, self.estimated_hours // 8)
            self.completion_estimate = self.start_availability + timedelta(
                days=days_needed
            )

    @factory.post_generation
    def set_total_cost_if_not_provided(self, create, extracted, **kwargs):
        """Set total cost from components if not explicitly provided."""
        # If total_cost is None or not set, calculate it
        if not hasattr(self, "total_cost") or self.total_cost is None:
            self.total_cost = self.labor_cost + self.material_cost + self.travel_cost


class BookingFactory(factory.alchemy.SQLAlchemyModelFactory):
    """Factory for creating Booking test instances."""

    class Meta:
        model = Booking
        sqlalchemy_session_persistence = "flush"

    service_request_id = factory.Sequence(lambda n: n + 5000)
    quote_id = factory.Sequence(lambda n: n + 6000)
    provider_id = factory.Sequence(lambda n: n + 7000)
    client_id = factory.Sequence(lambda n: n + 8000)

    # Schedule information
    scheduled_start_date = factory.LazyFunction(
        lambda: datetime.now() + timedelta(days=fake.random_int(min=1, max=30))
    )
    scheduled_completion_date = factory.LazyAttribute(
        lambda obj: obj.scheduled_start_date
        + timedelta(days=fake.random_int(min=1, max=7))
    )

    # Cost information
    total_cost = factory.LazyFunction(
        lambda: Decimal(str(fake.random_int(min=500, max=5000)))
    )
    currency = "USD"
    payment_terms = factory.LazyFunction(
        lambda: {
            "payment_method": "credit_card",
            "milestone_based": True,
            "deposit_percentage": 25,
            "final_payment_percentage": 25,
        }
    )

    # Status
    status = BookingStatus.CONFIRMED

    # Additional information
    notes = factory.Faker("text", max_nb_chars=500)


class BookingMilestoneFactory(factory.alchemy.SQLAlchemyModelFactory):
    """Factory for creating BookingMilestone test instances."""

    class Meta:
        model = BookingMilestone
        sqlalchemy_session_persistence = "flush"

    booking_id = factory.Sequence(
        lambda n: n + 1000
    )  # Default booking_id, can be overridden
    title = factory.Faker("sentence", nb_words=3)
    description = factory.Faker("text", max_nb_chars=300)
    sequence_number = factory.Sequence(lambda n: n + 1)

    # Payment information
    amount = factory.LazyFunction(
        lambda: Decimal(str(fake.random_int(min=100, max=1000)))
    )
    currency = "USD"

    # Status
    status = MilestoneStatus.PENDING

    # Dates
    due_date = factory.LazyFunction(
        lambda: datetime.now() + timedelta(days=fake.random_int(min=7, max=30))
    )

    # Additional information
    notes = factory.Faker("sentence")


class ReviewFactory(factory.alchemy.SQLAlchemyModelFactory):
    """Factory for creating Review test instances."""

    class Meta:
        model = Review
        sqlalchemy_session_persistence = "flush"

    booking_id = factory.Sequence(lambda n: n + 9000)
    reviewer_id = factory.Sequence(lambda n: n + 10000)
    reviewee_id = factory.Sequence(lambda n: n + 11000)

    # Review type
    review_type = factory.Faker(
        "random_element",
        elements=[ReviewType.SEEKER_TO_PROVIDER, ReviewType.PROVIDER_TO_SEEKER],
    )

    # Rating system (1-5 scale)
    overall_rating = factory.Faker("random_int", min=1, max=5)
    quality_rating = factory.Faker("random_int", min=1, max=5)
    timeliness_rating = factory.Faker("random_int", min=1, max=5)
    communication_rating = factory.Faker("random_int", min=1, max=5)

    # Review content
    comment = factory.Faker("text", max_nb_chars=1000)
    images = factory.LazyFunction(
        lambda: [
            f"https://example.com/review_image_{i}.jpg"
            for i in range(fake.random_int(min=0, max=2))
        ]
    )

    # Status
    status = ReviewStatus.PUBLISHED

    # Community features
    helpful_votes = factory.Faker("random_int", min=0, max=50)


# Specialized factories for specific test scenarios


class HighUrgencyServiceRequestFactory(ServiceRequestFactory):
    """Factory for high urgency service requests."""

    urgency_level = UrgencyLevel.EMERGENCY
    preferred_start_date = factory.LazyFunction(
        lambda: datetime.now() + timedelta(hours=24)
    )


class LowBudgetServiceRequestFactory(ServiceRequestFactory):
    """Factory for low budget service requests."""

    budget_min = Decimal("100.00")
    budget_max = Decimal("300.00")


class HighBudgetServiceRequestFactory(ServiceRequestFactory):
    """Factory for high budget service requests."""

    budget_min = Decimal("2000.00")
    budget_max = Decimal("5000.00")


class ExpiredQuoteFactory(QuoteFactory):
    """Factory for expired quotes."""

    valid_until = factory.LazyFunction(lambda: datetime.now() - timedelta(days=1))
    status = QuoteStatus.EXPIRED


class AcceptedQuoteFactory(QuoteFactory):
    """Factory for accepted quotes."""

    status = QuoteStatus.ACCEPTED
    submitted_at = factory.LazyFunction(lambda: datetime.now() - timedelta(days=2))


class CompletedBookingFactory(BookingFactory):
    """Factory for completed bookings."""

    status = BookingStatus.COMPLETED
    actual_start_date = factory.LazyFunction(lambda: datetime.now() - timedelta(days=5))
    actual_completion_date = factory.LazyFunction(
        lambda: datetime.now() - timedelta(days=1)
    )


class PaidMilestoneFactory(BookingMilestoneFactory):
    """Factory for paid milestones."""

    status = MilestoneStatus.PAID
    completed_date = factory.LazyFunction(lambda: datetime.now() - timedelta(days=3))
    paid_date = factory.LazyFunction(lambda: datetime.now() - timedelta(days=1))


class PositiveReviewFactory(ReviewFactory):
    """Factory for positive reviews."""

    overall_rating = 5
    quality_rating = 5
    timeliness_rating = 5
    communication_rating = 5
    comment = "Excellent work! Highly professional and completed on time."


class NegativeReviewFactory(ReviewFactory):
    """Factory for negative reviews."""

    overall_rating = 2
    quality_rating = 2
    timeliness_rating = 1
    communication_rating = 3
    comment = "Work quality was below expectations and took much longer than promised."


# Utility functions for creating related test data


def create_complete_service_workflow(db_session) -> Dict[str, Any]:
    """
    Create a complete service workflow for integration testing.

    Returns a dictionary with all related objects:
    - service_request
    - quote
    - booking
    - milestones
    - reviews
    """
    # Create service request
    service_request = ServiceRequestFactory.create()
    db_session.add(service_request)
    db_session.flush()

    # Create quote for the request
    quote = QuoteFactory.create(request_id=service_request.id)
    db_session.add(quote)
    db_session.flush()

    # Create booking from accepted quote
    quote.status = QuoteStatus.ACCEPTED
    booking = BookingFactory.create(
        service_request_id=service_request.id,
        quote_id=quote.id,
        provider_id=quote.provider_id,
        client_id=service_request.seeker_id,
        total_cost=quote.total_cost,
    )
    db_session.add(booking)
    db_session.flush()

    # Create milestones for the booking
    milestones = [
        BookingMilestoneFactory.create(
            booking_id=booking.id,
            title="Initial Payment",
            sequence_number=1,
            amount=booking.total_cost * Decimal("0.25"),
        ),
        BookingMilestoneFactory.create(
            booking_id=booking.id,
            title="Mid-project Payment",
            sequence_number=2,
            amount=booking.total_cost * Decimal("0.50"),
        ),
        BookingMilestoneFactory.create(
            booking_id=booking.id,
            title="Final Payment",
            sequence_number=3,
            amount=booking.total_cost * Decimal("0.25"),
        ),
    ]

    for milestone in milestones:
        db_session.add(milestone)
    db_session.flush()

    # Create reviews (bidirectional)
    seeker_review = ReviewFactory.create(
        booking_id=booking.id,
        reviewer_id=booking.client_id,
        reviewee_id=booking.provider_id,
        review_type=ReviewType.SEEKER_TO_PROVIDER,
    )

    provider_review = ReviewFactory.create(
        booking_id=booking.id,
        reviewer_id=booking.provider_id,
        reviewee_id=booking.client_id,
        review_type=ReviewType.PROVIDER_TO_SEEKER,
    )

    db_session.add_all([seeker_review, provider_review])
    db_session.commit()

    return {
        "service_request": service_request,
        "quote": quote,
        "booking": booking,
        "milestones": milestones,
        "reviews": [seeker_review, provider_review],
    }


def create_provider_with_multiple_quotes(
    db_session, num_quotes: int = 3
) -> Dict[str, Any]:
    """
    Create a provider with multiple quotes for testing aggregation.
    """
    provider = ServiceProviderFactory.create()
    db_session.add(provider)
    db_session.flush()

    quotes = []
    for i in range(num_quotes):
        quote = QuoteFactory.create(provider_id=provider.id)
        quotes.append(quote)
        db_session.add(quote)

    db_session.commit()

    return {"provider": provider, "quotes": quotes}


def create_provider_with_reviews(db_session, num_reviews: int = 5) -> Dict[str, Any]:
    """
    Create a provider with multiple reviews for testing rating aggregation.
    """
    provider = ServiceProviderFactory.create()
    db_session.add(provider)
    db_session.flush()

    reviews = []
    for i in range(num_reviews):
        # Create a booking first
        booking = BookingFactory.create(provider_id=provider.id)
        db_session.add(booking)
        db_session.flush()

        # Create review for the booking
        review = ReviewFactory.create(
            booking_id=booking.id,
            reviewee_id=provider.id,
            review_type=ReviewType.SEEKER_TO_PROVIDER,
        )
        reviews.append(review)
        db_session.add(review)

    db_session.commit()

    return {"provider": provider, "reviews": reviews}
