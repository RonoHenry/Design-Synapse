# Labor Service API Fixes Implementation Tasks

## Overview

This implementation plan addresses critical API routing, business logic, and code quality issues in the Labor Services Marketplace. The tasks are organized to fix API endpoints, implement proper business logic, and ensure consistent response formats.

## Tasks

- [x] 1. Fix Matching API Routes and Parameters
  - Update routes to use query parameters instead of path parameters
  - Add missing search endpoints under `/api/v1/search/`
  - Implement proper response formats for matching operations
  - _Requirements: 1.1, 1.2, 1.3, 3.1_

- [x] 1.1 Update Matching Routes Parameter Handling
  - Fix `apps/labor-service/src/api/v1/routes/matching.py`
  - Change `/providers/{request_id}` to `/providers` with query parameter
  - Add query parameters: `max_distance`, `min_rating`, `limit`
  - Update response format to include `providers`, `match_scores`, `total_matches`
  - _Requirements: 1.1, 3.1_

- [x] 1.2 Add Missing Search Endpoints
  - Add `/api/v1/search/providers` endpoint
  - Add `/api/v1/search/requests` endpoint
  - Implement proper search response format with `results`, `total`, `facets`
  - _Requirements: 1.4, 1.5, 3.2_

- [x] 1.3 Write property test for matching response format
  - **Property 1: Matching endpoints return required response fields**
  - **Validates: Requirements 1.1, 1.2, 1.3, 3.1**

- [x] 2. Fix Booking Status Management
  - Implement proper booking state transitions
  - Add business logic validation for status changes
  - Fix status transition endpoints returning 400 errors
  - _Requirements: 2.1, 2.2, 2.3, 5.2_

- [x] 2.1 Implement Booking State Machine
  - Update `apps/labor-service/src/api/v1/routes/bookings.py`
  - Add proper validation for booking status transitions
  - Implement start booking endpoint with status validation
  - Implement complete booking endpoint with completion data
  - _Requirements: 2.1, 2.2, 5.2_

- [x] 2.2 Add Booking Status Validation Logic
  - Update `apps/labor-service/src/services/booking_service.py`
  - Implement state machine: confirmed → in_progress → completed
  - Add cancellation logic from any valid state
  - Add proper error handling for invalid transitions
  - _Requirements: 2.1, 2.2, 2.3_

- [x] 2.3 Write property test for booking state transitions
  - **Property 3: Booking state transitions follow business rules**
  - **Validates: Requirements 2.1, 2.2, 2.3, 5.2**

- [-] 3. Implement Real Business Logic
  - Replace mock implementations with actual matching algorithms
  - Add database queries for search and matching operations
  - Implement proper error handling throughout service layer
  - _Requirements: 5.1, 5.3_

- [x] 3.1 Implement Matching Algorithm
  - Update `apps/labor-service/src/services/matching_service.py`
  - Replace mock responses with actual matching logic
  - Implement skill matching, location scoring, availability checking
  - Add weighted scoring algorithm for provider matching
  - _Requirements: 5.1_

- [x] 3.2 Implement Search Functionality
  - Add database queries for provider and request search
  - Implement filter application for search criteria
  - Add faceted search with proper aggregations
  - _Requirements: 5.3_

- [ ] 3.3 Write property test for real matching functionality
  - **Property 7: Matching algorithms provide real functionality**
  - **Validates: Requirements 5.1**

- [ ] 4. Standardize Response Formats
  - Create consistent response schemas across all endpoints
  - Update API responses to match expected formats
  - Add proper error response standardization
  - _Requirements: 3.1, 3.2, 3.3, 3.4_

- [ ] 4.1 Create Response Schema Standards
  - Update `apps/labor-service/src/api/v1/schemas/`
  - Add `MatchingResponse`, `SearchResponse`, `BookingStatusResponse` schemas
  - Standardize error response format across all endpoints
  - _Requirements: 3.1, 3.2, 3.3_

