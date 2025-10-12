# Implementation Plan

## Overview
This implementation plan follows Test-Driven Development (TDD) principles. Each task involves writing tests first, then implementing the functionality to make tests pass. Tasks are ordered to build incrementally, ensuring each step is tested and integrated before moving forward.

## Phase 1: Foundation and Infrastructure

- [x] 1. Set up project structure and dependencies






  - Create apps/design-service directory structure (src/, tests/, migrations/)
  - Create requirements.txt with FastAPI, SQLAlchemy 2.0, Pydantic v2, pytest, factory-boy
  - Set up __init__.py files for proper package structure
  - Create main.py with basic FastAPI app initialization
  - _Requirements: 10.5_

- [x] 2. Configure database and migrations






  - [x] 2.1 Create database configuration


    - Create src/core/config.py using packages.common.config patterns
    - Add DesignServiceConfig class with database, LLM, and service URL settings
    - Write unit tests for configuration validation and environment variable loading
    - _Requirements: 9.1, 9.2_



  - [x] 2.2 Set up database infrastructure






    - Create src/infrastructure/database.py with Base and get_db dependency
    - Configure SQLAlchemy engine with TiDB connection string
    - Write tests for database connection and session management



    - _Requirements: 10.5_

  - [ ] 2.3 Initialize Alembic migrations
    - Run alembic init migrations in apps/design-service
    - Update alembic.ini with mysql+pymysql connection string
    - Update migrations/env.py to import Base and use async if needed
    - Test migration configuration with alembic check
    - _Requirements: 2.2_

- [ ] 3. Create shared test infrastructure
  - Create tests/conftest.py with database fixtures (test_db, db_session)
  - Create tests/factories.py with base factory setup
  - Add mock fixtures for external services (LLM client, user service, project service)
  - Write tests to verify test infrastructure works correctly
  - _Requirements: 10.1, 10.2_

## Phase 2: Core Data Models (TDD)

- [ ] 4. Implement Design model
  - [ ] 4.1 Write Design model tests
    - Create tests/unit/models/test_design.py
    - Write tests for Design model creation with required fields
    - Write tests for field validation (name length, status values, version)
    - Write tests for JSON specification field storage and retrieval
    - Write tests for version control (parent_design_id relationship)
    - _Requirements: 2.1, 2.2_

  - [ ] 4.2 Implement Design model
    - Create src/models/design.py with Design class using SQLAlchemy 2.0 Mapped types
    - Implement all fields: id, project_id, name, description, specification, metadata
    - Add version control fields: version, parent_design_id
    - Add audit fields: created_by, created_at, updated_at
    - Implement __init__ with validation for status and name length
    - Run tests to verify implementation
    - _Requirements: 2.1, 2.2_


- [ ] 5. Implement DesignValidation model
  - [ ] 5.1 Write DesignValidation model tests
    - Create tests/unit/models/test_design_validation.py
    - Write tests for DesignValidation creation with design relationship
    - Write tests for CASCADE delete (delete design, verify validations deleted)
    - Write tests for violations and warnings JSON field storage
    - Write tests for is_compliant flag logic
    - _Requirements: 3.1, 3.2, 3.3_

  - [ ] 5.2 Implement DesignValidation model
    - Create DesignValidation class in src/models/design_validation.py
    - Implement fields: id, design_id, validation_type, rule_set, is_compliant
    - Add violations and warnings JSON fields
    - Add relationship to Design with CASCADE delete
    - Run tests to verify implementation
    - _Requirements: 3.1, 3.2, 3.3_

- [ ] 6. Implement DesignOptimization model
  - [ ] 6.1 Write DesignOptimization model tests
    - Create tests/unit/models/test_design_optimization.py
    - Write tests for DesignOptimization creation and relationships
    - Write tests for CASCADE delete behavior
    - Write tests for status transitions (suggested -> applied/rejected)
    - Write tests for cost impact and difficulty validation
    - _Requirements: 4.1, 4.2, 4.3_

  - [ ] 6.2 Implement DesignOptimization model
    - Create DesignOptimization class in src/models/design_optimization.py
    - Implement fields: id, design_id, optimization_type, title, description
    - Add impact fields: estimated_cost_impact, implementation_difficulty, priority
    - Add status tracking: status, applied_at, applied_by
    - Add relationship to Design with CASCADE delete
    - Run tests to verify implementation
    - _Requirements: 4.1, 4.2, 4.3_

