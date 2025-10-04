"""LLM service implementation."""

from typing import Type, Dict, Any
from .base import BaseLLMProvider
from .openai_provider import OpenAIProvider
from .huggingface_provider import HuggingFaceProvider


class LLMService:
    """LLM service that supports multiple providers."""

    PROVIDERS = {
        'openai': OpenAIProvider,
        'huggingface': HuggingFaceProvider,
    }

    def __init__(self, provider_name: str = 'openai', provider_config: Dict[str, Any] = None):
        """
        Initialize LLM service with specified provider.
        
        Args:
            provider_name: Name of the LLM provider to use ('openai' or 'huggingface')
            provider_config: Configuration for the provider
        """
        self.provider_name = provider_name
        self.provider_config = provider_config or {}
        
        provider_class = self.get_provider_class(provider_name)
        self.provider = provider_class(**self.provider_config)

    @classmethod
    def get_provider_class(cls, provider_name: str) -> Type[BaseLLMProvider]:
        """Get the provider class by name."""
        if provider_name not in cls.PROVIDERS:
            raise ValueError(f"Unsupported provider: {provider_name}. "
                           f"Supported providers: {list(cls.PROVIDERS.keys())}")
        return cls.PROVIDERS[provider_name]

    @classmethod
    def register_provider(cls, name: str, provider_class: Type[BaseLLMProvider]):
        """Register a new LLM provider."""
        if not issubclass(provider_class, BaseLLMProvider):
            raise TypeError("Provider class must inherit from BaseLLMProvider")
        cls.PROVIDERS[name] = provider_class

    def summarize_resource(self, content: str, max_length: int = None) -> str:
        """Generate a summary of resource content."""
        return self.provider.summarize(content, max_length)

    def extract_topics(self, content: str) -> list[str]:
        """Extract topics from content."""
        return self.provider.extract_topics(content)

    def classify_resource(self, content: str, categories: list[str] = None) -> list[str]:
        """Classify resource content."""
        return self.provider.classify_content(content, categories)

    def extract_keywords(self, content: str) -> list[str]:
        """Extract keywords from content."""
        return self.provider.extract_key_points(content)

    def compare_similarity(self, text1: str, text2: str) -> float:
        """Compare similarity between two texts."""
        return self.provider.calculate_similarity(text1, text2)

    def batch_summarize(self, texts: list[str]) -> list[str]:
        """Summarize multiple texts."""
        return self.provider.batch_process(texts, "summarize")

    def detect_language(self, content: str) -> str:
        """Detect language of content."""
        return self.provider.detect_language(content)