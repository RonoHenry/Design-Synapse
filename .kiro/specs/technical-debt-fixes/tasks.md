mplementation Plan

## Current Status Summary
**MAJOR PROGRESS COMPLETED:**
- ✅ All SQLAlchemy models modernized to 2.0 patterns with Mapped types
- ✅ All Pydantic schemas updated to v2 with ConfigDict
- ✅ Configuration management modernized with Pydantic Settings v2
- ✅ Import structures cleaned up and circular dependencies resolved
- ✅ Database models have proper relationships and constraints
- ✅ URL validation regex pattern fixed in Resource model
- ✅ Comprehensive test infrastructure with factories and shared utilities
- ✅ User service has comprehensive error handling patterns
- ✅ Knowledge service has comprehensive error handling patterns
- ✅ Project service has basic error handling patterns (needs shared error integration)
- ✅ Project service schemas fully updated to Pydantic v2
- ✅ Dependencies updated to modern versions (SQLAlchemy 2.0.25+, Pydantic v2.5+)
- ✅ All services have Alembic migrations configured

**REMAINING WORK:**
- 🔄 Project service error handling integration with shared error classes
- 🔄 Service boundary enforcement (health checks missing in user/project services, /ready endpoints needed)
- 🔄 Inter-service HTTP communication infrastructure
- 🔄 Database migration validation and testing
- 🔄 Integration testing and validation
- 🔄 API documentation updates

**PRIORITY NEXT TASKS:** Focus on tasks 7.4 (Project Service Error Handling), 8.2 (Health Checks), 8.3 (Service Communication), and 9.x (Migration Validation)

---

- [x] 1. Foundation Setup and Dependency Updates





  - Update all requirements.txt files to modern versions (SQLAlchemy 2.0+, Pydantic v2, FastAPI latest)
  - Create unified configuration management base classes
  - Set up test infrastructure with database isolation
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [x] 1.1 Update User Service Dependencies



  - Modify apps/user-service/requirements.txt to use SQLAlchemy 2.0.25+, Pydantic v2.5+
  - Update imports in user service to use new Pydantic patterns
  - Test that user service starts without import errors
  - _Requirements: 5.1, 5.2, 5.3_


- [x] 1.2 Update Knowledge Service Dependencies

  - Modify apps/knowledge-service/requirements.txt to use SQLAlchemy 2.0.25+, Pydantic v2.5+
  - Update imports in knowledge service to use new patterns
  - Test that knowledge service starts without import errors
  - _Requirements: 5.1, 5.2, 5.3_


- [x] 1.3 Update Project Service Dependencies

  - Create apps/project-service/requirements.txt with SQLAlchemy 2.0.25+, Pydantic v2.5+
  - Update imports in project service to use new patterns
  - Test that project service starts without import errors
  - _Requirements: 5.1, 5.2, 5.3_

- [x] 2. Configuration Management Modernization






  - Create unified configuration classes using Pydantic Settings v2
  - Implement environment variable validation with clear error messages
  - Add configuration for Pinecone, LLM providers, and database connections
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [x] 2.1 Create Base Configuration Classes



  - Create shared configuration base classes in packages/common/config/
  - Implement DatabaseConfig, LLMConfig, VectorConfig classes with proper validation
  - Add environment-specific configuration loading with fallbacks
  - _Requirements: 3.1, 3.2, 3.3, 3.4_


- [x] 2.2 Update User Service Configuration

  - Replace src/core/config.py with new Pydantic Settings v2 patterns
  - Add proper environment variable validation for JWT settings
  - Update database configuration to use new patterns
  - _Requirements: 3.1, 3.3, 3.4_


- [x] 2.3 Update Knowledge Service Configuration

  - Create knowledge_service/core/config.py using new configuration patterns
  - Add Pinecone configuration with proper validation and error messages
  - Add LLM provider configuration with fallback mechanisms
  - _Requirements: 3.1, 3.2, 3.3, 3.4_

- [x] 2.4 Update Project Service Configuration


  - Create src/core/config.py using new configuration patterns
  - Add database configuration with connection pooling settings
  - Update project-specific settings to use new validation patterns
  - _Requirements: 3.1, 3.3, 3.4_

- [x] 3. Database Model Modernization





  - Migrate all SQLAlchemy models to 2.0 patterns with proper type hints
  - Fix Citation model foreign key constraints and cascade behavior
  - Update relationship definitions to use modern patterns
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6_

- [x] 3.1 Modernize User Service Models


  - Update apps/user-service/src/models/user.py to use SQLAlchemy 2.0 Mapped types
  - Update apps/user-service/src/models/role.py to use modern relationship patterns
  - Add proper type hints and validation to all model fields
  - _Requirements: 1.1, 1.2, 1.3, 1.6_



