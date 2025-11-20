"""Tests for Review model."""

from datetime import datetime
from decimal import Decimal

import pytest
from src.models.product import Product
from src.models.review import Review
from src.models.vendor import Vendor


class TestReviewModel:
    """Test Review model functionality."""

    def test_create_review(self):
        """Test creating a review with valid data."""
        review = Review(
            user_id=1,
            product_id=10,
            vendor_id=5,
            rating=5,
            comment="Excellent product!",
            verified_purchase=True,
        )

        assert review.user_id == 1
        assert review.product_id == 10
        assert review.vendor_id == 5
        assert review.rating == 5
        assert review.comment == "Excellent product!"
        assert review.verified_purchase is True
        assert isinstance(review.created_at, datetime)

    def test_review_without_comment(self):
        """Test creating a review without a comment."""
        review = Review(user_id=1, product_id=10, vendor_id=5, rating=4)

        assert review.comment is None
        assert review.verified_purchase is False

    def test_review_rating_validation(self):
        """Test review rating validation."""
        # Rating too low
        with pytest.raises(ValueError, match="Rating must be between 1 and 5"):
            Review(user_id=1, product_id=10, vendor_id=5, rating=0)

        # Rating too high
        with pytest.raises(ValueError, match="Rating must be between 1 and 5"):
            Review(user_id=1, product_id=10, vendor_id=5, rating=6)

        # Non-integer rating
        with pytest.raises(ValueError, match="Rating must be an integer"):
            Review(user_id=1, product_id=10, vendor_id=5, rating=3.5)

    def test_review_valid_ratings(self):
        """Test all valid rating values."""
        for rating in [1, 2, 3, 4, 5]:
            review = Review(user_id=1, product_id=10, vendor_id=5, rating=rating)
            assert review.rating == rating

    def test_review_comment_validation(self):
        """Test review comment validation."""
        # Comment too long
        long_comment = "A" * 5001
        with pytest.raises(ValueError, match="Comment cannot exceed 5000 characters"):
            Review(
                user_id=1, product_id=10, vendor_id=5, rating=5, comment=long_comment
            )

    def test_review_comment_whitespace_trimming(self):
        """Test that review comments are trimmed."""
        review = Review(
            user_id=1,
            product_id=10,
            vendor_id=5,
            rating=5,
            comment="  Great product!  ",
        )

        assert review.comment == "Great product!"

    def test_review_is_verified(self):
        """Test verified purchase check."""
        review = Review(
            user_id=1, product_id=10, vendor_id=5, rating=5, verified_purchase=True
        )

        assert review.is_verified() is True

        review2 = Review(user_id=1, product_id=10, vendor_id=5, rating=5)

        assert review2.is_verified() is False

    def test_review_sentiment_checks(self):
        """Test review sentiment classification."""
        # Positive reviews (4-5 stars)
        positive_review = Review(user_id=1, product_id=10, vendor_id=5, rating=5)
        assert positive_review.is_positive() is True
        assert positive_review.is_negative() is False
        assert positive_review.is_neutral() is False

        # Negative reviews (1-2 stars)
        negative_review = Review(user_id=1, product_id=10, vendor_id=5, rating=1)
        assert negative_review.is_positive() is False
        assert negative_review.is_negative() is True
        assert negative_review.is_neutral() is False

        # Neutral reviews (3 stars)
        neutral_review = Review(user_id=1, product_id=10, vendor_id=5, rating=3)
        assert neutral_review.is_positive() is False
        assert neutral_review.is_negative() is False
        assert neutral_review.is_neutral() is True

    def test_review_mark_as_verified(self):
        """Test marking a review as verified."""
        review = Review(user_id=1, product_id=10, vendor_id=5, rating=5)

        assert review.is_verified() is False

        review.mark_as_verified()
        assert review.is_verified() is True

    def test_review_repr(self):
        """Test review string representation."""
        review = Review(
            user_id=1, product_id=10, vendor_id=5, rating=5, verified_purchase=True
        )

        repr_str = repr(review)
        assert "user_id=1" in repr_str
        assert "product_id=10" in repr_str
        assert "rating=5" in repr_str
        assert "(verified)" in repr_str


