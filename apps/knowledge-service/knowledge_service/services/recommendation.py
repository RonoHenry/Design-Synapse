"""Recommendation service for personalized content recommendations."""

import logging
import math
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, desc, func, or_
from sqlalchemy.orm import Session

from ..core.error_handling import (ErrorRecovery, error_context,
                                   handle_service_errors)
from ..exceptions import ContentProcessingError
from ..interfaces.services import ILLMService, IVectorSearchService
from ..models.bookmark import Bookmark
from ..models.resource import Resource

logger = logging.getLogger(__name__)


class RecommendationType(Enum):
    """Types of recommendations."""

    CONTENT_BASED = "content_based"
    COLLABORATIVE = "collaborative"
    HYBRID = "hybrid"
    TRENDING = "trending"
    SIMILAR_USERS = "similar_users"
    CONTEXTUAL = "contextual"


@dataclass
class RecommendationScore:
    """Recommendation with score and explanation."""

    resource_id: int
    score: float
    recommendation_type: RecommendationType
    explanation: str
    metadata: Dict[str, Any]


@dataclass
class UserProfile:
    """User profile for recommendations."""

    user_id: int
    interests: List[str]
    expertise_level: str
    recent_activity: List[Dict]
    bookmarked_resources: List[int]
    search_history: List[str]
    preferred_content_types: List[str]
    technical_domains: List[str]