- [x] 3.2 Fix Knowledge Service Resource Model
  - Update apps/knowledge-service/knowledge_service/models/resource.py to use SQLAlchemy 2.0 patterns
  - Fix URL validation regex pattern that's currently broken
  - Add proper type hints using Mapped[Type] pattern
  - _Requirements: 1.1, 1.2, 1.3, 1.6_

- [x] 3.3 Fix Citation Model Foreign Key Constraints

  - Update Citation model in apps/knowledge-service/knowledge_service/models/resource.py
  - Add proper CASCADE delete constraints for resource relationships
  - Fix created_by field to have proper default value handling


  - Test cascade delete behavior with unit tests
  - _Requirements: 1.1, 1.2, 1.4, 1.5_

- [x] 3.4 Fix Bookmark Model Constraints


  - Update apps/knowledge-service/knowledge_service/models/bookmark.py to use SQLAlchemy 2.0 patterns
  - Ensure unique constraint and check constraint work properly
  - Add proper cascade delete relationship with Resource model
  - _Requirements: 1.1, 1.2, 1.4, 1.5_

- [x] 3.5 Modernize Project Service Models

  - Update apps/project-service/src/models/project.py to use SQLAlchemy 2.0 Mapped types
  - Update apps/project-service/src/models/comment.py to use modern patterns
  - Fix relationship definitions to use proper type hints
  - _Requirements: 1.1, 1.2, 1.3, 1.6_
-

- [x] 4. Import Structure Cleanup




  - Resolve circular import issues across all services
  - Standardize import patterns within each service
  - Update __init__.py files to properly expose public APIs
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

- [x] 4.1 Fix User Service Import Structure


  - Update apps/user-service/src/models/__init__.py to properly export models
  - Fix circular imports between user.py and role.py models
  - Update all service files to use consistent relative import patterns
  - _Requirements: 2.1, 2.2, 2.3, 2.4_

- [x] 4.2 Fix Knowledge Service Import Structure


  - Update knowledge_service/models/__init__.py to export models properly
  - Fix circular imports in knowledge_service/core/ modules
  - Reorganize imports to eliminate dependency cycles
  - _Requirements: 2.1, 2.2, 2.3, 2.4_


- [x] 4.3 Fix Project Service Import Structure


  - Create apps/project-service/src/models/__init__.py with proper exports
  - Fix imports in project and comment models
  - Update API route files to use consistent import patterns
  - _Requirements: 2.1, 2.2, 2.3, 2.4_

- [x] 5. Pydantic Schema Modernization

















  - Update all Pydantic schemas to v2 patterns
  - Add proper validation and serialization configuration
  - Update API endpoints to use new schema patterns
  - _Requirements: 5.2, 5.4, 1.6_


- [x] 5.1 Update User Service Schemas



  - Update apps/user-service/src/api/v1/schemas/ files to use Pydantic v2
  - Add model_config = ConfigDict(from_attributes=True) to all schemas
  - Update validation patterns to use v2 field validators
  - _Requirements: 5.2, 5.4, 1.6_

- [x] 5.2 Update Knowledge Service Schemas


  - Update apps/knowledge-service/knowledge_service/schemas.py to use Pydantic v2
  - Add proper validation for URL fields and file size constraints
  - Update API endpoints to use new schema patterns
  - _Requirements: 5.2, 5.4, 1.6_


- [x] 5.3 Update Project Service Schemas


  - Update apps/project-service/src/api/v1/schemas/ files to use Pydantic v2
  - Fix validation patterns for project status and name length
  - Add proper error handling for validation failures
  - _Requirements: 5.2, 5.4, 1.6_



- [x] 6. Test Infrastructure Enhancement
  - Enhance existing test infrastructure with factory patterns and shared utilities
  - Improve database isolation and test data creation
  - Add comprehensive model and API testing
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

- [x] 6.1 Create Shared Test Infrastructure
  - Create packages/common/testing/ with shared test utilities and base classes
  - Implement factory base classes using factory_boy for consistent test data creation across services
  - Create database isolation utilities that can be reused by all services
  - Add shared mock utilities for external services (LLM, vector search)
  - Create pytest plugins for common test patterns and fixtures
  - Add factory_boy to requirements.txt files for all services
  - _Requirements: 4.1, 4.2, 4.5_

- [x] 6.2 Enhance User Service Test Infrastructure
  - Create apps/user-service/tests/factories.py with UserFactory and RoleFactory using factory_boy
  - Enhance existing conftest.py with better database isolation and cleanup
  - Write comprehensive unit tests for User and Role models with 80%+ coverage
  - Add integration tests for authentication and role management endpoints
  - _Requirements: 4.1, 4.2, 4.3, 4.4_

