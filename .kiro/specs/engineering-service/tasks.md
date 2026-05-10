# Engineering Service - Implementation Tasks

## Overview

This task list implements the Engineering Service following Test-Driven Development (TDD) methodology. Each task includes unit tests and property-based tests to ensure correctness.

**Implementation Language:** Python with FastAPI framework (as specified in the design document)

## 🚀 UPDATED IMPLEMENTATION STRATEGY (December 2024)

### Current Status Assessment
- **Foundation:** ✅ Complete (Models, schemas, basic structure)
- **Tests Created:** 544+ tests exist across all layers
- **Implementation Gap:** Many test files exist but implementations are incomplete
- **Priority:** Focus on completing existing implementations rather than creating new components

### 🎯 IMMEDIATE ACTION PLAN

#### Phase 1: Complete Core Calculation Engines (1-2 weeks)
**Why First:** All other layers depend on these calculations being correct

**High Priority Files to Complete:**
1. `src/calculations/load_calculator.py` - Structural load calculations
2. `src/calculations/beam_designer.py` - Beam design algorithms
3. `src/calculations/column_designer.py` - Column design algorithms
4. `src/calculations/foundation_designer.py` - Foundation design
5. `src/calculations/hvac_calculator.py` - HVAC load calculations
6. `src/calculations/electrical_calculator.py` - Electrical load calculations
7. `src/calculations/plumbing_calculator.py` - Plumbing calculations
8. `src/calculations/fire_protection_calculator.py` - Fire protection calculations

**Action Steps:**
```bash
# Navigate to engineering service
cd apps/engineering-service

# Run tests to see current failures
python -m pytest tests/unit/calculations/ -v

# Fix implementations one by one
# Start with load_calculator.py as it's used by others
python -m pytest tests/unit/calculations/test_load_calculator.py -v

# Check coverage after fixes
python -m pytest --cov=src/calculations --cov-report=term-missing
```

#### Phase 2: Complete Repository Layer (3-5 days)
**Why Second:** Services need working repositories to persist data

**Files to Complete:**
1. `src/repositories/calculation_sheet_repository.py`
2. `src/repositories/structural_design_repository.py`
3. `src/repositories/mep_design_repository.py`
4. `src/repositories/civil_design_repository.py`
5. `src/repositories/compliance_report_repository.py`
6. `src/repositories/audit_log_repository.py`

#### Phase 3: Complete Service Layer (1 week)
**Why Third:** Business logic layer that orchestrates calculations and data

**Files to Complete:**
1. `src/services/structural_calculation_service.py` (partially done)
2. Create `src/services/mep_calculation_service.py`
3. Create `src/services/civil_calculation_service.py`
4. Create `src/services/document_service.py`

#### Phase 4: API Endpoints (1 week)
**Why Fourth:** Expose functionality via REST API

**Create API Routes:**
1. `src/api/v1/routes/structural.py`
2. `src/api/v1/routes/mep.py`
3. `src/api/v1/routes/civil.py`
4. `src/api/v1/routes/documents.py`
5. `src/api/v1/routes/health.py`

### 🔧 Development Workflow

1. **Pick a calculation engine** (start with `load_calculator.py`)
2. **Run its tests:** `python -m pytest tests/unit/calculations/test_load_calculator.py -v`
3. **Fix failing tests** by completing the implementation
4. **Verify coverage:** `python -m pytest --cov=src/calculations/load_calculator.py --cov-report=term-missing`
5. **Move to next file** when coverage > 80%

### 📊 Success Metrics

- **Calculation Engines:** 80%+ coverage each
- **Repositories:** 80%+ coverage each
- **Services:** 80%+ coverage each
- **API Endpoints:** 80%+ coverage each
- **All Tests Passing:** 100% pass rate
- **Property Tests:** All 12 properties validated

### 🚨 Critical Dependencies