- [ ] 7. Implement DesignFile model
  - [ ] 7.1 Write DesignFile model tests
    - Create tests/unit/models/test_design_file.py
    - Write tests for DesignFile creation with file metadata
    - Write tests for file type validation (PDF, DWG, DXF, PNG, JPG, IFC)
    - Write tests for file size validation (max 50MB)
    - Write tests for CASCADE delete with design
    - _Requirements: 6.1, 6.2, 6.3_

  - [ ] 7.2 Implement DesignFile model
    - Create DesignFile class in src/models/design_file.py
    - Implement fields: id, design_id, filename, file_type, file_size, storage_path
    - Add validation for file_type (allowed formats)
    - Add validation for file_size (max 50MB = 52428800 bytes)
    - Add relationship to Design with CASCADE delete
    - Run tests to verify implementation
    - _Requirements: 6.1, 6.2, 6.3_

- [ ] 8. Implement DesignComment model
  - [ ] 8.1 Write DesignComment model tests
    - Create tests/unit/models/test_design_comment.py
    - Write tests for DesignComment creation with content
    - Write tests for optional spatial positioning (x, y, z coordinates)
    - Write tests for is_edited flag when comment is updated
    - Write tests for CASCADE delete with design
    - _Requirements: 7.1, 7.2, 7.3_

  - [ ] 8.2 Implement DesignComment model
    - Create DesignComment class in src/models/design_comment.py
    - Implement fields: id, design_id, content, position_x, position_y, position_z
    - Add audit fields: created_by, created_at, updated_at, is_edited
    - Add relationship to Design with CASCADE delete
    - Run tests to verify implementation
    - _Requirements: 7.1, 7.2, 7.3_

- [ ] 9. Create model factories for testing
  - Create DesignFactory in tests/factories.py using factory_boy
  - Create DesignValidationFactory with design relationship
  - Create DesignOptimizationFactory with design relationship
  - Create DesignFileFactory with design relationship
  - Create DesignCommentFactory with design relationship
  - Write tests to verify all factories create valid model instances
  - _Requirements: 10.1_

- [ ] 10. Generate and test initial database migration
  - Run alembic revision --autogenerate -m "Initial design service schema"
  - Review generated migration for correctness (indexes, constraints, CASCADE)
  - Test migration: alembic upgrade head on test database
  - Verify all tables created with correct schema
  - Test migration rollback: alembic downgrade -1
  - _Requirements: 2.2_

## Phase 3: Pydantic Schemas (TDD)

- [ ] 11. Implement request schemas
  - [ ] 11.1 Write request schema tests
    - Create tests/unit/schemas/test_requests.py
    - Write tests for DesignGenerationRequest validation (required fields, field types)
    - Write tests for DesignUpdateRequest with optional fields
    - Write tests for ValidationRequest with validation_type and rule_set
    - Write tests for OptimizationRequest with optimization_types list
    - Write tests for invalid data (missing fields, wrong types, out of range values)
    - _Requirements: 1.1, 1.2, 3.1, 4.1_

  - [ ] 11.2 Implement request schemas
    - Create src/api/v1/schemas/requests.py
    - Implement DesignGenerationRequest with Field validators
    - Implement DesignUpdateRequest with optional fields
    - Implement ValidationRequest schema
    - Implement OptimizationRequest schema
    - Add model_config = ConfigDict(from_attributes=True) to all schemas
    - Run tests to verify validation works correctly
    - _Requirements: 1.1, 1.2, 3.1, 4.1_

- [ ] 12. Implement response schemas
  - [ ] 12.1 Write response schema tests
    - Create tests/unit/schemas/test_responses.py
    - Write tests for DesignResponse serialization from Design model
    - Write tests for ValidationResponse serialization
    - Write tests for OptimizationResponse serialization
    - Write tests for DesignFileResponse and DesignCommentResponse
    - Write tests for nested relationships (design with validations)
    - _Requirements: 2.1, 3.1, 4.1, 6.1, 7.1_

  - [ ] 12.2 Implement response schemas
    - Create src/api/v1/schemas/responses.py
    - Implement DesignResponse with all design fields
    - Implement ValidationResponse schema
    - Implement OptimizationResponse schema
    - Implement DesignFileResponse and DesignCommentResponse
    - Add model_config for ORM mode
    - Run tests to verify serialization works correctly
    - _Requirements: 2.1, 3.1, 4.1, 6.1, 7.1_