- [x] 6.3 Enhance Knowledge Service Test Infrastructure
  - Create apps/knowledge-service/tests/factories.py for Resource, Citation, Bookmark, and Topic models
  - Enhance existing test infrastructure with better isolation and mock external services
  - Write comprehensive unit tests for model validation, relationships, and cascade behavior
  - Add integration tests for search and citation endpoints with proper mocking
  - _Requirements: 4.1, 4.2, 4.3, 4.4_

- [x] 6.4 Enhance Project Service Test Infrastructure
  - Create apps/project-service/tests/factories.py for Project and Comment models using factory_boy
  - Enhance existing test infrastructure with better isolation and async test support
  - Write comprehensive unit tests for project model validation and business logic
  - Add integration tests for project CRUD operations and comment functionality
  - _Requirements: 4.1, 4.2, 4.3, 4.4_

- [-] 7. Error Handling Standardization
  - Implement consistent error response formats across all services
  - Add proper database error handling with meaningful messages
  - Create error handling middleware for common patterns
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

- [x] 7.1 Create Shared Error Handling Classes
  - Create packages/common/errors/ with StandardErrorResponse classes and ErrorType enum
  - Implement error detail structures and validation error formatting
  - Add error handling decorators for common database operations and external service calls
  - Create base exception classes that can be extended by all services
  - Add FastAPI exception handlers that can be reused across services
  - _Requirements: 7.1, 7.2, 7.4_

- [x] 7.2 Update User Service Error Handling
  - Update apps/user-service/src/core/exceptions.py to use standard error patterns
  - Add database error handling to user creation and authentication
  - Update API endpoints to return consistent error responses
  - _Requirements: 7.1, 7.2, 7.3, 7.4_

- [x] 7.3 Update Knowledge Service Error Handling
  - Create knowledge_service/core/exceptions.py with standard error handling
  - Implement proper error responses for LLM service failures
  - Add validation error handling for resource creation and updates
  - _Requirements: 7.1, 7.2, 7.3, 7.4_

- [ ] 7.4 Update Project Service Error Handling



  - Migrate apps/project-service/src/core/exceptions.py to use shared error handling classes
  - Replace custom APIError, ProjectNotFoundError, and ProjectAccessError with shared error classes
  - Update main.py to use register_error_handlers from common.errors
  - Implement proper error responses for project validation failures using shared patterns
  - Add database constraint violation handling using shared database error utilities
  - Update all API endpoints to use shared error response formats
  - _Requirements: 7.1, 7.2, 7.3, 7.4_

- [-] 8. Service Boundary Enforcement
  - Remove direct database access between services
  - Implement proper API communication patterns
  - Add comprehensive service health checks and monitoring
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

- [x] 8.1 Audit and Remove Cross-Service Database Access
  - Audit all services for direct database access to other service databases
  - Replace direct database calls with HTTP API calls using proper DTOs
  - Update service dependencies to use API-based communication
  - _Requirements: 6.1, 6.2, 6.3_




- [ ] 8.2 Implement Comprehensive Service Health Checks
  - Add /health endpoint to user-service (basic endpoint returning service status)
  - Add /health endpoint to project-service (basic endpoint returning service status)
  - Enhance knowledge-service /health endpoint with database connection check
  - Add /ready endpoint to all three services that checks database connectivity
  - Add external service dependency health checks to knowledge-service /ready (Pinecone, OpenAI availability)
  - Implement health check response format with status, service name, version, and dependency checks
  - _Requirements: 6.4, 6.5_

- [x] 8.3 Create Service Communication Infrastructure



  - Create packages/common/http/ directory with HTTP client utilities for inter-service communication
  - Implement base HTTP client class with proper error handling and timeout configuration
  - Add retry mechanism with exponential backoff for transient failures
  - Implement circuit breaker pattern for external service calls to prevent cascade failures
  - Create service registry/configuration for API endpoint discovery (service URLs, ports)
  - Add request/response logging and tracing utilities for debugging inter-service calls
  - Create typed client classes for each service (UserServiceClient, ProjectServiceClient, KnowledgeServiceClient)
  - _Requirements: 6.1, 6.2, 6.4_

- [ ] 9. Database Migration Validation and Updates
  - Validate existing migrations work with modernized models
  - Create additional migrations if needed for recent model changes
  - Test migration rollback procedures
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

