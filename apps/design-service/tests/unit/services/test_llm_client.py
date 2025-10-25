"""
Unit tests for LLM client.

Tests cover:
- Design specification generation
- Optimization generation
- Fallback mechanism when primary model fails
- Timeout handling (60 second timeout)
- Token usage tracking
"""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest
from openai import OpenAI, APIError, APITimeoutError, RateLimitError

from src.services.llm_client import LLMClient, LLMGenerationError, LLMTimeoutError, LLMImageGenerationError
from common.config import LLMConfig, LLMProvider


@pytest.fixture
def llm_config():
    """Create LLM configuration for testing."""
    return LLMConfig(
        primary_provider=LLMProvider.OPENAI,
        fallback_providers=[LLMProvider.OPENAI],
        openai_api_key="test-api-key",
        openai_model="gpt-4",
        openai_max_tokens=4000,
        openai_temperature=0.7,
        timeout=60,
        max_retries=3
    )


@pytest.fixture
def llm_client(llm_config):
    """Create LLM client instance for testing."""
    return LLMClient(llm_config)


@pytest.fixture
def mock_openai_response():
    """Create a mock OpenAI API response."""
    mock_response = Mock()
    mock_response.choices = [
        Mock(
            message=Mock(
                content='{"building_info": {"type": "residential", "total_area": 250.5}, "structure": {"foundation_type": "slab"}}'
            )
        )
    ]
    mock_response.usage = Mock(
        prompt_tokens=100,
        completion_tokens=200,
        total_tokens=300
    )
    mock_response.model = "gpt-4"
    return mock_response


@pytest.fixture
def mock_optimization_response():
    """Create a mock OpenAI API response for optimizations."""
    mock_response = Mock()
    mock_response.choices = [
        Mock(
            message=Mock(
                content='[{"optimization_type": "cost", "title": "Use local materials", "description": "Replace imported materials", "estimated_cost_impact": -15.0, "implementation_difficulty": "easy", "priority": "high"}]'
            )
        )
    ]
    mock_response.usage = Mock(
        prompt_tokens=150,
        completion_tokens=250,
        total_tokens=400
    )
    mock_response.model = "gpt-4"
    return mock_response


class TestLLMClientInitialization:
    """Test LLM client initialization."""

    def test_client_initialization_with_valid_config(self, llm_config):
        """Test that client initializes correctly with valid configuration."""
        client = LLMClient(llm_config)
        
        assert client.config == llm_config
        assert client.primary_provider == LLMProvider.OPENAI
        assert client.fallback_providers == [LLMProvider.OPENAI]
        assert client.timeout == 60

    def test_client_initialization_creates_openai_client(self, llm_config):
        """Test that OpenAI client is created during initialization."""
        client = LLMClient(llm_config)
        
        assert hasattr(client, '_openai_client')
        assert client._openai_client is not None


