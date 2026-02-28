# Engineering Service

Comprehensive engineering analysis, calculations, and design capabilities for structural, MEP, and civil engineering disciplines.

## Features

- **Structural Engineering**: Load calculations, beam/column/foundation design per ASCE 7 and IBC
- **MEP Systems**: HVAC, electrical, plumbing, and fire protection design per ASHRAE, NEC, IPC, NFPA
- **Civil Engineering**: Site grading, stormwater management, utility design
- **Code Compliance**: Automated verification against building codes
- **Document Management**: Versioned calculation sheets and technical specifications
- **Unit Support**: Both Imperial and Metric unit systems

## Tech Stack

- **Framework**: FastAPI
- **Database**: TiDB/MySQL with SQLAlchemy
- **Cache**: Redis
- **Testing**: Pytest with Hypothesis for property-based testing
- **Authentication**: JWT tokens

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Copy environment file:
```bash
cp .env.example .env
```

3. Run database migrations:
```bash
alembic upgrade head
```

4. Start the service:
```bash
uvicorn src.main:app --reload --port 8006
```

## Testing

Run all tests:
```bash
pytest
```

Run specific test types:
```bash
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests only
pytest -m property      # Property-based tests only
```

## API Documentation

Once running, visit:
- Swagger UI: http://localhost:8006/docs
- ReDoc: http://localhost:8006/redoc

## Project Structure

```
apps/engineering-service/
├── src/
│   ├── api/              # API routes and endpoints
│   ├── calculations/     # Engineering calculation engines
│   ├── core/             # Core configuration and utilities
│   ├── integrations/     # External service clients
│   ├── models/           # Database models
│   ├── repositories/     # Data access layer
│   ├── services/         # Business logic
│   └── validators/       # Code compliance validators
├── tests/
│   ├── unit/             # Unit tests
│   ├── integration/      # Integration tests
│   └── property/         # Property-based tests
└── migrations/           # Database migrations
```

## Development

Follow TDD methodology:
1. Write tests first
2. Implement minimal code to pass tests
3. Refactor while keeping tests green

## License

Proprietary - DesignSynapse Platform
