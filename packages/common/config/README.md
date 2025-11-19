# Configuration Management System

This module provides unified configuration management for DesignSynapse services using Pydantic Settings v2 with proper environment variable validation and clear error messages.

## Features

- **Unified Configuration**: Consistent configuration patterns across all services
- **Environment Variable Validation**: Automatic validation with clear error messages
- **Type Safety**: Full type hints and runtime validation
- **Environment-Specific Settings**: Support for development, testing, and production environments
- **Provider Abstraction**: Support for multiple LLM and vector database providers
- **Connection Management**: Database connection pooling and SSL configuration
- **Fallback Mechanisms**: LLM provider fallbacks and graceful degradation

## Configuration Classes

### BaseServiceConfig

Base configuration class that all services should inherit from.

```python
from packages.common.config import BaseServiceConfig, Environment

config = BaseServiceConfig(
    service_name="my-service",
    environment=Environment.DEVELOPMENT,
    port=8000
)
```

**Environment Variables:**
- `ENVIRONMENT`: development, testing, or production
- `DEBUG`: Enable debug mode (default: False)
- `SECRET_KEY`: Required in production
- `LOG_LEVEL`: Logging level (default: INFO)
- `HOST`: Service host (default: 0.0.0.0)
- `PORT`: Service port (default: 8000)

### DatabaseConfig

Database configuration with connection pooling and SSL support.

```python
from packages.common.config import DatabaseConfig

db_config = DatabaseConfig()
connection_url = db_config.get_connection_url()
engine_kwargs = db_config.get_engine_kwargs()
```

**Environment Variables:**
- `DB_HOST`: Database host (default: localhost)
- `DB_PORT`: Database port (default: 5432)
- `DB_USERNAME`: Database username (required)
- `DB_PASSWORD`: Database password (required)
- `DB_DATABASE`: Database name (required)
- `DB_POOL_SIZE`: Connection pool size (default: 10)
- `DB_MAX_OVERFLOW`: Max overflow connections (default: 20)
- `DB_SSL_MODE`: SSL mode (default: prefer)

### LLMConfig

LLM provider configuration with fallback mechanisms.

```python
from packages.common.config import LLMConfig, LLMProvider

llm_config = LLMConfig(
    primary_provider=LLMProvider.OPENAI,
    fallback_providers=[LLMProvider.ANTHROPIC]
)
```

**Supported Providers:**
- OpenAI (GPT models)
- Anthropic (Claude models)
- Azure OpenAI
- HuggingFace

**Environment Variables:**
- `LLM_PRIMARY_PROVIDER`: Primary LLM provider
- `LLM_OPENAI_API_KEY`: OpenAI API key
- `LLM_ANTHROPIC_API_KEY`: Anthropic API key
- `LLM_MAX_RETRIES`: Max retry attempts (default: 3)
- `LLM_TIMEOUT`: Request timeout in seconds (default: 30)

### VectorConfig

Vector database configuration with multiple provider support.

```python
from packages.common.config import VectorConfig, VectorProvider

vector_config = VectorConfig(
    provider=VectorProvider.PINECONE,
    dimension=384
)
```

**Supported Providers:**
- Pinecone
- Weaviate
- Qdrant
- Chroma

**Environment Variables:**
- `VECTOR_PROVIDER`: Vector database provider
- `VECTOR_PINECONE_API_KEY`: Pinecone API key
- `VECTOR_PINECONE_ENVIRONMENT`: Pinecone environment
- `VECTOR_DIMENSION`: Vector dimension (default: 384)
- `VECTOR_TOP_K`: Search results limit (default: 10)

## Usage Examples

### Service-Specific Configuration

```python
from packages.common.config import BaseServiceConfig, DatabaseConfig, LLMConfig

class MyServiceConfig(BaseServiceConfig):
    def __init__(self, **kwargs):
        super().__init__(
            service_name="my-service",
            port=8001,
            **kwargs
        )
        
        # Initialize sub-configurations
        self.database = DatabaseConfig()
        self.llm = LLMConfig()
        
        # Service-specific settings
        self.custom_setting = os.getenv("CUSTOM_SETTING", "default")
        
        # Validate configuration
        self._validate_config()
    
    def _validate_config(self):
        self.database.validate_connection_settings()
        self.llm.validate_configuration()
```

### Environment-Specific Configuration