class TestDesignSpecificationGeneration:
    """Test design specification generation."""

    @pytest.mark.asyncio
    async def test_generate_design_specification_success(
        self, llm_client, mock_openai_response
    ):
        """Test successful design specification generation."""
        with patch.object(
            llm_client._openai_client.chat.completions,
            'create',
            return_value=mock_openai_response
        ):
            result = await llm_client.generate_design_specification(
                description="A 2-story residential building",
                building_type="residential",
                requirements={"num_floors": 2, "total_area": 250}
            )
            
            assert "specification" in result
            assert "confidence_score" in result
            assert "model_version" in result
            assert "token_usage" in result
            
            assert result["specification"]["building_info"]["type"] == "residential"
            assert result["model_version"] == "gpt-4"
            assert result["token_usage"]["total_tokens"] == 300

    @pytest.mark.asyncio
    async def test_generate_design_specification_with_prompt_construction(
        self, llm_client, mock_openai_response
    ):
        """Test that prompt is constructed correctly from inputs."""
        with patch.object(
            llm_client._openai_client.chat.completions,
            'create',
            return_value=mock_openai_response
        ) as mock_create:
            await llm_client.generate_design_specification(
                description="A modern office building",
                building_type="commercial",
                requirements={"num_floors": 5, "total_area": 1000}
            )
            
            # Verify the API was called
            assert mock_create.called
            call_args = mock_create.call_args
            
            # Check that messages were passed
            assert "messages" in call_args.kwargs
            messages = call_args.kwargs["messages"]
            
            # Verify system message exists
            assert any(msg["role"] == "system" for msg in messages)
            
            # Verify user message contains the description
            user_messages = [msg for msg in messages if msg["role"] == "user"]
            assert len(user_messages) > 0
            assert "modern office building" in user_messages[0]["content"]

    @pytest.mark.asyncio
    async def test_generate_design_specification_with_confidence_score(
        self, llm_client, mock_openai_response
    ):
        """Test that confidence score is calculated and included."""
        with patch.object(
            llm_client._openai_client.chat.completions,
            'create',
            return_value=mock_openai_response
        ):
            result = await llm_client.generate_design_specification(
                description="A residential building",
                building_type="residential",
                requirements={}
            )
            
            assert "confidence_score" in result
            assert isinstance(result["confidence_score"], (int, float))
            assert 0 <= result["confidence_score"] <= 100

    @pytest.mark.asyncio
    async def test_generate_design_specification_invalid_json_response(
        self, llm_client
    ):
        """Test handling of invalid JSON in API response."""
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Invalid JSON {"))]
        mock_response.usage = Mock(total_tokens=100)
        mock_response.model = "gpt-4"
        
        with patch.object(
            llm_client._openai_client.chat.completions,
            'create',
            return_value=mock_response
        ):
            with pytest.raises(LLMGenerationError, match="Failed to parse"):
                await llm_client.generate_design_specification(
                    description="Test",
                    building_type="residential",
                    requirements={}
                )


class TestOptimizationGeneration:
    """Test optimization generation."""

    @pytest.mark.asyncio
    async def test_generate_optimizations_success(
        self, llm_client, mock_optimization_response
    ):
        """Test successful optimization generation."""
        design_spec = {
            "building_info": {"type": "residential", "total_area": 250},
            "structure": {"foundation_type": "slab"}
        }
        
        with patch.object(
            llm_client._openai_client.chat.completions,
            'create',
            return_value=mock_optimization_response
        ):
            result = await llm_client.generate_optimizations(
                design_specification=design_spec,
                optimization_types=["cost", "structural", "sustainability"]
            )
            
            assert "optimizations" in result
            assert "token_usage" in result
            assert isinstance(result["optimizations"], list)
            assert len(result["optimizations"]) > 0
            
            # Verify optimization structure
            opt = result["optimizations"][0]
            assert "optimization_type" in opt
            assert "title" in opt
            assert "description" in opt
            assert "estimated_cost_impact" in opt
            assert "implementation_difficulty" in opt
            assert "priority" in opt

    @pytest.mark.asyncio
    async def test_generate_optimizations_multiple_types(
        self, llm_client, mock_optimization_response
    ):
        """Test optimization generation with multiple types."""
        design_spec = {"building_info": {"type": "residential"}}
        
        with patch.object(
            llm_client._openai_client.chat.completions,
            'create',
            return_value=mock_optimization_response
        ):
            result = await llm_client.generate_optimizations(
                design_specification=design_spec,
                optimization_types=["cost", "structural", "sustainability"]
            )
            
            assert "optimizations" in result
            assert len(result["optimizations"]) >= 1

    @pytest.mark.asyncio
    async def test_generate_optimizations_empty_list(self, llm_client):
        """Test handling when no optimizations are found."""
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="[]"))]
        mock_response.usage = Mock(total_tokens=50)
        mock_response.model = "gpt-4"
        
        design_spec = {"building_info": {"type": "residential"}}
        
        with patch.object(
            llm_client._openai_client.chat.completions,
            'create',
            return_value=mock_response
        ):
            result = await llm_client.generate_optimizations(
                design_specification=design_spec,
                optimization_types=["cost"]
            )
            
            assert result["optimizations"] == []


