"""
MatchingService - GREEN Phase Implementation
Following TDD methodology - minimal implementation to make tests pass
"""
from typing import Any, Dict, List

from src.core.exceptions import MatchingError


class MatchingService:
    """Service for matching providers with requests - minimal TDD implementation"""

    def __init__(self, provider_repository, request_repository, notification_service):
        self.provider_repository = provider_repository
        self.request_repository = request_repository
        self.notification_service = notification_service

    async def find_providers_for_request(
        self,
        request_id: int,
        max_distance: float = None,
        min_rating: float = None,
        limit: int = 10,
    ) -> Dict[str, Any]:
        """Find matching providers for a service request using real matching algorithms."""
        # Verify request exists
        request = await self.request_repository.get_by_id(request_id)
        if not request:
            raise MatchingError("Request not found")

        # Get all potential providers from repository with filters
        providers = await self.provider_repository.find_matching_providers(
            request_id,
            max_distance=max_distance,
            min_rating=min_rating,
            limit=limit * 2,  # Get more for filtering
        )

        # Apply real matching algorithm to each provider
        scored_providers = []
        for provider in providers:
            if not provider.get("is_active", True):
                continue  # Skip inactive providers

            # Calculate comprehensive match score
            skill_score = self._calculate_skill_match(
                provider.get("skills", []), request.get("required_skills", [])
            )
            location_score = self._calculate_distance_score(
                provider.get("location", {}), request.get("location", {})
            )
            availability_score = self._calculate_availability_score(
                provider.get("availability", {}), request.get("timeline", {})
            )
            reputation_score = self._calculate_reputation_score(provider, request)

            # Weighted overall score
            overall_score = (
                skill_score * 0.4
                + location_score * 0.25  # 40% weight on skills
                + availability_score * 0.2  # 25% weight on location
                + reputation_score  # 20% weight on availability
                * 0.15  # 15% weight on reputation
            )

            # Add calculated scores to provider data
            provider["match_score"] = round(overall_score, 3)
            provider["skill_match"] = round(skill_score, 3)
            provider["location_score"] = round(location_score, 3)
            provider["availability_score"] = round(availability_score, 3)
            provider["reputation_score"] = round(reputation_score, 3)

            scored_providers.append(provider)

        # Sort by match score (descending) and limit results
        sorted_providers = sorted(
            scored_providers, key=lambda p: p.get("match_score", 0), reverse=True
        )[:limit]

        # Extract match scores for response
        match_scores = [p.get("match_score", 0) for p in sorted_providers]

        return {
            "providers": sorted_providers,
            "match_scores": match_scores,
            "total_matches": len(scored_providers),
        }

    async def find_opportunities_for_provider(
        self,
        provider_id: int,
        max_distance: float = None,
        budget_min: float = None,
        limit: int = 15,
    ) -> Dict[str, Any]:
        """Find job opportunities for a service provider"""
        requests = await self.request_repository.find_matching_requests(
            provider_id, max_distance=max_distance, budget_min=budget_min, limit=limit
        )

        # Calculate match scores for each request
        match_scores = [r.get("match_score", 0) for r in requests]

        return {
            "requests": requests,
            "match_scores": match_scores,
            "total_matches": len(requests),
        }

    async def calculate_match_score(
        self, provider_id: int, request_id: int
    ) -> Dict[str, float]:
        """Calculate match score between provider and request"""
        # Get provider and request data
        provider = await self.provider_repository.get_by_id(provider_id)
        request = await self.request_repository.get_by_id(request_id)

        if not provider or not request:
            raise MatchingError("Provider or request not found")

        # Calculate individual score components
        skill_score = self._calculate_skill_match(
            provider.get("skills", []), request.get("required_skills", [])
        )
        location_score = self._calculate_distance_score(
            provider.get("location", {}), request.get("location", {})
        )
        availability_score = self._calculate_availability_score(
            provider.get("availability", {}), request.get("timeline", {})
        )
        rating_score = self._calculate_reputation_score(provider, request)

        # Weighted average: skill(40%) + location(25%) + availability(20%) + rating(15%)
        overall_score = (
            skill_score * 0.4
            + location_score * 0.25
            + availability_score * 0.2
            + rating_score * 0.15
        )

        return {
            "overall_score": round(overall_score, 1),
            "skill_match": round(skill_score, 1),
            "location_score": round(location_score, 1),
            "availability_score": round(availability_score, 1),
            "rating_score": round(rating_score, 1),
        }

    def _calculate_skill_match(
        self, provider_skills: List[Dict], request_skills: List[Dict]
    ) -> float:
        """Calculate skill matching score based on skill overlap and proficiency levels."""
        if not provider_skills or not request_skills:
            return 0.0  # No skills means no match

        # Convert to sets for easier comparison
        provider_skill_map = {
            skill.get("skill_id"): skill.get("proficiency_level", 1)
            for skill in provider_skills
        }
        request_skill_map = {
            skill.get("skill_id"): skill.get("required_level", 1)
            for skill in request_skills
        }

        # Calculate skill overlap
        provider_skill_ids = set(provider_skill_map.keys())
        required_skill_ids = set(request_skill_map.keys())

        if not required_skill_ids:
            return 0.0

        # Find matching skills
        matching_skills = provider_skill_ids.intersection(required_skill_ids)
        missing_skills = required_skill_ids - provider_skill_ids

        if not matching_skills:
            return 0.0  # No matching skills

        # Calculate proficiency match for matching skills
        proficiency_scores = []
        for skill_id in matching_skills:
            provider_level = provider_skill_map[skill_id]
            required_level = request_skill_map[skill_id]

            # Score based on how well provider level meets requirement
            if provider_level >= required_level:
                # Exceeds requirement - full points plus bonus
                score = 1.0 + min(0.2, (provider_level - required_level) * 0.1)
            else:
                # Below requirement - partial points
                score = max(0.0, provider_level / required_level * 0.8)

            proficiency_scores.append(score)

        # Calculate overall skill score
        avg_proficiency = sum(proficiency_scores) / len(proficiency_scores)
        coverage_ratio = len(matching_skills) / len(required_skill_ids)

        # Penalize for missing critical skills
        missing_penalty = len(missing_skills) * 0.15

        final_score = (avg_proficiency * coverage_ratio) - missing_penalty
        return max(0.0, min(1.0, final_score))

    def _calculate_distance_score(
        self, provider_location: Dict, request_location: Dict
    ) -> float:
        """Calculate distance-based score using haversine formula."""
        if not provider_location or not request_location:
            return 0.5  # Neutral score for missing location data

        provider_lat = provider_location.get("latitude")
        provider_lng = provider_location.get("longitude")
        request_lat = request_location.get("latitude")
        request_lng = request_location.get("longitude")

        if None in [provider_lat, provider_lng, request_lat, request_lng]:
            return 0.5  # Neutral score for incomplete coordinates

        # Calculate distance using simplified haversine formula
        import math

        # Convert to radians
        lat1, lng1, lat2, lng2 = map(
            math.radians, [provider_lat, provider_lng, request_lat, request_lng]
        )

        # Haversine formula
        dlat = lat2 - lat1
        dlng = lng2 - lng1
        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
        )
        c = 2 * math.asin(math.sqrt(a))

        # Earth's radius in miles
        earth_radius_miles = 3959
        distance_miles = earth_radius_miles * c

        # Score based on distance (closer = higher score)
        if distance_miles <= 5:
            return 1.0  # Excellent - within 5 miles
        elif distance_miles <= 15:
            return 0.9  # Very good - within 15 miles
        elif distance_miles <= 30:
            return 0.7  # Good - within 30 miles
        elif distance_miles <= 50:
            return 0.5  # Fair - within 50 miles
        elif distance_miles <= 100:
            return 0.3  # Poor - within 100 miles
        else:
            return 0.1  # Very poor - over 100 miles

    def _calculate_availability_score(
        self, provider_availability: Dict, request_timing: Dict
    ) -> float:
        """Calculate availability matching score based on schedule overlap."""
        if not provider_availability or not request_timing:
            return 0.5  # Neutral score for missing data

        from datetime import datetime, timezone

        # Get provider availability window
        provider_start = provider_availability.get("available_from")
        provider_end = provider_availability.get("available_until")

        # Get request timing requirements
        request_start = request_timing.get("preferred_start_date")
        request_duration = request_timing.get("estimated_duration_hours", 8)

        if not all([provider_start, provider_end, request_start]):
            return 0.5  # Missing critical timing data

        # Convert to datetime objects if they're strings
        if isinstance(provider_start, str):
            provider_start = datetime.fromisoformat(
                provider_start.replace("Z", "+00:00")
            )
        if isinstance(provider_end, str):
            provider_end = datetime.fromisoformat(provider_end.replace("Z", "+00:00"))
        if isinstance(request_start, str):
            request_start = datetime.fromisoformat(request_start.replace("Z", "+00:00"))

        # Ensure timezone awareness
        if provider_start.tzinfo is None:
            provider_start = provider_start.replace(tzinfo=timezone.utc)
        if provider_end.tzinfo is None:
            provider_end = provider_end.replace(tzinfo=timezone.utc)
        if request_start.tzinfo is None:
            request_start = request_start.replace(tzinfo=timezone.utc)

        # Calculate request end time
        from datetime import timedelta

        request_end = request_start + timedelta(hours=request_duration)

        # Check if request fits within provider availability
        if request_start >= provider_start and request_end <= provider_end:
            return 1.0  # Perfect fit
        elif request_start >= provider_start and request_start <= provider_end:
            # Partial overlap - request starts within availability
            overlap_hours = (provider_end - request_start).total_seconds() / 3600
            overlap_ratio = min(1.0, overlap_hours / request_duration)
            return 0.7 + (0.3 * overlap_ratio)
        elif request_end >= provider_start and request_end <= provider_end:
            # Partial overlap - request ends within availability
            overlap_hours = (request_end - provider_start).total_seconds() / 3600
            overlap_ratio = min(1.0, overlap_hours / request_duration)
            return 0.7 + (0.3 * overlap_ratio)
        else:
            # No overlap
            return 0.1

    def _calculate_reputation_score(
        self, provider_data: Dict, request_data: Dict
    ) -> float:
        """Calculate reputation-based score using provider ratings and history."""
        if not provider_data:
            return 0.5  # Neutral score for missing data

        # Get provider rating and review metrics
        rating = provider_data.get("rating", 0.0)
        total_reviews = provider_data.get("total_reviews", 0)
        completion_rate = provider_data.get("completion_rate", 0.0)
        response_time_avg = provider_data.get("response_time_avg", 0)  # in minutes

        # Base score from rating (0-5 scale normalized to 0-1)
        rating_score = rating / 5.0 if rating > 0 else 0.0

        # Confidence factor based on number of reviews
        if total_reviews >= 50:
            confidence_factor = 1.0
        elif total_reviews >= 20:
            confidence_factor = 0.9
        elif total_reviews >= 10:
            confidence_factor = 0.8
        elif total_reviews >= 5:
            confidence_factor = 0.7
        elif total_reviews >= 1:
            confidence_factor = 0.6
        else:
            confidence_factor = 0.5  # New provider

        # Completion rate bonus (0-1 scale)
        completion_bonus = completion_rate if completion_rate > 0 else 0.0

        # Response time factor (faster response = higher score)
        if response_time_avg <= 30:  # 30 minutes or less
            response_factor = 1.0
        elif response_time_avg <= 60:  # 1 hour
            response_factor = 0.9
        elif response_time_avg <= 120:  # 2 hours
            response_factor = 0.8
        elif response_time_avg <= 240:  # 4 hours
            response_factor = 0.7
        elif response_time_avg <= 480:  # 8 hours
            response_factor = 0.6
        else:
            response_factor = 0.5  # Slow response

        # Weighted combination
        final_score = (
            rating_score * 0.5
            + completion_bonus * 0.3  # 50% weight on rating
            + response_factor  # 30% weight on completion rate
            * 0.2  # 20% weight on response time
        ) * confidence_factor

        return max(0.0, min(1.0, final_score))

    async def send_job_alerts(
        self, provider_id: int, matching_requests: List[Dict[str, Any]]
    ) -> bool:
        """Send job alerts to providers"""
        await self.notification_service.send_job_alerts(provider_id, matching_requests)
        return True

    async def notify_providers_of_new_request(self, request_id: int) -> bool:
        """Notify relevant providers of new request"""
        matching_providers = await self.provider_repository.find_matching_providers(
            request_id
        )

        # Filter to only notify high-quality matches (score >= 0.85)
        high_quality_matches = [
            p for p in matching_providers if p.get("match_score", 0) >= 0.85
        ]

        if high_quality_matches:
            await self.notification_service.notify_providers(high_quality_matches)

        return True

    async def find_providers_for_emergency_request(
        self, request_id: int
    ) -> List[Dict[str, Any]]:
        """Find providers for emergency requests prioritizing availability"""
        return await self.provider_repository.find_emergency_providers(request_id)

    async def find_team_for_project(
        self, project_requests: List[int]
    ) -> List[Dict[str, Any]]:
        """Find team of providers for large project"""
        return await self.provider_repository.find_team_matches(project_requests)

    async def search_providers(self, search_params: Dict[str, Any]) -> Dict[str, Any]:
        """Search providers with advanced filtering and faceting."""
        # Extract search parameters
        skills = search_params.get("skills", [])
        location = search_params.get("location")
        radius = search_params.get("radius")
        min_rating = search_params.get("min_rating")
        max_hourly_rate = search_params.get("max_hourly_rate")
        available_from = search_params.get("available_from")
        available_until = search_params.get("available_until")
        certifications = search_params.get("certifications", [])
        sort_by = search_params.get("sort_by", "rating")
        order = search_params.get("order", "desc")
        limit = search_params.get("limit", 20)
        offset = search_params.get("offset", 0)

        # Build filter criteria for repository
        filters = {}
        if skills:
            filters["skills"] = skills
        if location:
            filters["location"] = location
        if radius:
            filters["radius"] = radius
        if min_rating:
            filters["min_rating"] = min_rating
        if max_hourly_rate:
            filters["max_hourly_rate"] = max_hourly_rate
        if available_from:
            filters["available_from"] = available_from
        if available_until:
            filters["available_until"] = available_until
        if certifications:
            filters["certifications"] = certifications

        # Get search results from repository
        search_results = await self.provider_repository.search_providers(
            {
                "filters": filters,
                "sort_by": sort_by,
                "order": order,
                "limit": limit,
                "offset": offset,
            }
        )

        # Apply additional business logic filtering
        filtered_results = []
        for provider in search_results.get("results", []):
            # Skip inactive providers
            if not provider.get("is_active", True):
                continue

            # Apply skill matching if skills specified
            if skills:
                skill_match_score = self._calculate_skill_match(
                    provider.get("skills", []),
                    [{"skill_id": skill, "required_level": 1} for skill in skills],
                )
                provider["skill_match_score"] = round(skill_match_score, 3)

                # Filter out providers with very low skill match
                if skill_match_score < 0.3:
                    continue

            # Apply location scoring if location specified
            if location:
                location_score = self._calculate_distance_score(
                    provider.get("location", {}),
                    {"address": location},  # Simplified location format
                )
                provider["location_score"] = round(location_score, 3)

            filtered_results.append(provider)

        # Generate facets for filtering UI
        facets = self._generate_search_facets(filtered_results)

        return {
            "results": filtered_results,
            "total": len(filtered_results),
            "facets": facets,
        }

    def _generate_search_facets(self, results: List[Dict]) -> Dict[str, Any]:
        """Generate facets for search results to help with filtering."""
        facets = {
            "skills": {},
            "locations": {},
            "ratings": {"1-2": 0, "2-3": 0, "3-4": 0, "4-5": 0},
            "hourly_rates": {"0-25": 0, "25-50": 0, "50-75": 0, "75+": 0},
            "experience_levels": {
                "beginner": 0,
                "intermediate": 0,
                "advanced": 0,
                "expert": 0,
            },
        }

        for provider in results:
            # Skills facet
            for skill in provider.get("skills", []):
                skill_name = skill.get("name", "Unknown")
                facets["skills"][skill_name] = facets["skills"].get(skill_name, 0) + 1

            # Location facet
            location = provider.get("location", {})
            city = location.get("city", "Unknown")
            facets["locations"][city] = facets["locations"].get(city, 0) + 1

            # Rating facet
            rating = provider.get("rating", 0)
            if rating >= 4:
                facets["ratings"]["4-5"] += 1
            elif rating >= 3:
                facets["ratings"]["3-4"] += 1
            elif rating >= 2:
                facets["ratings"]["2-3"] += 1
            else:
                facets["ratings"]["1-2"] += 1

            # Hourly rate facet
            hourly_rate = provider.get("hourly_rate", 0)
            if hourly_rate >= 75:
                facets["hourly_rates"]["75+"] += 1
            elif hourly_rate >= 50:
                facets["hourly_rates"]["50-75"] += 1
            elif hourly_rate >= 25:
                facets["hourly_rates"]["25-50"] += 1
            else:
                facets["hourly_rates"]["0-25"] += 1

            # Experience level facet
            experience_years = provider.get("experience_years", 0)
            if experience_years >= 10:
                facets["experience_levels"]["expert"] += 1
            elif experience_years >= 5:
                facets["experience_levels"]["advanced"] += 1
            elif experience_years >= 2:
                facets["experience_levels"]["intermediate"] += 1
            else:
                facets["experience_levels"]["beginner"] += 1

        return facets

    async def search_requests(self, search_params: Dict[str, Any]) -> Dict[str, Any]:
        """Search service requests with advanced filtering and faceting."""
        # Extract search parameters
        category = search_params.get("category")
        location = search_params.get("location")
        radius = search_params.get("radius")
        budget_min = search_params.get("budget_min")
        budget_max = search_params.get("budget_max")
        urgency = search_params.get("urgency")
        timeline_start = search_params.get("timeline_start")
        timeline_end = search_params.get("timeline_end")
        limit = search_params.get("limit", 20)
        offset = search_params.get("offset", 0)

        # Build filter criteria for repository
        filters = {}
        if category:
            filters["category"] = category
        if location:
            filters["location"] = location
        if radius:
            filters["radius"] = radius
        if budget_min:
            filters["budget_min"] = budget_min
        if budget_max:
            filters["budget_max"] = budget_max
        if urgency:
            filters["urgency"] = urgency
        if timeline_start:
            filters["timeline_start"] = timeline_start
        if timeline_end:
            filters["timeline_end"] = timeline_end

        # Get search results from repository
        search_results = await self.request_repository.search_requests(
            {"filters": filters, "limit": limit, "offset": offset}
        )

        # Apply additional business logic filtering
        filtered_results = []
        for request in search_results.get("results", []):
            # Only include active requests
            if request.get("status") != "ACTIVE":
                continue

            # Apply budget filtering if specified
            if budget_min or budget_max:
                request_budget_min = request.get("budget_min", 0)
                request_budget_max = request.get("budget_max", float("inf"))

                # Check if budgets overlap
                if budget_min and request_budget_max < budget_min:
                    continue
                if budget_max and request_budget_min > budget_max:
                    continue

            # Apply location scoring if location specified
            if location:
                location_score = self._calculate_distance_score(
                    {"address": location},  # Simplified location format
                    request.get("location", {}),
                )
                request["location_score"] = round(location_score, 3)

            # Calculate urgency score for sorting
            urgency_level = request.get("urgency_level", "MEDIUM")
            urgency_scores = {"LOW": 0.3, "MEDIUM": 0.6, "HIGH": 0.8, "EMERGENCY": 1.0}
            request["urgency_score"] = urgency_scores.get(urgency_level, 0.6)

            filtered_results.append(request)

        # Sort by urgency and timeline by default
        filtered_results.sort(
            key=lambda r: (
                r.get("urgency_score", 0.6),
                -r.get("location_score", 0.5),  # Negative for descending order
            ),
            reverse=True,
        )

        # Generate facets for filtering UI
        facets = self._generate_request_search_facets(filtered_results)

        return {
            "results": filtered_results,
            "total": len(filtered_results),
            "facets": facets,
        }

    def _generate_request_search_facets(self, results: List[Dict]) -> Dict[str, Any]:
        """Generate facets for request search results."""
        facets = {
            "categories": {},
            "locations": {},
            "budgets": {"0-500": 0, "500-1500": 0, "1500-5000": 0, "5000+": 0},
            "urgency": {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "EMERGENCY": 0},
            "timeline": {
                "immediate": 0,
                "this_week": 0,
                "this_month": 0,
                "flexible": 0,
            },
        }

        from datetime import datetime, timedelta, timezone

        now = datetime.now(timezone.utc)

        for request in results:
            # Category facet
            category = request.get("category", "Other")
            facets["categories"][category] = facets["categories"].get(category, 0) + 1

            # Location facet
            location = request.get("location", {})
            city = location.get("city", "Unknown")
            facets["locations"][city] = facets["locations"].get(city, 0) + 1

            # Budget facet
            budget_max = request.get("budget_max", 0)
            if budget_max >= 5000:
                facets["budgets"]["5000+"] += 1
            elif budget_max >= 1500:
                facets["budgets"]["1500-5000"] += 1
            elif budget_max >= 500:
                facets["budgets"]["500-1500"] += 1
            else:
                facets["budgets"]["0-500"] += 1

            # Urgency facet
            urgency = request.get("urgency_level", "MEDIUM")
            facets["urgency"][urgency] = facets["urgency"].get(urgency, 0) + 1

            # Timeline facet
            preferred_start = request.get("preferred_start_date")
            if preferred_start:
                if isinstance(preferred_start, str):
                    preferred_start = datetime.fromisoformat(
                        preferred_start.replace("Z", "+00:00")
                    )

                days_until_start = (preferred_start - now).days
                if days_until_start <= 1:
                    facets["timeline"]["immediate"] += 1
                elif days_until_start <= 7:
                    facets["timeline"]["this_week"] += 1
                elif days_until_start <= 30:
                    facets["timeline"]["this_month"] += 1
                else:
                    facets["timeline"]["flexible"] += 1
            else:
                facets["timeline"]["flexible"] += 1

        return facets

    async def get_search_suggestions(
        self, query: str, suggestion_type: str, limit: int = 10
    ) -> Dict[str, Any]:
        """Get search suggestions based on query"""
        if suggestion_type == "providers":
            suggestions = await self.provider_repository.get_provider_suggestions(
                query, limit
            )
        elif suggestion_type == "requests":
            suggestions = await self.request_repository.get_request_suggestions(
                query, limit
            )
        elif suggestion_type == "skills":
            suggestions = await self.provider_repository.get_skill_suggestions(
                query, limit
            )
        else:  # all
            provider_suggestions = (
                await self.provider_repository.get_provider_suggestions(
                    query, limit // 3
                )
            )
            request_suggestions = await self.request_repository.get_request_suggestions(
                query, limit // 3
            )
            skill_suggestions = await self.provider_repository.get_skill_suggestions(
                query, limit // 3
            )
            suggestions = provider_suggestions + request_suggestions + skill_suggestions

        return {"suggestions": suggestions}

    async def get_analytics(self) -> Dict[str, Any]:
        """Get matching analytics and metrics"""
        total_matches = await self.provider_repository.get_total_matches()
        success_rate = await self.provider_repository.get_match_success_rate()
        avg_response_time = await self.provider_repository.get_average_response_time()
        top_skills = await self.provider_repository.get_top_skills()
        top_skills_requested = await self.request_repository.get_top_requested_skills()

        return {
            "total_matches": total_matches,
            "match_success_rate": success_rate,
            "average_response_time": avg_response_time,
            "top_skills": top_skills,
            "top_skills_requested": top_skills_requested,
        }
