"""
LLM provider configuration classes.
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMProvider(str, Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    AZURE_OPENAI = "azure_openai"
    HUGGINGFACE = "huggingface"
    GROQ = "groq"


class LLMConfig(BaseSettings):
    """LLM provider configuration with fallback mechanisms."""
    
    model_config = SettingsConfigDict(
        env_prefix="LLM_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Primary provider settings
    primary_provider: LLMProvider = LLMProvider.GROQ
    fallback_providers: List[LLMProvider] = Field(default_factory=lambda: [LLMProvider.OPENAI])
    
    # OpenAI settings
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-3.5-turbo"
    openai_max_tokens: int = Field(default=1000, ge=1, le=8000)
    openai_temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    
    # Anthropic settings
    anthropic_api_key: Optional[str] = None
    anthropic_model: str = "claude-3-sonnet-20240229"
    anthropic_max_tokens: int = Field(default=1000, ge=1, le=4000)
    anthropic_temperature: float = Field(default=0.7, ge=0.0, le=1.0)
    
    # Azure OpenAI settings
    azure_openai_api_key: Optional[str] = None
    azure_openai_endpoint: Optional[str] = None
    azure_openai_deployment: Optional[str] = None
    azure_openai_api_version: str = "2023-12-01-preview"
    
    # HuggingFace settings
    huggingface_api_key: Optional[str] = None
    huggingface_model: str = "microsoft/DialoGPT-medium"
    
    # Groq settings
    groq_api_key: Optional[str] = None
    groq_model: str = "llama3-8b-8192"
    groq_max_tokens: int = Field(default=1000, ge=1, le=8000)
    groq_temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    
    # Request settings
    max_retries: int = Field(default=3, ge=0, le=10)
    timeout: int = Field(default=30, ge=1, le=300)
    request_delay: float = Field(default=0.1, ge=0.0, le=5.0)
    
    # Rate limiting
    requests_per_minute: int = Field(default=60, ge=1, le=1000)
    tokens_per_minute: int = Field(default=10000, ge=100, le=100000)
    
    @field_validator("fallback_providers")
    @classmethod
    def validate_fallback_providers(cls, v: List[LLMProvider]) -> List[LLMProvider]:
        """Validate fallback providers list."""
        if len(v) > 3:
            raise ValueError("Maximum 3 fallback providers allowed")
        return v
    
    @model_validator(mode="after")
    def validate_provider_credentials(self) -> "LLMConfig":
        """Validate that required credentials are provided for configured providers."""
        all_providers = [self.primary_provider] + self.fallback_providers
        
        for provider in all_providers:
            if provider == LLMProvider.OPENAI and not self.openai_api_key:
                raise ValueError(
                    f"LLM_OPENAI_API_KEY is required when using {provider.value} provider"
                )
            elif provider == LLMProvider.ANTHROPIC and not self.anthropic_api_key:
                raise ValueError(
                    f"LLM_ANTHROPIC_API_KEY is required when using {provider.value} provider"
                )
            elif provider == LLMProvider.AZURE_OPENAI:
                if not self.azure_openai_api_key:
                    raise ValueError(
                        f"LLM_AZURE_OPENAI_API_KEY is required when using {provider.value} provider"
                    )
                if not self.azure_openai_endpoint:
                    raise ValueError(
                        f"LLM_AZURE_OPENAI_ENDPOINT is required when using {provider.value} provider"
                    )
                if not self.azure_openai_deployment:
                    raise ValueError(
                        f"LLM_AZURE_OPENAI_DEPLOYMENT is required when using {provider.value} provider"
                    )
            elif provider == LLMProvider.HUGGINGFACE and not self.huggingface_api_key:
                raise ValueError(
                    f"LLM_HUGGINGFACE_API_KEY is required when using {provider.value} provider"
                )
            elif provider == LLMProvider.GROQ and not self.groq_api_key:
                raise ValueError(
                    f"LLM_GROQ_API_KEY is required when using {provider.value} provider"
                )
        
        return self
    
    def get_provider_config(self, provider: LLMProvider) -> Dict[str, Any]:
        """Get configuration for a specific provider."""
        if provider == LLMProvider.OPENAI:
            return {
                "api_key": self.openai_api_key,
                "model": self.openai_model,
                "max_tokens": self.openai_max_tokens,
                "temperature": self.openai_temperature,
            }
        elif provider == LLMProvider.ANTHROPIC:
            return {
                "api_key": self.anthropic_api_key,
                "model": self.anthropic_model,
                "max_tokens": self.anthropic_max_tokens,
                "temperature": self.anthropic_temperature,
            }
        elif provider == LLMProvider.AZURE_OPENAI:
            return {
                "api_key": self.azure_openai_api_key,
                "endpoint": self.azure_openai_endpoint,
                "deployment": self.azure_openai_deployment,
                "api_version": self.azure_openai_api_version,
            }
        elif provider == LLMProvider.HUGGINGFACE:
            return {
                "api_key": self.huggingface_api_key,
                "model": self.huggingface_model,
            }
        elif provider == LLMProvider.GROQ:
            return {
                "api_key": self.groq_api_key,
                "model": self.groq_model,
                "max_tokens": self.groq_max_tokens,
                "temperature": self.groq_temperature,
            }
        else:
            raise ValueError(f"Unknown provider: {provider}")
    
    def get_all_providers(self) -> List[LLMProvider]:
        """Get list of all configured providers in priority order."""
        return [self.primary_provider] + self.fallback_providers
    
    def validate_configuration(self) -> None:
        """Validate the complete LLM configuration."""
        # Check that primary provider is not in fallback list
        if self.primary_provider in self.fallback_providers:
            raise ValueError("Primary provider cannot be in fallback providers list")
        
        # Validate rate limiting settings
        if self.requests_per_minute <= 0:
            raise ValueError("requests_per_minute must be positive")
        if self.tokens_per_minute <= 0:
            raise ValueError("tokens_per_minute must be positive")