# Architectural Service

Architectural design management, building code compliance checking, and structural analysis service for the DesignSynapse platform.

## Features

- **Design Management**: Create, update, and version architectural design documents
- **Building Code Compliance**: Automated compliance checking against IBC, IRC, and local codes
- **Structural Analysis**: Load calculations and structural integrity validation
- **Material Specifications**: Material management with vendor integration
- **Space Planning**: Layout optimization and space utilization analysis
- **Accessibility Compliance**: ADA and ANSI A117.1 compliance checking
- **Energy Analysis**: Building envelope performance and energy efficiency analysis
- **Real-time Collaboration**: Multi-user design collaboration with conflict resolution

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Environment Variables](#environment-variables)
- [Database Setup](#database-setup)
- [Running the Service](#running-the-service)
- [Testing](#testing)
- [API Usage Examples](#api-usage-examples)
- [Project Structure](#project-structure)
- [Development](#development)

## Prerequisites

- **Python**: 3.11 or higher
- **Database**: TiDB/MySQL 8.0+
- **Cache**: Redis 6.0+
- **External Services**:
  - Design Service (for visual rendering)
  - Knowledge Service (for building codes)
  - Project Service (for project management)
  - Vendor Service (for material information)

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/designsynapse/platform.git
cd platform/apps/architectural-service
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your configuration (see [Environment Variables](#environment-variables) section).

## Environment Variables

Create a `.env` file in the project root with the following variables:

### Database Configuration

```bash
# Database connection
DATABASE_URL=mysql+aiomysql://user:password@localhost:4000/architectural_service
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10
DATABASE_POOL_TIMEOUT=30
DATABASE_POOL_RECYCLE=3600
```

### External Service URLs

```bash
# External service endpoints
DESIGN_SERVICE_URL=http://design-service:8000
KNOWLEDGE_SERVICE_URL=http://knowledge-service:8000
PROJECT_SERVICE_URL=http://project-service:8000
VENDOR_SERVICE_URL=http://vendor-service:8000
```

### Redis Cache Configuration

```bash
# Redis connection
REDIS_URL=redis://localhost:6379/0
CACHE_TTL=3600
CACHE_ENABLED=true
```

### Authentication Configuration

```bash
# JWT authentication
JWT_SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
```

### Service Configuration

```bash
# Service settings
SERVICE_NAME=architectural-service
APP_VERSION=1.0.0
DEBUG=false
LOG_LEVEL=INFO

# API configuration
API_V1_PREFIX=/api/v1
ENABLE_CORS=true
CORS_ORIGINS=["http://localhost:3000"]
CORS_ALLOW_CREDENTIALS=true
CORS_ALLOW_METHODS=["*"]
CORS_ALLOW_HEADERS=["*"]
```

### Circuit Breaker Configuration

```bash
# Circuit breaker settings
CIRCUIT_BREAKER_FAILURE_THRESHOLD=5
CIRCUIT_BREAKER_RECOVERY_TIMEOUT=60
CIRCUIT_BREAKER_EXPECTED_EXCEPTION=httpx.HTTPError
```

### Retry Configuration

```bash
# Retry settings
RETRY_MAX_ATTEMPTS=5
RETRY_INITIAL_DELAY=1.0
RETRY_MAX_DELAY=16.0
RETRY_EXPONENTIAL_BASE=2.0
```

## Database Setup

### 1. Create Database

```sql
CREATE DATABASE architectural_service CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 2. Run Migrations

```bash
# Apply all migrations
alembic upgrade head
```

### 3. Verify Schema

```bash
# Check current migration version
alembic current

# View migration history
alembic history
```

### Migration Commands

```bash
# Generate a new migration
alembic revision --autogenerate -m "description of changes"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# Rollback to specific version
alembic downgrade <revision_id>

# View SQL without applying
alembic upgrade head --sql
```

## Running the Service

### Development Mode

```bash
# With auto-reload
uvicorn src.main:app --reload --port 8005

# With specific host
uvicorn src.main:app --reload --host 0.0.0.0 --port 8005
```

### Production Mode

```bash
# Single worker
uvicorn src.main:app --host 0.0.0.0 --port 8005

# Multiple workers (recommended)
gunicorn src.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8005
```

### Docker

```bash
# Build image
docker build -t architectural-service .

# Run container
docker run -p 8005:8005 --env-file .env architectural-service
```

### Health Check

Verify the service is running:

```bash
curl http://localhost:8005/api/v1/health
```

## Testing

### Run All Tests

```bash
pytest
```

### Run with Coverage

```bash
# Generate coverage report
pytest --cov=src --cov-report=html --cov-report=term

# View HTML report
open htmlcov/index.html  # On macOS
start htmlcov/index.html  # On Windows
```

### Run Specific Test Types

```bash
# Unit tests only
pytest -m unit

# Integration tests only
pytest -m integration

# Property-based tests only
pytest -m property

# Slow tests
pytest -m slow
```

### Run Specific Test Files

```bash
# Single test file
pytest tests/unit/services/test_design_service.py

# Single test function
pytest tests/unit/services/test_design_service.py::test_create_design

# Tests matching pattern
pytest -k "design"
```

### Property-Based Testing

```bash
# Run with default profile (100 examples)
pytest -m property

# Run with CI profile (200 examples)
pytest -m property --hypothesis-profile=ci

# Run with dev profile (50 examples)
pytest -m property --hypothesis-profile=dev
```

### Test Configuration

Configure pytest in `pytest.ini`:

```ini
[pytest]
asyncio_mode = auto
testpaths = tests
markers =
    unit: Unit tests
    integration: Integration tests
    property: Property-based tests
    slow: Slow-running tests
```

## API Usage Examples

### Authentication

All API requests require JWT authentication:

```bash
# Include token in Authorization header
curl -H "Authorization: Bearer <your-jwt-token>" \
  http://localhost:8005/api/v1/designs
```

### Create a Design Document

```bash
curl -X POST http://localhost:8005/api/v1/designs \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "660e8400-e29b-41d4-a716-446655440000",
    "name": "Downtown Office Building",
    "description": "Modern 10-story office building",
    "building_type": "commercial",
    "location": {
      "address": "123 Main St",
      "city": "Seattle",
      "state": "WA",
      "zip": "98101"
    }
  }'
```

### List Design Documents

```bash
# List all designs
curl -H "Authorization: Bearer <token>" \
  http://localhost:8005/api/v1/designs

# Filter by project
curl -H "Authorization: Bearer <token>" \
  "http://localhost:8005/api/v1/designs?project_id=660e8400-e29b-41d4-a716-446655440000"

# With pagination
curl -H "Authorization: Bearer <token>" \
  "http://localhost:8005/api/v1/designs?limit=20&cursor=<cursor>"
```

### Get a Design Document

```bash
# Get current version
curl -H "Authorization: Bearer <token>" \
  http://localhost:8005/api/v1/designs/550e8400-e29b-41d4-a716-446655440000

# Get specific version
curl -H "Authorization: Bearer <token>" \
  "http://localhost:8005/api/v1/designs/550e8400-e29b-41d4-a716-446655440000?version=1.0"
```

### Update a Design Document

```bash
curl -X PUT http://localhost:8005/api/v1/designs/550e8400-e29b-41d4-a716-446655440000 \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Downtown Office Building - Updated",
    "description": "Modern 10-story office building with updated layout"
  }'
```

### Request Compliance Check

```bash
curl -X POST http://localhost:8005/api/v1/designs/550e8400-e29b-41d4-a716-446655440000/compliance-checks \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "code_standards": ["IBC-2021", "ADA"],
    "jurisdiction": "Seattle, WA"
  }'
```

### Get Compliance Check Results

```bash
curl -H "Authorization: Bearer <token>" \
  http://localhost:8005/api/v1/compliance-checks/880e8400-e29b-41d4-a716-446655440000
```

### Upload Drawing

```bash
curl -X POST http://localhost:8005/api/v1/designs/550e8400-e29b-41d4-a716-446655440000/drawings \
  -H "Authorization: Bearer <token>" \
  -F "file=@floor_plan.pdf" \
  -F "drawing_type=floor_plan" \
  -F "scale=1/4 inch" \
  -F "sheet_number=A1.1"
```

### Python Client Example

```python
import httpx
from uuid import UUID

class ArchitecturalServiceClient:
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {token}"}

    async def create_design(self, project_id: UUID, name: str, building_type: str):
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/designs",
                headers=self.headers,
                json={
                    "project_id": str(project_id),
                    "name": name,
                    "building_type": building_type,
                    "location": {"city": "Seattle", "state": "WA"}
                }
            )
            response.raise_for_status()
            return response.json()

    async def get_design(self, design_id: UUID, version: str = None):
        async with httpx.AsyncClient() as client:
            params = {"version": version} if version else {}
            response = await client.get(
                f"{self.base_url}/api/v1/designs/{design_id}",
                headers=self.headers,
                params=params
            )
            response.raise_for_status()
            return response.json()

# Usage
client = ArchitecturalServiceClient("http://localhost:8005", "your-token")
design = await client.create_design(
    project_id=UUID("660e8400-e29b-41d4-a716-446655440000"),
    name="My Building",
    building_type="commercial"
)
```

## Project Structure

```
apps/architectural-service/
├── src/
│   ├── api/                    # API layer
│   │   ├── middleware.py       # Custom middleware
│   │   └── v1/
│   │       ├── dependencies.py # Dependency injection
│   │       ├── routes/         # API endpoints
│   │       │   ├── accessibility.py
│   │       │   ├── collaboration.py
│   │       │   ├── compliance.py
│   │       │   ├── designs.py
│   │       │   ├── drawings.py
│   │       │   ├── energy_analysis.py
│   │       │   ├── health.py
│   │       │   ├── materials.py
│   │       │   ├── projects.py
│   │       │   ├── space_planning.py
│   │       │   └── structural_analysis.py
│   │       └── schemas/        # Pydantic schemas
│   │           ├── analysis.py
│   │           ├── base.py
│   │           └── design.py
│   ├── core/                   # Core configuration
│   │   ├── cache.py            # Redis caching
│   │   ├── config.py           # Settings
│   │   ├── database.py         # Database setup
│   │   ├── exceptions.py       # Custom exceptions
│   │   ├── pagination.py       # Pagination utilities
│   │   └── transactions.py     # Transaction management
│   ├── infrastructure/         # External service clients
│   │   ├── design_service_client.py
│   │   ├── knowledge_service_client.py
│   │   ├── project_service_client.py
│   │   └── vendor_service_client.py
│   ├── models/                 # SQLAlchemy ORM models
│   │   ├── accessibility_check.py
│   │   ├── collaboration_session.py
│   │   ├── compliance_check.py
│   │   ├── design.py
│   │   ├── design_version.py
│   │   ├── drawing.py
│   │   ├── energy_analysis.py
│   │   ├── material_specification.py
│   │   ├── space_planning.py
│   │   └── structural_analysis.py
│   ├── repositories/           # Data access layer
│   │   ├── base_repository.py
│   │   ├── design_repository.py
│   │   └── ...
│   ├── services/               # Business logic
│   │   ├── accessibility_service.py
│   │   ├── collaboration_service.py
│   │   ├── compliance_service.py
│   │   ├── design_service.py
│   │   ├── drawing_service.py
│   │   ├── energy_analysis_service.py
│   │   ├── material_service.py
│   │   ├── space_planning_service.py
│   │   └── structural_analysis_service.py
│   └── main.py                 # Application entry point
├── tests/
│   ├── conftest.py             # Pytest fixtures
│   ├── unit/                   # Unit tests
│   │   ├── core/
│   │   ├── repositories/
│   │   └── services/
│   ├── integration/            # Integration tests
│   │   ├── api/
│   │   └── test_*.py
│   └── property/               # Property-based tests
│       └── test_*_properties.py
├── migrations/                 # Alembic migrations
│   ├── versions/
│   └── env.py
├── .env.example                # Example environment file
├── .gitignore                  # Git ignore rules
├── alembic.ini                 # Alembic configuration
├── generate_openapi_spec.py    # OpenAPI spec generator
├── openapi.json                # Generated OpenAPI specification
├── pytest.ini                  # Pytest configuration
├── pyproject.toml              # Project metadata
├── README.md                   # This file
└── requirements.txt            # Python dependencies
```

## API Documentation

### Interactive Documentation

When running in development mode (`DEBUG=true`), interactive API documentation is available:

- **Swagger UI**: http://localhost:8005/docs
  - Interactive API explorer
  - Try out endpoints directly
  - View request/response schemas

- **ReDoc**: http://localhost:8005/redoc
  - Clean, readable documentation
  - Better for reference and sharing

### OpenAPI Specification

Generate the OpenAPI 3.0 specification:

```bash
python generate_openapi_spec.py
```

This creates `openapi.json` with the complete API specification.

### API Endpoints Overview

#### Design Management
- `POST /api/v1/designs` - Create design document
- `GET /api/v1/designs` - List design documents
- `GET /api/v1/designs/{id}` - Get design document
- `PUT /api/v1/designs/{id}` - Update design document
- `DELETE /api/v1/designs/{id}` - Soft delete design document
- `GET /api/v1/designs/{id}/versions` - List design versions
- `GET /api/v1/designs/{id}/versions/{version}` - Get specific version

#### Drawing Management
- `POST /api/v1/designs/{id}/drawings` - Upload drawing
- `GET /api/v1/designs/{id}/drawings` - List drawings
- `GET /api/v1/drawings/{id}` - Get drawing
- `DELETE /api/v1/drawings/{id}` - Delete drawing

#### Compliance Checking
- `POST /api/v1/designs/{id}/compliance-checks` - Request compliance check
- `GET /api/v1/compliance-checks/{id}` - Get compliance results
- `GET /api/v1/designs/{id}/compliance-checks` - List compliance checks

#### Structural Analysis
- `POST /api/v1/designs/{id}/structural-analysis` - Request structural analysis
- `GET /api/v1/structural-analysis/{id}` - Get analysis results

#### Material Specifications
- `POST /api/v1/designs/{id}/materials` - Add material specification
- `GET /api/v1/designs/{id}/materials` - List materials
- `GET /api/v1/materials/search` - Search materials

#### Space Planning
- `POST /api/v1/designs/{id}/space-planning` - Request space planning
- `GET /api/v1/space-planning/{id}` - Get planning results

#### Accessibility Checking
- `POST /api/v1/designs/{id}/accessibility-checks` - Request accessibility check
- `GET /api/v1/accessibility-checks/{id}` - Get accessibility results

#### Energy Analysis
- `POST /api/v1/designs/{id}/energy-analysis` - Request energy analysis
- `GET /api/v1/energy-analysis/{id}` - Get energy results

#### Collaboration
- `POST /api/v1/designs/{id}/collaboration/join` - Join collaboration session
- `WS /api/v1/collaboration/{session_id}/ws` - WebSocket for real-time updates

#### Health & Monitoring
- `GET /api/v1/health` - Service health check

## Development

### Code Style

This project follows PEP 8 style guidelines with the following tools:

```bash
# Format code
black src/ tests/

# Sort imports
isort src/ tests/

# Lint code
flake8 src/ tests/

# Type checking
mypy src/
```

### Pre-commit Hooks

Install pre-commit hooks:

```bash
pre-commit install
```

### Testing Strategy

The project uses a comprehensive testing approach:

#### 1. Unit Tests
Test individual components in isolation with mocked dependencies.

**Location**: `tests/unit/`

**Example**:
```python
async def test_create_design_success():
    """Test successful design creation."""
    service = DesignService(mock_repo, mock_project_client)
    design = await service.create_design(...)
    assert design.version == "1.0"
```

#### 2. Integration Tests
Test API endpoints and external service interactions with real database.

**Location**: `tests/integration/`

**Example**:
```python
async def test_create_design_endpoint(client, auth_headers):
    """Test POST /api/v1/designs endpoint."""
    response = await client.post("/api/v1/designs", ...)
    assert response.status_code == 201
```

#### 3. Property-Based Tests
Test universal properties using Hypothesis with randomized inputs.

**Location**: `tests/property/`

**Example**:
```python
@given(name=st.text(min_size=1), building_type=st.sampled_from([...]))
async def test_property_design_initialization(name, building_type):
    """Property: All designs start at version 1.0."""
    design = await service.create_design(...)
    assert design.version == "1.0"
    assert design.version_number == 1
```

### Coverage Requirements

- Minimum 90% code coverage for all business logic
- 100% coverage for critical paths (design creation, version management)
- All API endpoints must have integration tests
- All correctness properties must have property-based tests

### Debugging

Enable debug logging:

```bash
# In .env
DEBUG=true
LOG_LEVEL=DEBUG
```

View logs:

```bash
# Follow logs in real-time
tail -f logs/architectural-service.log

# Search logs
grep "ERROR" logs/architectural-service.log
```

### Performance Profiling

Profile API endpoints:

```bash
# Install profiling tools
pip install py-spy

# Profile running service
py-spy top --pid <process-id>

# Generate flame graph
py-spy record -o profile.svg --pid <process-id>
```

## Troubleshooting

### Common Issues

#### Database Connection Errors

```bash
# Check database is running
mysql -h localhost -P 4000 -u root -p

# Verify connection string in .env
DATABASE_URL=mysql+aiomysql://user:pass@host:4000/db_name
```

#### Redis Connection Errors

```bash
# Check Redis is running
redis-cli ping

# Verify Redis URL in .env
REDIS_URL=redis://localhost:6379/0
```

#### Migration Errors

```bash
# Reset migrations (development only!)
alembic downgrade base
alembic upgrade head

# Check current version
alembic current

# View pending migrations
alembic heads
```

#### Import Errors

```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### Getting Help

- **Documentation**: https://docs.designsynapse.com
- **Support Email**: support@designsynapse.com
- **Issue Tracker**: https://github.com/designsynapse/platform/issues

## Contributing

1. Create a feature branch
2. Make your changes
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

Proprietary - DesignSynapse Platform

Copyright (c) 2024 DesignSynapse. All rights reserved.
