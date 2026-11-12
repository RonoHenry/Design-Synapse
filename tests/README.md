# Integration Test Infrastructure

This directory contains workspace-level integration tests for the DesignSynapse microservices architecture. The tests follow Test-Driven Development (TDD) methodology and validate cross-service functionality.

## Overview

The integration test infrastructure provides:

- **Service Orchestration**: Docker Compose setup for all services
- **Database Isolation**: Separate test databases for each service
- **Mock External Services**: WireMock for LLM and vector services
- **Cross-Service Testing**: Factories and utilities for multi-service scenarios
- **Health Monitoring**: Service health and readiness validation
- **Cleanup Automation**: Automatic cleanup of test data and infrastructure

## Test Structure

```
tests/
├── integration/           # Integration test files
│   ├── conftest.py       # Shared fixtures and configuration
│   ├── factories.py      # Cross-service test data factories
│   ├── test_service_startup_shutdown.py
│   ├── test_database_integration.py
│   └── test_configuration_validation.py
├── mocks/                # Mock service configurations
│   ├── llm/             # LLM service mocks (WireMock)
│   └── vector/          # Vector service mocks (WireMock)
├── scripts/             # Infrastructure scripts
│   └── create-multiple-databases.sh
├── docker-compose.integration.yml
├── pytest.ini          # Pytest configuration
├── requirements.txt     # Test dependencies
├── run_integration_tests.py  # Test runner script
├── Makefile            # Test commands
└── README.md           # This file
```

## Prerequisites

- Docker and Docker Compose
- Python 3.9+
- Make (optional, for convenience commands)

## Quick Start

1. **Install dependencies:**
   ```bash
   cd tests
   pip install -r requirements.txt
   ```

2. **Run integration tests:**
   ```bash
   # Using the test runner (recommended)
   python run_integration_tests.py

   # Or using Make
   make test-all

   # Or manually
   make setup
   make test-integration
   make teardown
   ```

## Test Categories

### Service Startup/Shutdown Tests
- Service container startup and health checks
- Graceful shutdown handling
- Service dependency management
- Recovery after failures

### Database Integration Tests
- Database isolation between services
- Migration handling and validation
- Transaction isolation
- Constraint enforcement
- Performance validation

### Configuration Validation Tests
- Environment variable validation
- Configuration consistency across services
- Sensitive data protection
- Service discovery configuration

## Test Infrastructure

### Docker Services

The integration tests use Docker Compose to orchestrate:

- **test-postgres**: PostgreSQL with separate databases for each service
- **test-user-service**: User service container
- **test-project-service**: Project service container
- **test-knowledge-service**: Knowledge service container
- **mock-llm-service**: WireMock for LLM API simulation
- **mock-vector-service**: WireMock for vector database simulation

### Service Ports

- User Service: `localhost:8001`
- Project Service: `localhost:8002`
- Knowledge Service: `localhost:8003`
- PostgreSQL: `localhost:5433`
- Mock LLM: `localhost:8080`
- Mock Vector: `localhost:8081`

### Test Databases

Each service gets its own isolated test database:
- `test_user_service`
- `test_project_service`
- `test_knowledge_service`

## Writing Integration Tests

### Basic Test Structure

```python
import pytest
from httpx import AsyncClient

class TestCrossServiceIntegration:
    async def test_user_project_workflow(self, service_clients, test_data_factory):
        # Create test user
        user = await test_data_factory.create_test_user()

        # Create test project
        project = await test_data_factory.create_test_project(user["id"])

        # Verify cross-service functionality
        user_client = service_clients["user-service"]
        project_client = service_clients["project-service"]

        # Test user can access their project
        response = await project_client.get(f"/api/v1/projects/{project['id']}")
        assert response.status_code == 200
```

### Available Fixtures

- `service_containers`: Docker containers for all services
- `service_clients`: HTTP clients for each service
- `test_database`: Database connection information
- `test_data_factory`: Factory for creating cross-service test data

### Test Data Factory

The `IntegrationTestFactory` provides methods for creating related test data:

```python
async def test_complete_workflow(self, test_data_factory):
    # Create complete test scenario
    scenario = await test_data_factory.create_complete_test_scenario()

    user = scenario["user"]
    project = scenario["project"]
    resource = scenario["resource"]
    citation = scenario["citation"]
    bookmark = scenario["bookmark"]

    # Test cross-service relationships
    # ... test logic here ...

    # Cleanup is automatic
```

## Test Execution

### Running All Tests

```bash
# Full test suite with infrastructure management
python run_integration_tests.py

# Using Make
make test-all
```

### Running Specific Tests

```bash
# Specific test file
make test-file FILE=integration/test_service_startup_shutdown.py

# Tests with specific marker
make test-marker MARKER=database

# Pytest directly
pytest integration/test_database_integration.py -v
```

### Development Mode

For active development, keep infrastructure running:

```bash
# Start infrastructure
make dev-setup

# Run tests multiple times
make test-integration

# Check status
make status

# View logs
make logs

# Clean up when done
make teardown
```

## Debugging

### Service Logs

```bash
# All service logs
make logs

# Specific service logs
docker-compose -f docker-compose.integration.yml -p integration-tests logs test-user-service

# Follow logs in real-time
docker-compose -f docker-compose.integration.yml -p integration-tests logs -f
```

### Database Access

```bash
# Connect to test database
docker exec -it integration-tests_test-postgres_1 psql -U test -d test_user_service
```

### Service Health

```bash
# Check service health
curl http://localhost:8001/health  # User service
curl http://localhost:8002/health  # Project service
curl http://localhost:8003/health  # Knowledge service
```

## Troubleshooting

### Common Issues

1. **Port conflicts**: Ensure ports 8001-8003, 5433, 8080-8081 are available
2. **Docker issues**: Ensure Docker daemon is running
3. **Service startup timeout**: Services may take 30-60 seconds to start
4. **Database connection**: Check PostgreSQL container health

### Cleanup

```bash
# Full cleanup
make clean

# Manual cleanup
docker-compose -f docker-compose.integration.yml -p integration-tests down -v --remove-orphans
docker system prune -f
```

## Configuration

### Environment Variables

The tests use these environment variables:

- `ENVIRONMENT=testing`
- `DB_HOST=test-postgres`
- `DB_PORT=5432`
- `DB_USERNAME=test`
- `DB_PASSWORD=test`
- `JWT_SECRET_KEY=test-secret-key-for-integration-tests`
- `LLM_PROVIDER=mock`
- `VECTOR_PROVIDER=mock`

### Pytest Configuration

See `pytest.ini` for:
- Test discovery patterns
- Async test support
- Coverage configuration
- Timeout settings
- Logging configuration

## Contributing

When adding new integration tests:

1. **Follow TDD**: Write failing tests first
2. **Use fixtures**: Leverage existing fixtures and factories
3. **Clean up**: Ensure tests clean up after themselves
4. **Document**: Add docstrings explaining test purpose
5. **Categorize**: Use appropriate pytest markers

### Test Markers

- `@pytest.mark.integration`: Integration tests
- `@pytest.mark.slow`: Slow-running tests
- `@pytest.mark.database`: Database-dependent tests
- `@pytest.mark.external`: Tests requiring external services

## Future Enhancements

Planned improvements:

- [ ] Parallel test execution
- [ ] Performance benchmarking
- [ ] Security testing integration
- [ ] Load testing capabilities
- [ ] CI/CD pipeline integration
- [ ] Test result reporting
- [ ] Flaky test detection
