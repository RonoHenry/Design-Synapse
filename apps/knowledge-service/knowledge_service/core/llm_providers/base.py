"""Base LLM provider interface."""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Union


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    @abstractmethod
    def __init__(self, **config):
        """Initialize the LLM provider with configuration."""
        pass
    
    @abstractmethod
    def summarize(self, text: str, max_length: Optional[int] = None) -> str:
        """Generate a summary of the input text."""
        pass
    
    @abstractmethod
    def extract_key_points(self, text: str, max_points: Optional[int] = None) -> List[str]:
        """Extract key points from the input text."""
        pass
    
    @abstractmethod
    def classify_content(self, text: str, categories: Optional[List[str]] = None) -> List[str]:
        """Classify content into categories."""
        pass
    
    @abstractmethod
    def extract_topics(self, text: str) -> List[str]:
        """Extract topics from the input text."""
        pass
    
    @abstractmethod
    def calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts."""
        pass
    
    @abstractmethod
    def batch_process(self, texts: List[str], operation: str) -> List[Union[str, List[str]]]:
        """Process multiple texts with the specified operation."""
        pass
    
    @abstractmethod
    def detect_language(self, text: str) -> str:
        """Detect the language of the input text."""
        pass