## Phase 4: Repository Layer (TDD)

- [ ] 13. Implement DesignRepository
  - [ ] 13.1 Write DesignRepository tests
    - Create tests/unit/repositories/test_design_repository.py
    - Write tests for create_design (save and return design)
    - Write tests for get_design_by_id (found and not found cases)
    - Write tests for update_design (update fields and return updated design)
    - Write tests for delete_design (soft delete by setting is_archived)
    - Write tests for list_designs with filters (project_id, building_type, status)
    - Write tests for get_design_versions (return all versions of a design)
    - _Requirements: 2.1, 2.2, 2.5, 2.6_

  - [ ] 13.2 Implement DesignRepository
    - Create src/repositories/design_repository.py
    - Implement create_design method
    - Implement get_design_by_id with error handling
    - Implement update_design method
    - Implement delete_design (set is_archived=True)
    - Implement list_designs with filtering and pagination
    - Implement get_design_versions method
    - Run tests to verify all CRUD operations work
    - _Requirements: 2.1, 2.2, 2.5, 2.6_

- [ ] 14. Implement ValidationRepository
  - [ ] 14.1 Write ValidationRepository tests
    - Create tests/unit/repositories/test_validation_repository.py
    - Write tests for create_validation
    - Write tests for get_validations_by_design_id
    - Write tests for get_latest_validation for a design
    - _Requirements: 3.1, 3.2_

  - [ ] 14.2 Implement ValidationRepository
    - Create src/repositories/validation_repository.py
    - Implement create_validation method
    - Implement get_validations_by_design_id
    - Implement get_latest_validation method
    - Run tests to verify implementation
    - _Requirements: 3.1, 3.2_

- [ ] 15. Implement OptimizationRepository
  - [ ] 15.1 Write OptimizationRepository tests
    - Create tests/unit/repositories/test_optimization_repository.py
    - Write tests for create_optimization
    - Write tests for get_optimizations_by_design_id
    - Write tests for update_optimization_status (apply/reject)
    - _Requirements: 4.1, 4.2, 4.5_

  - [ ] 15.2 Implement OptimizationRepository
    - Create src/repositories/optimization_repository.py
    - Implement create_optimization method
    - Implement get_optimizations_by_design_id
    - Implement update_optimization_status method
    - Run tests to verify implementation
    - _Requirements: 4.1, 4.2, 4.5_

## Phase 5: External Service Clients (TDD)

- [ ] 16. Implement LLM client for design generation
  - [ ] 16.1 Write LLM client tests
    - Create tests/unit/services/test_llm_client.py
    - Write tests for generate_design_specification (mock OpenAI response)
    - Write tests for generate_optimizations (mock OpenAI response)
    - Write tests for fallback mechanism when primary model fails
    - Write tests for timeout handling (60 second timeout)
    - Write tests for token usage tracking
    - _Requirements: 1.1, 1.4, 4.1, 9.1, 9.2, 9.3, 9.4_

  - [ ] 16.2 Implement LLM client
    - Create src/services/llm_client.py
    - Implement generate_design_specification using OpenAI API
    - Implement generate_optimizations method
    - Add fallback logic (try primary model, then fallback model)
    - Add timeout handling with 60 second limit
    - Add token usage logging
    - Use packages.common.config.LLMConfig for configuration
    - Run tests with mocked OpenAI client
    - _Requirements: 1.1, 1.4, 4.1, 9.1, 9.2, 9.3, 9.4_

- [ ] 17. Implement project service client
  - [ ] 17.1 Write project service client tests
    - Create tests/unit/services/test_project_client.py
    - Write tests for verify_project_access (user is member)
    - Write tests for verify_project_access (user not member, raises error)
    - Write tests for get_project_details
    - Write tests for HTTP error handling and retries
    - _Requirements: 2.4, 7.6_

  - [ ] 17.2 Implement project service client
    - Create src/services/project_client.py using packages.common.http.BaseHTTPClient
    - Implement verify_project_access method (GET /api/v1/projects/{id}/members/{user_id})
    - Implement get_project_details method
    - Add error handling for 404, 403, 500 responses
    - Add retry logic with exponential backoff
    - Run tests with mocked HTTP responses
    - _Requirements: 2.4, 7.6_