- [ ] 4.2 Update API Endpoints with Standard Responses
  - Apply new response schemas to all matching endpoints
  - Apply new response schemas to all search endpoints
  - Apply new response schemas to all booking endpoints
  - _Requirements: 3.1, 3.2, 3.3_

- [ ] 4.3 Write property test for response format consistency
  - **Property 2: Search endpoints return consistent format**
  - **Property 4: Booking operations return complete data**
  - **Validates: Requirements 1.4, 1.5, 2.4, 2.5, 3.2, 3.3**

- [ ] 5. Fix Pydantic v2 Compliance
  - Update all schemas to use ConfigDict instead of class-based config
  - Remove deprecated Pydantic v1 patterns
  - Ensure proper field serialization
  - _Requirements: 6.1, 6.5_

- [ ] 5.1 Update Schema Configuration
  - Fix all Pydantic schemas to use `model_config = ConfigDict(...)`
  - Remove class-based `Config` classes
  - Update field definitions for Pydantic v2 compatibility
  - _Requirements: 6.1_

- [ ] 5.2 Write property test for schema serialization
  - **Property 9: Schema serialization handles all field types**
  - **Validates: Requirements 6.5**

- [ ] 6. Add Analytics and Notification Integration
  - Implement analytics endpoints with proper metrics
  - Add notification service integration for booking events
  - Ensure proper error handling for external service calls
  - _Requirements: 3.5, 5.4, 5.5_

- [ ] 6.1 Implement Analytics Endpoints
  - Add analytics endpoints returning match success rates
  - Add top skills requested metrics
  - Implement proper aggregation queries
  - _Requirements: 3.5, 5.4_

- [ ] 6.2 Add Notification Service Integration
  - Integrate notification service for booking status changes
  - Add proper error handling for notification failures
  - Implement retry logic for failed notifications
  - _Requirements: 5.5_

- [ ] 6.3 Write property tests for analytics and notifications
  - **Property 6: Analytics return all expected metrics**
  - **Property 10: Notification integration works properly**
  - **Validates: Requirements 3.5, 5.4, 5.5**

- [ ] 7. Code Quality and Error Handling
  - Remove duplicate function definitions
  - Implement consistent error handling across all endpoints
  - Add proper logging and monitoring
  - _Requirements: 3.4, 4.5, 6.4, 7.1_

- [ ] 7.1 Clean Up Code Quality Issues
  - Remove duplicate function definitions
  - Fix any remaining import issues
  - Ensure consistent code formatting and structure
  - _Requirements: 7.1_

- [ ] 7.2 Implement Comprehensive Error Handling
  - Add consistent error response format
  - Implement proper HTTP status codes for all error conditions
  - Add detailed error messages with context
  - _Requirements: 3.4, 4.5, 6.4_

- [ ] 7.3 Write property test for error handling consistency
  - **Property 5: Error responses are consistent**
  - **Validates: Requirements 3.4, 4.5, 6.4**

- [ ] 8. Integration Testing and Validation
  - Run comprehensive integration tests
  - Validate all API endpoints work correctly
  - Ensure proper database integration
  - _Requirements: All requirements_

- [ ] 8.1 Run Integration Test Suite
  - Execute all existing integration tests
  - Fix any remaining test failures
  - Validate API contract compliance
  - _Requirements: All requirements_

- [ ] 8.2 Write property test for search filter application
  - **Property 8: Search operations apply filters correctly**
  - **Validates: Requirements 5.3**

- [ ] 8.3 Final Validation and Documentation
  - Document all API changes and fixes
  - Update service README with corrected endpoints
  - Validate complete system functionality
  - _Requirements: All requirements_

## Notes

- Each task references specific requirements for traceability
- Property tests validate universal correctness properties
- Focus on fixing critical API routing issues first
- Implement real business logic to replace mock responses
- Ensure Pydantic v2 compliance throughout
- Add comprehensive error handling and logging
- Property tests should run minimum 100 iterations each
- Tag property tests with: **Feature: labor-service-fixes, Property {number}: {property_text}**
