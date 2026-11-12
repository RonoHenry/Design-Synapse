# Labor Service API Fixes Design

## Overview

This design addresses critical API routing, business logic, and code quality issues in the Labor Services Marketplace that are causing integration test failures. The fixes will ensure proper API functionality, consistent response formats, and clean, maintainable code.

## Architecture

The Labor service follows a layered architecture:
- **API Layer**: FastAPI routes with proper parameter handling
- **Service Layer**: Business logic for matching, booking, and search operations
- **Repository Layer**: Data access with proper error handling
- **Model Layer**: SQLAlchemy models with Pydantic schemas

## Components and Interfaces

### 1. Matching API Routes
**File**: `apps/labor-service/src/api/v1/routes/matching.py`

**Current Issues**:
- Routes use path parameters where tests expect query parameters
- Mock responses don't match expected response formats
- Missing search endpoints under `/api/v1/search/`

**Design Changes**:
```python
# Change from: /providers/{request_id}
# Change to: /providers (with request_id as query param)
@router.get("/providers")
async def find_providers_for_request(
    request_id: int = Query(...),
    max_distance: Optional[float] = Query(None),
    min_rating: Optional[float] = Query(None),
    limit: int = Query(10, ge=1, le=50)
):
    return {
        "providers": [...],
        "match_scores": {...},
        "total_matches": 0
    }

# Add missing search routes
@router.get("/search/providers")
@router.get("/search/requests")
```

### 2. Booking Status Management
**File**: `apps/labor-service/src/api/v1/routes/bookings.py`

**Current Issues**:
- Status transition endpoints return 400 errors
- Missing business logic for state validation
- No proper error handling for invalid transitions

**Design Changes**:
```python
@router.post("/{booking_id}/start")
async def start_booking(
    booking_id: int,
    booking_service: BookingService = Depends(get_booking_service)
):
    # Validate booking exists and is in "confirmed" status
    # Update status to "in_progress" with actual_start_date
    # Return updated booking data

@router.post("/{booking_id}/complete")
async def complete_booking(
    booking_id: int,
    completion_data: BookingCompletionRequest,
    booking_service: BookingService = Depends(get_booking_service)
):
    # Validate booking is in "in_progress" status
    # Update status to "completed" with actual_completion_date
    # Handle milestone completion and payment processing
```

### 3. Service Layer Enhancements
**Files**:
- `apps/labor-service/src/services/matching_service.py`
- `apps/labor-service/src/services/booking_service.py`

**Design Changes**:
- Replace mock implementations with actual business logic
- Add proper error handling and validation
- Implement state machine for booking status transitions
- Add database queries for matching and search operations

### 4. Response Format Standardization
**File**: `apps/labor-service/src/api/v1/schemas/`

**Design Changes**:
```python
class MatchingResponse(BaseModel):
    providers: List[ProviderMatch]
    match_scores: Dict[int, float]
    total_matches: int

class SearchResponse(BaseModel):
    results: List[SearchResult]
    total: int
    facets: Dict[str, List[FacetValue]]
    filters_applied: Dict[str, Any]

class BookingStatusResponse(BaseModel):
    booking: BookingResponse
    status_changed: bool
    previous_status: str
    new_status: str
```

## Data Models

### Booking Status State Machine
```
confirmed -> in_progress -> completed
    |            |
    v            v
cancelled    cancelled
```

**Valid Transitions**:
- `confirmed` → `in_progress` (start booking)
- `confirmed` → `cancelled` (cancel before start)
- `in_progress` → `completed` (complete work)
- `in_progress` → `cancelled` (cancel during work)