class TestFallbackMechanism:
    """Test fallback mechanism when primary model fails."""

    @pytest.mark.asyncio
    async def test_fallback_on_api_error(self, llm_config, mock_openai_response):
        """Test that fallback provider is used when primary fails."""
        # Configure with fallback
        llm_config.fallback_providers = [LLMProvider.OPENAI]
        client = LLMClient(llm_config)
        
        call_count = 0
        
        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First call fails
                raise APIError("Primary model failed")
            else:
                # Second call (fallback) succeeds
                return mock_openai_response
        
        with patch.object(
            client._openai_client.chat.completions,
            'create',
            side_effect=side_effect
        ):
            result = await client.generate_design_specification(
                description="Test building",
                building_type="residential",
                requirements={}
            )
            
            # Should succeed with fallback
            assert "specification" in result
            assert call_count == 2  # Primary + fallback

    @pytest.mark.asyncio
    async def test_fallback_on_rate_limit_error(self, llm_config, mock_openai_response):
        """Test fallback on rate limit error."""
        llm_config.fallback_providers = [LLMProvider.OPENAI]
        client = LLMClient(llm_config)
        
        call_count = 0
        
        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RateLimitError("Rate limit exceeded")
            return mock_openai_response
        
        with patch.object(
            client._openai_client.chat.completions,
            'create',
            side_effect=side_effect
        ):
            result = await client.generate_design_specification(
                description="Test",
                building_type="residential",
                requirements={}
            )
            
            assert "specification" in result
            assert call_count == 2

    @pytest.mark.asyncio
    async def test_all_providers_fail(self, llm_config):
        """Test error when all providers fail."""
        llm_config.fallback_providers = [LLMProvider.OPENAI]
        client = LLMClient(llm_config)
        
        # Create a proper APIError with required parameters
        mock_request = Mock()
        mock_request.method = "POST"
        mock_request.url = "https://api.openai.com/v1/chat/completions"
        api_error = APIError("All providers failed", request=mock_request, body=None)
        
        with patch.object(
            client._openai_client.chat.completions,
            'create',
            side_effect=api_error
        ):
            with pytest.raises(LLMGenerationError, match="All LLM providers failed"):
                await client.generate_design_specification(
                    description="Test",
                    building_type="residential",
                    requirements={}
                )


class TestTimeoutHandling:
    """Test timeout handling (60 second timeout)."""

    @pytest.mark.asyncio
    async def test_timeout_on_slow_response(self, llm_client):
        """Test that timeout is enforced on slow API responses."""
        async def slow_response(*args, **kwargs):
            await asyncio.sleep(65)  # Longer than 60 second timeout
            return Mock()
        
        with patch.object(
            llm_client._openai_client.chat.completions,
            'create',
            side_effect=APITimeoutError("Request timed out")
        ):
            with pytest.raises(LLMTimeoutError, match="timed out"):
                await llm_client.generate_design_specification(
                    description="Test",
                    building_type="residential",
                    requirements={}
                )

    @pytest.mark.asyncio
    async def test_timeout_triggers_fallback(self, llm_config, mock_openai_response):
        """Test that timeout triggers fallback mechanism."""
        llm_config.fallback_providers = [LLMProvider.OPENAI]
        client = LLMClient(llm_config)
        
        call_count = 0
        
        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise APITimeoutError("Timeout")
            return mock_openai_response
        
        with patch.object(
            client._openai_client.chat.completions,
            'create',
            side_effect=side_effect
        ):
            result = await client.generate_design_specification(
                description="Test",
                building_type="residential",
                requirements={}
            )
            
            assert "specification" in result
            assert call_count == 2

    @pytest.mark.asyncio
    async def test_timeout_configuration(self, llm_config):
        """Test that timeout is configured correctly."""
        llm_config.timeout = 60
        client = LLMClient(llm_config)
        
        assert client.timeout == 60


