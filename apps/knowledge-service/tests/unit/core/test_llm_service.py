"""Tests for modular LLM service with different providers."""

import pytest
from unittest.mock import Mock

from knowledge_service.core.llm_providers.base import BaseLLMProvider
from knowledge_service.core.llm_providers.service import LLMService
from knowledge_service.core.llm_providers.openai_provider import OpenAIProvider
from knowledge_service.core.llm_providers.huggingface_provider import HuggingFaceProvider


class MockProvider(BaseLLMProvider):
    """Mock LLM provider for testing."""
    
    def __init__(self, **config):
        self.config = config
        self.calls = []

    def summarize(self, text, max_length=None):
        self.calls.append(('summarize', text, max_length))
        return "Mock summary"

    def extract_key_points(self, text, max_points=None):
        self.calls.append(('extract_key_points', text, max_points))
        return ["Mock point 1", "Mock point 2"]

    def classify_content(self, text, categories=None):
        self.calls.append(('classify_content', text, categories))
        return ["Category 1", "Category 2"]

    def extract_topics(self, text):
        self.calls.append(('extract_topics', text))
        return ["Topic 1", "Topic 2"]

    def calculate_similarity(self, text1, text2):
        self.calls.append(('calculate_similarity', text1, text2))
        return 0.85

    def batch_process(self, texts, operation):
        self.calls.append(('batch_process', texts, operation))
        return ["Result 1", "Result 2"]

    def detect_language(self, text):
        self.calls.append(('detect_language', text))
        return "English"


@pytest.fixture
def mock_provider():
    """Create a mock provider instance."""
    return MockProvider()


@pytest.fixture
def llm_service(mock_provider):
    """Create LLM service with mock provider for testing."""
    LLMService.register_provider('mock', MockProvider)
    return LLMService(provider_name='mock')


def test_provider_registration():
    """Test registering new provider."""
    LLMService.register_provider('test', MockProvider)
    service = LLMService(provider_name='test')
    assert isinstance(service.provider, MockProvider)


def test_invalid_provider():
    """Test initializing service with invalid provider."""
    with pytest.raises(ValueError):
        LLMService(provider_name='invalid')


def test_invalid_provider_registration():
    """Test registering invalid provider class."""
    class InvalidProvider:
        pass

    with pytest.raises(TypeError):
        LLMService.register_provider('invalid', InvalidProvider)


def test_provider_config(mock_provider):
    """Test provider configuration."""
    config = {'api_key': 'test_key', 'model': 'test_model'}
    LLMService.register_provider('mock', MockProvider)
    service = LLMService(provider_name='mock', provider_config=config)
    assert service.provider.config == config


def test_summarize_resource(llm_service):
    """Test resource summarization."""
    content = "Test content for summarization"
    summary = llm_service.summarize_resource(content)
    assert summary == "Mock summary"
    assert ('summarize', content, None) in llm_service.provider.calls


def test_extract_topics(llm_service):
    """Test topic extraction."""
    content = "Test content for topic extraction"
    topics = llm_service.extract_topics(content)
    assert topics == ["Topic 1", "Topic 2"]
    assert ('extract_topics', content) in llm_service.provider.calls


def test_classify_resource(llm_service):
    """Test resource classification."""
    content = "Test content for classification"
    categories = llm_service.classify_resource(content)
    assert categories == ["Category 1", "Category 2"]
    assert ('classify_content', content, None) in llm_service.provider.calls


def test_compare_similarity(llm_service):
    """Test content similarity comparison."""
    text1 = "First text"
    text2 = "Second text"
    similarity = llm_service.compare_similarity(text1, text2)
    assert similarity == 0.85
    assert ('calculate_similarity', text1, text2) in llm_service.provider.calls


def test_batch_processing(llm_service):
    """Test batch processing."""
    texts = ["Text 1", "Text 2"]
    results = llm_service.batch_summarize(texts)
    assert results == ["Result 1", "Result 2"]
    assert ('batch_process', texts, "summarize") in llm_service.provider.calls


def test_language_detection(llm_service):
    """Test language detection."""
    content = "Test content for language detection"
    language = llm_service.detect_language(content)
    assert language == "English"
    assert ('detect_language', content) in llm_service.provider.calls


@pytest.mark.integration
def test_openai_provider_integration():
    """Integration test for OpenAI provider."""
    if not pytest.config.getoption("--run-integration"):
        pytest.skip("Integration tests not enabled")
    
    service = LLMService(provider_name='openai', provider_config={
        'api_key': 'your_api_key_here'
    })
    
    result = service.summarize_resource("Test content")
    assert isinstance(result, str)


@pytest.mark.integration
def test_huggingface_provider_integration():
    """Integration test for HuggingFace provider."""
    if not pytest.config.getoption("--run-integration"):
        pytest.skip("Integration tests not enabled")
    
    service = LLMService(provider_name='huggingface')
    result = service.summarize_resource("Test content")
    assert isinstance(result, str)


def test_provider_switching():
    """Test switching between providers."""
    service = LLMService(provider_name='mock')
    initial_provider = service.provider
    
    # Switch to a different provider
    service = LLMService(provider_name='mock', provider_config={'different': 'config'})
    new_provider = service.provider
    
    assert isinstance(initial_provider, MockProvider)
    assert isinstance(new_provider, MockProvider)
    assert initial_provider != new_provider