**Before starting API work, ensure:**
- All calculation engines are complete and tested
- All repositories are complete and tested
- All services are complete and tested
- Database migrations are applied
- External service clients are implemented

### 📁 File Status Overview

#### ✅ COMPLETE
- Database models and migrations
- Pydantic schemas
- Project structure and configuration
- Test framework setup
- Unit conversion utilities

#### ⚠️ NEEDS COMPLETION (Priority Order)
1. **Calculation Engines** - Tests exist, implementations incomplete
2. **Repositories** - Tests exist, CRUD operations incomplete
3. **Services** - Structural service started, others need creation
4. **API Routes** - None created yet
5. **Validators** - None created yet
6. **Integration Clients** - None created yet

#### ❌ NOT STARTED
- Code compliance validators
- External service integration clients
- API endpoint implementations
- Health check endpoints
- Audit logging implementation
- Caching and performance optimization

---

## 📋 UPDATED TASK LIST

### ✅ COMPLETED TASKS (Foundation)

- [x] 1. Project Setup and Infrastructure
- [x] 2. Database Models and Schemas
- [x] 3. Pydantic Request/Response Schemas
- [x] 4. Repository Layer (structure created, implementations need completion)
- [x] 5. Unit Conversion System
- [x] 6. Structural Engineering Calculations (structure created, implementations need completion)
- [x] 7. MEP Systems Calculations (structure created, implementations need completion)
- [x] 8. Civil Engineering Calculations (structure created, implementations need completion)

### 🔄 IN PROGRESS TASKS

- [x] 9. Structural Engineering Service Layer (partially complete - needs method implementations)

### 🎯 HIGH PRIORITY TASKS (Complete These First)

#### Phase 1: Complete Calculation Engine Implementations

- [ ] **PRIORITY 1A: Complete LoadCalculator Implementation**
  - [ ] 1A.1 Fix `calculate_dead_load()` method implementation
    - Review test failures in `tests/unit/calculations/test_load_calculator.py`
    - Complete dead load calculation logic per ASCE 7
    - Ensure proper unit handling and validation
    - _Requirements: 1.1_

  - [ ] 1A.2 Fix `calculate_live_load()` method implementation
    - Complete live load calculation per ASCE 7 Table 4.3-1
    - Handle different occupancy types correctly
    - Add proper input validation
    - _Requirements: 1.1_

  - [ ] 1A.3 Fix `calculate_wind_load()` method implementation
    - Complete wind load calculation per ASCE 7 Chapter 27
    - Handle building geometry and exposure categories
    - Calculate pressure coefficients correctly
    - _Requirements: 1.1_

  - [ ] 1A.4 Fix `calculate_seismic_load()` method implementation
    - Complete seismic load calculation per ASCE 7 Chapter 12
    - Handle seismic design categories and response modification factors
    - Calculate base shear and distribution correctly
    - _Requirements: 1.1_

- [ ] **PRIORITY 1B: Complete BeamDesigner Implementation**
  - [ ] 1B.1 Fix `design_beam()` method implementation
    - Complete beam design calculations for flexure
    - Add deflection checks per code requirements
    - Calculate required section properties
    - _Requirements: 1.2_

  - [ ] 1B.2 Fix `check_deflection()` method implementation
    - Implement deflection calculations for various load cases
    - Check against allowable deflection limits
    - Handle different support conditions
    - _Requirements: 1.2_

  - [ ] 1B.3 Fix `calculate_shear()` method implementation
    - Complete shear design calculations
    - Check shear capacity and reinforcement requirements
    - _Requirements: 1.2_

- [ ] **PRIORITY 1C: Complete ColumnDesigner Implementation**
  - [ ] 1C.1 Fix `design_column()` method implementation
    - Complete column design for axial loads and moments
    - Handle different column types (steel, concrete)
    - Calculate required section properties
    - _Requirements: 1.3_

  - [ ] 1C.2 Fix `check_buckling()` method implementation
    - Implement buckling analysis per code requirements
    - Calculate effective length factors
    - Check stability requirements
    - _Requirements: 1.3_

