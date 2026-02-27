# Integration Test Infrastructure

This directory contains workspace-level integration tests that validate cross-service functionality, database integration, and service communication patterns. The tests follow Test-Driven Development (TDD) methodology - they are written first to fail, then infrastructure is implemented to make them pass.

## Overview

The integration test infrastructure provides:

- **Cross-service testing**: Validates authentication flows, service-to-service communication, and data consistency across services
- **Database integration**: Tests database setup, isolation, migration validation, and connection pooling
- **Configuration validation**: Ensures configuration management works correctly across environments
- **Service lifecycle**: Tests service startup, shutdown, health checks, and recovery scenarios
- **Error handling**: Validates consistent error response formats across all services

## Test Structure

```
tests/integration/
├── conftest.py                           # Shared fixtures and test configuration
├── test_cross_service_integration.py     # Cross-service workflow tests
├── test_database_integration.py          # Database integration tests
├── test_configuration_validation.py      # Configuration validation tests
├── test_service_startup_shutdown.py      # Service lifecycle tests
├── test_migration_validation.py          # Migration validation tests
├── run_integration_tests.py              # Test runner script
└── README.md                            # This file
```

## Test Categories

### Cross-Service Integration Tests

Tests that validate functionality spanning multiple services:

- **Authentication Flow**: User creation → JWT token → Cross-service authorization
- **Project-Resource Workflow**: Project creation → Resource addition → Citation linking
- **Service Communication**: HTTP client usage, retry mechanisms, circuit breakers
- **Error Consistency**: Standardized error response formats across services

### Database Integration Tests

Tests that validate database functionality:

- **Isolation**: Each test gets a unique database instance
- **Migration Validation**: Ensures all migrations are applied correctly
- **Connection Pooling**: Tests concurrent database operations
- **CASCADE Behavior**: Validates foreign key constraints and cascade deletes
- **Transaction Handling**: Tests rollback scenarios and constraint violations

### Configuration Validation Tests

Tests that validate configuration management:

- **Missing Configuration**: Proper error handling for missing required values
- **Invalid Values**: Validation of configuration value formats and ranges
- **Fallback Mechanisms**: LLM provider fallbacks, default value handling
- **Environment Handling**: Development vs production configuration patterns
- **Secret Management**: Secure handling of sensitive configuration values

### Service Lifecycle Tests

Tests that validate service startup and shutdown:

- **Startup Sequence**: Services start in correct order and become healthy
- **Health Checks**: `/health` and `/ready` endpoints return correct formats
- **Graceful Shutdown**: Services shut down without data loss
- **Error Recovery**: Handling of database/external service unavailability
- **Restart Recovery**: Services recover properly after restart

## Running Tests

### Prerequisites

1. **Python Dependencies**: Install required packages
   ```bash
   pip install pytest pytest-asyncio testcontainers httpx sqlalchemy
   ```

2. **Database**: MySQL/TiDB instance for testing (can use testcontainers)

3. **Environment Variables**: Set required test environment variables
   ```bash
   export ENVIRONMENT=testing
   export DATABASE_URL=mysql://test:test@localhost:3306/test_db
   export JWT_SECRET_KEY=test-jwt-secret-key-for-integration-tests-only
   ```

### Basic Test Execution

```bash
# Run all integration tests
pytest tests/integration/

# Run specific test file
pytest tests/integration/test_cross_service_integration.py

# Run with verbose output
pytest tests/integration/ -v

# Run specific test category
pytest tests/integration/ -m "cross_service"
```

### Using the Test Runner

The `run_integration_tests.py` script provides comprehensive test execution:

```bash
# Basic test run
python tests/integration/run_integration_tests.py

# Run with coverage
python tests/integration/run_integration_tests.py --coverage

# Run specific pattern
python tests/integration/run_integration_tests.py --pattern "test_database*"

# Run health checks only
python tests/integration/run_integration_tests.py --health-check-only

# Run with external service mocks
python tests/integration/run_integration_tests.py --external-services
```

### Test Markers

Tests are categorized with pytest markers:

- `integration`: All integration tests
- `database`: Database-related tests
- `external`: Tests requiring external services
- `slow`: Tests taking longer than 5 seconds
- `health`: Health check tests
- `startup`: Service startup/shutdown tests
- `config`: Configuration validation tests
- `cross_service`: Cross-service workflow tests

Example usage:
```bash
# Run only database tests
pytest tests/integration/ -m "database"

# Run fast tests only (exclude slow)
pytest tests/integration/ -m "not slow"

# Run cross-service and health tests
pytest tests/integration/ -m "cross_service or health"
```

