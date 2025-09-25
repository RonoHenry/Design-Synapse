# Environment Configuration Guide

## Overview

This document outlines the environment configuration strategy for DesignSynapse, covering all microservices and deployment environments.

## Environment Types

1. **Local Development** (`development`)
   - Individual developer machines
   - Local databases
   - Mock external services

2. **Testing** (`test`)
   - Used for automated tests
   - Isolated test databases
   - Mock external services

3. **Staging** (`staging`)
   - Production-like environment
   - Staging databases
   - Staging external service credentials

4. **Production** (`production`)
   - Live environment
   - Production databases
   - Real external service credentials

## Environment Files Structure

```
.env.example                 # Template with all possible variables
.env.local                  # Local overrides (git-ignored)
.env.test                   # Testing environment variables
.env.staging               # Staging environment variables
.env.production           # Production environment variables

apps/
├── design-service/
│   ├── .env.example
│   ├── .env.local
│   ├── .env.test
│   ├── .env.staging
│   └── .env.production
├── user-service/
│   ├── .env.example
│   ├── .env.local
│   ├── .env.test
│   ├── .env.staging
│   └── .env.production
└── frontend/
    ├── .env.example
    ├── .env.local
    ├── .env.test
    ├── .env.staging
    └── .env.production
```

## Environment Variables

### Common Variables (Root Level)

```env
# General
NODE_ENV=development|test|staging|production
DEBUG=true|false

# Services
DESIGN_SERVICE_URL=http://localhost:8000
USER_SERVICE_URL=http://localhost:8001
FRONTEND_URL=http://localhost:3000

# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=designsynapse

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=

# JWT
JWT_SECRET=your-secret-key
JWT_EXPIRATION=24h

# AWS
AWS_REGION=us-west-2
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
```

### Design Service Variables

```env
# AI Model Configuration
MODEL_ENDPOINT=http://localhost:8002
MODEL_API_KEY=your-api-key
MODEL_VERSION=v1

# Storage
DESIGN_STORAGE_BUCKET=designs-bucket
DESIGN_CACHE_TTL=3600

# Performance
MAX_CONCURRENT_GENERATIONS=5
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=15m
```

### User Service Variables

```env
# Authentication
AUTH_PROVIDER=oauth2
OAUTH_CLIENT_ID=your-client-id
OAUTH_CLIENT_SECRET=your-client-secret
OAUTH_CALLBACK_URL=http://localhost:8001/auth/callback

# User Preferences
DEFAULT_THEME=light
SESSION_DURATION=24h
```

### Frontend Variables

```env
# Next.js
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000

# Feature Flags
NEXT_PUBLIC_ENABLE_3D_VIEWER=true
NEXT_PUBLIC_ENABLE_REAL_TIME=true

# Analytics
NEXT_PUBLIC_ANALYTICS_ID=your-analytics-id
```

## Security Guidelines

1. **Never commit sensitive values**
   - Keep `.env.local` and `.env.production` in `.gitignore`
   - Use secrets management in production

2. **Use strong values**
   - Long random strings for secrets
   - Different values per environment
   - Regular rotation schedule

3. **Access Control**
   - Restrict access to production credentials
   - Use role-based access control
   - Audit access logs

## Setup Instructions

### Local Development

1. Copy example files:
```bash
cp .env.example .env.local
cd apps/design-service && cp .env.example .env.local
cd apps/user-service && cp .env.example .env.local
cd apps/frontend && cp .env.example .env.local
```

2. Update local values in each `.env.local`

### CI/CD Setup

1. Add environment variables to CI/CD platform
2. Use different variables per environment
3. Encrypt sensitive values

### Production Deployment

1. Use secrets management service
2. Implement automatic rotation
3. Monitor for exposed secrets

## Loading Environments

### Python (FastAPI) Services

```python
from functools import lru_cache
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Database
    postgres_host: str
    postgres_port: int
    postgres_user: str
    postgres_password: str
    postgres_db: str

    # Service specific
    model_endpoint: str
    model_api_key: str

    class Config:
        env_file = f".env.{env_name}"

@lru_cache()
def get_settings():
    return Settings()
```

### Next.js Frontend

```typescript
// next.config.js
module.exports = {
  env: {
    API_URL: process.env.NEXT_PUBLIC_API_URL,
    WS_URL: process.env.NEXT_PUBLIC_WS_URL,
  }
}
```

## Environment Validation

### Service Startup Checks

1. Required variables present
2. Variable format correct
3. Services accessible
4. Credentials valid

Example validation:
```python
def validate_environment():
    required_vars = [
        'POSTGRES_HOST',
        'POSTGRES_PORT',
        'MODEL_ENDPOINT',
        'AWS_ACCESS_KEY_ID'
    ]

    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        raise ValueError(f"Missing required environment variables: {missing}")
```

## Development Workflow

1. Copy `.env.example` to `.env.local`
2. Update values for local development
3. Never commit `.env.local`
4. Update `.env.example` when adding new variables

## Troubleshooting

Common issues and solutions:

1. **Missing Variables**
   - Check `.env.example` for required variables
   - Verify environment file naming
   - Confirm environment loading

2. **Invalid Values**
   - Check variable format
   - Verify service URLs
   - Confirm credential validity

3. **Environment Loading**
   - Verify file location
   - Check file permissions
   - Confirm loading method