- [ ] **PRIORITY 1D: Complete FoundationDesigner Implementation**
  - [ ] 1D.1 Fix `design_foundation()` method implementation
    - Complete foundation design calculations
    - Handle different foundation types
    - Calculate required dimensions and reinforcement
    - _Requirements: 1.4_

  - [ ] 1D.2 Fix `calculate_bearing_capacity()` method implementation
    - Implement bearing capacity calculations per code
    - Handle different soil conditions
    - Apply appropriate safety factors
    - _Requirements: 1.4_

- [ ] **PRIORITY 1E: Complete MEP Calculator Implementations**
  - [ ] 1E.1 Fix HVACCalculator implementations
    - Complete `calculate_heating_load()` per ASHRAE standards
    - Complete `calculate_cooling_load()` per ASHRAE standards
    - Complete `size_equipment()` method
    - _Requirements: 2.1_

  - [ ] 1E.2 Fix ElectricalCalculator implementations
    - Complete `calculate_load()` per NEC requirements
    - Complete `size_panel()` per NEC requirements
    - Complete `size_circuit()` per NEC requirements
    - _Requirements: 2.2_

  - [ ] 1E.3 Fix PlumbingCalculator implementations
    - Complete `calculate_fixture_units()` per IPC
    - Complete `size_pipes()` per IPC requirements
    - Complete `calculate_water_demand()` method
    - _Requirements: 2.3_

  - [ ] 1E.4 Fix FireProtectionCalculator implementations
    - Complete `calculate_sprinkler_demand()` per NFPA 13
    - Complete `size_pipes()` per NFPA 13
    - Complete `calculate_coverage()` method
    - _Requirements: 2.4_

#### Phase 2: Complete Repository Layer Implementations

- [ ] **PRIORITY 2A: Complete CalculationSheetRepository**
  - [ ] 2A.1 Fix `create()` method implementation
    - Complete database insertion logic
    - Handle proper error handling and validation
    - Ensure proper transaction management
    - _Requirements: 4.1_

  - [ ] 2A.2 Fix `get_by_id()` method implementation
    - Complete database query logic
    - Handle not found cases properly
    - Include proper relationship loading
    - _Requirements: 4.1_

  - [ ] 2A.3 Fix `update()` method implementation
    - Complete update logic with version control
    - Handle optimistic locking
    - Preserve audit trail
    - _Requirements: 4.2_

  - [ ] 2A.4 Fix `delete()` method implementation
    - Implement soft delete functionality
    - Preserve referential integrity
    - Update related records appropriately
    - _Requirements: 4.1_

- [ ] **PRIORITY 2B: Complete Other Repository Implementations**
  - [ ] 2B.1 Complete StructuralDesignRepository CRUD operations
  - [ ] 2B.2 Complete MEPDesignRepository CRUD operations
  - [ ] 2B.3 Complete CivilDesignRepository CRUD operations
  - [ ] 2B.4 Complete ComplianceReportRepository CRUD operations
  - [ ] 2B.5 Complete AuditLogRepository query operations

#### Phase 3: Complete Service Layer Implementations

- [ ] **PRIORITY 3A: Complete StructuralCalculationService**
  - [ ] 3A.1 Complete `calculate_loads()` method implementation
    - Integrate with LoadCalculator
    - Handle database persistence via repository
    - Add proper error handling and validation
    - _Requirements: 1.1, 4.1_

  - [ ] 3A.2 Complete `design_beam()` method implementation
    - Integrate with BeamDesigner
    - Handle database persistence via repository
    - Link to calculation sheets properly
    - _Requirements: 1.2, 4.1_

  - [ ] 3A.3 Complete `design_column()` method implementation
    - Integrate with ColumnDesigner
    - Handle database persistence via repository
    - Include buckling analysis results
    - _Requirements: 1.3, 4.1_

  - [ ] 3A.4 Complete `design_foundation()` method implementation
    - Integrate with FoundationDesigner
    - Handle database persistence via repository
    - Include bearing capacity and settlement results
    - _Requirements: 1.4, 4.1_