## Phase 6: Business Logic Services (TDD)

- [ ] 18. Implement DesignGeneratorService
  - [ ] 18.1 Write DesignGeneratorService tests
    - Create tests/unit/services/test_design_generator.py
    - Write tests for generate_design (happy path with valid request)
    - Write tests for generate_design with project access denied
    - Write tests for generate_design with LLM failure
    - Write tests for create_design_version (creates new version with parent_design_id)
    - Write tests for confidence score calculation
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 2.5_

  - [ ] 18.2 Implement DesignGeneratorService
    - Create src/services/design_generator.py
    - Implement generate_design method:
      - Verify project access via project_client
      - Build AI prompt from request
      - Call LLM client to generate specification
      - Parse and validate LLM response
      - Create Design entity with specification
      - Save via design_repository
    - Implement create_design_version method
    - Add confidence score calculation logic
    - Run tests to verify business logic
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 2.5_

- [ ] 19. Implement ValidationService
  - [ ] 19.1 Write ValidationService tests
    - Create tests/unit/services/test_validation_service.py
    - Write tests for validate_design (compliant design)
    - Write tests for validate_design (design with violations)
    - Write tests for validate_design (design with warnings only)
    - Write tests for rule set loading and parsing
    - Write tests for validation completion within 10 seconds
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_

  - [ ] 19.2 Implement ValidationService
    - Create src/services/validation_service.py
    - Implement validate_design method:
      - Load rule set configuration from config/building_codes
      - Extract design parameters from specification
      - Run validation rules
      - Collect violations and warnings
      - Create DesignValidation entity
      - Update design status based on validation result
    - Implement rule engine for building code checks
    - Add performance optimization to complete within 10 seconds
    - Run tests to verify validation logic
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_

- [ ] 20. Implement OptimizationService
  - [ ] 20.1 Write OptimizationService tests
    - Create tests/unit/services/test_optimization_service.py
    - Write tests for generate_optimizations (returns at least 3 suggestions)
    - Write tests for generate_optimizations with no optimizations found
    - Write tests for apply_optimization (creates new design version)
    - Write tests for optimization completion within 20 seconds
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6_

  - [ ] 20.2 Implement OptimizationService
    - Create src/services/optimization_service.py
    - Implement generate_optimizations method:
      - Analyze design specification
      - Build optimization prompt for LLM
      - Call LLM for each optimization type
      - Parse suggestions
      - Create DesignOptimization entities
    - Implement apply_optimization method (creates new design version)
    - Add performance optimization to complete within 20 seconds
    - Run tests to verify optimization logic
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6_

## Phase 7: API Endpoints (TDD)

- [ ] 21. Implement design CRUD endpoints
  - [ ] 21.1 Write design endpoint tests
    - Create tests/integration/api/v1/test_designs.py
    - Write tests for POST /api/v1/designs (create design)
    - Write tests for GET /api/v1/designs/{id} (get design)
    - Write tests for PUT /api/v1/designs/{id} (update design)
    - Write tests for DELETE /api/v1/designs/{id} (soft delete)
    - Write tests for GET /api/v1/designs (list with filters)
    - Write tests for authentication required (401 without token)
    - Write tests for authorization (403 if not project member)
    - _Requirements: 1.1, 2.1, 2.2, 2.3, 2.4, 2.5_

  - [ ] 21.2 Implement design endpoints
    - Create src/api/v1/routes/designs.py
    - Implement POST /api/v1/designs endpoint
    - Implement GET /api/v1/designs/{id} endpoint
    - Implement PUT /api/v1/designs/{id} endpoint
    - Implement DELETE /api/v1/designs/{id} endpoint
    - Implement GET /api/v1/designs endpoint with filters
    - Add authentication dependency (JWT token validation)
    - Add authorization checks (project membership)
    - Use shared error handlers from packages.common.errors
    - Run integration tests to verify endpoints
    - _Requirements: 1.1, 2.1, 2.2, 2.3, 2.4, 2.5_