class TestTokenUsageTracking:
    """Test token usage tracking."""

    @pytest.mark.asyncio
    async def test_token_usage_tracked_on_success(
        self, llm_client, mock_openai_response
    ):
        """Test that token usage is tracked on successful generation."""
        with patch.object(
            llm_client._openai_client.chat.completions,
            'create',
            return_value=mock_openai_response
        ):
            result = await llm_client.generate_design_specification(
                description="Test",
                building_type="residential",
                requirements={}
            )
            
            assert "token_usage" in result
            assert result["token_usage"]["prompt_tokens"] == 100
            assert result["token_usage"]["completion_tokens"] == 200
            assert result["token_usage"]["total_tokens"] == 300

    @pytest.mark.asyncio
    async def test_token_usage_logged(self, llm_client, mock_openai_response):
        """Test that token usage is logged."""
        with patch.object(
            llm_client._openai_client.chat.completions,
            'create',
            return_value=mock_openai_response
        ):
            with patch('src.services.llm_client.logger') as mock_logger:
                await llm_client.generate_design_specification(
                    description="Test",
                    building_type="residential",
                    requirements={}
                )
                
                # Verify logging was called with token info
                assert mock_logger.info.called
                log_calls = [str(call) for call in mock_logger.info.call_args_list]
                assert any("token" in str(call).lower() for call in log_calls)

    @pytest.mark.asyncio
    async def test_token_usage_for_optimizations(
        self, llm_client, mock_optimization_response
    ):
        """Test token usage tracking for optimization generation."""
        design_spec = {"building_info": {"type": "residential"}}
        
        with patch.object(
            llm_client._openai_client.chat.completions,
            'create',
            return_value=mock_optimization_response
        ):
            result = await llm_client.generate_optimizations(
                design_specification=design_spec,
                optimization_types=["cost"]
            )
            
            assert "token_usage" in result
            assert result["token_usage"]["total_tokens"] == 400

    @pytest.mark.asyncio
    async def test_cumulative_token_tracking(
        self, llm_client, mock_openai_response
    ):
        """Test that client tracks cumulative token usage."""
        with patch.object(
            llm_client._openai_client.chat.completions,
            'create',
            return_value=mock_openai_response
        ):
            # Make multiple calls
            await llm_client.generate_design_specification(
                description="Test 1",
                building_type="residential",
                requirements={}
            )
            await llm_client.generate_design_specification(
                description="Test 2",
                building_type="commercial",
                requirements={}
            )
            
            # Check cumulative tracking
            stats = llm_client.get_usage_stats()
            assert stats["total_requests"] == 2
            assert stats["total_tokens"] == 600  # 300 * 2


class TestErrorHandling:
    """Test error handling in LLM client."""

    @pytest.mark.asyncio
    async def test_api_error_handling(self, llm_client):
        """Test handling of OpenAI API errors."""
        # Create a proper APIError with required parameters
        mock_request = Mock()
        mock_request.method = "POST"
        mock_request.url = "https://api.openai.com/v1/chat/completions"
        api_error = APIError("API Error", request=mock_request, body=None)
        
        with patch.object(
            llm_client._openai_client.chat.completions,
            'create',
            side_effect=api_error
        ):
            # Should try fallback, but if all fail, raise error
            with pytest.raises(LLMGenerationError):
                await llm_client.generate_design_specification(
                    description="Test",
                    building_type="residential",
                    requirements={}
                )

    @pytest.mark.asyncio
    async def test_invalid_input_handling(self, llm_client):
        """Test handling of invalid inputs."""
        with pytest.raises(ValueError, match="description"):
            await llm_client.generate_design_specification(
                description="",  # Empty description
                building_type="residential",
                requirements={}
            )

    @pytest.mark.asyncio
    async def test_missing_building_type(self, llm_client):
        """Test handling of missing building type."""
        with pytest.raises(ValueError, match="building_type"):
            await llm_client.generate_design_specification(
                description="Test building",
                building_type="",  # Empty building type
                requirements={}
            )


