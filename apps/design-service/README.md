# Design Service

AI-powered architectural design generation, validation, and optimization service for DesignSynapse.

## Overview

The Design Service provides intelligent design assistance including:
- AI-powered architectural design generation
- Design validation and feedback
- Design optimization suggestions
- Design pattern recommendations
- Component relationship analysis

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. Run the service:
```bash
uvicorn src.main:app --reload --port 8003
```

## Project Structure

```
apps/design-service/
├── src/
│   ├── api/              # API routes and endpoints
│   ├── core/             # Core configuration and utilities
│   ├── models/           # SQLAlchemy models
│   ├── repositories/     # Data access layer
│   ├── services/         # Business logic
│   ├── infrastructure/   # External integrations (LLM, etc.)
│   └── main.py          # FastAPI application
├── tests/
│   ├── unit/            # Unit tests
│   └── integration/     # Integration tests
├── migrations/          # Alembic database migrations
└── requirements.txt     # Python dependencies
```

## API Documentation

Once running, visit:
- Swagger UI: http://localhost:8003/docs
- ReDoc: http://localhost:8003/redoc

## Testing

Run tests with pytest:
```bash
pytest
```

With coverage:
```bash
pytest --cov=src --cov-report=html
```
