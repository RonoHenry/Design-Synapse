"""
Example usage of the configuration classes.

This file demonstrates how to use the unified configuration management system
across different services in the DesignSynapse architecture.
"""

import os
import sys
from pathlib import Path
from typing import Optional

# Add the packages directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from common.config import (
    BaseServiceConfig, 
    Environment,
    DatabaseConfig,
    LLMConfig, 
    LLMProvider,
    VectorConfig, 
    VectorProvider, 
    VectorMetric
)


class UserServiceConfig:
    """Configuration for the User Service."""
    
    def __init__(self, **kwargs):
        # Initialize base configuration
        self.base = BaseServiceConfig(
            service_name="user-service",
            service_version="1.0.0",
            port=8001,
            **kwargs
        )
        
        # Initialize sub-configurations
        self.database = DatabaseConfig()
        
        # JWT-specific settings
        self.jwt_secret_key: Optional[str] = os.getenv("JWT_SECRET_KEY")
        self.jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
        self.jwt_expiration_hours: int = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))
        
        # Validate configuration
        self._validate_user_service_config()
    
    @property
    def service_name(self) -> str:
        return self.base.service_name
    
    @property
    def port(self) -> int:
        return self.base.port
    
    @property
    def environment(self) -> Environment:
        return self.base.environment
    
    def is_production(self) -> bool:
        return self.base.is_production()
    
    def _validate_user_service_config(self) -> None:
        """Validate user service specific configuration."""
        self.database.validate_connection_settings()
        
        if self.is_production() and not self.jwt_secret_key:
            raise ValueError("JWT_SECRET_KEY is required in production")
        
        if self.jwt_expiration_hours <= 0:
            raise ValueError("JWT_EXPIRATION_HOURS must be positive")


class KnowledgeServiceConfig:
    """Configuration for the Knowledge Service."""
    
    def __init__(self, **kwargs):
        # Initialize base configuration
        self.base = BaseServiceConfig(
            service_name="knowledge-service",
            service_version="1.0.0",
            port=8002,
            **kwargs
        )
        
        # Initialize sub-configurations
        self.database = DatabaseConfig()
        self.llm = LLMConfig()
        self.vector = VectorConfig()
        
        # Service-specific settings
        self.max_file_size_mb: int = int(os.getenv("MAX_FILE_SIZE_MB", "50"))
        self.supported_file_types: list = os.getenv(
            "SUPPORTED_FILE_TYPES", 
            "pdf,docx,txt,md"
        ).split(",")
        
        # Validate configuration
        self._validate_knowledge_service_config()
    
    @property
    def service_name(self) -> str:
        return self.base.service_name
    
    @property
    def port(self) -> int:
        return self.base.port
    
    @property
    def environment(self) -> Environment:
        return self.base.environment
    
    def _validate_knowledge_service_config(self) -> None:
        """Validate knowledge service specific configuration."""
        self.database.validate_connection_settings()
        self.llm.validate_configuration()
        self.vector.validate_configuration()
        
        if self.max_file_size_mb <= 0:
            raise ValueError("MAX_FILE_SIZE_MB must be positive")
        
        if not self.supported_file_types:
            raise ValueError("SUPPORTED_FILE_TYPES cannot be empty")


class ProjectServiceConfig:
    """Configuration for the Project Service."""
    
    def __init__(self, **kwargs):
        # Initialize base configuration
        self.base = BaseServiceConfig(
            service_name="project-service",
            service_version="1.0.0",
            port=8003,
            **kwargs
        )
        
        # Initialize sub-configurations
        self.database = DatabaseConfig()
        
        # Project-specific settings
        self.max_projects_per_user: int = int(os.getenv("MAX_PROJECTS_PER_USER", "10"))
        self.project_name_max_length: int = int(os.getenv("PROJECT_NAME_MAX_LENGTH", "100"))
        self.enable_project_sharing: bool = os.getenv("ENABLE_PROJECT_SHARING", "true").lower() == "true"
        
        # Validate configuration
        self._validate_project_service_config()
    
    @property
    def service_name(self) -> str:
        return self.base.service_name
    
    @property
    def port(self) -> int:
        return self.base.port
    
    @property
    def environment(self) -> Environment:
        return self.base.environment
    
    def _validate_project_service_config(self) -> None:
        """Validate project service specific configuration."""
        self.database.validate_connection_settings()
        
        if self.max_projects_per_user <= 0:
            raise ValueError("MAX_PROJECTS_PER_USER must be positive")
        
        if self.project_name_max_length <= 0:
            raise ValueError("PROJECT_NAME_MAX_LENGTH must be positive")


