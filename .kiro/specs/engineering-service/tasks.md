# Engineering Service - Implementation Tasks

## Overview

This task list implements the Engineering Service following Test-Driven Development (TDD) methodology. Each task includes unit tests and property-based tests to ensure correctness.

**Implementation Language:** Python with FastAPI framework (as specified in the design document)

## Quick Start Guide for Developers

### Current State
- **Foundation Complete:** Models, schemas, repositories, calculation engines all created
- **Tests Created:** 544 tests exist but many implementations are incomplete
- **Coverage:** ~50% overall (target: 80%+)
- **Next Steps:** Complete calculation engines → Complete repositories → Complete services → Build API

### Where to Start

#### Option 1: Complete Calculation Engines (Recommended First)
**Why:** Tests exist but implementations are incomplete (28-50% coverage)
**Files:** `src/calculations/*.py`
**Tests:** `tests/unit/calculations/test_*.py`
**Action:** Run tests, fix failures, achieve 80%+ coverage

#### Option 2: Complete Repository Layer
**Why:** Tests exist but implementations are incomplete (17-45% coverage)
**Files:** `src/repositories/*_repository.py`
**Tests:** `tests/unit/repositories/test_*_repository.py`
**Action:** Run tests, implement missing CRUD operations, achieve 80%+ coverage

#### Option 3: Complete Service Layer
**Why:** Service classes started but methods not implemented (0% coverage)
**Files:** `src/services/*_service.py`
**Tests:** Need to be written (marked with * in task list)
**Action:** Implement service methods, write tests, achieve 80%+ coverage

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/unit/calculations/test_beam_designer.py

# Run with coverage
pytest --cov=src --cov-report=term-missing

# Run only failing tests
pytest --lf

