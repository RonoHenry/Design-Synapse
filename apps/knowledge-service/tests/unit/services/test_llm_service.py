"""Unit tests for LLM service."""
import json
from unittest.mock import AsyncMock, Mock, patch

import pytest
from knowledge_service.core.config import KnowledgeServiceConfig
from knowledge_service.services.llm import LLMService


class TestLLMService:
    """Test cases for LLMService."""

    @pytest.fixture
    def mock_config(self):
        """Mock configuration fixture."""
        config = Mock(spec=KnowledgeServiceConfig)
        config.llm_primary_provider = "openai"
        config.openai_api_key = "test-api-key"
        config.openai_model = "gpt-3.5-turbo"
        config.llm_fallback_provider = "anthropic"
        config.anthropic_api_key = "test-anthropic-key"
        config.anthropic_model = "claude-3-sonnet"
        config.llm_max_retries = 3
        config.llm_timeout = 30
        config.llm_temperature = 0.7
        return config

    @pytest.fixture
    def llm_service(self, mock_config):
        """LLM service fixture."""
        return LLMService(mock_config)

    @pytest.fixture
    def sample_content(self):
        """Sample content for testing."""
        return """
        Machine learning is a subset of artificial intelligence that focuses on
        algorithms that can learn from and make predictions on data. This guide
        covers supervised learning, unsupervised learning, and reinforcement learning.
        """

    def test_init(self, mock_config):
        """Test service initialization."""
        service = LLMService(mock_config)
        assert service.config == mock_config
        assert service.primary_provider == "openai"
        assert service.fallback_provider == "anthropic"
        assert service.max_retries == 3
        assert service.timeout == 30

    @pytest.mark.asyncio
    async def test_analyze_content_success(self, llm_service, sample_content):
        """Test successful content analysis."""
        expected_response = {
            "content_type": "technical_document",
            "complexity_level": "intermediate",
            "technical_domains": ["machine_learning", "artificial_intelligence"],
            "keywords": [
                "machine learning",
                "algorithms",
                "data",
                "supervised learning",
            ],
            "summary": "A guide covering machine learning fundamentals",
            "key_takeaways": ["ML is subset of AI", "Covers different learning types"],
            "readability_score": 0.7,
            "estimated_reading_time": 5,
        }

        with patch.object(llm_service, "_call_llm_provider") as mock_call:
            mock_call.return_value = expected_response

            result = await llm_service.analyze_content(
                content=sample_content, title="ML Guide"
            )

            assert result == expected_response
            mock_call.assert_called_once()

    @pytest.mark.asyncio
    async def test_analyze_content_with_fallback(self, llm_service, sample_content):
        """Test content analysis with fallback provider."""
        expected_response = {
            "content_type": "technical_document",
            "complexity_level": "intermediate",
            "technical_domains": ["machine_learning"],
            "keywords": ["machine learning", "algorithms"],
            "summary": "ML guide summary",
            "key_takeaways": ["Key takeaway"],
            "readability_score": 0.8,
            "estimated_reading_time": 4,
        }

        with patch.object(llm_service, "_call_llm_provider") as mock_call:
            # First call (primary) fails, second call (fallback) succeeds
            mock_call.side_effect = [
                Exception("Primary provider error"),
                expected_response,
            ]

            result = await llm_service.analyze_content(
                content=sample_content, title="ML Guide"
            )

            assert result == expected_response
            assert mock_call.call_count == 2

    @pytest.mark.asyncio
    async def test_analyze_content_all_providers_fail(
        self, llm_service, sample_content
    ):
        """Test content analysis when all providers fail."""
        with patch.object(llm_service, "_call_llm_provider") as mock_call:
            mock_call.side_effect = Exception("All providers failed")

            with pytest.raises(Exception, match="All LLM providers failed"):
                await llm_service.analyze_content(
                    content=sample_content, title="ML Guide"
                )

    @pytest.mark.asyncio
    async def test_extract_tags_success(self, llm_service, sample_content):
        """Test successful tag extraction."""
        expected_response = {
            "tags": ["machine learning", "AI", "algorithms", "data science"]
        }

        with patch.object(llm_service, "_call_llm_provider") as mock_call:
            mock_call.return_value = expected_response

            result = await llm_service.extract_tags(content=sample_content, max_tags=10)

            assert result == expected_response
            mock_call.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_summary_success(self, llm_service, sample_content):
        """Test successful summary generation."""
        expected_response = {
            "summary": "This guide provides an introduction to machine learning concepts.",
            "key_points": ["ML is subset of AI", "Covers learning types"],
        }

        with patch.object(llm_service, "_call_llm_provider") as mock_call:
            mock_call.return_value = expected_response

            result = await llm_service.generate_summary(
                content=sample_content, max_length=100
            )

            assert result == expected_response
            mock_call.assert_called_once()

    @pytest.mark.asyncio
    async def test_call_llm_provider_openai_success(self, llm_service):
        """Test successful OpenAI provider call."""
        prompt = "Test prompt"
        expected_response = {"test": "response"}

        with patch.object(llm_service, "_call_openai") as mock_openai:
            mock_openai.return_value = expected_response

            result = await llm_service._call_llm_provider("openai", prompt)

            assert result == expected_response
            mock_openai.assert_called_once_with(prompt)

    @pytest.mark.asyncio
    async def test_call_llm_provider_anthropic_success(self, llm_service):
        """Test successful Anthropic provider call."""
        prompt = "Test prompt"
        expected_response = {"test": "response"}

        with patch.object(llm_service, "_call_anthropic") as mock_anthropic:
            mock_anthropic.return_value = expected_response

            result = await llm_service._call_llm_provider("anthropic", prompt)

            assert result == expected_response
            mock_anthropic.assert_called_once_with(prompt)

    @pytest.mark.asyncio
    async def test_call_llm_provider_unsupported(self, llm_service):
        """Test unsupported provider."""
        with pytest.raises(ValueError, match="Unsupported LLM provider"):
            await llm_service._call_llm_provider("unsupported", "test prompt")

    @pytest.mark.asyncio
    async def test_call_openai_success(self, llm_service):
        """Test successful OpenAI API call."""
        prompt = "Test prompt"
        mock_response = {"choices": [{"message": {"content": '{"test": "response"}'}}]}

        with patch("openai.ChatCompletion.acreate") as mock_create:
            mock_create.return_value = mock_response

            result = await llm_service._call_openai(prompt)

            assert result == {"test": "response"}
            mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_call_openai_invalid_json(self, llm_service):
        """Test OpenAI call with invalid JSON response."""
        prompt = "Test prompt"
        mock_response = {"choices": [{"message": {"content": "Invalid JSON response"}}]}

        with patch("openai.ChatCompletion.acreate") as mock_create:
            mock_create.return_value = mock_response

            with pytest.raises(ValueError, match="Invalid JSON response from OpenAI"):
                await llm_service._call_openai(prompt)

    @pytest.mark.asyncio
    async def test_call_anthropic_success(self, llm_service):
        """Test successful Anthropic API call."""
        prompt = "Test prompt"
        mock_response = Mock()
        mock_response.content = [Mock()]
        mock_response.content[0].text = '{"test": "response"}'

        with patch("anthropic.Anthropic") as mock_anthropic_class:
            mock_client = Mock()
            mock_anthropic_class.return_value = mock_client
            mock_client.messages.create.return_value = mock_response

            result = await llm_service._call_anthropic(prompt)

            assert result == {"test": "response"}
            mock_client.messages.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_call_anthropic_invalid_json(self, llm_service):
        """Test Anthropic call with invalid JSON response."""
        prompt = "Test prompt"
        mock_response = Mock()
        mock_response.content = [Mock()]
        mock_response.content[0].text = "Invalid JSON response"

        with patch("anthropic.Anthropic") as mock_anthropic_class:
            mock_client = Mock()
            mock_anthropic_class.return_value = mock_client
            mock_client.messages.create.return_value = mock_response

            with pytest.raises(
                ValueError, match="Invalid JSON response from Anthropic"
            ):
                await llm_service._call_anthropic(prompt)

    def test_build_content_analysis_prompt(self, llm_service, sample_content):
        """Test content analysis prompt building."""
        prompt = llm_service._build_content_analysis_prompt(
            content=sample_content, title="ML Guide"
        )

        assert isinstance(prompt, str)
        assert "ML Guide" in prompt
        assert "machine learning" in prompt.lower()
        assert "JSON" in prompt
        assert "content_type" in prompt

    def test_build_tag_extraction_prompt(self, llm_service, sample_content):
        """Test tag extraction prompt building."""
        prompt = llm_service._build_tag_extraction_prompt(
            content=sample_content, max_tags=5
        )

        assert isinstance(prompt, str)
        assert "machine learning" in prompt.lower()
        assert "5" in prompt
        assert "tags" in prompt.lower()

    def test_build_summary_prompt(self, llm_service, sample_content):
        """Test summary generation prompt building."""
        prompt = llm_service._build_summary_prompt(
            content=sample_content, max_length=100
        )

        assert isinstance(prompt, str)
        assert "machine learning" in prompt.lower()
        assert "100" in prompt
        assert "summary" in prompt.lower()

    @pytest.mark.asyncio
    async def test_retry_mechanism(self, llm_service, sample_content):
        """Test retry mechanism on failures."""
        with patch.object(llm_service, "_call_openai") as mock_openai:
            # Fail twice, then succeed
            mock_openai.side_effect = [
                Exception("Temporary error"),
                Exception("Another error"),
                {"test": "success"},
            ]

            result = await llm_service.analyze_content(
                content=sample_content, title="Test"
            )

            assert result == {"test": "success"}
            assert mock_openai.call_count == 3

    @pytest.mark.asyncio
    async def test_retry_exhaustion(self, llm_service, sample_content):
        """Test retry exhaustion."""
        with patch.object(llm_service, "_call_openai") as mock_openai:
            mock_openai.side_effect = Exception("Persistent error")

            with patch.object(llm_service, "_call_anthropic") as mock_anthropic:
                mock_anthropic.side_effect = Exception("Fallback error")

                with pytest.raises(Exception, match="All LLM providers failed"):
                    await llm_service.analyze_content(
                        content=sample_content, title="Test"
                    )

    def test_validate_response_structure_valid(self, llm_service):
        """Test response structure validation with valid response."""
        valid_response = {
            "content_type": "technical_document",
            "complexity_level": "intermediate",
            "technical_domains": ["machine_learning"],
            "keywords": ["test"],
            "summary": "Test summary",
        }

        # Should not raise exception
        llm_service._validate_response_structure(valid_response, "content_analysis")

    def test_validate_response_structure_invalid(self, llm_service):
        """Test response structure validation with invalid response."""
        invalid_response = {
            "content_type": "technical_document"
            # Missing required fields
        }

        with pytest.raises(ValueError, match="Invalid response structure"):
            llm_service._validate_response_structure(
                invalid_response, "content_analysis"
            )

    def test_sanitize_content(self, llm_service):
        """Test content sanitization."""
        dirty_content = "  This is\n\n\ntest content\t\twith   extra   spaces  "
        clean_content = llm_service._sanitize_content(dirty_content)

        assert clean_content == "This is test content with extra spaces"

    def test_truncate_content(self, llm_service):
        """Test content truncation."""
        long_content = "word " * 1000  # 1000 words
        truncated = llm_service._truncate_content(long_content, max_words=100)

        word_count = len(truncated.split())
        assert word_count <= 100
        assert "..." in truncated

    @pytest.mark.asyncio
    async def test_health_check_success(self, llm_service):
        """Test successful health check."""
        with patch.object(llm_service, "_call_llm_provider") as mock_call:
            mock_call.return_value = {"status": "healthy"}

            is_healthy = await llm_service.health_check()

            assert is_healthy is True
            mock_call.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_check_failure(self, llm_service):
        """Test health check failure."""
        with patch.object(llm_service, "_call_llm_provider") as mock_call:
            mock_call.side_effect = Exception("Health check failed")

            is_healthy = await llm_service.health_check()

            assert is_healthy is False

    def test_get_provider_config_openai(self, llm_service):
        """Test getting OpenAI provider configuration."""
        config = llm_service._get_provider_config("openai")

        assert config["api_key"] == "test-api-key"
        assert config["model"] == "gpt-3.5-turbo"
        assert config["temperature"] == 0.7

    def test_get_provider_config_anthropic(self, llm_service):
        """Test getting Anthropic provider configuration."""
        config = llm_service._get_provider_config("anthropic")

        assert config["api_key"] == "test-anthropic-key"
        assert config["model"] == "claude-3-sonnet"

    def test_get_provider_config_invalid(self, llm_service):
        """Test getting configuration for invalid provider."""
        with pytest.raises(ValueError, match="Unsupported provider"):
            llm_service._get_provider_config("invalid")

    @pytest.mark.asyncio
    async def test_batch_analyze_content(self, llm_service):
        """Test batch content analysis."""
        content_items = [
            {"content": "First content", "title": "Title 1"},
            {"content": "Second content", "title": "Title 2"},
        ]

        expected_responses = [
            {"content_type": "document", "summary": "First summary"},
            {"content_type": "document", "summary": "Second summary"},
        ]

        with patch.object(llm_service, "analyze_content") as mock_analyze:
            mock_analyze.side_effect = expected_responses

            results = await llm_service.batch_analyze_content(content_items)

            assert len(results) == 2
            assert results == expected_responses
            assert mock_analyze.call_count == 2

    @pytest.mark.asyncio
    async def test_analyze_content_with_context(self, llm_service, sample_content):
        """Test content analysis with additional context."""
        context = {
            "domain": "machine_learning",
            "audience": "beginners",
            "purpose": "educational",
        }

        expected_response = {
            "content_type": "tutorial",
            "complexity_level": "basic",
            "technical_domains": ["machine_learning"],
            "keywords": ["machine learning", "beginners"],
            "summary": "Beginner-friendly ML guide",
        }

        with patch.object(llm_service, "_call_llm_provider") as mock_call:
            mock_call.return_value = expected_response

            result = await llm_service.analyze_content(
                content=sample_content, title="ML Guide", context=context
            )

            assert result == expected_response
            # Verify context was included in the prompt
            call_args = mock_call.call_args[0]
            prompt = call_args[1]
            assert "machine_learning" in prompt
            assert "beginners" in prompt