def create_service_config(service_name: str):
    """Factory function to create service-specific configuration."""
    if service_name == "user-service":
        return UserServiceConfig()
    elif service_name == "knowledge-service":
        return KnowledgeServiceConfig()
    elif service_name == "project-service":
        return ProjectServiceConfig()
    else:
        raise ValueError(f"Unknown service: {service_name}")


def example_usage():
    """Demonstrate configuration usage."""
    print("Configuration Examples")
    print("=" * 50)
    
    # Example 1: User Service Configuration
    print("\n1. User Service Configuration:")
    try:
        # Set required environment variables for demo
        os.environ.update({
            "DB_USERNAME": "user_service",
            "DB_PASSWORD": "secure_password",
            "DB_DATABASE": "user_db",
            "JWT_SECRET_KEY": "your-secret-key-here",
            "ENVIRONMENT": "development"
        })
        
        user_config = UserServiceConfig()
        print(f"   Service: {user_config.service_name}")
        print(f"   Port: {user_config.port}")
        print(f"   Environment: {user_config.environment}")
        print(f"   Database URL: {user_config.database.get_connection_url()}")
        print(f"   JWT Algorithm: {user_config.jwt_algorithm}")
        
    except Exception as e:
        print(f"   Error: {e}")
    
    # Example 2: Knowledge Service Configuration
    print("\n2. Knowledge Service Configuration:")
    try:
        # Set required environment variables for demo
        os.environ.update({
            "DB_USERNAME": "knowledge_service",
            "DB_PASSWORD": "secure_password",
            "DB_DATABASE": "knowledge_db",
            "LLM_OPENAI_API_KEY": "your-openai-key",
            "LLM_ANTHROPIC_API_KEY": "your-anthropic-key",  # Required for fallback
            "VECTOR_PINECONE_API_KEY": "your-pinecone-key",
            "VECTOR_PINECONE_ENVIRONMENT": "your-pinecone-env"
        })
        
        knowledge_config = KnowledgeServiceConfig()
        print(f"   Service: {knowledge_config.service_name}")
        print(f"   Port: {knowledge_config.port}")
        print(f"   LLM Provider: {knowledge_config.llm.primary_provider}")
        print(f"   Vector Provider: {knowledge_config.vector.provider}")
        print(f"   Max File Size: {knowledge_config.max_file_size_mb}MB")
        
    except Exception as e:
        print(f"   Error: {e}")
    
    # Example 3: Environment-specific configuration
    print("\n3. Environment-specific Configuration:")
    
    # Development
    os.environ["ENVIRONMENT"] = "development"
    dev_config = BaseServiceConfig(service_name="test-service")
    print(f"   Development - Debug: {dev_config.debug}")
    print(f"   Development - Log Level: {dev_config.log_level}")
    
    # Production
    os.environ.update({
        "ENVIRONMENT": "production",
        "SECRET_KEY": "production-secret-key",
        "LOG_LEVEL": "WARNING"
    })
    prod_config = BaseServiceConfig(service_name="test-service")
    print(f"   Production - Debug: {prod_config.debug}")
    print(f"   Production - Log Level: {prod_config.log_level}")
    
    print("\n✓ Configuration examples completed successfully!")


if __name__ == "__main__":
    example_usage()