class TestReviewModelDatabase:
    """Test Review model with database."""

    def test_create_review_in_db(self, db_session):
        """Test creating and persisting a review."""
        # Create vendor and product first
        vendor = Vendor(
            user_id=1, company_name="Test Vendor", email="vendor@example.com"
        )
        db_session.add(vendor)
        db_session.commit()

        product = Product(
            vendor_id=vendor.id,
            name="Test Product",
            category="materials",
            price=Decimal("99.99"),
        )
        db_session.add(product)
        db_session.commit()

        # Create review
        review = Review(
            user_id=2,
            product_id=product.id,
            vendor_id=vendor.id,
            rating=5,
            comment="Great product!",
            verified_purchase=True,
        )
        db_session.add(review)
        db_session.commit()

        assert review.id is not None

        # Retrieve from database
        retrieved = db_session.query(Review).filter_by(user_id=2).first()
        assert retrieved is not None
        assert retrieved.rating == 5
        assert retrieved.comment == "Great product!"
        assert retrieved.verified_purchase is True

    def test_review_cascade_delete_with_product(self, db_session):
        """Test that reviews are deleted when product is deleted."""
        vendor = Vendor(
            user_id=1, company_name="Test Vendor", email="vendor@example.com"
        )
        db_session.add(vendor)
        db_session.commit()

        product = Product(
            vendor_id=vendor.id,
            name="Test Product",
            category="materials",
            price=Decimal("99.99"),
        )
        db_session.add(product)
        db_session.commit()

        review = Review(user_id=2, product_id=product.id, vendor_id=vendor.id, rating=5)
        db_session.add(review)
        db_session.commit()

        review_id = review.id

        # Delete product
        db_session.delete(product)
        db_session.commit()

        # Review should be deleted
        deleted_review = db_session.query(Review).filter_by(id=review_id).first()
        assert deleted_review is None

    def test_review_cascade_delete_with_vendor(self, db_session):
        """Test that reviews are deleted when vendor is deleted."""
        vendor = Vendor(
            user_id=1, company_name="Test Vendor", email="vendor@example.com"
        )
        db_session.add(vendor)
        db_session.commit()

        product = Product(
            vendor_id=vendor.id,
            name="Test Product",
            category="materials",
            price=Decimal("99.99"),
        )
        db_session.add(product)
        db_session.commit()

        review = Review(user_id=2, product_id=product.id, vendor_id=vendor.id, rating=5)
        db_session.add(review)
        db_session.commit()

        review_id = review.id

        # Delete vendor (will cascade to product and review)
        db_session.delete(vendor)
        db_session.commit()

        # Review should be deleted
        deleted_review = db_session.query(Review).filter_by(id=review_id).first()
        assert deleted_review is None

    def test_multiple_reviews_same_product(self, db_session):
        """Test multiple reviews for the same product."""
        vendor = Vendor(
            user_id=1, company_name="Test Vendor", email="vendor@example.com"
        )
        db_session.add(vendor)
        db_session.commit()

        product = Product(
            vendor_id=vendor.id,
            name="Test Product",
            category="materials",
            price=Decimal("99.99"),
        )
        db_session.add(product)
        db_session.commit()

        # Create multiple reviews
        review1 = Review(
            user_id=2,
            product_id=product.id,
            vendor_id=vendor.id,
            rating=5,
            comment="Excellent!",
        )
        review2 = Review(
            user_id=3,
            product_id=product.id,
            vendor_id=vendor.id,
            rating=4,
            comment="Very good",
        )
        review3 = Review(
            user_id=4,
            product_id=product.id,
            vendor_id=vendor.id,
            rating=3,
            comment="Average",
        )

        db_session.add_all([review1, review2, review3])
        db_session.commit()

        # Query all reviews for product
        reviews = db_session.query(Review).filter_by(product_id=product.id).all()
        assert len(reviews) == 3

        # Calculate average rating
        avg_rating = sum(r.rating for r in reviews) / len(reviews)
        assert avg_rating == 4.0

    def test_review_query_by_user(self, db_session):
        """Test querying reviews by user."""
        vendor = Vendor(
            user_id=1, company_name="Test Vendor", email="vendor@example.com"
        )
        db_session.add(vendor)
        db_session.commit()

        product1 = Product(
            vendor_id=vendor.id,
            name="Product 1",
            category="materials",
            price=Decimal("99.99"),
        )
        product2 = Product(
            vendor_id=vendor.id,
            name="Product 2",
            category="tools",
            price=Decimal("49.99"),
        )
        db_session.add_all([product1, product2])
        db_session.commit()

        # User reviews multiple products
        review1 = Review(
            user_id=2, product_id=product1.id, vendor_id=vendor.id, rating=5
        )
        review2 = Review(
            user_id=2, product_id=product2.id, vendor_id=vendor.id, rating=4
        )
        db_session.add_all([review1, review2])
        db_session.commit()

        # Query user's reviews
        user_reviews = db_session.query(Review).filter_by(user_id=2).all()
        assert len(user_reviews) == 2

    def test_review_verified_purchase_filter(self, db_session):
        """Test filtering reviews by verified purchase."""
        vendor = Vendor(
            user_id=1, company_name="Test Vendor", email="vendor@example.com"
        )
        db_session.add(vendor)
        db_session.commit()

        product = Product(
            vendor_id=vendor.id,
            name="Test Product",
            category="materials",
            price=Decimal("99.99"),
        )
        db_session.add(product)
        db_session.commit()

        # Create verified and unverified reviews
        verified_review = Review(
            user_id=2,
            product_id=product.id,
            vendor_id=vendor.id,
            rating=5,
            verified_purchase=True,
        )
        unverified_review = Review(
            user_id=3,
            product_id=product.id,
            vendor_id=vendor.id,
            rating=4,
            verified_purchase=False,
        )
        db_session.add_all([verified_review, unverified_review])
        db_session.commit()

        # Query only verified reviews
        verified_reviews = (
            db_session.query(Review)
            .filter_by(product_id=product.id, verified_purchase=True)
            .all()
        )
        assert len(verified_reviews) == 1
        assert verified_reviews[0].user_id == 2

    def test_review_rating_distribution(self, db_session):
        """Test analyzing rating distribution."""
        vendor = Vendor(
            user_id=1, company_name="Test Vendor", email="vendor@example.com"
        )
        db_session.add(vendor)
        db_session.commit()

        product = Product(
            vendor_id=vendor.id,
            name="Test Product",
            category="materials",
            price=Decimal("99.99"),
        )
        db_session.add(product)
        db_session.commit()

        # Create reviews with different ratings
        ratings = [5, 5, 4, 4, 3, 2, 1]
        for i, rating in enumerate(ratings):
            review = Review(
                user_id=i + 2, product_id=product.id, vendor_id=vendor.id, rating=rating
            )
            db_session.add(review)
        db_session.commit()

        # Count positive, neutral, negative
        all_reviews = db_session.query(Review).filter_by(product_id=product.id).all()
        positive_count = sum(1 for r in all_reviews if r.is_positive())
        neutral_count = sum(1 for r in all_reviews if r.is_neutral())
        negative_count = sum(1 for r in all_reviews if r.is_negative())

        assert positive_count == 4  # 5, 5, 4, 4
        assert neutral_count == 1  # 3
        assert negative_count == 2  # 2, 1
