# Labor Service API Fixes Requirements

## Introduction

The Labor Services Marketplace has several critical API routing and implementation issues that are causing integration test failures. These issues prevent the service from functioning correctly and need immediate resolution.

## Glossary

- **Labor_Service**: The Labor Services Marketplace FastAPI application
- **Matching_API**: API endpoints for provider-request matching functionality
- **Booking_API**: API endpoints for booking management operations
- **Route_Mismatch**: When test expectations don't match actual API route definitions
- **Status_Transition**: Valid state changes for booking lifecycle management

## Requirements

### Requirement 1: Fix Matching API Route Mismatches

**User Story:** As a client application, I want to access matching endpoints with consistent URL patterns, so that I can find providers and opportunities reliably.

#### Acceptance Criteria

1. WHEN a client requests `/api/v1/matching/providers` with query parameters, THE Labor_Service SHALL return matching providers with scores
2. WHEN a client requests `/api/v1/matching/opportunities` with query parameters, THE Labor_Service SHALL return matching opportunities for providers
3. WHEN a client posts to `/api/v1/matching/calculate-score`, THE Labor_Service SHALL return detailed match scoring information
4. WHEN a client requests `/api/v1/search/providers` with advanced filters, THE Labor_Service SHALL return filtered provider results
5. WHEN a client requests `/api/v1/search/requests` with search criteria, THE Labor_Service SHALL return matching service requests

### Requirement 2: Implement Booking Status Management

**User Story:** As a service provider or client, I want to manage booking statuses through API endpoints, so that I can track and update booking progress.

#### Acceptance Criteria

1. WHEN a booking is in "confirmed" status, THE Labor_Service SHALL allow transition to "in_progress" via start endpoint
2. WHEN a booking is in "in_progress" status, THE Labor_Service SHALL allow transition to "completed" via complete endpoint
3. WHEN a booking is in valid status, THE Labor_Service SHALL allow cancellation with proper reason tracking
4. WHEN a booking needs rescheduling, THE Labor_Service SHALL update dates and maintain status consistency
5. WHEN booking updates are added, THE Labor_Service SHALL store progress information with timestamps

### Requirement 3: Standardize API Response Formats

**User Story:** As a client application, I want consistent API response formats across all endpoints, so that I can reliably parse and handle responses.

#### Acceptance Criteria

1. WHEN matching endpoints return results, THE Labor_Service SHALL include providers, match_scores, and total_matches fields
2. WHEN search endpoints return results, THE Labor_Service SHALL include results, total, and facets fields
3. WHEN booking operations succeed, THE Labor_Service SHALL return updated booking data with proper status
4. WHEN operations fail, THE Labor_Service SHALL return consistent error responses with detail messages
5. WHEN analytics are requested, THE Labor_Service SHALL return all expected metric fields

### Requirement 4: Fix Route Parameter Handling

**User Story:** As an API consumer, I want route parameters to be handled correctly, so that I can access specific resources by ID.

#### Acceptance Criteria

1. WHEN accessing provider-specific endpoints, THE Labor_Service SHALL accept provider_id as query parameter not path parameter
2. WHEN accessing request-specific endpoints, THE Labor_Service SHALL accept request_id as query parameter not path parameter
3. WHEN calculating match scores, THE Labor_Service SHALL accept both IDs in request body not URL path
4. WHEN accessing booking operations, THE Labor_Service SHALL maintain booking_id as path parameter
5. WHEN route parameters are missing or invalid, THE Labor_Service SHALL return appropriate validation errors

### Requirement 5: Implement Missing Service Logic

**User Story:** As a system administrator, I want all API endpoints to have proper business logic implementation, so that the service provides meaningful functionality.

#### Acceptance Criteria

1. WHEN matching requests are made, THE Labor_Service SHALL implement actual matching algorithms not just mock responses
2. WHEN booking status changes are requested, THE Labor_Service SHALL validate state transitions and business rules
3. WHEN search operations are performed, THE Labor_Service SHALL query the database and apply filters correctly
4. WHEN analytics are requested, THE Labor_Service SHALL calculate real metrics from stored data
5. WHEN notifications are triggered, THE Labor_Service SHALL integrate with notification service properly

### Requirement 6: Resolve Pydantic Schema Issues

**User Story:** As a developer, I want all Pydantic schemas to use modern v2 patterns, so that validation and serialization work correctly.

#### Acceptance Criteria

1. WHEN schemas are defined, THE Labor_Service SHALL use ConfigDict instead of class-based config
2. WHEN deprecated patterns are found, THE Labor_Service SHALL migrate to field_validator and model_validator
3. WHEN GenericModel is used, THE Labor_Service SHALL replace with BaseModel
4. WHEN validation errors occur, THE Labor_Service SHALL provide clear error messages
5. WHEN schemas are serialized, THE Labor_Service SHALL handle all field types correctly

### Requirement 7: Fix Code Quality Issues

**User Story:** As a developer, I want clean, maintainable code that follows best practices, so that the service is reliable and easy to maintain.

#### Acceptance Criteria

1. WHEN duplicate function definitions exist, THE Labor_Service SHALL remove redundant implementations
2. WHEN unused variables are present, THE Labor_Service SHALL clean up or utilize them appropriately
3. WHEN import statements are missing, THE Labor_Service SHALL add proper imports at file top
4. WHEN line length exceeds limits, THE Labor_Service SHALL format code to meet standards
5. WHEN files are missing newlines, THE Labor_Service SHALL add proper file endings