- [ ] 22. Implement validation endpoints
  - [ ] 22.1 Write validation endpoint tests
    - Create tests/integration/api/v1/test_validations.py
    - Write tests for POST /api/v1/designs/{id}/validate
    - Write tests for GET /api/v1/designs/{id}/validations
    - Write tests for validation with invalid rule set (404)
    - Write tests for validation without design access (403)
    - _Requirements: 3.1, 3.2, 3.3, 3.4_

  - [ ] 22.2 Implement validation endpoints
    - Create src/api/v1/routes/validations.py
    - Implement POST /api/v1/designs/{id}/validate endpoint
    - Implement GET /api/v1/designs/{id}/validations endpoint
    - Add error handling for invalid rule sets
    - Add authorization checks
    - Run integration tests
    - _Requirements: 3.1, 3.2, 3.3, 3.4_

- [ ] 23. Implement optimization endpoints
  - [ ] 23.1 Write optimization endpoint tests
    - Create tests/integration/api/v1/test_optimizations.py
    - Write tests for POST /api/v1/designs/{id}/optimize
    - Write tests for GET /api/v1/designs/{id}/optimizations
    - Write tests for POST /api/v1/optimizations/{id}/apply
    - Write tests for applying already applied optimization (400)
    - _Requirements: 4.1, 4.2, 4.5_

  - [ ] 23.2 Implement optimization endpoints
    - Create src/api/v1/routes/optimizations.py
    - Implement POST /api/v1/designs/{id}/optimize endpoint
    - Implement GET /api/v1/designs/{id}/optimizations endpoint
    - Implement POST /api/v1/optimizations/{id}/apply endpoint
    - Add validation for optimization status
    - Run integration tests
    - _Requirements: 4.1, 4.2, 4.5_

- [ ] 24. Implement file management endpoints
  - [ ] 24.1 Write file endpoint tests
    - Create tests/integration/api/v1/test_files.py
    - Write tests for POST /api/v1/designs/{id}/files (upload)
    - Write tests for GET /api/v1/designs/{id}/files (list)
    - Write tests for DELETE /api/v1/files/{id}
    - Write tests for GET /api/v1/files/{id}/download
    - Write tests for file size limit (50MB max)
    - Write tests for unsupported file type (400)
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

  - [ ] 24.2 Implement file endpoints
    - Create src/api/v1/routes/files.py
    - Implement POST /api/v1/designs/{id}/files endpoint with file upload
    - Implement GET /api/v1/designs/{id}/files endpoint
    - Implement DELETE /api/v1/files/{id} endpoint
    - Implement GET /api/v1/files/{id}/download endpoint with streaming
    - Add file type validation (PDF, DWG, DXF, PNG, JPG, IFC)
    - Add file size validation (max 50MB)
    - Implement file storage (local or S3 based on config)
    - Run integration tests
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

- [ ] 25. Implement comment endpoints
  - [ ] 25.1 Write comment endpoint tests
    - Create tests/integration/api/v1/test_comments.py
    - Write tests for POST /api/v1/designs/{id}/comments
    - Write tests for GET /api/v1/designs/{id}/comments
    - Write tests for PUT /api/v1/comments/{id} (update own comment)
    - Write tests for DELETE /api/v1/comments/{id} (delete own comment)
    - Write tests for updating other user's comment (403)
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6_

  - [ ] 25.2 Implement comment endpoints
    - Create src/api/v1/routes/comments.py
    - Implement POST /api/v1/designs/{id}/comments endpoint
    - Implement GET /api/v1/designs/{id}/comments endpoint
    - Implement PUT /api/v1/comments/{id} endpoint (owner only)
    - Implement DELETE /api/v1/comments/{id} endpoint (owner only)
    - Add authorization checks (comment owner or admin)
    - Run integration tests
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6_

- [ ] 26. Implement export endpoint
  - [ ] 26.1 Write export endpoint tests
    - Create tests/integration/api/v1/test_export.py
    - Write tests for POST /api/v1/designs/{id}/export (JSON format)
    - Write tests for POST /api/v1/designs/{id}/export (PDF format)
    - Write tests for POST /api/v1/designs/{id}/export (IFC format)
    - Write tests for export completion within 15 seconds
    - Write tests for unsupported format (400)
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6_

  - [ ] 26.2 Implement export endpoint
    - Create src/api/v1/routes/export.py
    - Implement POST /api/v1/designs/{id}/export endpoint
    - Add JSON export (full design data)
    - Add PDF export (formatted document generation)
    - Add IFC export (Building Information Model)
    - Add format validation
    - Optimize to complete within 15 seconds
    - Run integration tests
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6_

