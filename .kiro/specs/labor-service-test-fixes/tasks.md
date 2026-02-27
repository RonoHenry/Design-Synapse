# Labor Service Test Fixes - Systematic Approach

## Overview
Fix 44 failing tests and 3 errors in the labor service systematically, starting with quick wins and moving to complex issues.

## Test Results Summary
- **Total Tests:** 310
- **Passed:** 263 (85%)
- **Failed:** 44 (14%)
- **Errors:** 3 (1%)

## Priority 1: Schema/Response Format Fixes (Quick Wins)

- [ ] 1.1 Fix Review Response Schema Mismatch
  - **Issue:** API returns `results` but schema expects `items`
  - **Files:** `src/api/v1/routes/reviews.py`, `src/api/v1/schemas/review.py`
  - **Tests:** `test_reviews.py::test_search_reviews`, `test_reviews.py::test_get_provider_reviews`, `test_reviews.py::test_get_seeker_reviews`
  - **Fix:** Align response field names between service and schema

- [ ] 1.2 Add Missing Analytics Response Fields
  - **Issue:** Missing `average_rating` in review list responses
  - **Files:** `src/services/review_service.py`, `src/api/v1/schemas/review.py`
  - **Tests:** `test_reviews.py::test_get_provider_reviews`, `test_reviews.py::test_get_seeker_reviews`
  - **Fix:** Add analytics calculation to review list endpoints

- [ ] 1.3 Fix Booking Status Case Sensitivity
  - **Issue:** Test expects lowercase 'completed' but API returns 'COMPLETED'
  - **Files:** `src/api/v1/routes/bookings.py`
  - **Tests:** `test_bookings.py::test_complete_booking`
  - **Fix:** Ensure consistent status casing in responses

## Priority 2: Matching Service Fixes (Blocks Many Tests)

- [ ] 2.1 Fix ServiceRequest Dictionary Access
  - **Issue:** `ServiceRequest.get()` - treating model as dict
  - **Files:** `src/services/matching_service.py` line 39
  - **Tests:** `test_matching_service.py::test_find_providers_for_request`
  - **Fix:** Use attribute access instead of `.get()`

- [ ] 2.2 Add Missing Async/Await on Repository Calls
  - **Issue:** `TypeError: object Mock can't be used in 'await' expression`
  - **Files:** `src/services/matching_service.py` line 102
  - **Tests:** `test_matching_service.py::test_calculate_match_score`
  - **Fix:** Ensure all repository calls use `await`

- [ ] 2.3 Implement ProficiencyLevel Comparison
  - **Issue:** `TypeError: '>=' not supported between instances of 'ProficiencyLevel'`
  - **Files:** `src/models/service_provider.py` (ProficiencyLevel enum)
  - **Tests:** `test_matching_service.py::test_skill_match_calculation`, `test_matching_service.py::test_skill_mismatch_calculation`
  - **Fix:** Add `__ge__`, `__le__`, `__gt__`, `__lt__` methods to enum or use `.value` comparison

- [ ] 2.4 Fix Matching Service Return Format
  - **Issue:** Returning string instead of dict with match data
  - **Files:** `src/services/matching_service.py`
  - **Tests:** `test_matching_service.py::test_matching_performance_with_large_dataset`, `test_matching_service.py::test_matching_with_inactive_providers`
  - **Fix:** Ensure consistent dict return format with `provider_id`, `match_score` keys

- [ ] 2.5 Fix Integration Matching Endpoints
  - **Issue:** All matching integration tests returning 500 errors
  - **Files:** `src/api/v1/routes/matching.py`, `src/services/matching_service.py`
  - **Tests:** All `test_matching.py` integration tests (14 failures)
  - **Fix:** Fix underlying service issues from 2.1-2.4

## Priority 3: Booking Service Authorization & Business Rules

- [ ] 3.1 Fix Booking Authorization Checks
  - **Issue:** `AuthorizationError: Only the assigned provider can start the booking`
  - **Files:** `src/services/booking_service.py` lines 502, 533
  - **Tests:** `test_booking_service.py::test_update_booking_status`, `test_booking_service.py::test_cancel_booking`, `test_booking_service.py::test_cancel_booking_with_penalty`
  - **Fix:** Adjust authorization logic or fix test data to match business rules

- [ ] 3.2 Fix Booking Time Validation for Tests
  - **Issue:** `BusinessLogicError: Cannot start booking more than 1 hour before scheduled time`
  - **Files:** `src/services/booking_service.py` line 514
  - **Tests:** `test_booking_service_properties.py::test_property_booking_state_transitions_follow_business_rules`
  - **Fix:** Either relax validation for tests or ensure test data has proper scheduled times

- [ ] 3.3 Fix Booking Integration Test Data
  - **Issue:** Multiple booking integration tests failing with 400/422 errors
  - **Files:** Test data setup in `tests/integration/api/v1/test_bookings.py`
  - **Tests:** `test_bookings.py::test_create_booking_from_quote`, `test_bookings.py::test_update_booking_status`, etc.
  - **Fix:** Ensure test data meets all business rule requirements

