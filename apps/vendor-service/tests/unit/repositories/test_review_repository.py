"""Tests for ReviewRepository using TDD approach."""

from datetime import datetime, timedelta

import pytest
from src.repositories.review_repository import ReviewRepository
from tests.factories import ProductFactory, ReviewFactory, VendorFactory


class TestReviewRepository:
    """Test cases for ReviewRepository CRUD operations."""

    @pytest.fixture(autouse=True)
    def setup_test_data(self, db_session):
        """Set up test data for each test."""
        # Create vendors and products that reviews can reference
        self.vendor1 = VendorFactory(id=1, user_id=1)
        self.vendor2 = VendorFactory(id=2, user_id=2)
        self.product1 = ProductFactory(id=1, vendor_id=1)
        self.product2 = ProductFactory(id=2, vendor_id=1)
        self.product3 = ProductFactory(id=3, vendor_id=2)
        self.product4 = ProductFactory(id=4, vendor_id=2)
        db_session.add_all(
            [
                self.vendor1,
                self.vendor2,
                self.product1,
                self.product2,
                self.product3,
                self.product4,
            ]
        )
        db_session.commit()

    def test_create_review(self, db_session):
        """Test creating a new review."""
        repo = ReviewRepository(db_session)
        review_data = {
            "user_id": 1,
            "product_id": 1,
            "vendor_id": 1,
            "rating": 5,
            "comment": "Excellent product!",
            "verified_purchase": True,
        }

        review = repo.create(**review_data)

        assert review.id is not None
        assert review.user_id == 1
        assert review.product_id == 1
        assert review.vendor_id == 1
        assert review.rating == 5
        assert review.comment == "Excellent product!"
        assert review.verified_purchase is True
        assert review.created_at is not None

    def test_create_review_without_comment(self, db_session):
        """Test creating review without comment."""
        repo = ReviewRepository(db_session)
        review_data = {"user_id": 1, "product_id": 1, "vendor_id": 1, "rating": 4}

        review = repo.create(**review_data)

        assert review.id is not None
        assert review.comment is None
        assert review.verified_purchase is False

    def test_get_by_id_existing_review(self, db_session):
        """Test retrieving review by ID when review exists."""
        repo = ReviewRepository(db_session)
        review = ReviewFactory(user_id=1, product_id=1, vendor_id=1, rating=5)
        db_session.add(review)
        db_session.commit()

        result = repo.get_by_id(review.id)

        assert result is not None
        assert result.id == review.id
        assert result.user_id == 1
        assert result.rating == 5

    def test_get_by_id_nonexistent_review(self, db_session):
        """Test retrieving review by ID when review doesn't exist."""
        repo = ReviewRepository(db_session)

        result = repo.get_by_id(999)

        assert result is None

    def test_get_by_product(self, db_session):
        """Test retrieving reviews by product ID."""
        repo = ReviewRepository(db_session)
        reviews = [
            ReviewFactory(user_id=1, product_id=1, vendor_id=1, rating=5),
            ReviewFactory(user_id=2, product_id=1, vendor_id=1, rating=4),
            ReviewFactory(user_id=3, product_id=2, vendor_id=1, rating=3),
        ]
        for review in reviews:
            db_session.add(review)
        db_session.commit()

        product_1_reviews = repo.get_by_product(1)
        product_2_reviews = repo.get_by_product(2)

        assert len(product_1_reviews) == 2
        assert len(product_2_reviews) == 1
        assert all(review.product_id == 1 for review in product_1_reviews)

    def test_get_by_vendor(self, db_session):
        """Test retrieving reviews by vendor ID."""
        repo = ReviewRepository(db_session)
        reviews = [
            ReviewFactory(user_id=1, product_id=1, vendor_id=1, rating=5),
            ReviewFactory(user_id=2, product_id=2, vendor_id=1, rating=4),
            ReviewFactory(user_id=3, product_id=3, vendor_id=2, rating=3),
        ]
        for review in reviews:
            db_session.add(review)
        db_session.commit()

        vendor_1_reviews = repo.get_by_vendor(1)
        vendor_2_reviews = repo.get_by_vendor(2)

        assert len(vendor_1_reviews) == 2
        assert len(vendor_2_reviews) == 1
        assert all(review.vendor_id == 1 for review in vendor_1_reviews)

    def test_get_by_user(self, db_session):
        """Test retrieving reviews by user ID."""
        repo = ReviewRepository(db_session)
        reviews = [
            ReviewFactory(user_id=1, product_id=1, vendor_id=1, rating=5),
            ReviewFactory(user_id=1, product_id=2, vendor_id=1, rating=4),
            ReviewFactory(user_id=2, product_id=1, vendor_id=1, rating=3),
        ]
        for review in reviews:
            db_session.add(review)
        db_session.commit()

        user_1_reviews = repo.get_by_user(1)
        user_2_reviews = repo.get_by_user(2)

        assert len(user_1_reviews) == 2
        assert len(user_2_reviews) == 1
        assert all(review.user_id == 1 for review in user_1_reviews)

    def test_get_verified_reviews(self, db_session):
        """Test retrieving only verified reviews."""
        repo = ReviewRepository(db_session)
        reviews = [
            ReviewFactory(
                user_id=1, product_id=1, vendor_id=1, rating=5, verified_purchase=True
            ),
            ReviewFactory(
                user_id=2, product_id=1, vendor_id=1, rating=4, verified_purchase=False
            ),
            ReviewFactory(
                user_id=3, product_id=1, vendor_id=1, rating=3, verified_purchase=True
            ),
        ]
        for review in reviews:
            db_session.add(review)
        db_session.commit()

        verified_reviews = repo.get_verified_reviews()

        assert len(verified_reviews) == 2
        assert all(review.verified_purchase for review in verified_reviews)

    def test_get_by_rating_range(self, db_session):
        """Test retrieving reviews by rating range."""
        repo = ReviewRepository(db_session)
        reviews = [
            ReviewFactory(user_id=1, product_id=1, vendor_id=1, rating=1),
            ReviewFactory(user_id=2, product_id=1, vendor_id=1, rating=3),
            ReviewFactory(user_id=3, product_id=1, vendor_id=1, rating=5),
        ]
        for review in reviews:
            db_session.add(review)
        db_session.commit()

        high_ratings = repo.get_by_rating_range(4, 5)
        low_ratings = repo.get_by_rating_range(1, 2)

        assert len(high_ratings) == 1
        assert len(low_ratings) == 1
        assert high_ratings[0].rating == 5
        assert low_ratings[0].rating == 1

    def test_calculate_average_rating_for_product(self, db_session):
        """Test calculating average rating for a product."""
        repo = ReviewRepository(db_session)
        reviews = [
            ReviewFactory(user_id=1, product_id=1, vendor_id=1, rating=5),
            ReviewFactory(user_id=2, product_id=1, vendor_id=1, rating=3),
            ReviewFactory(user_id=3, product_id=1, vendor_id=1, rating=4),
        ]
        for review in reviews:
            db_session.add(review)
        db_session.commit()

        avg_rating = repo.calculate_average_rating_for_product(1)

        assert avg_rating == 4.0  # (5 + 3 + 4) / 3

    def test_calculate_average_rating_for_vendor(self, db_session):
        """Test calculating average rating for a vendor."""
        repo = ReviewRepository(db_session)
        reviews = [
            ReviewFactory(user_id=1, product_id=1, vendor_id=1, rating=5),
            ReviewFactory(user_id=2, product_id=2, vendor_id=1, rating=3),
            ReviewFactory(user_id=3, product_id=3, vendor_id=1, rating=2),
        ]
        for review in reviews:
            db_session.add(review)
        db_session.commit()

        avg_rating = repo.calculate_average_rating_for_vendor(1)

        assert avg_rating == pytest.approx(3.33, rel=1e-2)  # (5 + 3 + 2) / 3

    def test_calculate_average_rating_no_reviews(self, db_session):
        """Test calculating average rating when no reviews exist."""
        repo = ReviewRepository(db_session)

        avg_rating = repo.calculate_average_rating_for_product(999)

        assert avg_rating == 0.0

    def test_get_rating_distribution_for_product(self, db_session):
        """Test getting rating distribution for a product."""
        repo = ReviewRepository(db_session)
        reviews = [
            ReviewFactory(user_id=1, product_id=1, vendor_id=1, rating=5),
            ReviewFactory(user_id=2, product_id=1, vendor_id=1, rating=5),
            ReviewFactory(user_id=3, product_id=1, vendor_id=1, rating=4),
            ReviewFactory(user_id=4, product_id=1, vendor_id=1, rating=3),
            ReviewFactory(user_id=5, product_id=1, vendor_id=1, rating=1),
        ]
        for review in reviews:
            db_session.add(review)
        db_session.commit()

        distribution = repo.get_rating_distribution_for_product(1)

        assert distribution[5] == 2
        assert distribution[4] == 1
        assert distribution[3] == 1
        assert distribution[2] == 0
        assert distribution[1] == 1

    def test_get_rating_distribution_for_vendor(self, db_session):
        """Test getting rating distribution for a vendor."""
        repo = ReviewRepository(db_session)
        reviews = [
            ReviewFactory(user_id=1, product_id=1, vendor_id=1, rating=5),
            ReviewFactory(user_id=2, product_id=2, vendor_id=1, rating=4),
            ReviewFactory(user_id=3, product_id=3, vendor_id=1, rating=4),
            ReviewFactory(user_id=4, product_id=4, vendor_id=1, rating=2),
        ]
        for review in reviews:
            db_session.add(review)
        db_session.commit()

        distribution = repo.get_rating_distribution_for_vendor(1)

        assert distribution[5] == 1
        assert distribution[4] == 2
        assert distribution[3] == 0
        assert distribution[2] == 1
        assert distribution[1] == 0

    def test_update_review(self, db_session):
        """Test updating review."""
        repo = ReviewRepository(db_session)
        review = ReviewFactory(
            user_id=1, product_id=1, vendor_id=1, rating=3, comment="OK"
        )
        db_session.add(review)
        db_session.commit()

        updated_review = repo.update(review.id, rating=5, comment="Great product!")

        assert updated_review is not None
        assert updated_review.rating == 5
        assert updated_review.comment == "Great product!"

    def test_update_nonexistent_review(self, db_session):
        """Test updating review that doesn't exist."""
        repo = ReviewRepository(db_session)

        result = repo.update(999, rating=5)

        assert result is None

    def test_delete_review(self, db_session):
        """Test deleting review."""
        repo = ReviewRepository(db_session)
        review = ReviewFactory(user_id=1, product_id=1, vendor_id=1, rating=5)
        db_session.add(review)
        db_session.commit()
        review_id = review.id

        success = repo.delete(review_id)

        assert success is True
        assert repo.get_by_id(review_id) is None

    def test_delete_nonexistent_review(self, db_session):
        """Test deleting review that doesn't exist."""
        repo = ReviewRepository(db_session)

        success = repo.delete(999)

        assert success is False

    def test_count_reviews(self, db_session):
        """Test counting total reviews."""
        repo = ReviewRepository(db_session)
        reviews = [
            ReviewFactory(user_id=i, product_id=1, vendor_id=1, rating=5)
            for i in range(1, 4)
        ]
        for review in reviews:
            db_session.add(review)
        db_session.commit()

        count = repo.count()

        assert count == 3

    def test_count_reviews_by_product(self, db_session):
        """Test counting reviews by product."""
        repo = ReviewRepository(db_session)
        reviews = [
            ReviewFactory(user_id=1, product_id=1, vendor_id=1, rating=5),
            ReviewFactory(user_id=2, product_id=1, vendor_id=1, rating=4),
            ReviewFactory(user_id=3, product_id=2, vendor_id=1, rating=3),
        ]
        for review in reviews:
            db_session.add(review)
        db_session.commit()

        product_1_count = repo.count_by_product(1)
        product_2_count = repo.count_by_product(2)

        assert product_1_count == 2
        assert product_2_count == 1

    def test_count_reviews_by_vendor(self, db_session):
        """Test counting reviews by vendor."""
        repo = ReviewRepository(db_session)
        reviews = [
            ReviewFactory(user_id=1, product_id=1, vendor_id=1, rating=5),
            ReviewFactory(user_id=2, product_id=2, vendor_id=1, rating=4),
            ReviewFactory(user_id=3, product_id=3, vendor_id=2, rating=3),
        ]
        for review in reviews:
            db_session.add(review)
        db_session.commit()

        vendor_1_count = repo.count_by_vendor(1)
        vendor_2_count = repo.count_by_vendor(2)

        assert vendor_1_count == 2
        assert vendor_2_count == 1

    def test_get_recent_reviews(self, db_session):
        """Test retrieving recent reviews."""
        repo = ReviewRepository(db_session)
        reviews = [
            ReviewFactory(user_id=i, product_id=1, vendor_id=1, rating=5)
            for i in range(1, 6)  # Create 5 reviews
        ]
        for review in reviews:
            db_session.add(review)
        db_session.commit()

        recent_reviews = repo.get_recent_reviews(limit=3)

        assert len(recent_reviews) == 3

    def test_get_reviews_by_date_range(self, db_session):
        """Test retrieving reviews by date range."""
        repo = ReviewRepository(db_session)

        # Create reviews with different dates
        old_review = ReviewFactory(user_id=1, product_id=1, vendor_id=1, rating=5)
        old_review.created_at = datetime.now() - timedelta(days=10)

        recent_review = ReviewFactory(user_id=2, product_id=1, vendor_id=1, rating=4)
        recent_review.created_at = datetime.now() - timedelta(days=2)

        db_session.add_all([old_review, recent_review])
        db_session.commit()

        # Get reviews from last 5 days
        start_date = datetime.now() - timedelta(days=5)
        end_date = datetime.now()

        recent_reviews = repo.get_by_date_range(start_date, end_date)

        assert len(recent_reviews) == 1
        assert recent_reviews[0].id == recent_review.id

    def test_mark_review_as_verified(self, db_session):
        """Test marking review as verified purchase."""
        repo = ReviewRepository(db_session)
        review = ReviewFactory(
            user_id=1, product_id=1, vendor_id=1, rating=5, verified_purchase=False
        )
        db_session.add(review)
        db_session.commit()

        updated_review = repo.mark_as_verified(review.id)

        assert updated_review is not None
        assert updated_review.verified_purchase is True

    def test_mark_nonexistent_review_as_verified(self, db_session):
        """Test marking nonexistent review as verified."""
        repo = ReviewRepository(db_session)

        result = repo.mark_as_verified(999)

        assert result is None

    def test_get_top_rated_products(self, db_session):
        """Test getting top rated products based on reviews."""
        repo = ReviewRepository(db_session)

        # Product 1: avg 4.5 (4 + 5)
        ReviewFactory(user_id=1, product_id=1, vendor_id=1, rating=4)
        ReviewFactory(user_id=2, product_id=1, vendor_id=1, rating=5)

        # Product 2: avg 3.0 (3 + 3)
        ReviewFactory(user_id=3, product_id=2, vendor_id=1, rating=3)
        ReviewFactory(user_id=4, product_id=2, vendor_id=1, rating=3)

        # Product 3: avg 2.0 (1 + 3)
        ReviewFactory(user_id=5, product_id=3, vendor_id=1, rating=1)
        ReviewFactory(user_id=6, product_id=3, vendor_id=1, rating=3)

        db_session.commit()

        top_products = repo.get_top_rated_products(limit=2)

        assert len(top_products) == 2
        assert top_products[0]["product_id"] == 1
        assert top_products[0]["avg_rating"] == 4.5
        assert top_products[1]["product_id"] == 2
        assert top_products[1]["avg_rating"] == 3.0

    def test_get_top_rated_vendors(self, db_session):
        """Test getting top rated vendors based on reviews."""
        repo = ReviewRepository(db_session)

        # Vendor 1: avg 4.0 (3 + 5)
        ReviewFactory(user_id=1, product_id=1, vendor_id=1, rating=3)
        ReviewFactory(user_id=2, product_id=2, vendor_id=1, rating=5)

        # Vendor 2: avg 2.5 (2 + 3)
        ReviewFactory(user_id=3, product_id=3, vendor_id=2, rating=2)
        ReviewFactory(user_id=4, product_id=4, vendor_id=2, rating=3)

        db_session.commit()

        top_vendors = repo.get_top_rated_vendors(limit=2)

        assert len(top_vendors) == 2
        assert top_vendors[0]["vendor_id"] == 1
        assert top_vendors[0]["avg_rating"] == 4.0
        assert top_vendors[1]["vendor_id"] == 2
        assert top_vendors[1]["avg_rating"] == 2.5
