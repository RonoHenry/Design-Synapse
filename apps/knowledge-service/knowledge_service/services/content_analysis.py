"""Content analysis service for advanced content processing and tagging."""

import logging
import re
from collections import Counter
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from ..core.error_handling import (ErrorRecovery, error_context,
                                   handle_service_errors)
from ..exceptions import ContentProcessingError
from ..interfaces.services import ILLMService

logger = logging.getLogger(__name__)


class ContentType(Enum):
    """Content type classifications."""

    TECHNICAL_SPECIFICATION = "technical_specification"
    BUILDING_CODE = "building_code"
    DESIGN_GUIDELINE = "design_guideline"
    SAFETY_MANUAL = "safety_manual"
    CONSTRUCTION_MANUAL = "construction_manual"
    RESEARCH_PAPER = "research_paper"
    CASE_STUDY = "case_study"
    STANDARD_DOCUMENT = "standard_document"
    GENERAL_DOCUMENT = "general_document"


class ComplexityLevel(Enum):
    """Content complexity levels."""

    BASIC = "basic"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


@dataclass
class ContentAnalysis:
    """Content analysis results."""

    content_type: ContentType
    complexity_level: ComplexityLevel
    technical_domains: List[str]
    key_concepts: List[str]
    readability_score: float
    estimated_reading_time: int  # in minutes
    language: str
    quality_score: float
    tags: List[str]
    metadata: Dict[str, Any]