## Priority 4: Review Service Mock & Method Fixes

- [ ] 4.1 Fix Review Service Mock Returns
  - **Issue:** Mock `.save()` returning AsyncMock instead of actual object
  - **Files:** `tests/unit/services/test_review_service.py`
  - **Tests:** `test_review_service.py::test_submit_provider_review`, `test_review_service.py::test_submit_seeker_review`
  - **Fix:** Configure mocks to return proper Review objects with attributes

- [ ] 4.2 Fix respond_to_review Method Signature
  - **Issue:** `TypeError: ReviewService.respond_to_review() missing 1 required positional argument`
  - **Files:** `src/services/review_service.py` or test file
  - **Tests:** `test_review_service.py::test_respond_to_review`, `test_review_service.py::test_cannot_respond_to_own_review`
  - **Fix:** Align method signature between service and tests

- [ ] 4.3 Fix Review Repository Mock Async Methods
  - **Issue:** `TypeError: object Mock can't be used in 'await' expression`
  - **Files:** `tests/unit/services/test_review_service.py`
  - **Tests:** `test_review_service.py::test_flag_inappropriate_review`
  - **Fix:** Use AsyncMock for repository methods

- [ ] 4.4 Fix search_reviews Coroutine Slicing
  - **Issue:** `TypeError: 'coroutine' object is not subscriptable`
  - **Files:** `src/services/review_service.py` line 577
  - **Tests:** `test_review_service.py::test_search_reviews_by_rating`
  - **Fix:** Await the coroutine before slicing

## Priority 5: Property-Based Test Fixes

- [ ] 5.1 Fix Property Test Mock Datetime Operations
  - **Issue:** `TypeError: unsupported operand type(s) for -: 'Mock' and 'datetime.datetime'`
  - **Files:** `tests/unit/services/test_booking_service_properties.py`
  - **Tests:** `test_booking_service_properties.py::test_property_cancellation_allowed_from_valid_states`
  - **Fix:** Mock `scheduled_start` with actual datetime objects

- [ ] 5.2 Adjust Property Test Business Rule Expectations
  - **Issue:** Property tests failing due to strict business rules
  - **Files:** `tests/unit/services/test_booking_service_properties.py`
  - **Tests:** `test_booking_service_properties.py::test_property_booking_state_transitions_follow_business_rules`
  - **Fix:** Generate test data that satisfies business rules (e.g., scheduled_start within 1 hour)

## Priority 6: Quote & Request Integration Fixes

- [ ] 6.1 Fix Quote Update/Accept Endpoints
  - **Issue:** Returning 400 instead of 200
  - **Files:** `src/api/v1/routes/quotes.py`, `src/services/quote_service.py`
  - **Tests:** `test_quotes.py::test_update_quote_success`, `test_quotes.py::test_accept_quote_success`, `test_quotes.py::test_submit_counter_proposal`
  - **Fix:** Debug validation errors causing 400 responses

- [ ] 6.2 Fix Quote Comparison Endpoint
  - **Issue:** Returning 422 instead of 200
  - **Files:** `src/api/v1/routes/quotes.py`
  - **Tests:** `test_quotes.py::test_compare_quotes`
  - **Fix:** Fix request validation or endpoint implementation

- [ ] 6.3 Fix Request Search by Skills
  - **Issue:** Returning 422 instead of 200
  - **Files:** `src/api/v1/routes/requests.py`
  - **Tests:** `test_requests.py::test_search_requests_by_skills`
  - **Fix:** Fix query parameter validation

## Priority 7: Provider & Async Fixture Fixes

- [ ] 7.1 Fix Provider Analytics Endpoint
  - **Issue:** Returning 422 instead of 200
  - **Files:** `src/api/v1/routes/providers.py`
  - **Tests:** `test_providers.py::test_get_provider_analytics`
  - **Fix:** Fix request validation for analytics endpoint

- [ ] 7.2 Fix Async Fixture Requests
  - **Issue:** `pytest.PytestRemovedIn9Warning: requested an async fixture 'async_client'`
  - **Files:** Test files requesting async_client
  - **Tests:** `test_matching.py::test_real_time_matching_updates`, `test_providers.py::test_search_providers_async`, `test_requests.py::test_get_matching_providers`
  - **Fix:** Either remove async_client usage or properly configure async fixtures

## Execution Strategy

1. **Start with Priority 1** - Quick schema fixes (30 min)
2. **Move to Priority 2** - Matching service (1-2 hours) - blocks many tests
3. **Then Priority 3** - Booking authorization (1 hour)
4. **Then Priority 4** - Review service mocks (30 min)
5. **Then Priority 5** - Property tests (1 hour)
6. **Finally Priorities 6-7** - Remaining integration issues (1-2 hours)

## Success Criteria

- All 44 failing tests pass
- All 3 errors resolved
- No new test failures introduced
- Test coverage remains at 85%+