- [ ] **PRIORITY 3B: Create MEPCalculationService**
  - [ ] 3B.1 Create MEPCalculationService class structure
  - [ ] 3B.2 Implement `design_hvac_system()` method
  - [ ] 3B.3 Implement `design_electrical_system()` method
  - [ ] 3B.4 Implement `design_plumbing_system()` method
  - [ ] 3B.5 Implement `design_fire_protection()` method
  - [ ]* 3B.6 Write unit tests for all MEP service methods

- [ ] **PRIORITY 3C: Create CivilCalculationService**
  - [ ] 3C.1 Create CivilCalculationService class structure
  - [ ] 3C.2 Implement `design_grading()` method
  - [ ] 3C.3 Implement `design_stormwater()` method
  - [ ] 3C.4 Implement `design_utilities()` method
  - [ ]* 3C.5 Write unit tests for all civil service methods

#### Phase 4: Create API Endpoints

- [ ] **PRIORITY 4A: Create Structural API Endpoints**
  - [ ] 4A.1 Create `src/api/v1/routes/structural.py`
  - [ ] 4A.2 Implement POST /api/v1/structural/loads endpoint
  - [ ] 4A.3 Implement POST /api/v1/structural/beams endpoint
  - [ ] 4A.4 Implement POST /api/v1/structural/columns endpoint
  - [ ] 4A.5 Implement POST /api/v1/structural/foundations endpoint
  - [ ] 4A.6 Implement GET/PUT/DELETE endpoints for designs
  - [ ]* 4A.7 Write API integration tests

- [ ] **PRIORITY 4B: Create MEP API Endpoints**
  - [ ] 4B.1 Create `src/api/v1/routes/mep.py`
  - [ ] 4B.2 Implement POST /api/v1/mep/hvac endpoint
  - [ ] 4B.3 Implement POST /api/v1/mep/electrical endpoint
  - [ ] 4B.4 Implement POST /api/v1/mep/plumbing endpoint
  - [ ] 4B.5 Implement POST /api/v1/mep/fire-protection endpoint
  - [ ] 4B.6 Implement GET/PUT/DELETE endpoints for designs
  - [ ]* 4B.7 Write API integration tests

- [ ] **PRIORITY 4C: Create Civil API Endpoints**
  - [ ] 4C.1 Create `src/api/v1/routes/civil.py`
  - [ ] 4C.2 Implement POST /api/v1/civil/grading endpoint
  - [ ] 4C.3 Implement POST /api/v1/civil/stormwater endpoint
  - [ ] 4C.4 Implement POST /api/v1/civil/utilities endpoint
  - [ ] 4C.5 Implement GET/PUT/DELETE endpoints for designs
  - [ ]* 4C.6 Write API integration tests

### 🔮 FUTURE TASKS (Lower Priority)

#### Phase 5: Document Management & Code Compliance
- [ ] 10. MEP Engineering Service Layer (create from scratch)
- [ ] 11. Civil Engineering Service Layer (create from scratch)
- [ ] 13. Document Management Service (create from scratch)
- [ ] 14. Code Compliance Validation (create from scratch)

#### Phase 6: Integration & Security
- [ ] 16. External Service Integration Clients (create from scratch)
- [ ] 17. Authentication and Authorization (create from scratch)

#### Phase 7: Cross-Cutting Concerns
- [ ] 24. Audit Logging (create from scratch)
- [ ] 25. Input Validation and Error Handling (enhance existing)
- [ ] 26. Caching and Performance Optimization (create from scratch)
- [ ] 27. Health Checks and Monitoring (create from scratch)