### Match Scoring Algorithm
```python
def calculate_match_score(provider: Provider, request: ServiceRequest) -> float:
    skill_score = calculate_skill_match(provider.skills, request.required_skills)
    location_score = calculate_distance_score(provider.location, request.location)
    availability_score = check_availability_overlap(provider.availability, request.timeline)
    rating_score = normalize_rating(provider.average_rating)

    return weighted_average([
        (skill_score, 0.4),
        (location_score, 0.3),
        (availability_score, 0.2),
        (rating_score, 0.1)
    ])
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Acceptance Criteria Testing Prework:

1.1 WHEN a client requests `/api/v1/matching/providers` with query parameters, THE Labor_Service SHALL return matching providers with scores
  Thoughts: This is about API response format consistency across all matching requests. We can test this by generating random query parameters and ensuring all responses contain the required fields.
  Testable: yes - property

1.2 WHEN a client requests `/api/v1/matching/opportunities` with query parameters, THE Labor_Service SHALL return matching opportunities for providers
  Thoughts: Similar to 1.1, this is about consistent response format for opportunity matching across all requests.
  Testable: yes - property

1.3 WHEN a client posts to `/api/v1/matching/calculate-score`, THE Labor_Service SHALL return detailed match scoring information
  Thoughts: This is about ensuring the calculate-score endpoint returns all required scoring fields for any valid input.
  Testable: yes - property

2.1 WHEN a booking is in "confirmed" status, THE Labor_Service SHALL allow transition to "in_progress" via start endpoint
  Thoughts: This is testing state machine transitions. We can generate random bookings in confirmed state and ensure they can transition to in_progress.
  Testable: yes - property

2.2 WHEN a booking is in "in_progress" status, THE Labor_Service SHALL allow transition to "completed" via complete endpoint
  Thoughts: Another state machine transition that should work for all bookings in the correct state.
  Testable: yes - property

2.3 WHEN a booking is in valid status, THE Labor_Service SHALL allow cancellation with proper reason tracking
  Thoughts: This tests that cancellation works from any valid state and properly tracks reasons.
  Testable: yes - property

3.1 WHEN matching endpoints return results, THE Labor_Service SHALL include providers, match_scores, and total_matches fields
  Thoughts: This is about response format consistency across all matching endpoints.
  Testable: yes - property

3.2 WHEN search endpoints return results, THE Labor_Service SHALL include results, total, and facets fields
  Thoughts: This is about response format consistency across all search endpoints.
  Testable: yes - property

5.1 WHEN matching requests are made, THE Labor_Service SHALL implement actual matching algorithms not just mock responses
  Thoughts: This tests that different inputs produce different outputs based on real logic, not just static responses.
  Testable: yes - property

6.1 WHEN schemas are defined, THE Labor_Service SHALL use ConfigDict instead of class-based config
  Thoughts: This is about code structure and Pydantic v2 compliance, not runtime behavior.
  Testable: no

6.5 WHEN schemas are serialized, THE Labor_Service SHALL handle all field types correctly
  Thoughts: This tests that serialization works correctly for all schema field types without errors.
  Testable: yes - property

7.1 WHEN duplicate function definitions exist, THE Labor_Service SHALL remove redundant implementations
  Thoughts: This is about code quality and structure, not runtime behavior.
  Testable: no

### Property Reflection:

After reviewing the prework analysis, I identified several properties that can be consolidated:
- Properties 1.1, 1.2, 1.3 can be combined into one comprehensive matching response format property
- Properties 2.1, 2.2, 2.3 can be combined into one booking state transition property
- Properties 3.1 and 3.2 can be combined into one API response format property

### Property 1: Matching endpoints return required response fields
*For any* matching API request (providers, opportunities, calculate-score), the response should contain all required fields specific to that endpoint type
**Validates: Requirements 1.1, 1.2, 1.3, 3.1**

### Property 2: Search endpoints return consistent format
*For any* search API request (providers or requests), the response should contain results, total, and facets fields
**Validates: Requirements 1.4, 1.5, 3.2**

### Property 3: Booking state transitions follow business rules
*For any* booking status change request, the system should only allow valid state transitions according to the booking lifecycle
**Validates: Requirements 2.1, 2.2, 2.3, 5.2**

### Property 4: Booking operations return complete data
*For any* successful booking operation, the response should include updated booking data with proper status information
**Validates: Requirements 2.4, 2.5, 3.3**

### Property 5: Error responses are consistent
*For any* failed operation, the system should return error responses with consistent format and meaningful detail messages
**Validates: Requirements 3.4, 4.5, 6.4**

### Property 6: Analytics return all expected metrics
*For any* analytics request, the response should contain all expected metric fields including match_success_rate and top_skills_requested
**Validates: Requirements 3.5, 5.4**

### Property 7: Matching algorithms provide real functionality
*For any* matching request with different input parameters, the system should return different results based on actual matching logic
**Validates: Requirements 5.1**

### Property 8: Search operations apply filters correctly
*For any* search request with filter criteria, the returned results should match the specified filters
**Validates: Requirements 5.3**

### Property 9: Schema serialization handles all field types
*For any* Pydantic schema with various field types, serialization should produce correct JSON representation without errors
**Validates: Requirements 6.5**

### Property 10: Notification integration works properly
*For any* operation that should trigger notifications, the notification service should be called with appropriate parameters
**Validates: Requirements 5.5**

## Error Handling

### API Error Responses
All endpoints will return consistent error responses using the shared error handling infrastructure:

```python
{
    "error": "VALIDATION_ERROR",
    "message": "Invalid booking status transition",
    "detail": {
        "current_status": "completed",
        "requested_transition": "start",
        "valid_transitions": []
    }
}
```

### Booking State Validation
Invalid state transitions will be rejected with specific error messages:
- Cannot start a booking that's already completed
- Cannot complete a booking that hasn't been started
- Cannot cancel a booking that's already completed

### Parameter Validation
Missing or invalid parameters will return 422 validation errors with clear field-level messages.

## Testing Strategy

### Unit Tests
- Test individual service methods for business logic
- Test schema validation and serialization
- Test error handling for edge cases
- Test state machine transitions

### Property-Based Tests
- Test API endpoints with various parameter combinations
- Test booking state transitions with random valid/invalid sequences
- Test search filtering with random criteria
- Test response format consistency across endpoints

**Property Test Configuration**:
- Minimum 100 iterations per property test
- Each test tagged with: **Feature: labor-service-fixes, Property {number}: {property_text}**
- Use factories to generate test data for providers, requests, and bookings

### Integration Tests
- Test complete API workflows (create booking → start → complete)
- Test cross-service communication with notification service
- Test database persistence and retrieval
- Test error propagation through the stack

The testing approach ensures both specific examples work correctly and universal properties hold across all valid inputs, providing comprehensive coverage of the Labor service functionality.