- [ ] 9.1 Validate User Service Migrations
  - Review existing Alembic migrations in apps/user-service/migrations/versions/
  - Test migrations against updated User and Role models with SQLAlchemy 2.0 Mapped types
  - Run alembic upgrade head on a test database and verify schema matches model definitions
  - Generate new migration if model changes (Mapped types, relationship patterns) require schema updates
  - Test migration rollback with alembic downgrade -1 to ensure reversibility
  - Create automated migration testing script that validates schema consistency
  - Test migrations with sample data to ensure no data loss or corruption
  - _Requirements: 1.1, 1.2, 1.3_

- [ ] 9.2 Validate Knowledge Service Migrations
  - Review existing Alembic migrations in apps/knowledge-service/migrations/versions/
  - Test migrations work with updated Resource, Citation, and Bookmark models (SQLAlchemy 2.0 patterns)
  - Verify CASCADE delete constraints are properly defined in migrations for Citation and Bookmark
  - Generate new migration if URL validation regex changes or relationship updates require schema changes
  - Test cascade delete behavior: delete a Resource and verify Citations and Bookmarks are removed
  - Validate that existing URLs in database still validate with updated regex pattern
  - Test migration rollback procedures to ensure safe downgrade path
  - _Requirements: 1.1, 1.2, 1.4, 1.5_

- [ ] 9.3 Validate Project Service Migrations
  - Review existing Alembic migrations in apps/project-service/migrations/versions/
  - Test migrations work with updated Project and Comment models (SQLAlchemy 2.0 Mapped types)
  - Verify foreign key constraints and CASCADE deletes are properly defined for Comment model
  - Generate new migration if model constraint changes (status enum, name length, etc.) require updates
  - Test that existing project data validates with new constraints (allowed_statuses, name length limits)
  - Create data migration script if needed to update existing data to meet new constraints
  - Test migration rollback to ensure safe downgrade without data loss
  - _Requirements: 1.1, 1.2, 1.3, 1.6_

- [ ] 10. Integration Testing and Validation
  - Run comprehensive integration tests across all services
  - Validate that all services start and communicate properly
  - Test error handling and recovery scenarios
  - _Requirements: 4.3, 4.4, 7.3, 7.4, 7.5_

- [ ] 10.1 Service Integration Testing
  - Create end-to-end integration test suite in tests/integration/ at workspace root
  - Test authentication flow: user login in user-service, token validation in other services
  - Test cross-service workflows: create project in project-service, add resources in knowledge-service
  - Verify service-to-service communication using HTTP clients (once 8.3 is complete)
  - Validate that error responses are consistent across all services (same format, status codes)
  - Test service startup and shutdown procedures for all three services
  - _Requirements: 4.3, 7.3, 7.4_

- [ ] 10.2 Database Integration Testing
  - Test all CRUD operations work correctly with SQLAlchemy 2.0 model patterns
  - Validate CASCADE delete behavior: delete Resource and verify Citations/Bookmarks removed
  - Validate CASCADE delete behavior: delete Project and verify Comments removed
  - Test foreign key constraint violations return proper error messages
  - Test database connection pooling under load (concurrent requests)
  - Test database error recovery: simulate connection loss and verify reconnection
  - Test transaction rollback scenarios for data integrity
  - _Requirements: 1.4, 1.5, 4.3, 4.4_

- [ ] 10.3 Configuration Validation Testing
  - Test each service starts successfully with valid configuration
  - Test services fail fast with clear error messages for missing required config (DB credentials, JWT secret)
  - Test knowledge-service with missing LLM API keys (should fail or use fallback)
  - Test knowledge-service with missing Pinecone config (should fail with clear message)
  - Test configuration validation for invalid values (negative pool_size, invalid JWT algorithm)
  - Test environment-specific configuration (development, testing, production modes)
  - Test fallback mechanisms: LLM provider fallback when primary fails
  - _Requirements: 3.4, 3.5, 7.3, 7.5_

- [ ] 11. API Documentation and Validation
  - Update OpenAPI documentation to reflect Pydantic v2 schema changes
  - Validate API documentation accuracy with automated tests
  - Update service README files with current API examples
  - _Requirements: 5.2, 5.4_

- [ ] 11.1 Update Service API Documentation
  - Verify OpenAPI specs are auto-generated correctly by FastAPI with Pydantic v2 schemas
  - Test OpenAPI documentation endpoints (/docs, /redoc) for all three services
  - Add example requests/responses to Pydantic schemas using Field(examples=[...])
  - Create or update README.md for each service with:
    - Service overview and purpose
    - Configuration requirements and environment variables
    - API endpoint documentation with curl examples
    - Development setup instructions
    - Testing instructions
  - Add API contract tests that validate responses match OpenAPI schema definitions
  - Document error response formats and status codes for each endpoint
  - _Requirements: 5.2, 5.4_