```python
# .env file
ENVIRONMENT=development
DEBUG=true
DB_USERNAME=dev_user
DB_PASSWORD=dev_pass
DB_DATABASE=dev_db
LLM_OPENAI_API_KEY=your-dev-key

# Production overrides
ENVIRONMENT=production
DEBUG=false
SECRET_KEY=your-production-secret
LOG_LEVEL=WARNING
```

### Error Handling

The configuration system provides clear error messages for common issues:

```python
try:
    config = DatabaseConfig()
    config.validate_connection_settings()
except ValueError as e:
    print(f"Configuration error: {e}")
    # Output: "DB_USERNAME environment variable is required"
```

## Testing

Run the configuration tests to verify everything works:

```bash
python packages/common/config/test_config.py
```

## Migration from Legacy Configuration

### Before (Legacy Pattern)
```python
# Old hardcoded configuration
DATABASE_URL = "postgresql://user:pass@localhost/db"
OPENAI_API_KEY = "hardcoded-key"
DEBUG = True
```

### After (New Pattern)
```python
from packages.common.config import BaseServiceConfig, DatabaseConfig, LLMConfig

class ServiceConfig(BaseServiceConfig):
    def __init__(self):
        super().__init__(service_name="my-service")
        self.database = DatabaseConfig()
        self.llm = LLMConfig()

config = ServiceConfig()
database_url = config.database.get_connection_url()
```

## Best Practices

1. **Inherit from BaseServiceConfig**: Always extend the base configuration class
2. **Validate Early**: Call validation methods during initialization
3. **Use Environment Variables**: Never hardcode sensitive values
4. **Provide Defaults**: Use sensible defaults for non-critical settings
5. **Document Variables**: Clearly document required environment variables
6. **Test Configuration**: Write tests for your configuration classes
7. **Handle Errors Gracefully**: Provide clear error messages for configuration issues

## Environment Variable Reference

### Required Variables (Production)
- `SECRET_KEY`: Application secret key
- `DB_USERNAME`: Database username
- `DB_PASSWORD`: Database password
- `DB_DATABASE`: Database name

### LLM Provider Variables
- `LLM_OPENAI_API_KEY`: Required for OpenAI
- `LLM_ANTHROPIC_API_KEY`: Required for Anthropic
- `LLM_AZURE_OPENAI_API_KEY`: Required for Azure OpenAI
- `LLM_AZURE_OPENAI_ENDPOINT`: Required for Azure OpenAI

### Vector Database Variables
- `VECTOR_PINECONE_API_KEY`: Required for Pinecone
- `VECTOR_PINECONE_ENVIRONMENT`: Required for Pinecone
- `VECTOR_WEAVIATE_URL`: Required for Weaviate
- `VECTOR_QDRANT_URL`: Required for Qdrant

### Optional Variables
- `ENVIRONMENT`: development (default), testing, production
- `DEBUG`: true/false (default: false)
- `LOG_LEVEL`: DEBUG, INFO, WARNING, ERROR (default: INFO)
- `HOST`: Service host (default: 0.0.0.0)
- `PORT`: Service port (default: 8000)
--
-

# Production Configuration Management System (TDD Implementation)

A comprehensive, production-ready configuration management system built using Test-Driven Development (TDD).

## New Features (Production System)

### 🔧 Advanced Configuration Loading
- **Multi-source configuration**: Load from JSON files, environment variables, or both
- **Environment-specific configs**: Support for dev, staging, prod configurations
- **Validation**: Pydantic-based validation with clear error messages
- **Type safety**: Full type hints and IDE support

### 🔐 Secrets Management
- **Multiple providers**: Environment variables, JSON files, extensible provider system
- **Fallback support**: Try multiple providers in order
- **Security**: Automatic secret masking in logs and string representations
- **Production-ready**: Secure secret handling for production deployments

### 🛡️ Security Configuration
- **SSL/TLS support**: Complete SSL configuration with validation
- **Security headers**: Production-ready security headers middleware
- **HSTS, CSP, X-Frame-Options**: All modern security headers supported
- **Customizable**: Flexible configuration for different security requirements

## Production Configuration Usage

### Configuration Loading with Environment Overrides

```python
from packages.common.config import ConfigLoader

# Load configuration from file with environment overrides
loader = ConfigLoader()
config = loader.load_from_file_and_env("config/config.prod.json")

print(f"Database: {config.database.host}:{config.database.port}")
print(f"API Debug: {config.api.debug}")
```

