# Shared Testing Infrastructure

This package provides shared testing utilities and infrastructure for DesignSynapse services.

## Components

### Base Factory (`base_factory.py`)

Provides base factory classes for consistent test data creation across services using factory_boy.

**Key Features:**
- `BaseFactory`: Base class with common patterns for all model factories
- `TimestampMixin`: Mixin for factories that need timestamp fields
- `UserReferenceMixin`: Mixin for factories that reference user IDs
- `SequentialNameMixin`: Mixin for factories that need sequential names
- `FakerMixin`: Mixin providing common Faker patterns
- `CommonTraits`: Reusable traits for inactive, archived entities

**Usage Example:**
```python
from packages.common.testing import BaseFactory
from your_service.models import User

class UserFactory(BaseFactory):
    class Meta:
        model = User
        sqlalchemy_session = db_session
    
    email = factory.Faker("email")
    username = factory.Sequence(lambda n: f"user{n}")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")

# Create test data
user = UserFactory()
users = UserFactory.create_batch(5)
```

### Database Utilities (`database.py`)

Provides database isolation utilities that can be reused by all services.

**Key Features:**
- `DatabaseTestMixin`: Mixin class for database testing utilities
- `create_test_engine()`: Create test database engines with sensible defaults
- `create_test_session()`: Context manager for test database sessions
- `create_async_test_session()`: Async context manager for async database sessions
- `TransactionalTestCase`: Base test case with transactional isolation

**Usage Example:**
```python
from packages.common.testing.database import create_test_engine, create_test_session
from your_service.models import Base

# Create test engine and session
engine = create_test_engine()
with create_test_session(engine, Base) as session:
    # Your test code here
    pass
```

### Mock Services (`mocks.py`)

Provides mock utilities for external services (LLM, vector search, HTTP).

**Key Features:**
- `MockLLMService`: Mock LLM service with configurable responses
- `MockVectorService`: Mock vector search service with in-memory storage
- `MockHTTPService`: Mock HTTP service for inter-service communication
- Configurable failure rates and delays for testing error scenarios

**Usage Example:**
```python
from packages.common.testing.mocks import MockLLMService

# Create mock LLM service
mock_llm = MockLLMService()
mock_llm.set_response("summary", "Custom test summary")

# Use in tests
summary = await mock_llm.generate_summary("test content")
assert summary == "Custom test summary"
```

### Pytest Fixtures (`fixtures.py`)

Provides pytest plugins and fixtures for common test patterns.

**Key Features:**
- `CommonTestFixtures`: Collection of common fixtures
- Individual fixture functions for direct import
- Factory functions for creating service-specific fixtures
- `TestDataMixin`: Mixin for common test data creation patterns

**Usage Example:**
```python
# In your service's conftest.py
from packages.common.testing.fixtures import (
    event_loop,
    test_db_engine,
    mock_llm_service,
    create_service_test_session_fixture
)
from your_service.models import Base

# Create service-specific session fixture
db_session = create_service_test_session_fixture(Base)
```

## Integration with Services

### 1. Update requirements.txt

Add factory_boy to your service's requirements.txt:
```
factory-boy>=3.3.0
pytest-asyncio>=0.21.1
```

### 2. Create Service-Specific Factories

Create `tests/factories.py` in your service:
```python
from packages.common.testing import BaseFactory, FakerMixin
from your_service.models import YourModel

class YourModelFactory(BaseFactory, FakerMixin):
    class Meta:
        model = YourModel
        sqlalchemy_session_persistence = "commit"
    
    # Define your model-specific fields
    name = factory.Sequence(lambda n: f"Test Item {n}")
```

### 3. Update conftest.py

Update your service's `tests/conftest.py`:
```python
from packages.common.testing.fixtures import (
    event_loop,
    test_db_engine,
    mock_llm_service,
    mock_vector_service,
    create_service_test_session_fixture,
    create_fastapi_test_client_fixture
)
from your_service.models import Base
from your_service.main import app
from your_service.infrastructure.database import get_db

# Create service-specific fixtures
db_session = create_service_test_session_fixture(Base)
client = create_fastapi_test_client_fixture(app, get_db)
```

### 4. Write Tests

Use the shared infrastructure in your tests:
```python
import pytest
from packages.common.testing import TestDataMixin
from .factories import YourModelFactory

class TestYourModel(TestDataMixin):
    def test_model_creation(self, db_session):
        # Use factory to create test data
        instance = YourModelFactory(db_session=db_session)
        assert instance.id is not None
    
    def test_with_mock_services(self, mock_llm_service):
        # Test with mocked external services
        mock_llm_service.set_response("summary", "Test summary")
        # Your test code here
```

## Best Practices

1. **Use Factories for Test Data**: Always use factories instead of manually creating test data
2. **Isolate Tests**: Each test should run in its own transaction/session
3. **Mock External Services**: Use provided mocks for external dependencies
4. **Consistent Patterns**: Follow the established patterns for naming and structure
5. **Test Coverage**: Aim for 80%+ coverage using the shared infrastructure

## Configuration

The shared testing infrastructure supports various database configurations:
- SQLite in-memory (default for fast tests)
- SQLite file-based (for debugging)
- PostgreSQL (for integration tests)
- Async variants of all above

Configure via environment variables or test configuration files as needed.