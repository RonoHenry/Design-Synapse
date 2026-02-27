# System-Wide Fixes Design Document

## Overview

This design addresses critical system-wide issues preventing proper testing and operation of the DesignSynapse microservices architecture. The fixes will resolve import path issues, complete Pydantic v2 migration, repair test infrastructure, and ensure all services can start and run properly.

## Architecture

The system follows a microservices architecture with shared common packages:

```
DesignSynapse/
├── packages/common/          # Shared utilities and libraries
├── apps/                     # Individual microservices
│   ├── user-service/
│   ├── knowledge-service/
│   ├── labor-service/
│   └── project-service/
└── tests/                    # Integration tests
```

## Components and Interfaces

### 1. Import Path Resolution System

**Problem**: Services cannot import `packages.common` modules due to Python path issues.

**Solution**: Implement consistent PYTHONPATH configuration across all services.

**Files to Modify**:
- `pytest.ini` files in each service
- Service startup scripts
- Test configuration files

**Design Pattern**:
```python
# In each service's conftest.py or __init__.py
import sys
from pathlib import Path

# Add workspace root to Python path
workspace_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(workspace_root))
```

### 2. Pydantic v2 Migration System

**Problem**: Labor service has 57+ Pydantic v1 deprecation warnings.

**Files Requiring Updates**:
- `apps/labor-service/src/api/v1/schemas/base.py`
- `apps/labor-service/src/api/v1/schemas/booking.py`
- `apps/labor-service/src/api/v1/schemas/quote.py`
- `apps/labor-service/src/api/v1/schemas/request.py`
- `apps/labor-service/src/api/v1/schemas/review.py`

**Migration Patterns**:

```python
# OLD (Pydantic v1)
from pydantic.generics import GenericModel

class BaseResponse(BaseModel):
    class Config:
        from_attributes = True
        json_encoders = {...}

# NEW (Pydantic v2)
from pydantic import BaseModel, ConfigDict

class BaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    # Use custom serializers instead of json_encoders
```

### 3. Test Infrastructure Repair System

**Problem**: Multiple test collection and execution failures.

**Issues to Fix**:
1. **Syntax Error**: `test_database_integration.py` line 88 - `await` outside async function
2. **Missing Dependencies**: `asyncpg`, `testcontainers`
3. **Configuration Issues**: Duplicate pytest configuration entries

**Solutions**:

```python
# Fix async syntax error
@pytest.mark.asyncio
async def test_health_endpoint():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
```

### 4. Dependency Management System

**Missing Dependencies to Add**:
- `asyncpg>=0.28.0` - PostgreSQL async driver
- `testcontainers>=3.7.0` - Container testing support
- `pytest-asyncio>=0.21.0` - Async test support

**Files to Update**:
- `requirements-dev.txt` (workspace root)
- Individual service `requirements.txt` files

### 5. Service Configuration System

**Problem**: Services fail to start due to configuration issues.

**Configuration Fixes**:
1. **User Service**: Fix duplicate `extend-ignore` in `setup.cfg`
2. **Labor Service**: Complete Pydantic v2 migration
3. **All Services**: Ensure consistent pytest configuration

## Data Models

### Import Path Configuration
```python
# Standard import path setup for all services
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
PACKAGES_PATH = WORKSPACE_ROOT / "packages"
sys.path.insert(0, str(WORKSPACE_ROOT))
```

### Pydantic v2 Schema Pattern
```python
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import datetime

class ModernSchema(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        validate_assignment=True,
        arbitrary_types_allowed=True
    )

    id: int = Field(..., description="Unique identifier")
    name: str = Field(..., min_length=1, max_length=100)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    optional_field: Optional[str] = None
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Import resolution works consistently
*For any* service attempting to import packages.common modules, the import should succeed without ModuleNotFoundError
**Validates: Requirements 1.1, 1.2, 1.3**

### Property 2: Pydantic schemas use modern patterns
*For any* Pydantic schema in the system, it should use ConfigDict instead of class-based config and BaseModel instead of GenericModel
**Validates: Requirements 2.1, 2.2**

### Property 3: System runs without deprecation warnings
*For any* service startup or test execution, no Pydantic deprecation warnings should be produced
**Validates: Requirements 2.5**

### Property 4: Test collection succeeds
*For any* pytest execution from the workspace root, test collection should complete without syntax errors
**Validates: Requirements 3.1, 3.2**

### Property 5: Required dependencies are available
*For any* service requiring database drivers or test utilities, the necessary packages should be importable
**Validates: Requirements 4.1, 4.2**

### Property 6: Services start successfully
*For any* service application, startup should complete without configuration or import errors
**Validates: Requirements 5.1**

### Property 7: Health endpoints function properly
*For any* service with health endpoints, they should return proper status responses
**Validates: Requirements 5.4**

### Property 8: Configuration files are valid
*For any* configuration file, there should be no duplicate or conflicting entries
**Validates: Requirements 6.4**

### Property 9: Integration tests execute properly
*For any* integration test execution, tests should run without import or syntax errors
**Validates: Requirements 7.1**

## Error Handling

### Import Error Resolution
When import errors occur, the system will:
1. Check PYTHONPATH configuration
2. Verify workspace root is accessible
3. Ensure packages directory exists
4. Provide clear error messages with resolution steps

### Pydantic Migration Errors
When Pydantic v1 patterns are detected:
1. Log specific deprecation warnings
2. Provide migration guidance
3. Point to modern v2 patterns
4. Fail tests if warnings exceed threshold

### Test Infrastructure Errors
When test execution fails:
1. Validate async function syntax
2. Check required dependencies
3. Verify pytest configuration
4. Provide diagnostic information

## Testing Strategy

### Unit Tests
- Test import path resolution from different contexts
- Test Pydantic schema validation and serialization
- Test configuration file parsing
- Test service startup procedures

### Property-Based Tests
- Test import resolution with various service contexts
- Test schema patterns across all Pydantic models
- Test dependency availability across environments
- Test service startup with different configurations

**Property Test Configuration**:
- Minimum 100 iterations per property test
- Each test tagged with: **Feature: system-wide-fixes, Property {number}: {property_text}**
- Use pytest fixtures for consistent test environments

### Integration Tests
- Test complete service startup workflows
- Test cross-service import resolution
- Test end-to-end test execution
- Test health endpoint availability across all services

The testing approach ensures both specific fixes work correctly and universal properties hold across the entire system, providing comprehensive validation of the system-wide repairs.

<function_calls>
<invoke name="prework">
<parameter name="featureName">system-wide-fixes
