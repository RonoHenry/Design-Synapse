"""Production configuration management example."""

import os
from pathlib import Path

from fastapi import FastAPI

from packages.common.config import (ConfigLoader, EnvironmentSecretsProvider,
                                    FileSecretsProvider, SecretsManager,
                                    SecurityConfig, SecurityHeadersMiddleware)


def create_production_app():
    """Create a production FastAPI app with proper configuration management."""

    # 1. Load configuration from file with environment overrides
    config_loader = ConfigLoader()

    # Determine environment
    environment = os.getenv("ENVIRONMENT", "development")
    config_file = f"config/config.{environment}.json"

    try:
        # Load base config from file, override with environment variables
        if Path(config_file).exists():
            config = config_loader.load_from_file_and_env(config_file)
        else:
            # Fallback to environment-only configuration
            config = config_loader.load_from_env()
    except Exception as e:
        print(f"Configuration loading failed: {e}")
        raise

    # 2. Set up secrets management with multiple providers
    secrets_providers = [
        EnvironmentSecretsProvider(),  # Check environment first
        FileSecretsProvider("config/secrets.json"),  # Fallback to file
    ]
    secrets_manager = SecretsManager(secrets_providers)

    # 3. Load security configuration
    security_config_file = f"config/security.{environment}.json"
    if Path(security_config_file).exists():
        import json

        with open(security_config_file, "r") as f:
            security_data = json.load(f)
        security_config = SecurityConfig(**security_data)
    else:
        # Use default security configuration
        security_config = SecurityConfig()

    # 4. Create FastAPI app
    app = FastAPI(
        title="DesignSynapse API",
        version="1.0.0",
        debug=config.api.debug if config.api else False,
    )

    # 5. Add security headers middleware
    @app.middleware("http")
    async def add_security_headers(request, call_next):
        response = await call_next(request)

        # Add security headers
        security_middleware = SecurityHeadersMiddleware(security_config.headers)
        headers = security_middleware.get_security_headers()

        for name, value in headers.items():
            response.headers[name] = value

        return response

    # 6. Add configuration and secrets to app state
    app.state.config = config
    app.state.secrets = secrets_manager
    app.state.security_config = security_config

    # 7. Example endpoints showing configuration usage
    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {
            "status": "healthy",
            "environment": environment,
            "database_host": config.database.host,
            "debug_mode": config.api.debug if config.api else False,
        }

    @app.get("/config/info")
    async def config_info():
        """Get non-sensitive configuration information."""
        return {
            "database": {
                "host": config.database.host,
                "port": config.database.port,
                "name": config.database.name,
                "user": config.database.user
                # Note: password is not included for security
            },
            "redis": {
                "host": config.redis.host,
                "port": config.redis.port,
                "db": config.redis.db,
            }
            if config.redis
            else None,
            "api": {
                "host": config.api.host,
                "port": config.api.port,
                "debug": config.api.debug
                # Note: secret_key is not included for security
            }
            if config.api
            else None,
            "security": {
                "ssl_enabled": security_config.ssl.enabled,
                "hsts_enabled": security_config.headers.hsts_enabled,
                "hsts_max_age": security_config.headers.hsts_max_age,
            },
        }

    @app.get("/secrets/test")
    async def test_secrets():
        """Test secrets access (for development only)."""
        if config.api and config.api.debug:
            try:
                # Get a masked secret for logging
                masked_db_password = secrets_manager.get_secret(
                    "DATABASE_PASSWORD", mask_in_logs=True
                )

                return {
                    "secrets_available": True,
                    "database_password_masked": str(masked_db_password),
                    "api_key_exists": secrets_manager.get_secret("API_SECRET_KEY")
                    is not None,
                }
            except Exception as e:
                return {"error": str(e)}
        else:
            return {"error": "Secrets endpoint only available in debug mode"}

    return app


def main():
    """Main entry point for production deployment."""
    import uvicorn

    # Create the app
    app = create_production_app()

    # Get configuration for server settings
    config = app.state.config
    security_config = app.state.security_config

    # Determine server configuration
    host = config.api.host if config.api else "0.0.0.0"
    port = config.api.port if config.api else 8000

    # SSL configuration
    ssl_keyfile = None
    ssl_certfile = None
    if security_config.ssl.enabled:
        ssl_keyfile = security_config.ssl.key_file
        ssl_certfile = security_config.ssl.cert_file

    # Run the server
    uvicorn.run(
        app,
        host=host,
        port=port,
        ssl_keyfile=ssl_keyfile,
        ssl_certfile=ssl_certfile,
        access_log=True,
        log_level="info",
    )


if __name__ == "__main__":
    main()
