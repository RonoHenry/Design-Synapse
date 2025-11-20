"""Review service for business logic."""

from decimal import Decimal
from typing import Dict, List, Optional

from src.models.review import Review
from src.repositories.order_repository import OrderRepository
from src.repositories.product_repository import ProductRepository
from src.repositories.review_repository import ReviewRepository
from src.repositories.vendor_repository import VendorRepository


class ReviewService:
    """Service for review business logic."""

    def __init__(
        self,
        review_repository: ReviewRepository,
        order_repository: OrderRepository,
        product_repository: ProductRepository,
        vendor_repository: VendorRepository,
    ):
        """Initialize review service."""
        self.review_repository = review_repository
        self.order_repository = order_repository
        self.product_repository = product_repository
        self.vendor_repository = vendor_repository

    async def create_review(
        self,
        user_id: int,
        product_id: int,
        rating: int,
        comment: Optional[str] = None,
        verify_purchase: bool = True,
    ) -> Review:
        """Create a new review."""
        # Validate product exists
        product = await self.product_repository.get_by_id(product_id)
        if not product:
            raise ValueError(f"Product {product_id} not found")

        # Check if user already reviewed this product
        existing_review = await self.review_repository.get_by_user_and_product(
            user_id, product_id
        )
        if existing_review:
            raise ValueError("User has already reviewed this product")

        # Verify purchase if required
        verified_purchase = False
        if verify_purchase:
            verified_purchase = await self._verify_purchase(user_id, product_id)

        # Create review
        review = Review(
            user_id=user_id,
            product_id=product_id,
            vendor_id=product.vendor_id,
            rating=rating,
            comment=comment,
            verified_purchase=verified_purchase,
        )

        created_review = await self.review_repository.create(review)

        # Update product and vendor ratings
        await self._update_product_rating(product_id)
        await self._update_vendor_rating(product.vendor_id)

        return created_review

    async def get_review(self, review_id: int) -> Optional[Review]:
        """Get review by ID."""
        return await self.review_repository.get_by_id(review_id)

    async def get_product_reviews(
        self,
        product_id: int,
        skip: int = 0,
        limit: int = 100,
        verified_only: bool = False,
        min_rating: Optional[int] = None,
        max_rating: Optional[int] = None,
    ) -> List[Review]:
        """Get reviews for a product."""
        return await self.review_repository.get_by_product(
            product_id=product_id,
            skip=skip,
            limit=limit,
            verified_only=verified_only,
            min_rating=min_rating,
            max_rating=max_rating,
        )

    async def get_vendor_reviews(
        self,
        vendor_id: int,
        skip: int = 0,
        limit: int = 100,
        verified_only: bool = False,
        min_rating: Optional[int] = None,
        max_rating: Optional[int] = None,
    ) -> List[Review]:
        """Get reviews for a vendor."""
        return await self.review_repository.get_by_vendor(
            vendor_id=vendor_id,
            skip=skip,
            limit=limit,
            verified_only=verified_only,
            min_rating=min_rating,
            max_rating=max_rating,
        )

    async def get_user_reviews(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Review]:
        """Get reviews by a user."""
        return await self.review_repository.get_by_user(
            user_id=user_id,
            skip=skip,
            limit=limit,
        )

    async def update_review(
        self,
        review_id: int,
        user_id: int,
        rating: Optional[int] = None,
        comment: Optional[str] = None,
    ) -> Optional[Review]:
        """Update a review."""
        review = await self.review_repository.get_by_id(review_id)
        if not review:
            return None

        # Check ownership
        if review.user_id != user_id:
            raise ValueError("User can only update their own reviews")

        # Update fields
        if rating is not None:
            review.rating = review._validate_rating(rating)
        if comment is not None:
            review.comment = review._validate_comment(comment)

        updated_review = await self.review_repository.update(review)

        # Update ratings
        await self._update_product_rating(review.product_id)
        await self._update_vendor_rating(review.vendor_id)

        return updated_review

    async def delete_review(self, review_id: int, user_id: int) -> bool:
        """Delete a review."""
        review = await self.review_repository.get_by_id(review_id)
        if not review:
            return False

        # Check ownership
        if review.user_id != user_id:
            raise ValueError("User can only delete their own reviews")

        product_id = review.product_id
        vendor_id = review.vendor_id

        success = await self.review_repository.delete(review_id)

        if success:
            # Update ratings
            await self._update_product_rating(product_id)
            await self._update_vendor_rating(vendor_id)

        return success

    async def moderate_review(
        self,
        review_id: int,
        moderator_id: int,
        action: str,
        reason: Optional[str] = None,
    ) -> Optional[Review]:
        """Moderate a review (admin function)."""
        review = await self.review_repository.get_by_id(review_id)
        if not review:
            return None

        if action == "approve":
            # Mark as verified or approved
            review.verified_purchase = True
        elif action == "hide":
            # In a real implementation, you might add a 'hidden' field
            # For now, we'll delete the review
            await self.review_repository.delete(review_id)
            return None
        elif action == "flag":
            # In a real implementation, you might add a 'flagged' field
            pass

        return await self.review_repository.update(review)

    async def get_product_rating_summary(self, product_id: int) -> Dict:
        """Get rating summary for a product."""
        average_rating = (
            await self.review_repository.calculate_average_rating_for_product(
                product_id
            )
        )
        rating_distribution = (
            await self.review_repository.get_rating_distribution_for_product(product_id)
        )
        total_reviews = await self.review_repository.count_reviews_by_product(
            product_id
        )

        return {
            "average_rating": average_rating,
            "total_reviews": total_reviews,
            "rating_distribution": rating_distribution,
        }

    async def get_vendor_rating_summary(self, vendor_id: int) -> Dict:
        """Get rating summary for a vendor."""
        average_rating = (
            await self.review_repository.calculate_average_rating_for_vendor(vendor_id)
        )
        rating_distribution = (
            await self.review_repository.get_rating_distribution_for_vendor(vendor_id)
        )
        total_reviews = await self.review_repository.count_reviews_by_vendor(vendor_id)

        return {
            "average_rating": average_rating,
            "total_reviews": total_reviews,
            "rating_distribution": rating_distribution,
        }

    async def get_recent_reviews(
        self,
        limit: int = 10,
        product_id: Optional[int] = None,
        vendor_id: Optional[int] = None,
    ) -> List[Review]:
        """Get recent reviews."""
        return await self.review_repository.get_recent_reviews(
            limit=limit,
            product_id=product_id,
            vendor_id=vendor_id,
        )

    async def get_top_rated_products(
        self,
        limit: int = 10,
        min_reviews: int = 5,
    ) -> List[Dict]:
        """Get top-rated products."""
        return await self.review_repository.get_top_rated_products(
            limit=limit,
            min_reviews=min_reviews,
        )

    async def get_top_rated_vendors(
        self,
        limit: int = 10,
        min_reviews: int = 5,
    ) -> List[Dict]:
        """Get top-rated vendors."""
        return await self.review_repository.get_top_rated_vendors(
            limit=limit,
            min_reviews=min_reviews,
        )

    async def mark_review_as_verified(self, review_id: int) -> Optional[Review]:
        """Mark a review as verified purchase."""
        return await self.review_repository.mark_as_verified(review_id)

    async def _verify_purchase(self, user_id: int, product_id: int) -> bool:
        """Verify if user has purchased the product."""
        # Check if user has any delivered orders containing this product
        orders = await self.order_repository.get_by_customer_id(
            customer_id=user_id,
            status="delivered",
        )

        for order in orders:
            order_with_items = await self.order_repository.get_order_with_items(
                order.id
            )
            for item in order_with_items.items:
                if item.product_id == product_id:
                    return True

        return False

    async def _update_product_rating(self, product_id: int) -> None:
        """Update product's average rating."""
        average_rating = (
            await self.review_repository.calculate_average_rating_for_product(
                product_id
            )
        )
        if average_rating is not None:
            product = await self.product_repository.get_by_id(product_id)
            if product:
                # In a real implementation, you might add a rating field to Product model
                pass

    async def _update_vendor_rating(self, vendor_id: int) -> None:
        """Update vendor's average rating."""
        average_rating = (
            await self.review_repository.calculate_average_rating_for_vendor(vendor_id)
        )
        if average_rating is not None:
            vendor = await self.vendor_repository.get_by_id(vendor_id)
            if vendor:
                vendor.update_rating(average_rating)
                await self.vendor_repository.update(vendor)
