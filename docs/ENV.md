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

## Database Naming Conventions

DesignSynapse uses separate databases for each microservice to ensure data isolation and independent scaling:

| Service | Database Name | Purpose |
|---------|--------------|---------|
| User Service | `design_synapse_user_db` | User accounts, authentication, roles, permissions |
| Project Service | `design_synapse_project_db` | Projects, tasks, comments, collaboration |
| Knowledge Service | `design_synapse_knowledge_db` | Resources, bookmarks, citations, search |

**Naming Pattern**: `design_synapse_{service}_db`

**Character Set**: All databases use `utf8mb4` with `utf8mb4_unicode_ci` collation for full Unicode support.

**Creation Example**:
```sql
CREATE DATABASE IF NOT EXISTS design_synapse_user_db 
CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;
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

# TiDB Serverless Database Configuration
# TiDB is a MySQL-compatible distributed SQL database with auto-scaling
DATABASE_HOST=gateway01.eu-central-1.prod.aws.tidbcloud.com
DATABASE_PORT=4000
DATABASE_USER=your_cluster_id.root
DATABASE_PASSWORD=your_secure_password

# SSL Configuration (REQUIRED for TiDB Serverless)
# Download ca.pem from TiDB Cloud console
DATABASE_SSL_CA=./ca.pem
DATABASE_SSL_VERIFY_CERT=true
DATABASE_SSL_VERIFY_IDENTITY=true

# Service-specific databases (each service has its own database)
USER_SERVICE_DB=design_synapse_user_db
PROJECT_SERVICE_DB=design_synapse_project_db
KNOWLEDGE_SERVICE_DB=design_synapse_knowledge_db

# Connection Pool Settings (optimized for TiDB)
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20
DATABASE_POOL_RECYCLE=3600

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
    # TiDB Database Configuration
    database_host: str
    database_port: int = 4000
    database_user: str
    database_password: str
    database_name: str  # Service-specific database (e.g., design_synapse_user_db)
    
    # SSL Configuration (required for TiDB Serverless)
    database_ssl_ca: str = "./ca.pem"
    database_ssl_verify_cert: bool = True
    database_ssl_verify_identity: bool = True
    
    # Connection Pool Settings
    database_pool_size: int = 10
    database_max_overflow: int = 20
    database_pool_recycle: int = 3600

    # Service specific
    model_endpoint: str
    model_api_key: str

    class Config:
        env_file = f".env.{env_name}"
    
    @property
    def database_url(self) -> str:
        """
        Construct TiDB connection URL with SSL parameters.
        
        Format: mysql+pymysql://user:pass@host:port/db?ssl_params
        
        TiDB Serverless requires:
        - mysql+pymysql dialect (MySQL-compatible)
        - SSL/TLS encryption
        - utf8mb4 character set for full Unicode support
        """
        return (
            f"mysql+pymysql://{self.database_user}:{self.database_password}"
            f"@{self.database_host}:{self.database_port}/{self.database_name}"
            f"?ssl_ca={self.database_ssl_ca}"
            f"&ssl_verify_cert={str(self.database_ssl_verify_cert).lower()}"
            f"&ssl_verify_identity={str(self.database_ssl_verify_identity).lower()}"
            f"&charset=utf8mb4"
        )

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
    """
    Validate required environment variables for TiDB connection.
    
    TiDB Serverless requires:
    - Database connection parameters
    - SSL certificate for encrypted connection
    - Service-specific database name
    """
    required_vars = [
        'DATABASE_HOST',
        'DATABASE_PORT',
        'DATABASE_USER',
        'DATABASE_PASSWORD',
        'DATABASE_SSL_CA',
        'MODEL_ENDPOINT',
        'AWS_ACCESS_KEY_ID'
    ]

    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        raise ValueError(f"Missing required environment variables: {missing}")
    
    # Validate TiDB SSL certificate exists (required for TiDB Serverless)
    ssl_ca_path = os.getenv('DATABASE_SSL_CA')
    if ssl_ca_path and not os.path.exists(ssl_ca_path):
        raise ValueError(
            f"TiDB SSL certificate not found at: {ssl_ca_path}\n"
            f"Download ca.pem from TiDB Cloud console: "
            f"https://tidbcloud.com/console/clusters"
        )
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