# Run property tests only
pytest -m property
```

### Development Workflow

1. **Pick a task** from the list below (start with incomplete implementations)
2. **Run the tests** for that component
3. **Fix failures** by completing the implementation
4. **Verify coverage** reaches 80%+
5. **Move to next task**

---

---

## Detailed File Status

### Calculation Engines (src/calculations/)
| File | Status | Coverage | Action Needed |
|------|--------|----------|---------------|
| `load_calculator.py` | ⚠️ Incomplete | ~40% | Complete dead/live/wind/seismic load methods |
| `beam_designer.py` | ⚠️ Incomplete | ~38% | Complete beam design calculations |
| `column_designer.py` | ⚠️ Incomplete | ~44% | Complete column design and buckling |
| `foundation_designer.py` | ⚠️ Incomplete | ~42% | Complete foundation bearing capacity |
| `hvac_calculator.py` | ⚠️ Incomplete | ~50% | Complete heating/cooling load calculations |
| `electrical_calculator.py` | ⚠️ Incomplete | ~45% | Complete load/panel/circuit sizing |
| `plumbing_calculator.py` | ⚠️ Incomplete | ~28% | Complete fixture units and pipe sizing |
| `fire_protection_calculator.py` | ⚠️ Incomplete | ~35% | Complete sprinkler demand calculations |
| `civil_calculator.py` | ⚠️ Incomplete | ~40% | Complete grading and stormwater |

### Repositories (src/repositories/)
| File | Status | Coverage | Action Needed |
|------|--------|----------|---------------|
| `calculation_sheet_repository.py` | ⚠️ Incomplete | ~25% | Complete CRUD operations |
| `structural_design_repository.py` | ⚠️ Incomplete | ~17% | Complete CRUD operations |
| `mep_design_repository.py` | ⚠️ Incomplete | ~20% | Complete CRUD operations |
| `civil_design_repository.py` | ⚠️ Incomplete | ~22% | Complete CRUD operations |
| `compliance_report_repository.py` | ⚠️ Incomplete | ~30% | Complete CRUD operations |
| `audit_log_repository.py` | ⚠️ Incomplete | ~45% | Complete query operations |

### Services (src/services/)
| File | Status | Coverage | Action Needed |
|------|--------|----------|---------------|
| `structural_calculation_service.py` | ⚠️ Started | 0% | Implement all methods |
| `mep_calculation_service.py` | ❌ Not Created | 0% | Create and implement |
| `civil_calculation_service.py` | ❌ Not Created | 0% | Create and implement |
| `document_service.py` | ❌ Not Created | 0% | Create and implement |
| `code_validator_service.py` | ❌ Not Created | 0% | Create and implement |

### Integration Clients (src/integrations/)
| File | Status | Coverage | Action Needed |
|------|--------|----------|---------------|
| `architectural_service_client.py` | ❌ Not Created | 0% | Create and implement |
| `design_service_client.py` | ❌ Not Created | 0% | Create and implement |
| `knowledge_service_client.py` | ❌ Not Created | 0% | Create and implement |
| `project_service_client.py` | ❌ Not Created | 0% | Create and implement |

### API Routes (src/api/v1/routes/)
| File | Status | Coverage | Action Needed |
|------|--------|----------|---------------|
| `structural.py` | ❌ Not Created | 0% | Create 7 endpoints |
| `mep.py` | ❌ Not Created | 0% | Create 7 endpoints |
| `civil.py` | ❌ Not Created | 0% | Create 6 endpoints |
| `compliance.py` | ❌ Not Created | 0% | Create 3 endpoints |
| `documents.py` | ❌ Not Created | 0% | Create 6 endpoints |
| `health.py` | ❌ Not Created | 0% | Create health check endpoints |

### Validators (src/validators/)
| File | Status | Coverage | Action Needed |
|------|--------|----------|---------------|
| `structural_validator.py` | ❌ Not Created | 0% | Create IBC/ASCE 7 validators |
| `mep_validator.py` | ❌ Not Created | 0% | Create NEC/IPC/IMC/NFPA validators |
| `energy_validator.py` | ❌ Not Created | 0% | Create IECC/ASHRAE validators |

---

## Current Implementation Status

### Phase 1: Foundation (Complete ✅)
**Tasks 1-8 Complete:**
- ✅ Project infrastructure and configuration
- ✅ Database models (CalculationSheet, StructuralDesign, MEPDesign, CivilDesign, ComplianceReport, AuditLog)
- ✅ Pydantic schemas for all request/response types
- ✅ Repository layer with CRUD operations
- ✅ Unit conversion system with round-trip property tests
- ✅ Structural calculation engines (LoadCalculator, BeamDesigner, ColumnDesigner, FoundationDesigner)
- ✅ MEP calculation engines (HVACCalculator, ElectricalCalculator, PlumbingCalculator, FireProtectionCalculator)
- ✅ Civil calculation engines (grading, stormwater, utilities)
- ✅ Property-based tests for all calculation engines
- ✅ 544 tests created

**Test Coverage Analysis:**
- Overall: ~50% coverage
- Models: Well-tested with property tests
- Repositories: Tests exist but implementations incomplete (17-45% coverage)
- Calculation engines: Tests exist but implementations incomplete (28-50% coverage)
- Services: Structural service started but not implemented (0% coverage)

### Phase 2: Service Layer (In Progress ⚠️)
**Task 9 - Structural Service (Partially Complete):**
- ✅ Service class structure created
- ✅ LoadCalculationResult model defined
- ⚠️ calculate_loads method exists but not implemented
- ⚠️ design_beam method exists but not implemented
- ❌ design_column method not implemented
- ❌ design_foundation method not implemented
- ❌ Automatic recalculation logic not implemented
- ❌ Unit tests not passing (0% coverage)
- ❌ Property tests not implemented

**Tasks 10-11 - MEP and Civil Services (Not Started):**
- ❌ No MEP service implementation
- ❌ No Civil service implementation

### Phase 3: Core Business Services (Not Started ❌)
**Task 13 - Document Management:**
- ❌ DocumentService not created
- ❌ Versioning logic not implemented
- ❌ Search functionality not implemented

**Task 14 - Code Compliance:**
- ❌ CodeValidatorService not created
- ❌ No validators directory content
- ❌ No integration with Knowledge Service

### Phase 4: Integration Layer (Not Started ❌)
**Task 16 - External Service Clients:**
- ❌ integrations directory is empty
- ❌ No client implementations for Architectural, Design, Knowledge, Project services
- ❌ No retry logic or circuit breakers

**Task 17 - Authentication:**
- ❌ No auth middleware
- ❌ No RBAC implementation

### Phase 5: API Layer (Not Started ❌)
**Tasks 18-22 - API Endpoints:**
- ❌ routes directory is empty
- ❌ No structural endpoints
- ❌ No MEP endpoints
- ❌ No civil endpoints
- ❌ No compliance endpoints
- ❌ No document endpoints

### Phase 6: Cross-Cutting Concerns (Not Started ❌)
**Tasks 23-27:**
- ❌ No audit logging implementation
- ❌ No input validation beyond Pydantic
- ❌ No caching implementation
- ❌ No health check endpoints

### Phase 7: Testing & Deployment (Not Started ❌)
**Tasks 28-30:**
- ❌ No integration tests
- ❌ No API documentation
- ❌ No deployment configuration

---

## Critical Path Forward

### Immediate Priority: Complete Service Layer Foundation

**Why this matters:** The service layer is the bridge between calculation engines and API endpoints. Without complete service implementations, API endpoints cannot function properly.

### Recommended Implementation Order:

#### Stage 1: Complete Calculation Engine Implementations (1-2 days)
**Goal:** Bring calculation engine coverage from 28-50% to 80%+

The tests exist but implementations are incomplete. Focus on:
1. Review failing tests in `tests/unit/calculations/`
2. Complete implementation for each calculator
3. Ensure all unit tests pass
4. Verify property tests pass

**Files to complete:**
- `src/calculations/load_calculator.py`
- `src/calculations/beam_designer.py`
- `src/calculations/column_designer.py`
- `src/calculations/foundation_designer.py`
- `src/calculations/hvac_calculator.py`
- `src/calculations/electrical_calculator.py`
- `src/calculations/plumbing_calculator.py`
- `src/calculations/fire_protection_calculator.py`
- `src/calculations/civil_calculator.py`

#### Stage 2: Complete Repository Implementations (1 day)
**Goal:** Bring repository coverage from 17-45% to 80%+

The tests exist but implementations are incomplete. Focus on:
1. Review failing tests in `tests/unit/repositories/`
2. Complete CRUD operations for each repository
3. Ensure all unit tests pass

**Files to complete:**
- `src/repositories/calculation_sheet_repository.py`
- `src/repositories/structural_design_repository.py`
- `src/repositories/mep_design_repository.py`
- `src/repositories/civil_design_repository.py`
- `src/repositories/compliance_report_repository.py`
- `src/repositories/audit_log_repository.py`

#### Stage 3: Complete Service Layer (2-3 days)
**Goal:** Implement all three service layers with 80%+ coverage

**Task 9: Structural Service**
- Implement calculate_loads (integrate LoadCalculator)
- Implement design_beam (integrate BeamDesigner)
- Implement design_column (integrate ColumnDesigner)
- Implement design_foundation (integrate FoundationDesigner)
- Add automatic recalculation logic
- Write unit tests
- Write property test for calculation dependencies

**Task 10: MEP Service**
- Create MEPCalculationService class
- Implement design_hvac_system
- Implement design_electrical_system
- Implement design_plumbing_system
- Implement design_fire_protection
- Add automatic system updates
- Write unit tests
- Write property test for MEP system updates

**Task 11: Civil Service**
- Create CivilCalculationService class
- Implement design_grading
- Implement design_stormwater
- Implement design_utilities
- Write unit tests
- Write property test for civil design validity

#### Stage 4: Core Business Services (2-3 days)
**Goal:** Enable document management and code compliance

**Task 13: Document Management**
- Create DocumentService class
- Implement create_calculation_sheet with versioning
- Implement update_calculation_sheet with version control
- Implement get_document_history
- Implement generate_specification (CSI MasterFormat)
- Implement document search
- Write unit tests
- Write property test for document versioning

**Task 14: Code Compliance**
- Create CodeValidatorService class
- Implement validate_structural_code (IBC, ASCE 7)
- Implement validate_mep_code (NEC, IPC, IMC, NFPA)
- Implement validate_energy_code (IECC, ASHRAE 90.1)
- Implement code requirement retrieval from Knowledge Service
- Implement compliance report generation
- Write unit tests
- Write property tests for compliance checks and violation reporting

#### Stage 5: Integration & Auth (2-3 days)
**Goal:** Enable external service communication and security

**Task 16: External Service Clients**
- Create ArchitecturalServiceClient
- Create DesignServiceClient
- Create KnowledgeServiceClient
- Create ProjectServiceClient
- Add retry logic with exponential backoff
- Add circuit breaker pattern
- Add response caching
- Write unit tests with mocked responses
- Write property test for integration resilience

**Task 17: Authentication & Authorization**
- Implement JWT token validation middleware
- Implement RBAC (role-based access control)
- Implement project membership verification
- Add permission checks for engineering operations
- Write unit tests
- Write integration tests for protected endpoints

#### Stage 6: API Endpoints (3-4 days)
**Goal:** Expose all functionality via REST API

Can be done in parallel once services are complete:
- **Task 18:** Structural endpoints (7 endpoints)
- **Task 19:** MEP endpoints (7 endpoints)
- **Task 20:** Civil endpoints (6 endpoints)
- **Task 21:** Compliance endpoints (3 endpoints)
- **Task 22:** Document endpoints (6 endpoints)

Each task includes API integration tests.

#### Stage 7: Cross-Cutting Concerns (2-3 days)
**Goal:** Production-ready features

Can be done in parallel with API endpoints:
- **Task 24:** Audit logging for all operations
- **Task 25:** Input validation and error handling
- **Task 26:** Caching and performance optimization
- **Task 27:** Health checks and monitoring

#### Stage 8: Testing & Deployment (2-3 days)
**Goal:** End-to-end validation and deployment readiness

- **Task 28:** Integration tests for complete workflows
- **Task 29:** API documentation and usage examples
- **Task 30:** Deployment configuration (Docker, CI/CD)

---

## Key Success Metrics

### Coverage Targets:
- **Calculation engines:** 80%+ (currently 28-50%)
- **Repositories:** 80%+ (currently 17-45%)
- **Services:** 80%+ (currently 0%)
- **API endpoints:** 80%+
- **Overall:** 80%+

### Quality Gates:
- All unit tests passing
- All property tests passing (100+ iterations each)
- All integration tests passing
- No critical security vulnerabilities
- API documentation complete

---

## Notes for Implementation

### Test-Driven Development (TDD) Approach:
1. **Red:** Write failing test first
2. **Green:** Write minimal code to pass test
3. **Refactor:** Improve code while keeping tests green

### Property-Based Testing Guidelines:
- Use Hypothesis for all property tests
- Minimum 100 iterations per property test
- Test universal properties, not specific examples
- Focus on invariants that must always hold

### Code Quality Standards:
- Follow async/await patterns for all I/O
- Use Pydantic v2 for all schemas
- Ensure TiDB/MySQL compatibility
- Implement proper transaction management
- Add comprehensive logging
- Follow FastAPI best practices

### Integration Patterns:
- Use circuit breakers for external services
- Implement exponential backoff for retries
- Cache external service responses
- Handle service unavailability gracefully

---

## Estimated Timeline

**Total: 15-20 days of focused development**

- Stage 1 (Calculations): 1-2 days
- Stage 2 (Repositories): 1 day
- Stage 3 (Services): 2-3 days
- Stage 4 (Business Services): 2-3 days
- Stage 5 (Integration & Auth): 2-3 days
- Stage 6 (API Endpoints): 3-4 days
- Stage 7 (Cross-Cutting): 2-3 days
- Stage 8 (Testing & Deployment): 2-3 days

**Recommendation:** Start with Stage 1 (completing calculation engines) as this unblocks all subsequent work.

## Task List

- [x] 1. Project Setup and Infrastructure
  - [x] 1.1 Initialize FastAPI project structure
  - [x] 1.2 Configure TiDB/MySQL database connection
  - [x] 1.3 Set up Alembic for database migrations
  - [x] 1.4 Configure Pytest with Hypothesis for property-based testing
  - [x] 1.5 Set up Redis for caching
  - [x] 1.6 Configure logging and monitoring
  - [x] 1.7 Create base configuration management

- [x] 2. Database Models and Schemas
  - [x] 2.1 Create CalculationSheet model with tests
  - [x] 2.2 Create StructuralDesign model with tests
  - [x] 2.3 Create MEPDesign model with tests
  - [x] 2.4 Create CivilDesign model with tests
  - [x] 2.5 Create ComplianceReport model with tests
  - [x] 2.6 Create AuditLog model with tests
  - [x] 2.7 Generate and test initial database migration
  - [x] 2.8 Write property test for data persistence round-trip (Property 12)

- [x] 3. Pydantic Request/Response Schemas
  - [x] 3.1 Create structural calculation request/response schemas
  - [x] 3.2 Create MEP design request/response schemas
  - [x] 3.3 Create civil engineering request/response schemas
  - [x] 3.4 Create code validation request/response schemas
  - [x] 3.5 Create document management schemas
  - [x] 3.6 Add schema validation tests

- [x] 4. Repository Layer
  - [x] 4.1 Create CalculationSheetRepository with CRUD operations
  - [x] 4.2 Create StructuralDesignRepository with CRUD operations
  - [x] 4.3 Create MEPDesignRepository with CRUD operations
  - [x] 4.4 Create CivilDesignRepository with CRUD operations
  - [x] 4.5 Create ComplianceReportRepository with CRUD operations
  - [x] 4.6 Create AuditLogRepository with query operations
  - [x] 4.7 Write unit tests for all repository operations
    - Note: Tests complete, implementation has 17-45% coverage - needs completion

- [x] 5. Unit Conversion System
  - [x] 5.1 Implement UnitConverter class
  - [x] 5.2 Add Imperial to Metric conversion methods
  - [x] 5.3 Add Metric to Imperial conversion methods
  - [x] 5.4 Add unit formatting methods
  - [x] 5.5 Write unit tests for conversions
  - [x] 5.6 Write property test for conversion round-trip (Property 7)

- [x] 6. Structural Engineering Calculations
  - [x] 6.1 Implement LoadCalculator for dead loads
  - [x] 6.2 Implement LoadCalculator for live loads (ASCE 7)
  - [x] 6.3 Implement LoadCalculator for wind loads (ASCE 7)
  - [x] 6.4 Implement LoadCalculator for seismic loads (ASCE 7)
  - [x] 6.5 Implement beam design calculations
  - [x] 6.6 Implement column design calculations
  - [x] 6.7 Implement foundation design calculations
  - [x] 6.8 Write unit tests for all structural calculations
  - [x] 6.9 Write property test for load calculation reasonableness (Property 1)
  - [x] 6.10 Write property test for structural design validity (Property 2)
    - Note: Tests complete, implementation has 38-44% coverage - needs completion

- [x] 7. MEP Systems Calculations
  - [x] 7.1 Implement HVACCalculator for heating loads (ASHRAE)
  - [x] 7.2 Implement HVACCalculator for cooling loads (ASHRAE)
  - [x] 7.3 Implement HVACCalculator for equipment sizing
  - [x] 7.4 Implement ElectricalCalculator for load calculations
  - [x] 7.5 Implement ElectricalCalculator for panel sizing (NEC)
  - [x] 7.6 Implement ElectricalCalculator for circuit sizing (NEC)
  - [x] 7.7 Implement PlumbingCalculator for fixture units (IPC)
  - [x] 7.8 Implement PlumbingCalculator for pipe sizing
  - [x] 7.9 Implement FireProtectionCalculator (NFPA 13)
  - [x] 7.10 Write unit tests for all MEP calculations
  - [x] 7.11 Write property test for MEP system sizing (Property 3)
    - Note: Tests complete, implementation has 28-50% coverage - needs completion

- [x] 8. Civil Engineering Calculations
  - [x] 8.1 Implement grading design with cut/fill calculations
  - [x] 8.2 Implement stormwater runoff calculations
  - [x] 8.3 Implement detention pond sizing
  - [x] 8.4 Implement utility load calculations
  - [x] 8.5 Write unit tests for civil calculations
  - [x] 8.6 Write property test for cut/fill volume conservation (Property 4)

- [x] 9. Structural Engineering Service Layer
  - [x] 9.1 Complete StructuralCalculationService.calculate_loads implementation
    - Integrate LoadCalculator with service layer
    - Create and persist CalculationSheet records
    - Handle unit system conversions
    - Service class exists but methods need full implementation
    - _Requirements: 1.1, 4.1_
  - [x] 9.2 Complete StructuralCalculationService.design_beam implementation
    - Integrate BeamDesigner with service layer
    - Create and persist StructuralDesign records
    - Link to calculation sheets
    - Service method exists but needs completion
    - _Requirements: 1.2, 4.1_
  - [x] 9.3 Implement StructuralCalculationService.design_column
    - Integrate ColumnDesigner with service layer
    - Create and persist StructuralDesign records
    - Handle buckling analysis results
    - _Requirements: 1.3, 4.1_
  - [x] 9.4 Implement StructuralCalculationService.design_foundation
    - Integrate FoundationDesigner with service layer
    - Create and persist StructuralDesign records
    - Handle bearing capacity and settlement results
    - _Requirements: 1.4, 4.1_
  - [x] 9.5 Add automatic recalculation on input changes
    - Implement dependency tracking between calculations
    - Trigger recalculation cascade on updates
    - Update all dependent calculation sheets
    - _Requirements: 1.6_
  - [x] 9.6 Write unit tests for all service methods
    - Test calculate_loads with mocked LoadCalculator and repository
    - Test design_beam with mocked BeamDesigner and repository
    - Test design_column with mocked ColumnDesigner and repository
    - Test design_foundation with mocked FoundationDesigner and repository
    - Test automatic recalculation logic
    - _Requirements: 1.1-1.7_
  - [ ] 9.7 Write property test for calculation dependency updates (Property 5)
    - **Property 5: Calculation Dependency Updates**
    - **Validates: Requirements 1.6**
    - Test that changing input A triggers recalculation of dependent calculation B

- [-] 10. MEP Engineering Service Layer
  - [ ] 10.1 Implement MEPCalculationService.design_hvac_system
    - Integrate HVACCalculator with service layer
    - Add calculation sheet creation
    - _Requirements: 2.1, 4.1_
  - [ ] 10.2 Implement MEPCalculationService.design_electrical_system
    - Integrate ElectricalCalculator with service layer
    - Add calculation sheet creation
    - _Requirements: 2.2, 4.1_
  - [ ] 10.3 Implement MEPCalculationService.design_plumbing_system
    - Integrate PlumbingCalculator with service layer
    - Add calculation sheet creation
    - _Requirements: 2.3, 4.1_
  - [ ] 10.4 Implement MEPCalculationService.design_fire_protection
    - Integrate FireProtectionCalculator with service layer
    - Add calculation sheet creation
    - _Requirements: 2.4, 4.1_
  - [ ] 10.5 Add automatic system updates on parameter changes
    - Implement parameter change detection
    - Trigger system recalculation
    - _Requirements: 2.6_
  - [ ]* 10.6 Write unit tests for service methods
    - Test all MEP service methods
    - _Requirements: 2.1-2.6_
  - [ ]* 10.7 Write property test for MEP system updates (Property 6)
    - **Property 6: MEP System Updates**
    - **Validates: Requirements 2.6**

- [ ] 11. Civil Engineering Service Layer
  - [ ] 11.1 Implement CivilCalculationService.design_grading
    - Integrate grading calculations with service layer
    - Add calculation sheet creation
    - _Requirements: 3.1, 4.1_
  - [ ] 11.2 Implement CivilCalculationService.design_stormwater
    - Integrate stormwater calculations with service layer
    - Add calculation sheet creation
    - _Requirements: 3.2, 4.1_
  - [ ] 11.3 Implement CivilCalculationService.design_utilities
    - Integrate utility calculations with service layer
    - Add calculation sheet creation
    - _Requirements: 3.3, 4.1_
  - [ ]* 11.4 Write unit tests for service methods
    - Test all civil service methods
    - _Requirements: 3.1-3.4_
  - [ ]* 11.5 Write property test for civil design validity (Property 7)
    - **Property 7: Civil Design Validity**
    - **Validates: Requirements 3.4**

- [ ] 12. Checkpoint - Service Layer Complete
  - Ensure all service layer tests pass
  - Verify all calculation engines are integrated
  - Ask the user if questions arise

- [ ] 13. Document Management Service
  - [ ] 13.1 Implement DocumentService.create_calculation_sheet
    - Create versioned calculation sheets
    - Associate with projects and disciplines
    - _Requirements: 4.1, 4.5_
  - [ ] 13.2 Implement DocumentService.update_calculation_sheet with versioning
    - Create new versions on updates
    - Preserve previous versions
    - _Requirements: 4.2_
  - [ ] 13.3 Implement DocumentService.get_document_history
    - Return all versions with change summaries
    - _Requirements: 4.3_
  - [ ] 13.4 Implement DocumentService.generate_specification (CSI MasterFormat)
    - Format specifications per CSI standards
    - _Requirements: 4.4_
  - [ ] 13.5 Implement document search functionality
    - Filter by project, discipline, type, date range
    - _Requirements: 4.6_
  - [ ]* 13.6 Write unit tests for document operations
    - Test all document service methods
    - _Requirements: 4.1-4.6_
  - [ ]* 13.7 Write property test for document versioning (Property 10)
    - **Property 10: Document Versioning**
    - **Validates: Requirements 4.2, 4.3**

- [ ] 14. Code Compliance Validation
  - [ ] 14.1 Implement CodeValidatorService.validate_structural_code (IBC, ASCE 7)
    - Check structural code compliance
    - Generate violation reports
    - _Requirements: 5.1, 5.4, 5.5_
  - [ ] 14.2 Implement CodeValidatorService.validate_mep_code (NEC, IPC, IMC, NFPA)
    - Check MEP code compliance
    - Generate violation reports
    - _Requirements: 5.2, 5.4, 5.5_
  - [ ] 14.3 Implement CodeValidatorService.validate_energy_code (IECC, ASHRAE 90.1)
    - Check energy code compliance
    - Generate violation reports
    - _Requirements: 5.3, 5.4, 5.5_
  - [ ] 14.4 Implement code requirement retrieval from Knowledge Service
    - Fetch latest code versions
    - Cache code requirements
    - _Requirements: 5.6_
  - [ ] 14.5 Implement compliance report generation
    - Format reports with code references
    - Include recommended corrections
    - _Requirements: 5.4, 5.5_
  - [ ]* 14.6 Write unit tests for validation logic
    - Test all validation methods
    - _Requirements: 5.1-5.6_
  - [ ]* 14.7 Write property test for code compliance checks (Property 8)
    - **Property 8: Code Compliance Checks**
    - **Validates: Requirements 5.1-5.3**
  - [ ]* 14.8 Write property test for violation reporting (Property 9)
    - **Property 9: Violation Reporting**
    - **Validates: Requirements 5.5**

- [ ] 15. Checkpoint - Core Services Complete
  - Ensure all core service tests pass
  - Verify document management and code validation work
  - Ask the user if questions arise

- [ ] 16. External Service Integration Clients
  - [ ] 16.1 Implement ArchitecturalServiceClient
    - Get architectural designs
    - Subscribe to design changes
    - _Requirements: 6.1_
  - [ ] 16.2 Implement DesignServiceClient
    - Update technical requirements
    - Get technical drawings
    - _Requirements: 6.2_
  - [ ] 16.3 Implement KnowledgeServiceClient
    - Retrieve engineering standards
    - Search formulas and references
    - _Requirements: 6.3_
  - [ ] 16.4 Implement ProjectServiceClient
    - Update milestone status
    - Get project information
    - _Requirements: 6.4_
  - [ ] 16.5 Add retry logic with exponential backoff
    - Implement retry decorator
    - Configure backoff parameters
    - _Requirements: 6.5_
  - [ ] 16.6 Add circuit breaker pattern
    - Implement circuit breaker for each client
    - Configure failure thresholds
    - _Requirements: 6.5_
  - [ ] 16.7 Add response caching
    - Cache external service responses
    - Implement cache invalidation
    - _Requirements: 6.6_
  - [ ]* 16.8 Write unit tests with mocked responses
    - Test all client methods
    - _Requirements: 6.1-6.4_
  - [ ]* 16.9 Write property test for integration resilience (Property 11)
    - **Property 11: Integration Resilience**
    - **Validates: Requirements 6.5, 6.6**

- [ ] 17. Authentication and Authorization
  - [ ] 17.1 Implement JWT token validation middleware
    - Validate tokens from User Service
    - Extract user information
    - _Requirements: 10.1_
  - [ ] 17.2 Implement role-based access control (RBAC)
    - Verify engineer role permissions
    - Check document modification permissions
    - _Requirements: 10.2, 10.3_
  - [ ] 17.3 Implement project membership verification
    - Verify user-project associations
    - _Requirements: 10.4_
  - [ ] 17.4 Add permission checks for engineering operations
    - Protect all sensitive endpoints
    - Return appropriate error responses
    - _Requirements: 10.5, 10.6_
  - [ ]* 17.5 Write unit tests for auth/authz logic
    - Test authentication and authorization
    - _Requirements: 10.1-10.6_
  - [ ]* 17.6 Write integration tests for protected endpoints
    - Test endpoint protection
    - _Requirements: 10.1-10.6_

- [ ] 18. API Endpoints - Structural Engineering
  - [ ] 18.1 POST /api/v1/structural/loads - Calculate loads
    - Implement endpoint with request validation
    - Return load calculation results
    - _Requirements: 1.1, 8.1_
  - [ ] 18.2 POST /api/v1/structural/beams - Design beam
    - Implement endpoint with request validation
    - Return beam design results
    - _Requirements: 1.2, 8.1_
  - [ ] 18.3 POST /api/v1/structural/columns - Design column
    - Implement endpoint with request validation
    - Return column design results
    - _Requirements: 1.3, 8.1_
  - [ ] 18.4 POST /api/v1/structural/foundations - Design foundation
    - Implement endpoint with request validation
    - Return foundation design results
    - _Requirements: 1.4, 8.1_
  - [ ] 18.5 GET /api/v1/structural/designs/{id} - Get design
    - Retrieve structural design by ID
    - _Requirements: 4.1_
  - [ ] 18.6 PUT /api/v1/structural/designs/{id} - Update design
    - Update existing design with versioning
    - _Requirements: 4.2_
  - [ ] 18.7 DELETE /api/v1/structural/designs/{id} - Delete design
    - Soft delete design
    - _Requirements: 4.1_
  - [ ]* 18.8 Write API integration tests
    - Test all structural endpoints
    - _Requirements: 1.1-1.7_

- [ ] 19. API Endpoints - MEP Engineering
  - [ ] 19.1 POST /api/v1/mep/hvac - Design HVAC system
    - Implement endpoint with request validation
    - Return HVAC design results
    - _Requirements: 2.1, 8.1_
  - [ ] 19.2 POST /api/v1/mep/electrical - Design electrical system
    - Implement endpoint with request validation
    - Return electrical design results
    - _Requirements: 2.2, 8.1_
  - [ ] 19.3 POST /api/v1/mep/plumbing - Design plumbing system
    - Implement endpoint with request validation
    - Return plumbing design results
    - _Requirements: 2.3, 8.1_
  - [ ] 19.4 POST /api/v1/mep/fire-protection - Design fire protection
    - Implement endpoint with request validation
    - Return fire protection design results
    - _Requirements: 2.4, 8.1_
  - [ ] 19.5 GET /api/v1/mep/designs/{id} - Get design
    - Retrieve MEP design by ID
    - _Requirements: 4.1_
  - [ ] 19.6 PUT /api/v1/mep/designs/{id} - Update design
    - Update existing design with versioning
    - _Requirements: 4.2_
  - [ ] 19.7 DELETE /api/v1/mep/designs/{id} - Delete design
    - Soft delete design
    - _Requirements: 4.1_
  - [ ]* 19.8 Write API integration tests
    - Test all MEP endpoints
    - _Requirements: 2.1-2.6_

- [ ] 20. API Endpoints - Civil Engineering
  - [ ] 20.1 POST /api/v1/civil/grading - Design grading
    - Implement endpoint with request validation
    - Return grading design results
    - _Requirements: 3.1, 8.1_
  - [ ] 20.2 POST /api/v1/civil/stormwater - Design stormwater
    - Implement endpoint with request validation
    - Return stormwater design results
    - _Requirements: 3.2, 8.1_
  - [ ] 20.3 POST /api/v1/civil/utilities - Design utilities
    - Implement endpoint with request validation
    - Return utility design results
    - _Requirements: 3.3, 8.1_
  - [ ] 20.4 GET /api/v1/civil/designs/{id} - Get design
    - Retrieve civil design by ID
    - _Requirements: 4.1_
  - [ ] 20.5 PUT /api/v1/civil/designs/{id} - Update design
    - Update existing design with versioning
    - _Requirements: 4.2_
  - [ ] 20.6 DELETE /api/v1/civil/designs/{id} - Delete design
    - Soft delete design
    - _Requirements: 4.1_
  - [ ]* 20.7 Write API integration tests
    - Test all civil endpoints
    - _Requirements: 3.1-3.4_

- [ ] 21. API Endpoints - Code Compliance
  - [ ] 21.1 POST /api/v1/compliance/validate - Validate design
    - Validate design against codes
    - Return compliance report
    - _Requirements: 5.1-5.3, 8.1_
  - [ ] 21.2 GET /api/v1/compliance/reports/{id} - Get report
    - Retrieve compliance report by ID
    - _Requirements: 5.4_
  - [ ] 21.3 GET /api/v1/compliance/codes - List available codes
    - Return list of supported codes by jurisdiction
    - _Requirements: 5.6_
  - [ ]* 21.4 Write API integration tests
    - Test all compliance endpoints
    - _Requirements: 5.1-5.6_

- [ ] 22. API Endpoints - Document Management
  - [ ] 22.1 POST /api/v1/documents/calculation-sheets - Create sheet
    - Create new calculation sheet
    - _Requirements: 4.1, 8.1_
  - [ ] 22.2 GET /api/v1/documents/calculation-sheets/{id} - Get sheet
    - Retrieve calculation sheet by ID
    - _Requirements: 4.1_
  - [ ] 22.3 PUT /api/v1/documents/calculation-sheets/{id} - Update sheet
    - Update sheet with versioning
    - _Requirements: 4.2_
  - [ ] 22.4 GET /api/v1/documents/calculation-sheets/{id}/history - Get history
    - Retrieve version history
    - _Requirements: 4.3_
  - [ ] 22.5 POST /api/v1/documents/specifications - Generate specification
    - Generate CSI MasterFormat specification
    - _Requirements: 4.4_
  - [ ] 22.6 GET /api/v1/documents/search - Search documents
    - Search with filters
    - _Requirements: 4.6_
  - [ ]* 22.7 Write API integration tests
    - Test all document endpoints
    - _Requirements: 4.1-4.6_

- [ ] 23. Checkpoint - API Endpoints Complete
  - Ensure all API endpoint tests pass
  - Verify all endpoints are properly secured
  - Test end-to-end workflows through APIs
  - Ask the user if questions arise

- [ ] 24. Audit Logging
  - [ ] 24.1 Implement audit log creation for document operations
    - Log create, update, delete operations
    - Include user ID, timestamp, document details
    - _Requirements: 11.1_
  - [ ] 24.2 Implement audit log creation for calculation modifications
    - Log before and after values
    - _Requirements: 11.2_
  - [ ] 24.3 Implement audit log creation for compliance checks
    - Log results and violations
    - _Requirements: 11.3_
  - [ ] 24.4 Implement audit log creation for integration events
    - Log event type, status, errors
    - _Requirements: 11.4_
  - [ ] 24.5 Implement audit log query endpoint
    - Filter by user, action type, date range
    - _Requirements: 11.5_
  - [ ] 24.6 Add PII redaction in logs
    - Redact sensitive information
    - _Requirements: 11.6_
  - [ ]* 24.7 Write unit tests for audit logging
    - Test all audit logging scenarios
    - _Requirements: 11.1-11.6_

- [ ] 25. Input Validation and Error Handling
  - [ ] 25.1 Add input validation for all API endpoints
    - Use Pydantic validators
    - Return clear validation errors
    - _Requirements: 8.1, 8.6_
  - [ ] 25.2 Add range validation for calculation inputs
    - Warn for out-of-range values
    - _Requirements: 8.2_
  - [ ] 25.3 Implement descriptive error messages
    - Provide specific error details
    - Include suggested corrections
    - _Requirements: 8.3_
  - [ ] 25.4 Add database error handling with rollback
    - Handle transaction failures
    - _Requirements: 8.4_
  - [ ] 25.5 Add external service error handling
    - Return graceful error messages
    - Don't expose internal details
    - _Requirements: 8.5_
  - [ ]* 25.6 Write tests for error scenarios
    - Test all error handling paths
    - _Requirements: 8.1-8.6_

- [ ] 26. Caching and Performance Optimization
  - [ ] 26.1 Implement Redis caching for calculation results
    - Cache results for 5 minutes
    - Use calculation inputs as cache key
    - _Requirements: 9.4_
  - [ ] 26.2 Add cache invalidation on updates
    - Invalidate cache when data changes
    - _Requirements: 9.4_
  - [ ] 26.3 Implement database query optimization with indexes
    - Add indexes for common queries
    - _Requirements: 9.5_
  - [ ] 26.4 Add connection pooling
    - Configure optimal pool size
    - _Requirements: 9.5_
  - [ ]* 26.5 Write performance tests
    - Test response times
    - Test concurrent requests
    - _Requirements: 9.1-9.3_
  - [ ]* 26.6 Write property test for cache consistency
    - Verify cached values match computed values
    - _Requirements: 9.4_

- [ ] 27. Health Checks and Monitoring
  - [ ] 27.1 Implement /health endpoint
    - Basic health check
    - _Requirements: 9.6_
  - [ ] 27.2 Implement /health/ready endpoint
    - Readiness check for dependencies
    - _Requirements: 9.6_
  - [ ] 27.3 Add database health check
    - Verify database connectivity
    - _Requirements: 9.6_
  - [ ] 27.4 Add Redis health check
    - Verify Redis connectivity
    - _Requirements: 9.6_
  - [ ] 27.5 Add external service health checks
    - Check integration service availability
    - _Requirements: 6.6_
  - [ ]* 27.6 Write health check tests
    - Test all health check endpoints
    - _Requirements: 9.6_

- [ ] 28. Integration Testing
  - [ ]* 28.1 Write end-to-end structural engineering workflow test
    - Test complete structural design workflow
    - _Requirements: 1.1-1.7_
  - [ ]* 28.2 Write end-to-end MEP engineering workflow test
    - Test complete MEP design workflow
    - _Requirements: 2.1-2.6_
  - [ ]* 28.3 Write end-to-end civil engineering workflow test
    - Test complete civil design workflow
    - _Requirements: 3.1-3.4_
  - [ ]* 28.4 Write code compliance workflow test
    - Test validation and reporting workflow
    - _Requirements: 5.1-5.6_
  - [ ]* 28.5 Write document management workflow test
    - Test document creation, versioning, search
    - _Requirements: 4.1-4.6_
  - [ ]* 28.6 Write service integration tests
    - Test external service integrations
    - _Requirements: 6.1-6.6_

- [ ] 29. Documentation
  - [ ] 29.1 Generate OpenAPI/Swagger documentation
    - Auto-generate from FastAPI
    - Add descriptions and examples
  - [ ] 29.2 Write API usage examples
    - Provide code examples for common use cases
  - [ ] 29.3 Document calculation formulas and references
    - Document engineering formulas used
    - Include code references (ASCE 7, NEC, etc.)
  - [ ] 29.4 Document code compliance rules
    - Document validation rules by code
  - [ ] 29.5 Create deployment guide
    - Document deployment process

- [ ] 30. Deployment Configuration
  - [ ] 30.1 Create Dockerfile
    - Multi-stage build for production
  - [ ] 30.2 Create docker-compose.yml for local development
    - Include all dependencies
  - [ ] 30.3 Configure environment variables
    - Document all required variables
  - [ ] 30.4 Set up CI/CD pipeline
    - Automated testing and deployment
  - [ ] 30.5 Configure production settings
    - Security, performance, monitoring

## Property-Based Tests Summary

The following properties must be validated with Hypothesis:

1. **Load Calculation Reasonableness**: All calculated loads are non-negative and proportional to inputs
2. **Structural Design Validity**: Designed members meet strength and serviceability requirements
3. **MEP System Sizing**: Sized equipment meets calculated loads with appropriate safety factors
4. **Cut/Fill Volume Conservation**: Total cut + fill volumes equal net volume change
5. **Calculation Dependency Updates**: Dependent calculations update when inputs change
6. **MEP System Updates**: System parameters update when building parameters change
7. **Civil Design Validity**: Civil designs meet jurisdiction requirements
8. **Code Compliance Checks**: Violations are correctly identified per code requirements
9. **Violation Reporting**: All violations include code references and corrections
10. **Document Versioning**: Version history preserves all changes accurately
11. **Integration Resilience**: Service failures are handled gracefully with retries
12. **Data Persistence Round-Trip**: Serialization and deserialization preserve data integrity

## Testing Guidelines

- Write tests BEFORE implementing functionality (TDD)
- Each property test should run minimum 100 iterations
- Use descriptive test names that explain what is being tested
- Mock external service calls in unit tests
- Use test database for integration tests
- Achieve minimum 80% code coverage
- All tests must pass before marking task complete

## Notes

- Follow async/await patterns for all I/O operations
- Use Pydantic v2 for all schemas
- Ensure TiDB/MySQL compatibility in all queries
- Implement proper transaction management
- Add comprehensive logging for debugging
- Follow FastAPI best practices