#### Phase 8: Testing & Documentation
- [ ] 28. Integration Testing (create comprehensive tests)
- [ ] 29. Documentation (create API docs and guides)
- [ ] 30. Deployment Configuration (create deployment configs)

---

## 🧪 TESTING STRATEGY

### Current Test Status
- **544+ tests created** across all layers
- **Property-based tests** implemented for core algorithms
- **Unit tests** exist for most components
- **Integration tests** framework ready

### Testing Workflow
1. **Run existing tests** to identify failures
2. **Fix implementations** to make tests pass
3. **Verify coverage** reaches 80%+ per component
4. **Add missing tests** only if gaps identified

### Key Test Commands
```bash
# Run all tests
python -m pytest

# Run specific layer tests
python -m pytest tests/unit/calculations/ -v
python -m pytest tests/unit/repositories/ -v
python -m pytest tests/unit/services/ -v

# Run with coverage
python -m pytest --cov=src --cov-report=term-missing

# Run property tests only
python -m pytest tests/property/ -v

# Run failing tests only
python -m pytest --lf
```

---

## 📈 SUCCESS METRICS

### Phase 1 Success Criteria
- [ ] All calculation engine tests passing (100%)
- [ ] Calculation engine coverage > 80% each
- [ ] All property tests passing (12 properties)
- [ ] No critical test failures

### Phase 2 Success Criteria
- [ ] All repository tests passing (100%)
- [ ] Repository coverage > 80% each
- [ ] Database operations working correctly
- [ ] Transaction handling implemented

### Phase 3 Success Criteria
- [ ] All service tests passing (100%)
- [ ] Service coverage > 80% each
- [ ] Business logic correctly implemented
- [ ] Integration between layers working

### Phase 4 Success Criteria
- [ ] All API tests passing (100%)
- [ ] API coverage > 80% each
- [ ] All endpoints functional
- [ ] Request/response validation working

### Overall Success Criteria
- [ ] **Overall coverage > 80%**
- [ ] **All 544+ tests passing**
- [ ] **All 12 property tests validated**
- [ ] **No critical bugs or failures**
- [ ] **API endpoints fully functional**

---

## 🚨 CRITICAL NOTES

### Before Starting Development
1. **Ensure database is running** (TiDB/MySQL)
2. **Apply all migrations** (`alembic upgrade head`)
3. **Install all dependencies** (`pip install -r requirements.txt`)
4. **Set up environment variables** (copy `.env.example` to `.env`)

### Development Best Practices
- **Test-Driven Development:** Fix tests before adding new features
- **One Component at a Time:** Complete each calculation engine fully before moving to next
- **Coverage Monitoring:** Check coverage after each fix
- **Property Test Validation:** Ensure all property tests pass
- **Code Quality:** Follow existing patterns and conventions

### Integration Dependencies
- **Calculation Engines** → **Services** → **API Endpoints**
- **Repositories** → **Services** → **API Endpoints**
- **Models/Schemas** → **All Layers**

### Performance Targets
- Simple calculations: < 500ms response time
- Complex calculations: < 3 seconds response time
- Concurrent requests: 100+ requests/second
- Database queries: Optimized with proper indexes

---

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
  - [x] 9.7 Write property test for calculation dependency updates (Property 5)
    - **Property 5: Calculation Dependency Updates**
    - **Validates: Requirements 1.6**
    - Test that changing input A triggers recalculation of dependent calculation B

- [x] 10. MEP Engineering Service Layer
  - [x] 10.1 Implement MEPCalculationService.design_hvac_system
    - Integrate HVACCalculator with service layer
    - Add calculation sheet creation
    - _Requirements: 2.1, 4.1_
  - [x] 10.2 Implement MEPCalculationService.design_electrical_system
    - Integrate ElectricalCalculator with service layer
    - Add calculation sheet creation
    - _Requirements: 2.2, 4.1_
  - [x] 10.3 Implement MEPCalculationService.design_plumbing_system
    - Integrate PlumbingCalculator with service layer
    - Add calculation sheet creation
    - _Requirements: 2.3, 4.1_
  - [x] 10.4 Implement MEPCalculationService.design_fire_protection
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

