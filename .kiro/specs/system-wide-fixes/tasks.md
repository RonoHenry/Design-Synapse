# Implementation Plan: System-Wide Fixes

## Overview

This implementation plan addresses critical system-wide issues preventing proper testing and operation of the DesignSynapse microservices architecture. The tasks are organized to fix import paths, complete Pydantic v2 migration, repair test infrastructure, and ensure all services start properly.

## Tasks

- [x] 1. Fix Import Path Resolution
  - Configure consistent PYTHONPATH across all services
  - Update pytest configuration files
  - Add workspace root to Python path in service startup
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

- [x] 1.1 Update Workspace Root pytest Configuration
  - Fix `pytest.ini` in workspace root to include proper Python path
  - Add packages directory to pytest path configuration
  - Ensure test collection works from workspace root
  - _Requirements: 1.2, 3.1_

- [x] 1.2 Write property test for import resolution
  - **Property 1: Import resolution works consistently**
  - **Validates: Requirements 1.1, 1.2, 1.3**

- [x] 1.3 Update Service-Level pytest Configuration
  - Fix `pytest.ini` files in each service directory
  - Add workspace root path resolution to service test configurations
  - Remove duplicate configuration entries
  - _Requirements: 1.1, 1.2, 6.4_

- [x] 1.4 Write property test for service test execution
  - **Property 4: Test collection succeeds**
  - **Validates: Requirements 3.1, 3.2**

- [-] 2. Complete Pydantic v2 Migration
  - Update all Pydantic v1 patterns to v2 in labor service
  - Replace GenericModel with BaseModel
  - Update class-based config to ConfigDict
  - Remove deprecated json_encoders usage
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

- [x] 2.1 Fix Labor Service Base Schemas
  - Update `apps/labor-service/src/api/v1/schemas/base.py`
  - Replace `from pydantic.generics import GenericModel` with `from pydantic import BaseModel`
  - Convert all class-based Config to `model_config = ConfigDict(...)`
  - Remove deprecated json_encoders usage
  - _Requirements: 2.1, 2.2, 2.4_

- [-] 2.2 Write property test for Pydantic v2 compliance
  - **Property 2: Pydantic schemas use modern patterns**
  - **Validates: Requirements 2.1, 2.2**

- [x] 2.3 Fix Labor Service Request/Response Schemas
  - Update `apps/labor-service/src/api/v1/schemas/booking.py`
  - Update `apps/labor-service/src/api/v1/schemas/quote.py`
  - Update `apps/labor-service/src/api/v1/schemas/request.py`
  - Update `apps/labor-service/src/api/v1/schemas/review.py`
  - Convert all class-based Config to ConfigDict patterns
  - _Requirements: 2.1, 2.2, 2.3_

- [ ] 2.4 Write property test for deprecation warnings
  - **Property 3: System runs without deprecation warnings**
  - **Validates: Requirements 2.5**

- [ ] 3. Fix Test Infrastructure Issues
  - Fix syntax errors in test files
  - Add missing dependencies for test execution
  - Repair async test function definitions
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [x] 3.1 Fix Database Integration Test Syntax Error
  - Fix `tests/integration/test_database_integration.py` line 88
  - Add proper `@pytest.mark.asyncio` decorator to async test functions
  - Ensure all async functions are properly defined within async test methods
  - _Requirements: 3.1, 3.2_

- [x] 3.2 Fix User Service Configuration Duplicate Entry
  - Fix `apps/user-service/setup.cfg` line 14 duplicate `extend-ignore`
  - Remove duplicate configuration entries
  - Validate configuration file syntax
  - _Requirements: 6.4_

- [ ] 3.3 Write property test for configuration validity
  - **Property 8: Configuration files are valid**
  - **Validates: Requirements 6.4**

- [ ] 4. Add Missing Dependencies
  - Install required packages for database and test operations
  - Update requirements files with missing dependencies
  - Ensure version compatibility across services
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

- [x] 4.1 Add Database Driver Dependencies
  - Add `asyncpg>=0.28.0` to `requirements-dev.txt`
  - Add `psycopg2-binary>=2.9.0` for synchronous database operations
  - Update service-specific requirements.txt files as needed
  - _Requirements: 4.1, 4.4_

- [x] 4.2 Add Test Infrastructure Dependencies
  - Add `testcontainers>=3.7.0` to `requirements-dev.txt`
  - Add `pytest-asyncio>=0.21.0` for async test support
  - Add `pytest-timeout>=2.1.0` for test timeout handling
  - _Requirements: 4.2, 4.4_

- [ ] 4.3 Write property test for dependency availability
  - **Property 5: Required dependencies are available**
  - **Validates: Requirements 4.1, 4.2**

- [ ] 5. Validate Service Startup and Health
  - Ensure all services can start without errors
  - Validate health endpoint functionality
  - Test configuration loading across services
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [ ] 5.1 Test Service Startup Procedures
  - Validate user-service starts without import errors
  - Validate knowledge-service starts with proper configuration
  - Validate labor-service starts after Pydantic fixes
  - Validate project-service starts with database connectivity
  - _Requirements: 5.1, 5.3_

- [ ] 5.2 Write property test for service startup
  - **Property 6: Services start successfully**
  - **Validates: Requirements 5.1**

- [ ] 5.3 Validate Health Endpoint Functionality
  - Test `/health` endpoints across all services
  - Test `/ready` endpoints with dependency checks
  - Ensure consistent health response formats
  - _Requirements: 5.4_

- [ ] 5.4 Write property test for health endpoints
  - **Property 7: Health endpoints function properly**
  - **Validates: Requirements 5.4**

- [ ] 6. Checkpoint - Validate All Fixes
  - Run comprehensive tests across all services
  - Verify no import errors or deprecation warnings
  - Ensure all integration tests can execute
  - _Requirements: All requirements_

- [ ] 6.1 Run Comprehensive Test Suite
  - Execute `python -m pytest tests/ -v` from workspace root
  - Execute service-specific tests from each service directory
  - Verify no collection errors or syntax issues
  - _Requirements: 3.1, 3.2, 7.1_

- [ ] 6.2 Write property test for integration test execution
  - **Property 9: Integration tests execute properly**
  - **Validates: Requirements 7.1**

- [ ] 6.3 Validate System-Wide Health
  - Start all services and verify no startup errors
  - Check for Pydantic deprecation warnings during startup
  - Validate import resolution works from all service contexts
  - Test health endpoints return proper responses
  - _Requirements: 1.1, 2.5, 5.1, 5.4_

- [ ] 7. Final Validation and Documentation
  - Document all fixes applied
  - Update service README files with corrected setup instructions
  - Validate complete system functionality
  - _Requirements: All requirements_

- [ ] 7.1 Update Service Documentation
  - Update README.md files with corrected import path setup
  - Document Pydantic v2 migration changes
  - Add troubleshooting guide for common import issues
  - _Requirements: 1.1, 2.1_

- [ ] 7.2 Create System Health Validation Script
  - Create script to validate all services can start
  - Add checks for import resolution and dependency availability
  - Include health endpoint validation
  - _Requirements: 5.1, 5.4, 4.1_

## Notes

- Each task references specific requirements for traceability
- Checkpoint tasks ensure incremental validation of fixes
- Property tests validate universal correctness properties
- Focus on fixing critical blocking issues first (imports, syntax errors, dependencies)
- Pydantic migration should eliminate all 57+ deprecation warnings in labor service