### Secrets Management

```python
from packages.common.config import SecretsManager, EnvironmentSecretsProvider, FileSecretsProvider

# Set up secrets with multiple providers
providers = [
    EnvironmentSecretsProvider(),  # Check environment first
    FileSecretsProvider("config/secrets.json")  # Fallback to file
]
secrets = SecretsManager(providers)

# Get secrets safely
db_password = secrets.get_secret("DATABASE_PASSWORD")
api_key = secrets.get_secret("API_SECRET_KEY", mask_in_logs=True)  # Masked in logs
```

### Security Headers Middleware

```python
from fastapi import FastAPI
from packages.common.config import SecurityHeadersConfig, SecurityHeadersMiddleware

app = FastAPI()
security_config = SecurityHeadersConfig(
    hsts_enabled=True,
    hsts_max_age=31536000,  # 1 year
    content_security_policy="default-src 'self'; script-src 'self' 'unsafe-inline'"
)

@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    
    middleware = SecurityHeadersMiddleware(security_config)
    headers = middleware.get_security_headers()
    
    for name, value in headers.items():
        response.headers[name] = value
    
    return response
```

## Production Configuration Schema

### Main Configuration

```json
{
    "database": {
        "host": "localhost",
        "port": 5432,
        "name": "app_db",
        "user": "app_user",
        "password": "secret"
    },
    "redis": {
        "host": "localhost", 
        "port": 6379,
        "db": 0
    },
    "api": {
        "host": "0.0.0.0",
        "port": 8000,
        "debug": false,
        "secret_key": "api-secret"
    }
}
```

### Security Configuration

```json
{
    "ssl": {
        "enabled": true,
        "cert_file": "/etc/ssl/certs/app.crt",
        "key_file": "/etc/ssl/private/app.key",
        "ca_file": "/etc/ssl/certs/ca.crt"
    },
    "headers": {
        "hsts_enabled": true,
        "hsts_max_age": 31536000,
        "content_security_policy": "default-src 'self'",
        "x_frame_options": "DENY"
    }
}
```

## Production Environment Variables

```bash
# Environment
ENVIRONMENT=production

# Database (required)
DATABASE_HOST=prod-db.cluster.local
DATABASE_PASSWORD=<secure-password>

# API secrets (required)
API_SECRET_KEY=<secure-api-key>

# Optional overrides
API_PORT=80
REDIS_URL=redis://redis.cluster.local:6379/0

# SSL certificate paths
SSL_CERT_FILE=/etc/ssl/certs/app.crt
SSL_KEY_FILE=/etc/ssl/private/app.key
```

## Testing the Production System

The production configuration system is built using TDD with comprehensive test coverage:

```bash
# Run all production config tests
python -m pytest packages/common/config/tests/ -v

# Run specific test categories
python -m pytest packages/common/config/tests/test_config_loader.py -v
python -m pytest packages/common/config/tests/test_secrets_manager.py -v
python -m pytest packages/common/config/tests/test_security_config.py -v
python -m pytest packages/common/config/tests/test_integration.py -v
```

## Production API Reference

### ConfigLoader

```python
class ConfigLoader:
    def load_from_file(self, file_path: str) -> ConfigSchema
    def load_from_env(self) -> ConfigSchema  
    def load_from_file_and_env(self, file_path: str) -> ConfigSchema
```

### SecretsManager

```python
class SecretsManager:
    def __init__(self, providers: Union[SecretsProvider, List[SecretsProvider]])
    def get_secret(self, key: str, default: Optional[str] = None, mask_in_logs: bool = False) -> Union[str, MaskedSecret]
```

### SecurityHeadersMiddleware

```python
class SecurityHeadersMiddleware:
    def __init__(self, config: SecurityHeadersConfig)
    def get_security_headers(self) -> Dict[str, str]
```

## Complete Production Example

See `production_example.py` for a complete example of setting up a production FastAPI application with:
- Full configuration management
- Secrets handling with multiple providers
- Security headers middleware
- SSL/TLS configuration
- Environment-specific settings

## Requirements Satisfied

This production configuration system satisfies:

- ✅ **4.1**: Environment-specific configuration loading
- ✅ **4.2**: Configuration validation with clear error messages  
- ✅ **4.3**: SSL/TLS configuration and security headers
- ✅ **4.5**: Secrets management with secure storage
- ✅ **6.1**: HTTPS enforcement and security headers