- [x] 11. Civil Engineering Service Layer
  - [x] 11.1 Implement CivilCalculationService.design_grading
    - Integrate grading calculations with service layer
    - Add calculation sheet creation
    - _Requirements: 3.1, 4.1_
  - [x] 11.2 Implement CivilCalculationService.design_stormwater
    - Integrate stormwater calculations with service layer
    - Add calculation sheet creation
    - _Requirements: 3.2, 4.1_
  - [x] 11.3 Implement CivilCalculationService.design_utilities
    - Integrate utility calculations with service layer
    - Add calculation sheet creation
    - _Requirements: 3.3, 4.1_
  - [x] 11.4 Write unit tests for service methods
    - Test all civil service methods
    - _Requirements: 3.1-3.4_
  - [x] 11.5 Write property test for civil design validity (Property 7)
    - **Property 7: Civil Design Validity**
    - **Validates: Requirements 3.4**

- [x] 12. Checkpoint - Service Layer Complete
  - Ensure all service layer tests pass
  - Verify all calculation engines are integrated
  - Ask the user if questions arise

- [x] 13. Document Management Service
  - [x] 13.1 Implement DocumentService.create_calculation_sheet
    - Create versioned calculation sheets
    - Associate with projects and disciplines
    - _Requirements: 4.1, 4.5_
  - [x] 13.2 Implement DocumentService.update_calculation_sheet with versioning
    - Create new versions on updates
    - Preserve previous versions
    - _Requirements: 4.2_
  - [x] 13.3 Implement DocumentService.get_document_history
    - Return all versions with change summaries
    - _Requirements: 4.3_
  - [x] 13.4 Implement DocumentService.generate_specification (CSI MasterFormat)
    - Format specifications per CSI standards
    - _Requirements: 4.4_
  - [x] 13.5 Implement document search functionality
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

---

## 🎯 SUMMARY & NEXT STEPS

### What Was Updated
This tasks.md file has been updated with a **priority-based implementation strategy** that focuses on:

1. **Completing existing implementations** rather than creating new components
2. **Fixing failing tests** to achieve 80%+ coverage per component
3. **Following dependency order** (calculations → repositories → services → APIs)
4. **Providing clear action steps** with specific files and methods to fix

### Key Changes Made
- ✅ **Added priority-based task organization** with 4 clear phases
- ✅ **Identified specific files and methods** that need completion
- ✅ **Provided concrete action steps** for each priority task
- ✅ **Added testing workflow** and coverage monitoring guidance
- ✅ **Included success metrics** and quality gates
- ✅ **Preserved original comprehensive task list** for reference

### Immediate Next Steps
1. **Start with Phase 1:** Complete calculation engine implementations
2. **Run existing tests:** `python -m pytest tests/unit/calculations/ -v`
3. **Fix failing implementations** one calculator at a time
4. **Monitor coverage:** `python -m pytest --cov=src/calculations --cov-report=term-missing`
5. **Move to Phase 2** when calculation engines reach 80%+ coverage

### Expected Timeline
- **Phase 1 (Calculations):** 1-2 weeks
- **Phase 2 (Repositories):** 3-5 days
- **Phase 3 (Services):** 1 week
- **Phase 4 (APIs):** 1 week
- **Total:** 4-6 weeks for core functionality

### Success Indicators
- All 544+ tests passing
- Overall coverage > 80%
- All 12 property tests validated
- Core API endpoints functional
- No critical bugs or failures

The engineering service now has a clear, actionable path forward that builds on the substantial foundation already created while focusing on completing implementations to achieve a working, tested system.
