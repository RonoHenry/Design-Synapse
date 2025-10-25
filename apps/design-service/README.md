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

## Performance Optimization

### Building Code Rule Caching

The ValidationService implements an in-memory caching system for building code rules to improve performance:

#### Caching Strategy

- **Cache Storage**: Rule sets are cached in memory after first load
- **TTL (Time-to-Live)**: Default 1 hour (3600 seconds), configurable via `cache_ttl` parameter
- **Automatic Invalidation**: Cache entries are automatically invalidated when:
  - The TTL expires
  - The source rule file is modified (detected via file modification time)
- **Manual Invalidation**: Cache can be manually cleared using `clear_cache()` method
- **Cache Statistics**: Track hits, misses, hit rate, and cache size for monitoring

#### Usage

```python
from src.services.validation_service import RuleEngine

# Create rule engine with default 1-hour cache TTL
rule_engine = RuleEngine()

# Create with custom cache TTL (in seconds)
rule_engine = RuleEngine(cache_ttl=7200)  # 2 hours

# Load rule set (first load is cached)
rule_set = rule_engine.load_rule_set("Kenya_Building_Code_2020")

# Subsequent loads use cache (if not expired and file not modified)
rule_set = rule_engine.load_rule_set("Kenya_Building_Code_2020")

# Get cache statistics
stats = rule_engine.get_cache_stats()
print(f"Cache hit rate: {stats['hit_rate']}%")
print(f"Cached items: {stats['cached_items']}")

# Clear specific rule set from cache
rule_engine.clear_cache("Kenya_Building_Code_2020")

# Clear entire cache
rule_engine.clear_cache()
```

#### Benefits

- **Performance**: Reduces file I/O and JSON parsing overhead for repeated validations
- **Scalability**: Enables handling multiple concurrent validation requests efficiently
- **Freshness**: Automatic invalidation ensures rule updates are detected
- **Monitoring**: Cache statistics help identify performance bottlenecks

#### Configuration

The cache TTL can be configured when initializing the RuleEngine:

```python
# Short TTL for development (5 minutes)
rule_engine = RuleEngine(cache_ttl=300)

# Long TTL for production (4 hours)
rule_engine = RuleEngine(cache_ttl=14400)

# Disable caching (always reload)
rule_engine = RuleEngine(cache_ttl=0)
```

## Testing

Run tests with pytest:
```bash
pytest
```

With coverage:
```bash
pytest --cov=src --cov-report=html
```

Run specific test suites:
```bash
# Test caching functionality
pytest tests/unit/services/test_validation_service.py::TestRuleEngineCaching -v

# Test all validation service tests
pytest tests/unit/services/test_validation_service.py -v
```