class RecommendationService:
    """Service for generating personalized content recommendations."""

    def __init__(
        self, vector_search_service: IVectorSearchService, llm_service: ILLMService
    ):
        """Initialize recommendation service.

        Args:
            vector_search_service: Vector search service for similarity
            llm_service: LLM service for content analysis
        """
        self.vector_search = vector_search_service
        self.llm_service = llm_service

        # Recommendation weights
        self.weights = {
            RecommendationType.CONTENT_BASED: 0.4,
            RecommendationType.COLLABORATIVE: 0.3,
            RecommendationType.TRENDING: 0.1,
            RecommendationType.CONTEXTUAL: 0.2,
        }

        # Cache for user profiles and recommendations
        self.user_profile_cache = {}
        self.recommendation_cache = {}
        self.cache_ttl = 3600  # 1 hour

    @handle_service_errors("recommendation", "get_recommendations")
    async def get_recommendations(
        self,
        user_id: int,
        db: Session,
        num_recommendations: int = 10,
        recommendation_types: Optional[List[RecommendationType]] = None,
        context: Optional[Dict] = None,
    ) -> List[RecommendationScore]:
        """Get personalized recommendations for a user.

        Args:
            user_id: User ID
            db: Database session
            num_recommendations: Number of recommendations to return
            recommendation_types: Types of recommendations to include
            context: Additional context (current project, search query, etc.)

        Returns:
            List of recommendation scores
        """
        with error_context(
            "get_recommendations",
            user_id=user_id,
            num_recommendations=num_recommendations,
        ):
            # Check cache first
            cache_key = f"{user_id}_{num_recommendations}_{hash(str(context))}"
            cached_recommendations = self._get_cached_recommendations(cache_key)
            if cached_recommendations:
                return cached_recommendations

            # Build user profile
            user_profile = await self._build_user_profile(user_id, db)

            # Get recommendations from different algorithms
            all_recommendations = []

            if not recommendation_types:
                recommendation_types = [
                    RecommendationType.CONTENT_BASED,
                    RecommendationType.COLLABORATIVE,
                    RecommendationType.TRENDING,
                    RecommendationType.CONTEXTUAL,
                ]

            for rec_type in recommendation_types:
                try:
                    recommendations = await self._get_recommendations_by_type(
                        rec_type, user_profile, db, context
                    )
                    all_recommendations.extend(recommendations)
                except Exception as e:
                    logger.warning(
                        f"Failed to get {rec_type.value} recommendations: {e}"
                    )

            # Combine and rank recommendations
            final_recommendations = self._combine_recommendations(
                all_recommendations, num_recommendations
            )

            # Cache results
            self._cache_recommendations(cache_key, final_recommendations)

            return final_recommendations

    async def _build_user_profile(self, user_id: int, db: Session) -> UserProfile:
        """Build comprehensive user profile for recommendations."""
        # Check cache first
        if user_id in self.user_profile_cache:
            cached_profile, timestamp = self.user_profile_cache[user_id]
            if datetime.now().timestamp() - timestamp < self.cache_ttl:
                return cached_profile

        # Get user's bookmarked resources
        bookmarked_resources = (
            db.query(Bookmark.resource_id).filter(Bookmark.user_id == user_id).all()
        )
        bookmarked_ids = [b.resource_id for b in bookmarked_resources]

        # Analyze bookmarked content to infer interests
        interests = []
        technical_domains = []
        preferred_content_types = []

        if bookmarked_ids:
            bookmarked_content = (
                db.query(Resource).filter(Resource.id.in_(bookmarked_ids)).all()
            )

            # Extract interests from bookmarked content
            all_keywords = []
            all_domains = []
            content_types = []

            for resource in bookmarked_content:
                if resource.keywords:
                    all_keywords.extend(resource.keywords)
                if resource.technical_domains:
                    all_domains.extend(resource.technical_domains)
                if resource.content_type:
                    content_types.append(resource.content_type)

            # Get most common interests
            keyword_counts = Counter(all_keywords)
            interests = [kw for kw, count in keyword_counts.most_common(10)]

            domain_counts = Counter(all_domains)
            technical_domains = [
                domain for domain, count in domain_counts.most_common(5)
            ]

            type_counts = Counter(content_types)
            preferred_content_types = [ct for ct, count in type_counts.most_common(3)]

        # Estimate expertise level based on content complexity
        expertise_level = self._estimate_expertise_level(
            bookmarked_content if bookmarked_ids else []
        )

        # Get recent activity (simplified - would need activity tracking)
        recent_activity = []  # Would be populated from activity logs

        # Get search history (simplified - would need search tracking)
        search_history = []  # Would be populated from search logs

        user_profile = UserProfile(
            user_id=user_id,
            interests=interests,
            expertise_level=expertise_level,
            recent_activity=recent_activity,
            bookmarked_resources=bookmarked_ids,
            search_history=search_history,
            preferred_content_types=preferred_content_types,
            technical_domains=technical_domains,
        )

        # Cache the profile
        self.user_profile_cache[user_id] = (user_profile, datetime.now().timestamp())

        return user_profile

    def _estimate_expertise_level(self, resources: List[Resource]) -> str:
        """Estimate user expertise level based on consumed content."""
        if not resources:
            return "intermediate"

        complexity_scores = {"basic": 1, "intermediate": 2, "advanced": 3, "expert": 4}
        total_score = 0
        count = 0

        for resource in resources:
            if hasattr(resource, "complexity_level") and resource.complexity_level:
                score = complexity_scores.get(resource.complexity_level.lower(), 2)
                total_score += score
                count += 1

        if count == 0:
            return "intermediate"

        avg_score = total_score / count

        if avg_score <= 1.5:
            return "basic"
        elif avg_score <= 2.5:
            return "intermediate"
        elif avg_score <= 3.5:
            return "advanced"
        else:
            return "expert"

    async def _get_recommendations_by_type(
        self,
        rec_type: RecommendationType,
        user_profile: UserProfile,
        db: Session,
        context: Optional[Dict] = None,
    ) -> List[RecommendationScore]:
        """Get recommendations by specific type."""
        if rec_type == RecommendationType.CONTENT_BASED:
            return await self._get_content_based_recommendations(user_profile, db)
        elif rec_type == RecommendationType.COLLABORATIVE:
            return await self._get_collaborative_recommendations(user_profile, db)
        elif rec_type == RecommendationType.TRENDING:
            return await self._get_trending_recommendations(user_profile, db)
        elif rec_type == RecommendationType.CONTEXTUAL:
            return await self._get_contextual_recommendations(user_profile, db, context)
        else:
            return []

    async def _get_content_based_recommendations(
        self, user_profile: UserProfile, db: Session
    ) -> List[RecommendationScore]:
        """Get content-based recommendations using user interests."""
        recommendations = []

        # Create query from user interests
        if user_profile.interests:
            query = " ".join(user_profile.interests[:5])  # Top 5 interests

            try:
                # Use vector search to find similar content
                search_results = await self.vector_search.search_resources(
                    query=query, top_k=20
                )

                for result in search_results:
                    resource_id = result["resource_id"]

                    # Skip already bookmarked resources
                    if resource_id in user_profile.bookmarked_resources:
                        continue

                    # Calculate content-based score
                    score = self._calculate_content_similarity_score(
                        result, user_profile
                    )

                    recommendations.append(
                        RecommendationScore(
                            resource_id=resource_id,
                            score=score,
                            recommendation_type=RecommendationType.CONTENT_BASED,
                            explanation=f"Based on your interests in {', '.join(user_profile.interests[:3])}",
                            metadata={
                                "vector_score": result["score"],
                                "interests_matched": user_profile.interests[:3],
                            },
                        )
                    )

            except Exception as e:
                logger.warning(f"Content-based recommendation failed: {e}")

        return recommendations[:10]

    async def _get_collaborative_recommendations(
        self, user_profile: UserProfile, db: Session
    ) -> List[RecommendationScore]:
        """Get collaborative filtering recommendations."""
        recommendations = []

        try:
            # Find users with similar bookmarks
            similar_users = self._find_similar_users(user_profile, db)

            # Get resources bookmarked by similar users
            similar_user_ids = [user_id for user_id, similarity in similar_users[:10]]

            if similar_user_ids:
                # Get resources bookmarked by similar users but not by current user
                similar_bookmarks = (
                    db.query(Bookmark)
                    .filter(
                        and_(
                            Bookmark.user_id.in_(similar_user_ids),
                            ~Bookmark.resource_id.in_(
                                user_profile.bookmarked_resources
                            ),
                        )
                    )
                    .all()
                )

                # Count bookmark frequency
                resource_counts = Counter([b.resource_id for b in similar_bookmarks])

                for resource_id, count in resource_counts.most_common(15):
                    # Calculate collaborative score
                    score = self._calculate_collaborative_score(
                        resource_id, count, len(similar_users)
                    )

                    recommendations.append(
                        RecommendationScore(
                            resource_id=resource_id,
                            score=score,
                            recommendation_type=RecommendationType.COLLABORATIVE,
                            explanation=f"Recommended by {count} users with similar interests",
                            metadata={
                                "bookmark_count": count,
                                "similar_users": len(similar_users),
                            },
                        )
                    )

        except Exception as e:
            logger.warning(f"Collaborative recommendation failed: {e}")

        return recommendations

    async def _get_trending_recommendations(
        self, user_profile: UserProfile, db: Session
    ) -> List[RecommendationScore]:
        """Get trending content recommendations."""
        recommendations = []

        try:
            # Get recently popular resources (simplified - would use view/bookmark metrics)
            recent_date = datetime.now() - timedelta(days=30)

            trending_resources = (
                db.query(
                    Bookmark.resource_id,
                    func.count(Bookmark.id).label("bookmark_count"),
                )
                .filter(Bookmark.created_at >= recent_date)
                .group_by(Bookmark.resource_id)
                .order_by(desc("bookmark_count"))
                .limit(20)
                .all()
            )

            for resource_id, bookmark_count in trending_resources:
                # Skip already bookmarked resources
                if resource_id in user_profile.bookmarked_resources:
                    continue

                # Calculate trending score
                score = self._calculate_trending_score(bookmark_count)

                recommendations.append(
                    RecommendationScore(
                        resource_id=resource_id,
                        score=score,
                        recommendation_type=RecommendationType.TRENDING,
                        explanation=f"Trending with {bookmark_count} recent bookmarks",
                        metadata={
                            "bookmark_count": bookmark_count,
                            "period": "30_days",
                        },
                    )
                )

        except Exception as e:
            logger.warning(f"Trending recommendation failed: {e}")

        return recommendations[:8]

    async def _get_contextual_recommendations(
        self, user_profile: UserProfile, db: Session, context: Optional[Dict] = None
    ) -> List[RecommendationScore]:
        """Get contextual recommendations based on current context."""
        recommendations = []

        if not context:
            return recommendations

        try:
            # Context-based recommendations
            if "current_project" in context:
                project_context = context["current_project"]
                # Find resources related to current project
                # This would integrate with project service
                pass

            if "search_query" in context:
                search_query = context["search_query"]
                # Find resources similar to current search
                search_results = await self.vector_search.search_resources(
                    query=search_query, top_k=10
                )

                for result in search_results:
                    resource_id = result["resource_id"]

                    if resource_id not in user_profile.bookmarked_resources:
                        score = result["score"] * 0.8  # Contextual weight

                        recommendations.append(
                            RecommendationScore(
                                resource_id=resource_id,
                                score=score,
                                recommendation_type=RecommendationType.CONTEXTUAL,
                                explanation=f"Related to your search: '{search_query}'",
                                metadata={
                                    "search_query": search_query,
                                    "vector_score": result["score"],
                                },
                            )
                        )

            if "current_resource" in context:
                current_resource_id = context["current_resource"]
                # Find similar resources
                current_resource = (
                    db.query(Resource)
                    .filter(Resource.id == current_resource_id)
                    .first()
                )

                if current_resource and current_resource.content:
                    similar_results = await self.vector_search.search_resources(
                        query=current_resource.content[:500],  # Use first 500 chars
                        top_k=8,
                    )

                    for result in similar_results:
                        resource_id = result["resource_id"]

                        if (
                            resource_id != current_resource_id
                            and resource_id not in user_profile.bookmarked_resources
                        ):
                            score = result["score"] * 0.7

                            recommendations.append(
                                RecommendationScore(
                                    resource_id=resource_id,
                                    score=score,
                                    recommendation_type=RecommendationType.CONTEXTUAL,
                                    explanation="Similar to current resource",
                                    metadata={
                                        "current_resource_id": current_resource_id,
                                        "vector_score": result["score"],
                                    },
                                )
                            )

        except Exception as e:
            logger.warning(f"Contextual recommendation failed: {e}")

        return recommendations[:10]

    def _find_similar_users(
        self, user_profile: UserProfile, db: Session
    ) -> List[Tuple[int, float]]:
        """Find users with similar interests and bookmarks."""
        # Get all users with bookmarks
        all_bookmarks = (
            db.query(Bookmark).filter(Bookmark.user_id != user_profile.user_id).all()
        )

        # Group by user
        user_bookmarks = defaultdict(set)
        for bookmark in all_bookmarks:
            user_bookmarks[bookmark.user_id].add(bookmark.resource_id)

        # Calculate similarity with current user
        current_user_bookmarks = set(user_profile.bookmarked_resources)
        similarities = []

        for other_user_id, other_bookmarks in user_bookmarks.items():
            # Calculate Jaccard similarity
            intersection = len(current_user_bookmarks.intersection(other_bookmarks))
            union = len(current_user_bookmarks.union(other_bookmarks))

            if union > 0:
                similarity = intersection / union
                if similarity > 0.1:  # Minimum similarity threshold
                    similarities.append((other_user_id, similarity))

        # Sort by similarity
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities

    def _calculate_content_similarity_score(
        self, search_result: Dict, user_profile: UserProfile
    ) -> float:
        """Calculate content-based similarity score."""
        base_score = search_result["score"]

        # Boost score based on user preferences
        metadata = search_result.get("metadata", {})

        # Check if content type matches user preferences
        content_type_boost = 0.0
        if "content_type" in metadata:
            if metadata["content_type"] in user_profile.preferred_content_types:
                content_type_boost = 0.2

        # Check if technical domain matches
        domain_boost = 0.0
        if "technical_domains" in metadata:
            resource_domains = metadata["technical_domains"]
            if isinstance(resource_domains, list):
                common_domains = set(resource_domains).intersection(
                    set(user_profile.technical_domains)
                )
                domain_boost = len(common_domains) * 0.1

        # Expertise level matching
        expertise_boost = 0.0
        if "complexity_level" in metadata:
            resource_complexity = metadata["complexity_level"]
            if resource_complexity == user_profile.expertise_level:
                expertise_boost = 0.15
            elif (
                abs(
                    self._complexity_to_number(resource_complexity)
                    - self._complexity_to_number(user_profile.expertise_level)
                )
                <= 1
            ):
                expertise_boost = 0.1

        final_score = base_score + content_type_boost + domain_boost + expertise_boost
        return min(1.0, final_score)

    def _complexity_to_number(self, complexity: str) -> int:
        """Convert complexity level to number for comparison."""
        mapping = {"basic": 1, "intermediate": 2, "advanced": 3, "expert": 4}
        return mapping.get(complexity.lower(), 2)

    def _calculate_collaborative_score(
        self, resource_id: int, bookmark_count: int, total_similar_users: int
    ) -> float:
        """Calculate collaborative filtering score."""
        # Normalize by number of similar users
        popularity_ratio = bookmark_count / max(1, total_similar_users)

        # Apply logarithmic scaling to prevent popular items from dominating
        score = math.log(1 + popularity_ratio * 10) / math.log(11)

        return min(1.0, score)

    def _calculate_trending_score(self, bookmark_count: int) -> float:
        """Calculate trending score based on recent popularity."""
        # Logarithmic scaling for trending score
        score = math.log(1 + bookmark_count) / math.log(
            100
        )  # Normalize to max ~100 bookmarks
        return min(1.0, score)

    def _combine_recommendations(
        self, all_recommendations: List[RecommendationScore], num_recommendations: int
    ) -> List[RecommendationScore]:
        """Combine recommendations from different algorithms."""
        # Group by resource ID
        resource_scores = defaultdict(list)

        for rec in all_recommendations:
            resource_scores[rec.resource_id].append(rec)

        # Calculate combined scores
        combined_recommendations = []

        for resource_id, recommendations in resource_scores.items():
            # Calculate weighted average score
            total_score = 0.0
            total_weight = 0.0
            explanations = []
            metadata = {}

            for rec in recommendations:
                weight = self.weights.get(rec.recommendation_type, 0.1)
                total_score += rec.score * weight
                total_weight += weight
                explanations.append(rec.explanation)
                metadata.update(rec.metadata)

            if total_weight > 0:
                final_score = total_score / total_weight

                # Create combined recommendation
                combined_rec = RecommendationScore(
                    resource_id=resource_id,
                    score=final_score,
                    recommendation_type=RecommendationType.HYBRID,
                    explanation="; ".join(
                        explanations[:2]
                    ),  # Combine top 2 explanations
                    metadata={
                        **metadata,
                        "algorithm_count": len(recommendations),
                        "component_scores": {
                            rec.recommendation_type.value: rec.score
                            for rec in recommendations
                        },
                    },
                )

                combined_recommendations.append(combined_rec)

        # Sort by final score and return top recommendations
        combined_recommendations.sort(key=lambda x: x.score, reverse=True)
        return combined_recommendations[:num_recommendations]

    def _get_cached_recommendations(
        self, cache_key: str
    ) -> Optional[List[RecommendationScore]]:
        """Get cached recommendations if available and not expired."""
        if cache_key in self.recommendation_cache:
            recommendations, timestamp = self.recommendation_cache[cache_key]
            if datetime.now().timestamp() - timestamp < self.cache_ttl:
                return recommendations
        return None

    def _cache_recommendations(
        self, cache_key: str, recommendations: List[RecommendationScore]
    ):
        """Cache recommendations with timestamp."""
        self.recommendation_cache[cache_key] = (
            recommendations,
            datetime.now().timestamp(),
        )

        # Clean old cache entries (simple cleanup)
        if len(self.recommendation_cache) > 1000:
            # Remove oldest 20% of entries
            sorted_entries = sorted(
                self.recommendation_cache.items(), key=lambda x: x[1][1]
            )
            entries_to_remove = len(sorted_entries) // 5
            for key, _ in sorted_entries[:entries_to_remove]:
                del self.recommendation_cache[key]

    @handle_service_errors("recommendation", "get_similar_resources")
    async def get_similar_resources(
        self, resource_id: int, db: Session, num_similar: int = 5
    ) -> List[RecommendationScore]:
        """Get resources similar to a given resource.

        Args:
            resource_id: ID of the reference resource
            db: Database session
            num_similar: Number of similar resources to return

        Returns:
            List of similar resources with scores
        """
        with error_context("get_similar_resources", resource_id=resource_id):
            # Get the reference resource
            resource = db.query(Resource).filter(Resource.id == resource_id).first()

            if not resource:
                return []

            # Use content for similarity search
            if resource.content:
                search_query = resource.content[:1000]  # Use first 1000 chars
            elif resource.summary:
                search_query = resource.summary
            else:
                search_query = resource.title or ""

            if not search_query:
                return []

            try:
                # Search for similar resources
                search_results = await self.vector_search.search_resources(
                    query=search_query,
                    top_k=num_similar + 5,  # Get extra to filter out the original
                )

                similar_resources = []

                for result in search_results:
                    result_resource_id = result["resource_id"]

                    # Skip the original resource
                    if result_resource_id == resource_id:
                        continue

                    similar_resources.append(
                        RecommendationScore(
                            resource_id=result_resource_id,
                            score=result["score"],
                            recommendation_type=RecommendationType.CONTENT_BASED,
                            explanation=f"Similar to '{resource.title}'",
                            metadata={
                                "reference_resource_id": resource_id,
                                "vector_score": result["score"],
                            },
                        )
                    )

                    if len(similar_resources) >= num_similar:
                        break

                return similar_resources

            except Exception as e:
                logger.error(f"Failed to find similar resources: {e}")
                return []

    def clear_cache(self):
        """Clear all caches."""
        self.user_profile_cache.clear()
        self.recommendation_cache.clear()
        logger.info("Recommendation caches cleared")

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "user_profile_cache_size": len(self.user_profile_cache),
            "recommendation_cache_size": len(self.recommendation_cache),
            "cache_ttl": self.cache_ttl,
            "weights": self.weights,
        }

    def update_weights(self, new_weights: Dict[RecommendationType, float]):
        """Update recommendation algorithm weights."""
        # Validate weights sum to 1.0
        total_weight = sum(new_weights.values())
        if abs(total_weight - 1.0) > 0.01:
            raise ValueError("Weights must sum to 1.0")

        self.weights.update(new_weights)
        logger.info(f"Updated recommendation weights: {self.weights}")

    async def explain_recommendation(
        self, user_id: int, resource_id: int, db: Session
    ) -> Dict[str, Any]:
        """Provide detailed explanation for why a resource was recommended.

        Args:
            user_id: User ID
            resource_id: Resource ID
            db: Database session

        Returns:
            Detailed explanation dictionary
        """
        with error_context(
            "explain_recommendation", user_id=user_id, resource_id=resource_id
        ):
            user_profile = await self._build_user_profile(user_id, db)
            resource = db.query(Resource).filter(Resource.id == resource_id).first()

            if not resource:
                return {"error": "Resource not found"}

            explanation = {
                "resource_id": resource_id,
                "resource_title": resource.title,
                "user_profile_summary": {
                    "interests": user_profile.interests[:5],
                    "expertise_level": user_profile.expertise_level,
                    "technical_domains": user_profile.technical_domains,
                    "preferred_content_types": user_profile.preferred_content_types,
                },
                "matching_factors": [],
                "recommendation_strength": "medium",
            }

            # Check interest matching
            if resource.keywords:
                matching_interests = set(user_profile.interests).intersection(
                    set(resource.keywords)
                )
                if matching_interests:
                    explanation["matching_factors"].append(
                        {
                            "factor": "interests",
                            "matches": list(matching_interests),
                            "strength": len(matching_interests)
                            / max(len(user_profile.interests), 1),
                        }
                    )

            # Check domain matching
            if resource.technical_domains:
                matching_domains = set(user_profile.technical_domains).intersection(
                    set(resource.technical_domains)
                )
                if matching_domains:
                    explanation["matching_factors"].append(
                        {
                            "factor": "technical_domains",
                            "matches": list(matching_domains),
                            "strength": len(matching_domains)
                            / max(len(user_profile.technical_domains), 1),
                        }
                    )

            # Check complexity level matching
            if hasattr(resource, "complexity_level") and resource.complexity_level:
                complexity_match = (
                    resource.complexity_level.lower()
                    == user_profile.expertise_level.lower()
                )
                explanation["matching_factors"].append(
                    {
                        "factor": "complexity_level",
                        "resource_level": resource.complexity_level,
                        "user_level": user_profile.expertise_level,
                        "exact_match": complexity_match,
                    }
                )

            # Calculate overall strength
            if len(explanation["matching_factors"]) >= 3:
                explanation["recommendation_strength"] = "strong"
            elif len(explanation["matching_factors"]) >= 2:
                explanation["recommendation_strength"] = "medium"
            else:
                explanation["recommendation_strength"] = "weak"

            return explanation
