"""Service for generating resource summaries and insights using LLMs."""

import asyncio
import logging
import os
import time
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional, Tuple

import httpx
import numpy as np
from sentence_transformers import SentenceTransformer
from sqlalchemy.orm import Session

from ..config import get_config
from ..core.error_handling import (ErrorRecovery, error_context,
                                   handle_service_errors)
from ..exceptions import EmbeddingGenerationError, LLMServiceError
from ..interfaces.services import ILLMService
from ..models import Resource

logger = logging.getLogger(__name__)


class CircuitBreaker:
    """Simple circuit breaker implementation for LLM service resilience."""

    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    def can_execute(self) -> bool:
        """Check if operation can be executed."""
        if self.state == "CLOSED":
            return True
        elif self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF_OPEN"
                return True
            return False
        else:  # HALF_OPEN
            return True

    def record_success(self):
        """Record successful operation."""
        self.failure_count = 0
        self.state = "CLOSED"

    def record_failure(self):
        """Record failed operation."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            logger.warning(
                f"Circuit breaker opened after {self.failure_count} failures"
            )


class LLMService(ILLMService):
    """Service for LLM-based text analysis and generation with enhanced error handling."""

    def __init__(self, config=None):
        """Initialize the service."""
        from ..config import get_config

        self.config = config or get_config()
        self.api_key = self.config.llm.get_provider_config("openai").get(
            "api_key"
        ) or os.getenv("OPENAI_API_KEY")
        self.api_url = "https://api.openai.com/v1/chat/completions"
        self.model = self.config.llm.get_provider_config("openai").get(
            "model", "gpt-3.5-turbo"
        )

        # Circuit breaker for resilience
        self.circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60)

        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 0.1  # 100ms between requests

        if not self.api_key:
            logger.warning("OpenAI API key not configured")

        # Initialize embedding model with error handling
        self._init_embedding_model()

        # Initialize HTTP client with enhanced configuration
        self._init_http_client()

    def _init_embedding_model(self):
        """Initialize embedding model with error handling."""
        try:
            embedding_config = self.config.vector.get_provider_config()
            model_name = embedding_config.get("embedding_model", "all-MiniLM-L6-v2")
            self.embedding_model = SentenceTransformer(model_name)
            logger.info(f"Loaded embedding model: {model_name}")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            # Try fallback model
            try:
                self.embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
                logger.info("Loaded fallback embedding model: all-MiniLM-L6-v2")
            except Exception as fallback_error:
                logger.error(
                    f"Failed to load fallback embedding model: {fallback_error}"
                )
                raise LLMServiceError(f"Failed to initialize embedding model: {str(e)}")

    def _init_http_client(self):
        """Initialize HTTP client with enhanced configuration."""
        timeout_config = httpx.Timeout(
            connect=10.0,  # Connection timeout
            read=30.0,  # Read timeout
            write=10.0,  # Write timeout
            pool=5.0,  # Pool timeout
        )

        self._client = httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "User-Agent": "DAEC-Knowledge-Service/1.0",
            },
            timeout=timeout_config,
            limits=httpx.Limits(
                max_keepalive_connections=5, max_connections=10, keepalive_expiry=30.0
            ),
            retries=2,
        )

    @handle_service_errors("llm", "generate_insights")
    @ErrorRecovery.with_retry(
        max_attempts=3,
        delay_seconds=1.0,
        exceptions=(httpx.TimeoutException, httpx.HTTPStatusError),
    )
    async def generate_insights(
        self, text: str, resource: Resource, db: Session
    ) -> Tuple[str, List[str], List[str]]:
        """Generate summary, key takeaways, and keywords for a resource.

        Args:
            text: The text content to analyze
            resource: The resource model
            db: Database session

        Returns:
            Tuple of (summary, key_takeaways, keywords)
        """
        with error_context(
            "generate_insights", resource_id=resource.id, content_length=len(text)
        ):
            # Validate inputs
            if not text or not text.strip():
                raise LLMServiceError("Text content cannot be empty")

            if len(text) < 50:
                logger.warning(
                    f"Text content is very short ({len(text)} chars) for resource {resource.id}"
                )

            # Check circuit breaker
            if not self.circuit_breaker.can_execute():
                raise LLMServiceError(
                    "LLM service temporarily unavailable (circuit breaker open)"
                )

            # Rate limiting
            await self._apply_rate_limiting()

            # Prepare the system message with context
            system_message = (
                "You are an expert in architecture, engineering, and construction. "
                "Analyze the following text from a technical resource and provide:\n"
                "1. A concise summary (max 2000 chars)\n"
                "2. Key takeaways (5-7 bullet points)\n"
                "3. Relevant keywords/tags (5-10 terms)\n\n"
                "Focus on practical implications for DAEC professionals. "
                "Format your response with clear sections separated by double newlines."
            )

            # Truncate content if needed
            max_content_length = getattr(self.config, "max_content_length", 8000)
            truncated_text = (
                text[:max_content_length] if len(text) > max_content_length else text
            )

            if len(text) > max_content_length:
                logger.info(
                    f"Truncated content from {len(text)} to {max_content_length} chars for resource {resource.id}"
                )

            try:
                # Make API request with enhanced error handling
                llm_config = self.config.llm.get_provider_config("openai")
                response = await self._client.post(
                    self.api_url,
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": system_message},
                            {"role": "user", "content": truncated_text},
                        ],
                        "temperature": llm_config.get("temperature", 0.3),
                        "max_tokens": llm_config.get("max_tokens", 1500),
                        "presence_penalty": 0.1,
                        "frequency_penalty": 0.1,
                    },
                )

                # Handle different HTTP status codes
                if response.status_code == 429:
                    self.circuit_breaker.record_failure()
                    retry_after = response.headers.get("Retry-After", "60")
                    raise LLMServiceError(
                        f"Rate limit exceeded. Retry after {retry_after} seconds"
                    )
                elif response.status_code == 401:
                    raise LLMServiceError("Invalid API key or authentication failed")
                elif response.status_code == 403:
                    raise LLMServiceError("Access forbidden. Check API permissions")
                elif response.status_code >= 500:
                    self.circuit_breaker.record_failure()
                    raise LLMServiceError(f"LLM service error: {response.status_code}")

                response.raise_for_status()
                result = response.json()

                # Record success for circuit breaker
                self.circuit_breaker.record_success()

            except httpx.TimeoutException as e:
                self.circuit_breaker.record_failure()
                logger.error(f"OpenAI API request timed out for resource {resource.id}")
                raise LLMServiceError("LLM request timed out") from e
            except httpx.HTTPStatusError as e:
                self.circuit_breaker.record_failure()
                error_detail = ""
                try:
                    error_detail = e.response.text
                except:
                    pass
                logger.error(
                    f"OpenAI API error for resource {resource.id}: {e.response.status_code} - {error_detail}"
                )
                raise LLMServiceError(f"LLM API error: {e.response.status_code}") from e
            except Exception as e:
                self.circuit_breaker.record_failure()
                logger.error(
                    f"Unexpected error calling LLM API for resource {resource.id}: {e}"
                )
                raise LLMServiceError(f"Failed to call LLM API: {str(e)}") from e

            # Parse and validate the response
            try:
                summary, key_takeaways, keywords = self._parse_insights_response(
                    result, resource.id
                )
            except Exception as e:
                logger.error(
                    f"Failed to parse LLM response for resource {resource.id}: {e}"
                )
                raise LLMServiceError(f"Failed to parse LLM response: {str(e)}") from e

            # Update resource with transaction safety
            try:
                resource.summary = summary
                resource.key_takeaways = key_takeaways
                resource.keywords = keywords
                db.commit()

                logger.info(
                    f"Successfully generated insights for resource {resource.id}"
                )

            except Exception as e:
                db.rollback()
                logger.error(f"Failed to save insights for resource {resource.id}: {e}")
                raise LLMServiceError(f"Failed to save insights: {str(e)}") from e

            return summary, key_takeaways, keywords

    def _parse_insights_response(
        self, result: Dict, resource_id: int
    ) -> Tuple[str, List[str], List[str]]:
        """Parse LLM response into structured insights.

        Args:
            result: LLM API response
            resource_id: Resource ID for logging

        Returns:
            Tuple of (summary, key_takeaways, keywords)
        """
        try:
            output = result["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as e:
            raise LLMServiceError(f"Invalid LLM response structure: {e}")

        if not output or not output.strip():
            raise LLMServiceError("Empty response from LLM")

        # Split into sections
        sections = [
            section.strip() for section in output.split("\n\n") if section.strip()
        ]

        if len(sections) < 3:
            logger.warning(
                f"LLM response has fewer than 3 sections for resource {resource_id}, attempting to parse anyway"
            )
            # Fallback parsing
            return self._fallback_parse_insights(output, resource_id)

        # Extract insights with validation
        summary = sections[0].strip()
        if len(summary) > 2500:  # Truncate if too long
            summary = summary[:2500] + "..."
            logger.warning(f"Truncated summary for resource {resource_id}")

        # Parse key takeaways
        key_takeaways = []
        takeaway_text = sections[1].strip()
        for line in takeaway_text.split("\n"):
            line = line.strip()
            if line and not line.startswith("Key takeaways:"):
                # Remove bullet points and numbering
                clean_line = line.lstrip("•-*123456789. ").strip()
                if clean_line:
                    key_takeaways.append(clean_line)

        # Parse keywords
        keywords = []
        keyword_text = sections[2].strip()
        if "," in keyword_text:
            keywords = [kw.strip() for kw in keyword_text.split(",") if kw.strip()]
        else:
            # Try splitting by newlines
            for line in keyword_text.split("\n"):
                line = line.strip()
                if line and not line.startswith("Keywords:"):
                    clean_line = line.lstrip("•-*123456789. ").strip()
                    if clean_line:
                        keywords.append(clean_line)

        # Validate results
        if not summary:
            raise LLMServiceError("No summary generated")
        if not key_takeaways:
            logger.warning(f"No key takeaways generated for resource {resource_id}")
            key_takeaways = ["Analysis completed"]
        if not keywords:
            logger.warning(f"No keywords generated for resource {resource_id}")
            keywords = ["general"]

        # Limit list sizes
        key_takeaways = key_takeaways[:10]  # Max 10 takeaways
        keywords = keywords[:15]  # Max 15 keywords

        return summary, key_takeaways, keywords

    def _fallback_parse_insights(
        self, output: str, resource_id: int
    ) -> Tuple[str, List[str], List[str]]:
        """Fallback parsing when structured response fails.

        Args:
            output: Raw LLM output
            resource_id: Resource ID for logging

        Returns:
            Tuple of (summary, key_takeaways, keywords)
        """
        logger.warning(f"Using fallback parsing for resource {resource_id}")

        # Use the entire output as summary if it's reasonable length
        summary = output[:2000] if len(output) > 2000 else output

        # Extract simple takeaways from the text
        lines = [line.strip() for line in output.split("\n") if line.strip()]
        key_takeaways = []
        keywords = []

        for line in lines:
            if any(
                marker in line.lower()
                for marker in ["key", "important", "takeaway", "conclusion"]
            ):
                clean_line = line.lstrip("•-*123456789. ").strip()
                if clean_line and len(clean_line) > 10:
                    key_takeaways.append(clean_line)

        # If no takeaways found, create a generic one
        if not key_takeaways:
            key_takeaways = ["Content analysis completed"]

        # Extract potential keywords (simple approach)
        words = output.lower().split()
        common_words = {
            "the",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "a",
            "an",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "could",
            "should",
            "may",
            "might",
            "can",
            "this",
            "that",
            "these",
            "those",
        }

        word_freq = {}
        for word in words:
            word = word.strip(".,!?;:()[]{}\"'").lower()
            if len(word) > 3 and word not in common_words:
                word_freq[word] = word_freq.get(word, 0) + 1

        # Get top keywords by frequency
        keywords = sorted(word_freq.keys(), key=lambda x: word_freq[x], reverse=True)[
            :10
        ]

        if not keywords:
            keywords = ["general"]

        return summary, key_takeaways, keywords

    async def _apply_rate_limiting(self):
        """Apply rate limiting between requests."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time

        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            await asyncio.sleep(sleep_time)

        self.last_request_time = time.time()

    async def generate_recommendations(
        self, user_id: int, user_role: str, project_context: Dict, db: Session
    ) -> List[Dict]:
        """Generate personalized resource recommendations.

        Args:
            user_id: The ID of the user
            user_role: The user's role (architect, engineer, etc.)
            project_context: Current project context
            db: Database session

        Returns:
            List of recommended resources with explanations
        """
        # TODO: Implement personalized recommendations using
        # user history, role, and project context
        pass

    @handle_service_errors("llm", "extract_topics")
    @ErrorRecovery.with_retry(
        max_attempts=2,
        delay_seconds=1.0,
        exceptions=(httpx.TimeoutException, httpx.HTTPStatusError),
    )
    async def extract_topics(self, content: str) -> List[str]:
        """Extract relevant topics from the content."""
        with error_context("extract_topics", content_length=len(content)):
            if not content or not content.strip():
                raise LLMServiceError("Content cannot be empty")

            # Check circuit breaker
            if not self.circuit_breaker.can_execute():
                logger.warning("Circuit breaker open, using fallback topic extraction")
                return self._fallback_extract_topics(content)

            # Rate limiting
            await self._apply_rate_limiting()

            # Truncate content if needed
            max_length = 4000
            truncated_content = (
                content[:max_length] if len(content) > max_length else content
            )

            try:
                # Make API request
                response = await self._client.post(
                    self.api_url,
                    json={
                        "model": self.model,
                        "messages": [
                            {
                                "role": "system",
                                "content": "Extract the main topics discussed in the content. Return them as a numbered list with one topic per line.",
                            },
                            {
                                "role": "user",
                                "content": f"Extract the main topics from this content:\n\n{truncated_content}",
                            },
                        ],
                        "temperature": 0.3,
                        "max_tokens": 300,
                    },
                )
                response.raise_for_status()
                result = response.json()

                self.circuit_breaker.record_success()

                topics_text = result["choices"][0]["message"]["content"].strip()
                topics = []

                for line in topics_text.split("\n"):
                    line = line.strip()
                    if line:
                        # Remove numbering and bullet points
                        clean_topic = line.lstrip("•-*123456789. ").strip()
                        if clean_topic and len(clean_topic) > 2:
                            topics.append(clean_topic)

                return topics[:10] if topics else ["General content"]

            except Exception as e:
                self.circuit_breaker.record_failure()
                logger.warning(f"LLM topic extraction failed, using fallback: {e}")
                return self._fallback_extract_topics(content)

    def _fallback_extract_topics(self, content: str) -> List[str]:
        """Fallback topic extraction using simple text analysis."""
        # Simple keyword-based topic extraction
        words = content.lower().split()

        # Common technical terms that might indicate topics
        technical_terms = {
            "architecture",
            "engineering",
            "construction",
            "design",
            "building",
            "structure",
            "material",
            "concrete",
            "steel",
            "foundation",
            "safety",
            "code",
            "regulation",
            "standard",
            "specification",
            "analysis",
            "load",
            "seismic",
            "thermal",
            "mechanical",
            "electrical",
            "plumbing",
            "hvac",
        }

        found_topics = []
        for term in technical_terms:
            if term in words:
                found_topics.append(term.title())

        return found_topics[:5] if found_topics else ["General Engineering"]

    @handle_service_errors("llm", "classify_resource")
    @ErrorRecovery.with_fallback(fallback_value=["General"], log_error=True)
    async def classify_resource(self, content: str) -> List[str]:
        """Classify the resource content into categories."""
        with error_context("classify_resource", content_length=len(content)):
            if not content or not content.strip():
                raise LLMServiceError("Content cannot be empty")

            # Check circuit breaker
            if not self.circuit_breaker.can_execute():
                return self._fallback_classify_resource(content)

            # Rate limiting
            await self._apply_rate_limiting()

            # Truncate content if needed
            max_length = 3000
            truncated_content = (
                content[:max_length] if len(content) > max_length else content
            )

            response = await self._client.post(
                self.api_url,
                json={
                    "model": self.model,
                    "messages": [
                        {
                            "role": "system",
                            "content": "Classify the content into relevant DAEC technical categories. Return a numbered list.",
                        },
                        {
                            "role": "user",
                            "content": f"Classify this content into relevant categories:\n\n{truncated_content}",
                        },
                    ],
                    "temperature": 0.3,
                    "max_tokens": 200,
                },
            )
            response.raise_for_status()
            result = response.json()

            self.circuit_breaker.record_success()

            categories_text = result["choices"][0]["message"]["content"].strip()
            categories = []

            for line in categories_text.split("\n"):
                line = line.strip()
                if line:
                    clean_category = line.lstrip("•-*123456789. ").strip()
                    if clean_category and len(clean_category) > 2:
                        categories.append(clean_category)

            return categories[:8] if categories else ["General"]

    def _fallback_classify_resource(self, content: str) -> List[str]:
        """Fallback classification using keyword matching."""
        content_lower = content.lower()

        categories = []
        category_keywords = {
            "Structural Engineering": [
                "structure",
                "beam",
                "column",
                "foundation",
                "load",
                "stress",
            ],
            "Architecture": [
                "design",
                "building",
                "space",
                "layout",
                "aesthetic",
                "plan",
            ],
            "Construction": [
                "construction",
                "building",
                "material",
                "concrete",
                "steel",
                "site",
            ],
            "Safety": ["safety", "hazard", "risk", "protection", "emergency", "code"],
            "Mechanical": [
                "hvac",
                "mechanical",
                "ventilation",
                "heating",
                "cooling",
                "system",
            ],
            "Electrical": [
                "electrical",
                "power",
                "lighting",
                "circuit",
                "wiring",
                "energy",
            ],
            "Plumbing": ["plumbing", "water", "pipe", "drainage", "sewer", "fixture"],
            "Codes & Standards": [
                "code",
                "standard",
                "regulation",
                "compliance",
                "requirement",
                "specification",
            ],
        }

        for category, keywords in category_keywords.items():
            if any(keyword in content_lower for keyword in keywords):
                categories.append(category)

        return categories if categories else ["General Engineering"]

    @handle_service_errors("llm", "extract_keywords")
    @ErrorRecovery.with_fallback(fallback_value=["general"], log_error=True)
    async def extract_keywords(self, content: str) -> List[str]:
        """Extract important keywords from the content."""
        with error_context("extract_keywords", content_length=len(content)):
            if not content or not content.strip():
                raise LLMServiceError("Content cannot be empty")

            # Check circuit breaker
            if not self.circuit_breaker.can_execute():
                return self._fallback_extract_keywords(content)

            # Rate limiting
            await self._apply_rate_limiting()

            # Truncate content if needed
            max_length = 3000
            truncated_content = (
                content[:max_length] if len(content) > max_length else content
            )

            response = await self._client.post(
                self.api_url,
                json={
                    "model": self.model,
                    "messages": [
                        {
                            "role": "system",
                            "content": "Extract important technical keywords and terms. Return them as a comma-separated list.",
                        },
                        {
                            "role": "user",
                            "content": f"Extract key technical terms from this content:\n\n{truncated_content}",
                        },
                    ],
                    "temperature": 0.3,
                    "max_tokens": 150,
                },
            )
            response.raise_for_status()
            result = response.json()

            self.circuit_breaker.record_success()

            keywords_text = result["choices"][0]["message"]["content"].strip()
            keywords = [k.strip() for k in keywords_text.split(",") if k.strip()]

            # Clean and validate keywords
            clean_keywords = []
            for keyword in keywords:
                keyword = keyword.strip().strip("\"'")
                if keyword and len(keyword) > 1 and len(keyword) < 50:
                    clean_keywords.append(keyword)

            return clean_keywords[:15] if clean_keywords else ["general"]

    def _fallback_extract_keywords(self, content: str) -> List[str]:
        """Fallback keyword extraction using frequency analysis."""
        import re

        # Simple keyword extraction based on word frequency
        words = re.findall(r"\b[a-zA-Z]{3,}\b", content.lower())

        # Common stop words to exclude
        stop_words = {
            "the",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "a",
            "an",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "could",
            "should",
            "may",
            "might",
            "can",
            "this",
            "that",
            "these",
            "those",
            "they",
            "them",
            "their",
            "there",
            "then",
            "than",
            "when",
            "where",
            "why",
            "how",
            "what",
            "who",
            "which",
            "while",
            "during",
        }

        # Count word frequencies
        word_freq = {}
        for word in words:
            if word not in stop_words and len(word) > 2:
                word_freq[word] = word_freq.get(word, 0) + 1

        # Get top keywords by frequency
        keywords = sorted(word_freq.keys(), key=lambda x: word_freq[x], reverse=True)[
            :10
        ]

        return keywords if keywords else ["general"]

    @handle_service_errors("llm", "compare_similarity")
    @ErrorRecovery.with_fallback(fallback_value=0.0, log_error=True)
    def compare_similarity(self, text1: str, text2: str) -> float:
        """Compare the semantic similarity between two texts."""
        with error_context(
            "compare_similarity", text1_length=len(text1), text2_length=len(text2)
        ):
            if not text1 or not text2 or not text1.strip() or not text2.strip():
                raise LLMServiceError("Both texts must be non-empty")

            # Truncate texts if too long
            max_length = 1000
            text1 = text1[:max_length] if len(text1) > max_length else text1
            text2 = text2[:max_length] if len(text2) > max_length else text2

            try:
                # Generate embeddings with error handling
                embedding1 = self.embedding_model.encode(text1, show_progress_bar=False)
                embedding2 = self.embedding_model.encode(text2, show_progress_bar=False)

                # Validate embeddings
                if embedding1 is None or embedding2 is None:
                    raise EmbeddingGenerationError("Failed to generate embeddings")

                # Compute cosine similarity
                dot_product = np.dot(embedding1, embedding2)
                norm1 = np.linalg.norm(embedding1)
                norm2 = np.linalg.norm(embedding2)

                if norm1 == 0 or norm2 == 0:
                    logger.warning("Zero norm detected in similarity computation")
                    return 0.0

                similarity = dot_product / (norm1 * norm2)

                # Ensure similarity is in valid range [-1, 1]
                similarity = max(-1.0, min(1.0, float(similarity)))

                return similarity

            except Exception as e:
                logger.error(f"Failed to compute similarity: {e}")
                raise EmbeddingGenerationError(
                    f"Failed to compute text similarity: {str(e)}"
                ) from e

    @asynccontextmanager
    async def get_client(self):
        """Get HTTP client as async context manager."""
        try:
            yield self._client
        finally:
            # Client cleanup is handled in __aexit__
            pass

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        try:
            await self._client.aclose()
        except Exception as e:
            logger.warning(f"Error closing HTTP client: {e}")

    @handle_service_errors("llm", "batch_summarize")
    async def batch_summarize(self, texts: List[str]) -> List[str]:
        """Summarize multiple texts in batch with enhanced error handling."""
        with error_context("batch_summarize", batch_size=len(texts)):
            if not texts:
                raise LLMServiceError("Text list cannot be empty")

            if len(texts) > 50:  # Reasonable batch limit
                raise LLMServiceError("Batch size too large (max 50)")

            summaries = []
            failed_indices = []

            for i, text in enumerate(texts):
                try:
                    if not text or not text.strip():
                        summaries.append("No content to summarize")
                        continue

                    # Create mock objects for the generate_insights method
                    class MockResource:
                        def __init__(self, idx):
                            self.id = f"batch_{idx}"
                            self.summary = None
                            self.key_takeaways = None
                            self.keywords = None

                    class MockDb:
                        def commit(self):
                            pass

                        def rollback(self):
                            pass

                    resource = MockResource(i)
                    db = MockDb()

                    summary, _, _ = await self.generate_insights(text, resource, db)
                    summaries.append(summary)

                except Exception as e:
                    logger.warning(f"Failed to summarize text {i}: {e}")
                    summaries.append(f"Summarization failed: {str(e)}")
                    failed_indices.append(i)

            if failed_indices:
                logger.warning(
                    f"Failed to summarize {len(failed_indices)} out of {len(texts)} texts"
                )

            return summaries

    @handle_service_errors("llm", "detect_language")
    @ErrorRecovery.with_fallback(fallback_value="English", log_error=True)
    async def detect_language(self, content: str) -> str:
        """Detect the language of the content."""
        with error_context("detect_language", content_length=len(content)):
            if not content or not content.strip():
                raise LLMServiceError("Content cannot be empty")

            # Check circuit breaker
            if not self.circuit_breaker.can_execute():
                return self._fallback_detect_language(content)

            # Rate limiting
            await self._apply_rate_limiting()

            # Use only first 500 characters for language detection
            sample_content = content[:500]

            response = await self._client.post(
                self.api_url,
                json={
                    "model": self.model,
                    "messages": [
                        {
                            "role": "system",
                            "content": "Detect the language of the given text. Respond with just the language name in English.",
                        },
                        {
                            "role": "user",
                            "content": f"What language is this text in:\n\n{sample_content}",
                        },
                    ],
                    "temperature": 0.1,
                    "max_tokens": 20,
                },
            )
            response.raise_for_status()
            result = response.json()

            self.circuit_breaker.record_success()

            language = result["choices"][0]["message"]["content"].strip()

            # Validate and clean the response
            if language and len(language) < 50:  # Reasonable language name length
                return language
            else:
                return "English"  # Default fallback

    def _fallback_detect_language(self, content: str) -> str:
        """Fallback language detection using simple heuristics."""
        # Simple character-based language detection
        content_sample = content[:200].lower()

        # Check for common non-English patterns
        if any(char in content_sample for char in "àáâãäåæçèéêëìíîïñòóôõöøùúûüý"):
            return "European Language"
        elif any(char in content_sample for char in "αβγδεζηθικλμνξοπρστυφχψω"):
            return "Greek"
        elif any(char in content_sample for char in "абвгдежзийклмнопрстуфхцчшщъыьэюя"):
            return "Russian"
        elif any(char in content_sample for char in "一二三四五六七八九十"):
            return "Chinese"
        elif any(char in content_sample for char in "ひらがなカタカナ"):
            return "Japanese"
        elif any(char in content_sample for char in "한글"):
            return "Korean"
        else:
            return "English"

    def get_service_health(self) -> Dict[str, Any]:
        """Get service health status."""
        return {
            "circuit_breaker_state": self.circuit_breaker.state,
            "circuit_breaker_failures": self.circuit_breaker.failure_count,
            "embedding_model_loaded": self.embedding_model is not None,
            "api_key_configured": bool(self.api_key),
            "last_request_time": self.last_request_time,
            "service_status": "healthy"
            if self.circuit_breaker.state == "CLOSED"
            else "degraded",
        }