class TestImageGeneration:
    """Test image generation functionality."""

    @pytest.fixture
    def mock_image_response(self):
        """Create a mock OpenAI image generation response."""
        mock_response = Mock()
        mock_data = Mock()
        mock_data.url = "https://example.com/generated-image.png"
        mock_data.revised_prompt = "Enhanced architectural floor plan"
        mock_response.data = [mock_data]
        return mock_response

    @pytest.fixture
    def mock_image_data(self):
        """Create mock image binary data."""
        return b"fake_image_data"

    @pytest.mark.asyncio
    async def test_generate_image_success(self, llm_client, mock_image_response, mock_image_data):
        """Test successful image generation."""
        with patch.object(
            llm_client._openai_client.images,
            'generate',
            return_value=mock_image_response
        ), patch('httpx.AsyncClient') as mock_client:
            # Mock the HTTP client for image download
            mock_response = Mock()
            mock_response.content = mock_image_data
            mock_response.raise_for_status = Mock()
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response

            result = await llm_client.generate_image(
                prompt="A modern house floor plan",
                image_type="floor_plan"
            )

            assert "image_url" in result
            assert "image_data" in result
            assert "revised_prompt" in result
            assert "generation_cost" in result
            assert "model_version" in result
            assert result["image_url"] == "https://example.com/generated-image.png"
            assert result["image_data"] == mock_image_data
            assert result["model_version"] == "dall-e-3"

    @pytest.mark.asyncio
    async def test_generate_image_with_different_types(self, llm_client, mock_image_response, mock_image_data):
        """Test image generation with different image types."""
        image_types = ["floor_plan", "rendering", "3d_model"]
        
        for image_type in image_types:
            with patch.object(
                llm_client._openai_client.images,
                'generate',
                return_value=mock_image_response
            ), patch('httpx.AsyncClient') as mock_client:
                mock_response = Mock()
                mock_response.content = mock_image_data
                mock_response.raise_for_status = Mock()
                mock_client.return_value.__aenter__.return_value.get.return_value = mock_response

                result = await llm_client.generate_image(
                    prompt="A building design",
                    image_type=image_type
                )

                assert result["model_version"] == "dall-e-3"

    @pytest.mark.asyncio
    async def test_generate_image_with_size_and_quality_options(self, llm_client, mock_image_response, mock_image_data):
        """Test image generation with different size and quality options."""
        with patch.object(
            llm_client._openai_client.images,
            'generate',
            return_value=mock_image_response
        ) as mock_generate, patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.content = mock_image_data
            mock_response.raise_for_status = Mock()
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response

            result = await llm_client.generate_image(
                prompt="A house design",
                image_type="rendering",
                size="1792x1024",
                quality="hd"
            )

            # Verify the OpenAI API was called with correct parameters
            mock_generate.assert_called_once_with(
                model="dall-e-3",
                prompt=unittest.mock.ANY,  # Enhanced prompt
                size="1792x1024",
                quality="hd",
                n=1,
                response_format="url"
            )

    @pytest.mark.asyncio
    async def test_generate_image_invalid_inputs(self, llm_client):
        """Test image generation with invalid inputs."""
        # Test empty prompt
        with pytest.raises(ValueError, match="prompt cannot be empty"):
            await llm_client.generate_image(prompt="")

        # Test invalid size
        with pytest.raises(ValueError, match="size must be one of"):
            await llm_client.generate_image(
                prompt="test",
                size="invalid_size"
            )

        # Test invalid quality
        with pytest.raises(ValueError, match="quality must be one of"):
            await llm_client.generate_image(
                prompt="test",
                quality="invalid_quality"
            )

    @pytest.mark.asyncio
    async def test_generate_image_api_error(self, llm_client):
        """Test handling of OpenAI API errors during image generation."""
        from src.services.llm_client import LLMImageGenerationError
        
        # Create a proper APIError with required parameters
        mock_request = Mock()
        mock_request.method = "POST"
        mock_request.url = "https://api.openai.com/v1/images/generations"
        api_error = APIError("API Error", request=mock_request, body=None)
        
        with patch.object(
            llm_client._openai_client.images,
            'generate',
            side_effect=api_error
        ):
            with pytest.raises(LLMImageGenerationError):
                await llm_client.generate_image(prompt="test prompt")

    @pytest.mark.asyncio
    async def test_generate_image_timeout(self, llm_client):
        """Test timeout handling during image generation."""
        from src.services.llm_client import LLMTimeoutError
        
        with patch.object(
            llm_client._openai_client.images,
            'generate',
            side_effect=APITimeoutError("Timeout")
        ):
            with pytest.raises(LLMTimeoutError):
                await llm_client.generate_image(prompt="test prompt")

    @pytest.mark.asyncio
    async def test_generate_image_download_failure(self, llm_client, mock_image_response):
        """Test handling of image download failures."""
        from src.services.llm_client import LLMImageGenerationError
        
        with patch.object(
            llm_client._openai_client.images,
            'generate',
            return_value=mock_image_response
        ), patch('httpx.AsyncClient') as mock_client:
            # Mock HTTP client to raise an exception
            mock_client.return_value.__aenter__.return_value.get.side_effect = Exception("Download failed")

            with pytest.raises(LLMImageGenerationError, match="Failed to download image"):
                await llm_client.generate_image(prompt="test prompt")

    def test_prompt_enhancement(self, llm_client):
        """Test prompt enhancement for different image types."""
        # Test floor plan enhancement
        enhanced = llm_client._enhance_image_prompt("a house", "floor_plan")
        assert "floor plan" in enhanced.lower()
        assert "architectural" in enhanced.lower()
        assert "top-down view" in enhanced.lower()

        # Test rendering enhancement
        enhanced = llm_client._enhance_image_prompt("a house", "rendering")
        assert "rendering" in enhanced.lower()
        assert "photorealistic" in enhanced.lower()

        # Test 3D model enhancement
        enhanced = llm_client._enhance_image_prompt("a house", "3d_model")
        assert "3d" in enhanced.lower()
        assert "model" in enhanced.lower()

    def test_image_cost_calculation(self, llm_client):
        """Test image generation cost calculation."""
        # Test standard quality costs
        cost = llm_client._calculate_image_cost("1024x1024", "standard")
        assert cost == 0.040

        cost = llm_client._calculate_image_cost("1792x1024", "standard")
        assert cost == 0.080

        # Test HD quality costs
        cost = llm_client._calculate_image_cost("1024x1024", "hd")
        assert cost == 0.080

        cost = llm_client._calculate_image_cost("1792x1024", "hd")
        assert cost == 0.120

    @pytest.mark.asyncio
    async def test_image_usage_tracking(self, llm_client, mock_image_response, mock_image_data):
        """Test that image generation usage is tracked."""
        initial_stats = llm_client.get_usage_stats()
        initial_requests = initial_stats["total_requests"]
        initial_cost = initial_stats["total_cost"]

        with patch.object(
            llm_client._openai_client.images,
            'generate',
            return_value=mock_image_response
        ), patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.content = mock_image_data
            mock_response.raise_for_status = Mock()
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response

            await llm_client.generate_image(
                prompt="test prompt",
                size="1024x1024",
                quality="standard"
            )

        final_stats = llm_client.get_usage_stats()
        assert final_stats["total_requests"] == initial_requests + 1
        assert final_stats["total_cost"] > initial_cost


# Add missing import for unittest.mock
import unittest.mock