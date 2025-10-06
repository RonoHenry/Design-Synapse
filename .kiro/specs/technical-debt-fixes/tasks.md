# Implementation Plan

## Current Status Summary
**MAJOR PROGRESS COMPLETED:**
- ✅ All SQLAlchemy models modernized to 2.0 patterns with Mapped types
- ✅ All Pydantic schemas updated to v2 with ConfigDict
- ✅ Configuration management modernized with Pydantic Settings v2
- ✅ Import structures cleaned up and circular dependencies resolved
- ✅ Database models have proper relationships and constraints
- ✅ URL validation regex pattern fixed in Resource model
- ✅ Basic test infrastructure exists with proper database isolation
- ✅ User service has comprehensive error handling patterns
- ✅ Project service has basic error handling patterns
- ✅ Project service schemas fully updated to Pydantic v2
- ✅ Dependencies updated to modern versions (SQLAlchemy 2.0.25+, Pydantic v2.5+)

**REMAINING WORK:**
- 🔄 Test infrastructure enhancement (factories, shared utilities)
- 🔄 Error handling standardization (knowledge service missing exceptions.py)
- 🔄 Service boundary enforcement (health checks missing in user/project services)
- 🔄 Database migration validation and testing
- 🔄 Integration testing and validation

**PRIORITY NEXT TASKS:** Focus on tasks 6.1-6.4 (Test Infrastructure) and 7.1, 7.3 (Knowledge Service Error Handling)

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



- [ ] 6. Test Infrastructure Enhancement









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

- [ ] 6.4 Enhance Project Service Test Infrastructure
  - Create apps/project-service/tests/factories.py for Project and Comment models using factory_boy
  - Enhance existing test infrastructure with better isolation and async test support
  - Write comprehensive unit tests for project model validation and business logic
  - Add integration tests for project CRUD operations and comment functionality
  - _Requirements: 4.1, 4.2, 4.3, 4.4_

- [ ] 7. Error Handling Standardization
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
  - Create apps/project-service/src/core/exceptions.py with standard error handling
  - Implement proper error responses for project validation failures
  - Add database constraint violation handling
  - _Requirements: 7.1, 7.2, 7.3, 7.4_

- [ ] 8. Service Boundary Enforcement
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
  - Add health check endpoints to user-service and project-service (/health, /ready)
  - Enhance knowledge-service health checks with database and external service checks (basic /health exists)
  - Implement database connection health checks for all services
  - Add external service dependency health checks (Pinecone, OpenAI)
  - Add /ready endpoint that checks all dependencies are available
  - _Requirements: 6.4, 6.5_

- [ ] 8.3 Create Service Communication Infrastructure
  - Create packages/common/http/ with HTTP client utilities for inter-service communication
  - Implement proper retry and timeout mechanisms for service calls
  - Add circuit breaker patterns for external service calls
  - Create service discovery and configuration for API endpoints
  - _Requirements: 6.1, 6.2, 6.4_

- [ ] 9. Database Migration Validation and Updates
  - Validate existing migrations work with modernized models
  - Create additional migrations if needed for recent model changes
  - Test migration rollback procedures
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

- [ ] 9.1 Validate User Service Migrations
  - Test existing Alembic migrations work with updated User and Role models
  - Generate additional migrations if model changes require them
  - Test migrations on sample data to ensure no data loss
  - Validate rollback procedures work correctly
  - Create migration testing script to validate schema consistency
  - _Requirements: 1.1, 1.2, 1.3_

- [ ] 9.2 Validate Knowledge Service Migrations
  - Test existing migrations work with updated Resource, Citation, and Bookmark models
  - Generate additional migrations for any new constraints or relationships
  - Test cascade delete behavior with existing data
  - Validate that URL regex fixes don't break existing URLs
  - _Requirements: 1.1, 1.2, 1.4, 1.5_

- [ ] 9.3 Validate Project Service Migrations
  - Test existing migrations work with updated Project and Comment models
  - Generate additional migrations if needed for constraint changes
  - Test that existing project data validates with new constraints
  - Create data migration scripts if needed for constraint changes
  - _Requirements: 1.1, 1.2, 1.3, 1.6_

- [ ] 10. Integration Testing and Validation
  - Run comprehensive integration tests across all services
  - Validate that all services start and communicate properly
  - Test error handling and recovery scenarios
  - _Requirements: 4.3, 4.4, 7.3, 7.4, 7.5_

- [ ] 10.1 Service Integration Testing
  - Create integration tests that verify service-to-service communication
  - Test authentication flow across services
  - Validate that error responses are consistent across services
  - _Requirements: 4.3, 7.3, 7.4_

- [ ] 10.2 Database Integration Testing
  - Test that all database operations work with new model constraints
  - Validate cascade delete behavior in realistic scenarios
  - Test database connection pooling and error recovery
  - _Requirements: 1.4, 1.5, 4.3, 4.4_

- [ ] 10.3 Configuration Validation Testing
  - Test all services with various configuration scenarios
  - Validate error messages for missing or invalid configuration
  - Test fallback mechanisms for external service failures
  - _Requirements: 3.4, 3.5, 7.3, 7.5_

- [ ] 11. API Documentation and Validation
  - Update OpenAPI documentation to reflect Pydantic v2 schema changes
  - Validate API documentation accuracy with automated tests
  - Update service README files with current API examples
  - _Requirements: 5.2, 5.4_

- [ ] 11.1 Update Service API Documentation
  - Regenerate OpenAPI specs for all services with updated schemas
  - Add example requests/responses using new validation patterns
  - Update service-specific documentation with configuration examples
  - Test API documentation accuracy with contract testing
  - _Requirements: 5.2, 5.4_