## Test Infrastructure Components

### ServiceManager

Manages service lifecycle for integration tests:

```python
# Start a service
client = await service_manager.start_service("user-service", "apps.user_service.src.main")

# Check if service is running
is_running = service_manager.is_service_running("user-service")

# Get test client
client = service_manager.get_client("user-service")

# Stop service
await service_manager.stop_service("user-service")
```

### Database Isolation

Each test gets an isolated database:

```python
@pytest.fixture
async def isolated_database(test_database: str) -> str:
    # Creates unique database for this test
    # Automatically cleaned up after test
```

### Integration Test Helper

Provides utilities for common test operations:

```python
# Wait for service health
is_healthy = await integration_helper.wait_for_service_health(client)

# Wait for service ready
is_ready = await integration_helper.wait_for_service_ready(client)

# Assert response formats
integration_helper.assert_health_response_format(response_data, service_name)
integration_helper.assert_ready_response_format(response_data, service_name)
```

## TDD Approach

These tests follow strict TDD methodology:

1. **Red Phase**: Tests are written first and should FAIL initially
2. **Green Phase**: Minimal infrastructure is implemented to make tests pass
3. **Refactor Phase**: Infrastructure is improved while keeping tests passing

### Expected Failures

Initially, these tests should fail because:

- Service endpoints don't exist yet
- Cross-service authentication not implemented
- HTTP client infrastructure not built
- Database isolation not fully configured
- Configuration validation not implemented
- Health check endpoints incomplete

### Implementation Order

1. **Basic Infrastructure**: Service startup, database connection
2. **Health Endpoints**: Implement `/health` and `/ready` endpoints
3. **Database Integration**: Migration validation, connection pooling
4. **Configuration**: Validation, fallbacks, error handling
5. **Cross-Service Communication**: HTTP clients, authentication
6. **Error Handling**: Consistent error formats, proper exception handling

## Configuration

### pytest.ini

The workspace-level `pytest.ini` configures:

- Test discovery patterns
- Async test support
- Logging configuration
- Test markers
- Environment variables
- Timeout settings

### Environment Variables

Required for integration tests:

```bash
# Core configuration
ENVIRONMENT=testing
DATABASE_URL=mysql://test:test@localhost:3306/test_db
JWT_SECRET_KEY=test-jwt-secret-key-for-integration-tests-only

# External services (for mocking)
LLM_OPENAI_API_KEY=test-openai-key
VECTOR_PINECONE_API_KEY=test-pinecone-key
VECTOR_PINECONE_ENVIRONMENT=test-environment

# Logging
DEBUG=false
LOG_LEVEL=INFO
```

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure packages path is in PYTHONPATH
   ```bash
   export PYTHONPATH="${PYTHONPATH}:$(pwd)/packages"
   ```

2. **Database Connection**: Verify DATABASE_URL and database availability
   ```bash
   mysql -h localhost -u test -p test_db
   ```

3. **Service Startup**: Check for port conflicts and dependency issues

4. **Test Isolation**: Ensure each test gets a fresh database instance

### Debug Mode

Run tests with debug logging:

```bash
pytest tests/integration/ --log-cli-level=DEBUG -s
```

### Health Checks

Validate test infrastructure:

```bash
python tests/integration/run_integration_tests.py --health-check-only
```

## Contributing

When adding new integration tests:

1. **Follow TDD**: Write failing tests first
2. **Use Markers**: Tag tests with appropriate markers
3. **Document Purpose**: Include docstrings explaining what should fail initially
4. **Isolation**: Ensure tests don't depend on each other
5. **Cleanup**: Use fixtures for proper setup/teardown
6. **Performance**: Mark slow tests appropriately

### Test Naming Convention

- `test_<functionality>_<scenario>`: Descriptive test names
- `Test<Component>Integration`: Test class names
- Use underscores for readability

### Fixture Usage

- Use session-scoped fixtures for expensive setup (database containers)
- Use function-scoped fixtures for test isolation
- Clean up resources in fixture teardown

## Future Enhancements

Planned improvements to the integration test infrastructure:

1. **Parallel Execution**: Support for running tests in parallel
2. **Performance Benchmarking**: Automated performance regression detection
3. **Visual Test Reports**: HTML reports with test execution details
4. **CI/CD Integration**: Automated test execution in build pipelines
5. **Load Testing**: Integration with load testing frameworks
6. **Monitoring Integration**: Real-time test execution monitoring
