"""Unit tests for content analysis service."""
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest
from knowledge_service.services.content_analysis import (
    ComplexityLevel, ContentAnalysisResult, ContentAnalysisService,
    ContentType, TechnicalDomain)


class TestContentAnalysisService:
    """Test cases for ContentAnalysisService."""

    @pytest.fixture
    def mock_llm_service(self):
        """Mock LLM service fixture."""
        mock = AsyncMock()
        return mock

    @pytest.fixture
    def content_analysis_service(self, mock_llm_service):
        """Content analysis service fixture."""
        return ContentAnalysisService(mock_llm_service)

    @pytest.fixture
    def sample_content(self):
        """Sample content for testing."""
        return {
            "title": "Introduction to Machine Learning",
            "content": """
            Machine learning is a subset of artificial intelligence that focuses on
            algorithms that can learn from and make predictions on data. This comprehensive
            guide covers the fundamental concepts including supervised learning,
            unsupervised learning, and reinforcement learning. We'll explore various
            algorithms such as linear regression, decision trees, neural networks,
            and support vector machines. The content includes practical examples
            using Python and popular libraries like scikit-learn and TensorFlow.
            """,
            "file_type": "pdf",
        }

    def test_init(self, mock_llm_service):
        """Test service initialization."""
        service = ContentAnalysisService(mock_llm_service)
        assert service.llm_service == mock_llm_service
        assert service.min_content_length == 50
        assert service.max_content_length == 1000000

    @pytest.mark.asyncio
    async def test_analyze_content_success(
        self, content_analysis_service, mock_llm_service, sample_content
    ):
        """Test successful content analysis."""
        # Mock LLM response
        mock_llm_response = {
            "content_type": "technical_document",
            "complexity_level": "intermediate",
            "technical_domains": ["machine_learning", "artificial_intelligence"],
            "keywords": ["machine learning", "algorithms", "neural networks", "python"],
            "summary": "A comprehensive guide to machine learning fundamentals",
            "key_takeaways": ["Understanding ML concepts", "Practical implementation"],
            "readability_score": 0.7,
            "estimated_reading_time": 15,
        }
        mock_llm_service.analyze_content.return_value = mock_llm_response

        # Perform analysis
        result = await content_analysis_service.analyze_content(
            content=sample_content["content"],
            title=sample_content["title"],
            file_type=sample_content["file_type"],
        )

        # Assertions
        assert isinstance(result, ContentAnalysisResult)
        assert result.content_type == ContentType.TECHNICAL_DOCUMENT
        assert result.complexity_level == ComplexityLevel.INTERMEDIATE
        assert TechnicalDomain.MACHINE_LEARNING in result.technical_domains
        assert "machine learning" in result.keywords
        assert (
            result.summary == "A comprehensive guide to machine learning fundamentals"
        )
        assert len(result.key_takeaways) == 2
        assert result.readability_score == 0.7
        assert result.estimated_reading_time == 15

        # Verify LLM service was called correctly
        mock_llm_service.analyze_content.assert_called_once()

    @pytest.mark.asyncio
    async def test_analyze_content_empty_content(self, content_analysis_service):
        """Test analysis with empty content."""
        with pytest.raises(ValueError, match="Content cannot be empty"):
            await content_analysis_service.analyze_content(
                content="", title="Test Title"
            )

    @pytest.mark.asyncio
    async def test_analyze_content_too_short(self, content_analysis_service):
        """Test analysis with content too short."""
        short_content = "Short"

        with pytest.raises(ValueError, match="Content too short"):
            await content_analysis_service.analyze_content(
                content=short_content, title="Test Title"
            )

    @pytest.mark.asyncio
    async def test_analyze_content_too_long(self, content_analysis_service):
        """Test analysis with content too long."""
        long_content = "x" * 1000001  # Exceeds max length

        with pytest.raises(ValueError, match="Content too long"):
            await content_analysis_service.analyze_content(
                content=long_content, title="Test Title"
            )

    @pytest.mark.asyncio
    async def test_analyze_content_llm_failure(
        self, content_analysis_service, mock_llm_service, sample_content
    ):
        """Test handling of LLM service failure."""
        # Mock LLM service to raise exception
        mock_llm_service.analyze_content.side_effect = Exception("LLM service error")

        # Should fall back to basic analysis
        result = await content_analysis_service.analyze_content(
            content=sample_content["content"], title=sample_content["title"]
        )

        # Should return basic analysis result
        assert isinstance(result, ContentAnalysisResult)
        assert result.content_type == ContentType.DOCUMENT
        assert result.complexity_level == ComplexityLevel.INTERMEDIATE
        assert len(result.keywords) > 0  # Should extract some keywords

    @pytest.mark.asyncio
    async def test_extract_keywords_basic(
        self, content_analysis_service, sample_content
    ):
        """Test basic keyword extraction."""
        keywords = await content_analysis_service._extract_keywords_basic(
            sample_content["content"], max_keywords=5
        )

        assert isinstance(keywords, list)
        assert len(keywords) <= 5
        assert "learning" in keywords or "machine" in keywords

    @pytest.mark.asyncio
    async def test_estimate_complexity_basic(self, content_analysis_service):
        """Test basic complexity estimation."""
        # Simple content
        simple_content = "This is a simple document with basic words."
        complexity = await content_analysis_service._estimate_complexity_basic(
            simple_content
        )
        assert complexity == ComplexityLevel.BASIC

        # Complex content with technical terms
        complex_content = """
        The implementation utilizes sophisticated algorithms including convolutional
        neural networks, backpropagation, and gradient descent optimization techniques
        for advanced pattern recognition and classification tasks.
        """
        complexity = await content_analysis_service._estimate_complexity_basic(
            complex_content
        )
        assert complexity in [ComplexityLevel.ADVANCED, ComplexityLevel.EXPERT]

    @pytest.mark.asyncio
    async def test_calculate_readability_score(
        self, content_analysis_service, sample_content
    ):
        """Test readability score calculation."""
        score = await content_analysis_service._calculate_readability_score(
            sample_content["content"]
        )

        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    @pytest.mark.asyncio
    async def test_estimate_reading_time(
        self, content_analysis_service, sample_content
    ):
        """Test reading time estimation."""
        reading_time = await content_analysis_service._estimate_reading_time(
            sample_content["content"]
        )

        assert isinstance(reading_time, int)
        assert reading_time > 0

    @pytest.mark.asyncio
    async def test_classify_content_type_basic(self, content_analysis_service):
        """Test basic content type classification."""
        # Technical content
        technical_content = (
            "This document explains machine learning algorithms and neural networks."
        )
        content_type = await content_analysis_service._classify_content_type_basic(
            technical_content, "ML Guide"
        )
        assert content_type == ContentType.TECHNICAL_DOCUMENT

        # Tutorial content
        tutorial_content = (
            "Step 1: Install Python. Step 2: Import libraries. Step 3: Run the code."
        )
        content_type = await content_analysis_service._classify_content_type_basic(
            tutorial_content, "Python Tutorial"
        )
        assert content_type == ContentType.TUTORIAL

        # Research content
        research_content = "Abstract: This paper presents a novel approach to deep learning optimization."
        content_type = await content_analysis_service._classify_content_type_basic(
            research_content, "Research Paper"
        )
        assert content_type == ContentType.RESEARCH_PAPER

    @pytest.mark.asyncio
    async def test_identify_technical_domains_basic(
        self, content_analysis_service, sample_content
    ):
        """Test basic technical domain identification."""
        domains = await content_analysis_service._identify_technical_domains_basic(
            sample_content["content"]
        )

        assert isinstance(domains, list)
        assert (
            TechnicalDomain.MACHINE_LEARNING in domains
            or TechnicalDomain.DATA_SCIENCE in domains
        )

    @pytest.mark.asyncio
    async def test_analyze_file_content(
        self, content_analysis_service, mock_llm_service
    ):
        """Test file content analysis."""
        # Mock file content
        mock_file_content = b"This is a test PDF content about machine learning."

        with patch(
            "knowledge_service.services.content_analysis.extract_text_from_file"
        ) as mock_extract:
            mock_extract.return_value = mock_file_content.decode()

            # Mock LLM response
            mock_llm_service.analyze_content.return_value = {
                "content_type": "technical_document",
                "complexity_level": "intermediate",
                "technical_domains": ["machine_learning"],
                "keywords": ["machine", "learning"],
                "summary": "Test summary",
                "key_takeaways": ["Test takeaway"],
                "readability_score": 0.8,
                "estimated_reading_time": 5,
            }

            result = await content_analysis_service.analyze_file_content(
                file_content=mock_file_content,
                filename="test.pdf",
                title="Test Document",
            )

            assert isinstance(result, ContentAnalysisResult)
            assert result.content_type == ContentType.TECHNICAL_DOCUMENT
            mock_extract.assert_called_once_with(mock_file_content, "test.pdf")

    @pytest.mark.asyncio
    async def test_batch_analyze_content(
        self, content_analysis_service, mock_llm_service
    ):
        """Test batch content analysis."""
        # Mock multiple content items
        content_items = [
            {"content": "First document about AI", "title": "AI Doc 1"},
            {"content": "Second document about ML", "title": "ML Doc 2"},
        ]

        # Mock LLM responses
        mock_responses = [
            {
                "content_type": "technical_document",
                "complexity_level": "basic",
                "technical_domains": ["artificial_intelligence"],
                "keywords": ["ai", "artificial"],
                "summary": "AI summary",
                "key_takeaways": ["AI takeaway"],
                "readability_score": 0.6,
                "estimated_reading_time": 3,
            },
            {
                "content_type": "technical_document",
                "complexity_level": "intermediate",
                "technical_domains": ["machine_learning"],
                "keywords": ["ml", "machine"],
                "summary": "ML summary",
                "key_takeaways": ["ML takeaway"],
                "readability_score": 0.7,
                "estimated_reading_time": 4,
            },
        ]
        mock_llm_service.analyze_content.side_effect = mock_responses

        results = await content_analysis_service.batch_analyze_content(content_items)

        assert len(results) == 2
        assert all(isinstance(result, ContentAnalysisResult) for result in results)
        assert results[0].content_type == ContentType.TECHNICAL_DOCUMENT
        assert results[1].content_type == ContentType.TECHNICAL_DOCUMENT

    @pytest.mark.asyncio
    async def test_extract_tags_only(
        self, content_analysis_service, mock_llm_service, sample_content
    ):
        """Test extracting tags only."""
        mock_llm_service.extract_tags.return_value = {
            "tags": ["machine learning", "AI", "algorithms", "python"]
        }

        tags = await content_analysis_service.extract_tags_only(
            content=sample_content["content"], max_tags=10
        )

        assert isinstance(tags, list)
        assert len(tags) <= 10
        assert "machine learning" in tags
        mock_llm_service.extract_tags.assert_called_once()

    @pytest.mark.asyncio
    async def test_extract_tags_only_fallback(
        self, content_analysis_service, mock_llm_service, sample_content
    ):
        """Test tag extraction with LLM fallback."""
        # Mock LLM service failure
        mock_llm_service.extract_tags.side_effect = Exception("LLM error")

        tags = await content_analysis_service.extract_tags_only(
            content=sample_content["content"], max_tags=5
        )

        # Should fall back to basic keyword extraction
        assert isinstance(tags, list)
        assert len(tags) <= 5
        assert len(tags) > 0  # Should extract some basic keywords

    def test_content_type_enum_values(self):
        """Test ContentType enum values."""
        assert ContentType.DOCUMENT.value == "document"
        assert ContentType.TECHNICAL_DOCUMENT.value == "technical_document"
        assert ContentType.RESEARCH_PAPER.value == "research_paper"
        assert ContentType.TUTORIAL.value == "tutorial"
        assert ContentType.REFERENCE.value == "reference"

    def test_complexity_level_enum_values(self):
        """Test ComplexityLevel enum values."""
        assert ComplexityLevel.BASIC.value == "basic"
        assert ComplexityLevel.INTERMEDIATE.value == "intermediate"
        assert ComplexityLevel.ADVANCED.value == "advanced"
        assert ComplexityLevel.EXPERT.value == "expert"

    def test_technical_domain_enum_values(self):
        """Test TechnicalDomain enum values."""
        assert TechnicalDomain.SOFTWARE_ENGINEERING.value == "software_engineering"
        assert TechnicalDomain.DATA_SCIENCE.value == "data_science"
        assert TechnicalDomain.MACHINE_LEARNING.value == "machine_learning"
        assert TechnicalDomain.WEB_DEVELOPMENT.value == "web_development"

    def test_content_analysis_result_creation(self):
        """Test ContentAnalysisResult creation."""
        result = ContentAnalysisResult(
            content_type=ContentType.TECHNICAL_DOCUMENT,
            complexity_level=ComplexityLevel.INTERMEDIATE,
            technical_domains=[TechnicalDomain.MACHINE_LEARNING],
            keywords=["test", "keywords"],
            summary="Test summary",
            key_takeaways=["Test takeaway"],
            readability_score=0.8,
            estimated_reading_time=10,
            language="en",
            quality_score=0.9,
            metadata={"test": "data"},
        )

        assert result.content_type == ContentType.TECHNICAL_DOCUMENT
        assert result.complexity_level == ComplexityLevel.INTERMEDIATE
        assert TechnicalDomain.MACHINE_LEARNING in result.technical_domains
        assert "test" in result.keywords
        assert result.summary == "Test summary"
        assert result.readability_score == 0.8
        assert result.estimated_reading_time == 10
        assert result.language == "en"
        assert result.quality_score == 0.9
        assert result.metadata["test"] == "data"