class ContentAnalysisService:
    """Service for advanced content analysis and tagging."""

    def __init__(self, llm_service: ILLMService):
        """Initialize content analysis service.

        Args:
            llm_service: LLM service for advanced analysis
        """
        self.llm_service = llm_service

        # Technical domain keywords
        self.domain_keywords = {
            "structural_engineering": [
                "beam",
                "column",
                "foundation",
                "load",
                "stress",
                "strain",
                "moment",
                "shear",
                "deflection",
                "reinforcement",
                "concrete",
                "steel",
                "seismic",
            ],
            "architecture": [
                "design",
                "space",
                "layout",
                "aesthetic",
                "plan",
                "elevation",
                "section",
                "facade",
                "interior",
                "exterior",
                "building",
                "structure",
                "form",
            ],
            "mechanical_engineering": [
                "hvac",
                "ventilation",
                "heating",
                "cooling",
                "air",
                "system",
                "duct",
                "pump",
                "fan",
                "compressor",
                "boiler",
                "chiller",
                "mechanical",
            ],
            "electrical_engineering": [
                "electrical",
                "power",
                "lighting",
                "circuit",
                "wiring",
                "voltage",
                "current",
                "transformer",
                "panel",
                "switch",
                "outlet",
                "energy",
            ],
            "civil_engineering": [
                "infrastructure",
                "road",
                "bridge",
                "water",
                "sewer",
                "drainage",
                "transportation",
                "geotechnical",
                "soil",
                "pavement",
                "traffic",
            ],
            "construction": [
                "construction",
                "building",
                "material",
                "site",
                "contractor",
                "project",
                "schedule",
                "cost",
                "quality",
                "safety",
                "equipment",
                "labor",
            ],
            "safety": [
                "safety",
                "hazard",
                "risk",
                "protection",
                "emergency",
                "fire",
                "code",
                "regulation",
                "compliance",
                "accident",
                "injury",
                "prevention",
            ],
            "sustainability": [
                "sustainable",
                "green",
                "energy",
                "efficiency",
                "renewable",
                "carbon",
                "environmental",
                "leed",
                "breeam",
                "lifecycle",
                "recycling",
            ],
        }

        # Complexity indicators
        self.complexity_indicators = {
            "basic": [
                "introduction",
                "basic",
                "simple",
                "overview",
                "guide",
                "tutorial",
            ],
            "intermediate": [
                "analysis",
                "design",
                "calculation",
                "method",
                "procedure",
                "standard",
            ],
            "advanced": [
                "optimization",
                "advanced",
                "complex",
                "research",
                "investigation",
                "modeling",
                "simulation",
                "theory",
                "algorithm",
            ],
            "expert": [
                "cutting-edge",
                "innovative",
                "experimental",
                "novel",
                "breakthrough",
                "state-of-the-art",
                "pioneering",
                "revolutionary",
            ],
        }

        # Content type patterns
        self.content_type_patterns = {
            ContentType.TECHNICAL_SPECIFICATION: [
                r"specification",
                r"spec\b",
                r"requirements?",
                r"technical.*standard",
                r"performance.*criteria",
                r"design.*parameters",
            ],
            ContentType.BUILDING_CODE: [
                r"building.*code",
                r"code.*compliance",
                r"regulatory.*requirements?",
                r"zoning.*ordinance",
                r"municipal.*code",
            ],
            ContentType.DESIGN_GUIDELINE: [
                r"design.*guideline",
                r"design.*manual",
                r"best.*practices?",
                r"design.*standards?",
                r"architectural.*guidelines?",
            ],
            ContentType.SAFETY_MANUAL: [
                r"safety.*manual",
                r"safety.*procedures?",
                r"emergency.*procedures?",
                r"hazard.*identification",
                r"risk.*assessment",
            ],
            ContentType.CONSTRUCTION_MANUAL: [
                r"construction.*manual",
                r"installation.*guide",
                r"assembly.*instructions?",
                r"construction.*procedures?",
                r"field.*guide",
            ],
            ContentType.RESEARCH_PAPER: [
                r"abstract",
                r"methodology",
                r"literature.*review",
                r"experimental.*results?",
                r"conclusions?",
                r"references?",
                r"bibliography",
            ],
            ContentType.CASE_STUDY: [
                r"case.*study",
                r"project.*overview",
                r"lessons.*learned",
                r"project.*analysis",
                r"real.*world.*application",
            ],
            ContentType.STANDARD_DOCUMENT: [
                r"standard",
                r"iso.*\d+",
                r"astm.*\d+",
                r"ansi.*\d+",
                r"ieee.*\d+",
                r"international.*standard",
                r"national.*standard",
            ],
        }

    @handle_service_errors("content_analysis", "analyze_content")
    async def analyze_content(
        self, content: str, title: str = "", metadata: Optional[Dict] = None
    ) -> ContentAnalysis:
        """Perform comprehensive content analysis.

        Args:
            content: Text content to analyze
            title: Optional title of the content
            metadata: Optional existing metadata

        Returns:
            ContentAnalysis object with analysis results
        """
        with error_context("analyze_content", content_length=len(content)):
            if not content or not content.strip():
                raise ContentProcessingError("Content cannot be empty")

            # Perform analysis components
            content_type = self._classify_content_type(content, title)
            complexity_level = self._assess_complexity(content)
            technical_domains = self._identify_technical_domains(content)
            key_concepts = await self._extract_key_concepts(content)
            readability_score = self._calculate_readability(content)
            reading_time = self._estimate_reading_time(content)
            language = await self._detect_language(content)
            quality_score = self._assess_quality(content)
            tags = await self._generate_tags(content, title)

            # Compile metadata
            analysis_metadata = {
                "word_count": len(content.split()),
                "character_count": len(content),
                "paragraph_count": len([p for p in content.split("\n\n") if p.strip()]),
                "sentence_count": len(re.findall(r"[.!?]+", content)),
                "analysis_timestamp": self._get_timestamp(),
                **(metadata or {}),
            }

            return ContentAnalysis(
                content_type=content_type,
                complexity_level=complexity_level,
                technical_domains=technical_domains,
                key_concepts=key_concepts,
                readability_score=readability_score,
                estimated_reading_time=reading_time,
                language=language,
                quality_score=quality_score,
                tags=tags,
                metadata=analysis_metadata,
            )

    def _classify_content_type(self, content: str, title: str = "") -> ContentType:
        """Classify content type based on patterns and keywords."""
        combined_text = f"{title} {content}".lower()

        type_scores = {}

        for content_type, patterns in self.content_type_patterns.items():
            score = 0
            for pattern in patterns:
                matches = len(re.findall(pattern, combined_text, re.IGNORECASE))
                score += matches

            if score > 0:
                type_scores[content_type] = score

        if type_scores:
            return max(type_scores.keys(), key=lambda k: type_scores[k])

        return ContentType.GENERAL_DOCUMENT

    def _assess_complexity(self, content: str) -> ComplexityLevel:
        """Assess content complexity based on various indicators."""
        content_lower = content.lower()

        complexity_scores = {level: 0 for level in ComplexityLevel}

        # Check for complexity indicators
        for level, indicators in self.complexity_indicators.items():
            for indicator in indicators:
                if indicator in content_lower:
                    complexity_scores[ComplexityLevel(level)] += 1

        # Additional complexity metrics
        words = content.split()
        avg_word_length = sum(len(word) for word in words) / len(words) if words else 0

        # Adjust scores based on metrics
        if avg_word_length > 6:
            complexity_scores[ComplexityLevel.ADVANCED] += 1
        elif avg_word_length > 5:
            complexity_scores[ComplexityLevel.INTERMEDIATE] += 1
        else:
            complexity_scores[ComplexityLevel.BASIC] += 1

        # Check for technical jargon density
        technical_words = sum(1 for word in words if len(word) > 8)
        jargon_ratio = technical_words / len(words) if words else 0

        if jargon_ratio > 0.15:
            complexity_scores[ComplexityLevel.EXPERT] += 2
        elif jargon_ratio > 0.10:
            complexity_scores[ComplexityLevel.ADVANCED] += 1

        # Return highest scoring complexity level
        if complexity_scores:
            return max(complexity_scores.keys(), key=lambda k: complexity_scores[k])

        return ComplexityLevel.INTERMEDIATE

    def _identify_technical_domains(self, content: str) -> List[str]:
        """Identify technical domains present in the content."""
        content_lower = content.lower()
        domain_scores = {}

        for domain, keywords in self.domain_keywords.items():
            score = 0
            for keyword in keywords:
                # Count occurrences with word boundaries
                pattern = r"\b" + re.escape(keyword) + r"\b"
                matches = len(re.findall(pattern, content_lower))
                score += matches

            if score > 0:
                domain_scores[domain] = score

        # Return domains sorted by relevance
        sorted_domains = sorted(
            domain_scores.keys(), key=lambda k: domain_scores[k], reverse=True
        )

        # Return top domains (max 5)
        return [domain.replace("_", " ").title() for domain in sorted_domains[:5]]

    async def _extract_key_concepts(self, content: str) -> List[str]:
        """Extract key concepts using LLM and statistical analysis."""
        try:
            # Use LLM for concept extraction
            llm_concepts = await self.llm_service.extract_keywords(content)

            # Statistical concept extraction as backup
            statistical_concepts = self._extract_statistical_concepts(content)

            # Combine and deduplicate
            all_concepts = list(set(llm_concepts + statistical_concepts))

            return all_concepts[:15]  # Limit to top 15 concepts

        except Exception as e:
            logger.warning(
                f"LLM concept extraction failed, using statistical method: {e}"
            )
            return self._extract_statistical_concepts(content)

    def _extract_statistical_concepts(self, content: str) -> List[str]:
        """Extract concepts using statistical analysis."""
        # Clean and tokenize
        words = re.findall(r"\b[a-zA-Z]{3,}\b", content.lower())

        # Remove common stop words
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
        }

        filtered_words = [word for word in words if word not in stop_words]

        # Count frequencies
        word_freq = Counter(filtered_words)

        # Get top concepts
        top_concepts = [word for word, count in word_freq.most_common(10)]

        return top_concepts

    def _calculate_readability(self, content: str) -> float:
        """Calculate readability score (simplified Flesch Reading Ease)."""
        sentences = re.split(r"[.!?]+", content)
        sentences = [s.strip() for s in sentences if s.strip()]

        words = content.split()

        if not sentences or not words:
            return 50.0  # Default score

        avg_sentence_length = len(words) / len(sentences)

        # Count syllables (simplified)
        syllable_count = 0
        for word in words:
            word = word.lower().strip('.,!?;:"()[]{}')
            syllable_count += max(1, len(re.findall(r"[aeiouAEIOU]", word)))

        avg_syllables_per_word = syllable_count / len(words)

        # Simplified Flesch Reading Ease formula
        readability = (
            206.835 - (1.015 * avg_sentence_length) - (84.6 * avg_syllables_per_word)
        )

        # Normalize to 0-100 range
        return max(0, min(100, readability))

    def _estimate_reading_time(self, content: str) -> int:
        """Estimate reading time in minutes (assuming 200 words per minute)."""
        word_count = len(content.split())
        reading_time = max(1, round(word_count / 200))
        return reading_time

    async def _detect_language(self, content: str) -> str:
        """Detect content language."""
        try:
            return await self.llm_service.detect_language(content)
        except Exception as e:
            logger.warning(f"LLM language detection failed, using fallback: {e}")
            return self._fallback_language_detection(content)

    def _fallback_language_detection(self, content: str) -> str:
        """Fallback language detection using character patterns."""
        # Simple character-based detection
        sample = content[:500].lower()

        if any(char in sample for char in "àáâãäåæçèéêëìíîïñòóôõöøùúûüý"):
            return "European Language"
        elif any(char in sample for char in "一二三四五六七八九十"):
            return "Chinese"
        elif any(char in sample for char in "ひらがなカタカナ"):
            return "Japanese"
        else:
            return "English"

    def _assess_quality(self, content: str) -> float:
        """Assess content quality based on various metrics."""
        quality_score = 0.0

        # Length factor (reasonable length gets higher score)
        word_count = len(content.split())
        if 100 <= word_count <= 5000:
            quality_score += 0.3
        elif word_count > 50:
            quality_score += 0.2

        # Structure factor (paragraphs, sentences)
        paragraphs = [p for p in content.split("\n\n") if p.strip()]
        if len(paragraphs) > 1:
            quality_score += 0.2

        # Sentence variety
        sentences = re.split(r"[.!?]+", content)
        if len(sentences) > 3:
            avg_sentence_length = sum(len(s.split()) for s in sentences) / len(
                sentences
            )
            if 10 <= avg_sentence_length <= 25:
                quality_score += 0.2

        # Technical content indicator
        technical_terms = sum(1 for word in content.split() if len(word) > 6)
        if technical_terms > word_count * 0.1:
            quality_score += 0.2

        # Grammar and spelling (simplified check)
        if not re.search(r"\b(teh|recieve|seperate|occured)\b", content.lower()):
            quality_score += 0.1

        return min(1.0, quality_score)

    async def _generate_tags(self, content: str, title: str = "") -> List[str]:
        """Generate comprehensive tags for the content."""
        tags = set()

        # Add content type tag
        content_type = self._classify_content_type(content, title)
        tags.add(content_type.value.replace("_", " ").title())

        # Add complexity tag
        complexity = self._assess_complexity(content)
        tags.add(complexity.value.title())

        # Add domain tags
        domains = self._identify_technical_domains(content)
        tags.update(domains)

        # Add keyword-based tags
        try:
            keywords = await self.llm_service.extract_keywords(content)
            tags.update(keywords[:5])  # Add top 5 keywords
        except Exception as e:
            logger.warning(f"Failed to extract keywords for tags: {e}")

        # Add length-based tags
        word_count = len(content.split())
        if word_count < 500:
            tags.add("Short")
        elif word_count > 2000:
            tags.add("Long")
        else:
            tags.add("Medium")

        return list(tags)[:20]  # Limit to 20 tags

    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime

        return datetime.now().isoformat()

    @handle_service_errors("content_analysis", "batch_analyze")
    async def batch_analyze_content(
        self, content_items: List[Dict[str, str]]
    ) -> List[ContentAnalysis]:
        """Analyze multiple content items in batch.

        Args:
            content_items: List of dicts with 'content', 'title', and optional 'metadata'

        Returns:
            List of ContentAnalysis results
        """
        with error_context("batch_analyze", batch_size=len(content_items)):
            if not content_items:
                raise ContentProcessingError("Content items list cannot be empty")

            results = []

            for i, item in enumerate(content_items):
                try:
                    content = item.get("content", "")
                    title = item.get("title", "")
                    metadata = item.get("metadata", {})

                    analysis = await self.analyze_content(content, title, metadata)
                    results.append(analysis)

                except Exception as e:
                    logger.error(f"Failed to analyze content item {i}: {e}")
                    # Add a minimal analysis result for failed items
                    results.append(
                        ContentAnalysis(
                            content_type=ContentType.GENERAL_DOCUMENT,
                            complexity_level=ComplexityLevel.INTERMEDIATE,
                            technical_domains=["general"],
                            key_concepts=["content"],
                            readability_score=50.0,
                            estimated_reading_time=1,
                            language="Unknown",
                            quality_score=0.0,
                            tags=["failed_analysis"],
                            metadata={"error": str(e)},
                        )
                    )

            return results