## Phase 8: Service Integration and Health Checks

- [ ] 27. Implement health and readiness endpoints
  - [ ] 27.1 Write health check tests
    - Create tests/integration/test_health.py
    - Write tests for GET /health (returns service status)
    - Write tests for GET /ready (checks database connectivity)
    - Write tests for GET /ready (checks AI service availability)
    - Write tests for /ready when database is down (returns unhealthy)
    - _Requirements: 10.5_

  - [ ] 27.2 Implement health endpoints
    - Add GET /health endpoint to main.py
    - Add GET /ready endpoint with database health check
    - Use packages.common.database.health.check_database_health
    - Add AI service availability check
    - Return appropriate status codes (200 healthy, 503 unhealthy)
    - Run integration tests
    - _Requirements: 10.5_

- [ ] 28. Implement error handling middleware
  - Register error handlers from packages.common.errors in main.py
  - Add custom exception handlers for DesignServiceError
  - Add validation error handler for Pydantic ValidationError
  - Add database error handler for SQLAlchemy errors
  - Test error responses follow standard format
  - _Requirements: 1.5, 3.5, 6.5, 8.5_

- [ ] 29. Add API documentation
  - Configure OpenAPI documentation in main.py
  - Add description and version information
  - Add example requests/responses to schemas using Field(examples=[...])
  - Test /docs endpoint returns Swagger UI
  - Test /redoc endpoint returns ReDoc UI
  - _Requirements: 8.1, 8.2, 8.3_

## Phase 9: Performance and Security

- [ ] 30. Implement database indexing and optimization
  - Add indexes to Design model (project_id, created_by, status, building_type)
  - Configure connection pooling (pool_size=10, max_overflow=20)
  - Add database query optimization (eager loading for relationships)
  - Test query performance with large datasets
  - _Requirements: 10.1, 10.2_

- [ ] 31. Implement caching
  - Add caching for building code rules (in-memory cache)
  - Add caching for frequently accessed designs (Redis optional)
  - Implement cache invalidation on design updates
  - Test cache hit/miss scenarios
  - _Requirements: 10.4_

- [ ] 32. Implement pagination
  - Add pagination to GET /api/v1/designs endpoint (limit=50, offset)
  - Add pagination to comment and validation list endpoints
  - Add pagination metadata to responses (total, page, per_page)
  - Test pagination with large datasets
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [ ] 33. Add authentication and authorization
  - Implement JWT token validation dependency
  - Add user_id extraction from JWT token
  - Implement project membership verification
  - Add role-based access control (admin can access all designs)
  - Test authentication failures (401)
  - Test authorization failures (403)
  - _Requirements: 2.4, 7.6_

## Phase 10: Testing and Documentation

- [ ] 34. Run comprehensive test suite
  - Run all unit tests: pytest apps/design-service/tests/unit -v
  - Run all integration tests: pytest apps/design-service/tests/integration -v
  - Verify test coverage is above 85%
  - Fix any failing tests
  - _Requirements: 10.1, 10.2_

- [ ] 35. Create service README
  - Create apps/design-service/README.md
  - Document service purpose and features
  - Add setup instructions (dependencies, environment variables)
  - Add API endpoint documentation with examples
  - Add testing instructions
  - Document building code configuration
  - _Requirements: 8.1, 8.2, 8.3_

- [ ] 36. Create building code configuration
  - Create config/building_codes directory
  - Create Kenya_Building_Code_2020.json with sample rules
  - Document rule format and structure
  - Add validation for rule configuration files
  - Test rule loading and parsing
  - _Requirements: 3.1, 3.6_

- [ ] 37. Final integration testing
  - Test complete design generation workflow end-to-end
  - Test design validation workflow
  - Test optimization workflow
  - Test file upload and download
  - Test comment collaboration
  - Test export functionality
  - Verify all requirements are met
  - _Requirements: All_

## Notes

- Each task should be completed with tests passing before moving to the next
- Use TDD: Write tests first, then implement functionality
- Follow existing patterns from user-service, project-service, knowledge-service
- Use shared packages (common.config, common.errors, common.testing, common.http)
- Ensure all database operations use SQLAlchemy 2.0 patterns
- Ensure all schemas use Pydantic v2 patterns
- Run tests frequently during development
- Commit after each completed task
