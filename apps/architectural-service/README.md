# Architectural Service

Architectural design management, building code compliance checking, and structural analysis service for the DesignSynapse platform.

## Features

- Architectural design document management with version control
- Building code compliance checking
- Structural analysis integration
- Material specifications with vendor integration
- Space planning and optimization
- Accessibility compliance checking
- Energy efficiency analysis
- Real-time collaboration

## Setup

### Prerequisites

- Python 3.11+
- TiDB/MySQL 8.0+
- Redis

### Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Copy environment file:
```bash
cp .env.example .env
```

3. Update `.env` with your configuration

4. Run database migrations:
```bash
alembic upgrade head
```

### Running the Service

Development mode:
```bash
uvicorn src.main:app --reload --port 8005
```

Production mode:
```bash
uvicorn src.main:app --host 0.0.0.0 --port 8005
```

## Testing

Run all tests:
```bash
pytest
```

Run with coverage:
```bash
pytest --cov=src --cov-report=html
```

Run specific test types:
```bash
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests only
pytest -m property      # Property-based tests only
```

Run with Hypothesis profile:
```bash
pytest --hypothesis-profile=ci
```

## Project Structure

```
apps/architectural-service/
├── src/
│   ├── api/              # API layer
│   │   └── v1/
│   │       ├── routes/   # API endpoints
│   │       └── schemas/  # Pydantic schemas
│   ├── core/             # Core configuration
│   ├── infrastructure/   # External service clients
│   ├── models/           # Database models
│   ├── repositories/     # Data access layer
│   ├── services/         # Business logic
│   └── main.py           # Application entry point
├── tests/
│   ├── unit/             # Unit tests
│   ├── integration/      # Integration tests
│   └── property/         # Property-based tests
├── migrations/           # Alembic migrations
├── alembic.ini           # Alembic configuration
├── pytest.ini            # Pytest configuration
├── pyproject.toml        # Project metadata
└── requirements.txt      # Dependencies
```

## API Documentation

When running in development mode, API documentation is available at:
- Swagger UI: http://localhost:8005/docs
- ReDoc: http://localhost:8005/redoc

## Database Migrations

Generate a new migration:
```bash
alembic revision --autogenerate -m "description"
```

Apply migrations:
```bash
alembic upgrade head
```

Rollback one migration:
```bash
alembic downgrade -1
```

View migration history:
```bash
alembic history
```

## Development

### Code Style

This project follows PEP 8 style guidelines.

### Testing Strategy

- **Unit Tests**: Test individual components in isolation
- **Integration Tests**: Test API endpoints and external service interactions
- **Property-Based Tests**: Test universal properties using Hypothesis

All critical business logic should have property-based tests with minimum 100 iterations.

## License

Proprietary - DesignSynapse Platform
