"""OpenAI LLM provider implementation."""
from typing import List, Optional, Union
import openai
from .base import BaseLLMProvider


class OpenAIProvider(BaseLLMProvider):
    """OpenAI-based LLM provider implementation."""

    def __init__(self, **config):
        """Initialize OpenAI provider with API key and model settings."""
        super().__init__()
        self.api_key = config.get('api_key')
        self.model = config.get('model', 'gpt-4')
        self.max_tokens = config.get('max_tokens', 500)
        openai.api_key = self.api_key

    def summarize(self, text: str, max_length: Optional[int] = None) -> str:
        """Generate a summary using OpenAI model."""
        response = openai.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a text summarization expert."},
                {"role": "user", "content": f"Please summarize this text concisely: {text}"}
            ],
            max_tokens=max_length or self.max_tokens
        )
        return response.choices[0].message.content

    def extract_key_points(self, text: str, max_points: Optional[int] = None) -> List[str]:
        """Extract key points using OpenAI model."""
        response = openai.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "Extract the main points from the text."},
                {"role": "user", "content": text}
            ],
            max_tokens=self.max_tokens
        )
        # Parse the response into a list of key points
        points = response.choices[0].message.content.split('\n')
        return points[:max_points] if max_points else points

    def classify_content(self, text: str, categories: Optional[List[str]] = None) -> List[str]:
        """Classify content using OpenAI model."""
        prompt = f"Classify this text into categories: {text}"
        if categories:
            prompt += f"\nUse only these categories: {', '.join(categories)}"
        
        response = openai.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a content classification expert."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=100
        )
        return response.choices[0].message.content.split(',')

    def extract_topics(self, text: str) -> List[str]:
        """Extract topics using OpenAI model."""
        response = openai.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "Extract the main topics from the text."},
                {"role": "user", "content": text}
            ],
            max_tokens=200
        )
        return response.choices[0].message.content.split(',')

    def calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity using OpenAI embeddings."""
        # Get embeddings for both texts
        embedding1 = openai.embeddings.create(
            model="text-embedding-ada-002",
            input=text1
        ).data[0].embedding

        embedding2 = openai.embeddings.create(
            model="text-embedding-ada-002",
            input=text2
        ).data[0].embedding

        # Calculate cosine similarity
        import numpy as np
        similarity = np.dot(embedding1, embedding2) / (np.linalg.norm(embedding1) * np.linalg.norm(embedding2))
        return float(similarity)

    def batch_process(self, texts: List[str], operation: str) -> List[Union[str, List[str]]]:
        """Process multiple texts with specified operation."""
        results = []
        for text in texts:
            if operation == "summarize":
                results.append(self.summarize(text))
            elif operation == "extract_topics":
                results.append(self.extract_topics(text))
            elif operation == "extract_key_points":
                results.append(self.extract_key_points(text))
            else:
                raise ValueError(f"Unsupported operation: {operation}")
        return results

    def detect_language(self, text: str) -> str:
        """Detect language using OpenAI model."""
        response = openai.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "Detect the language of this text. Respond with just the language name."},
                {"role": "user", "content": text}
            ],
            max_tokens=50
        )
        return response.choices[0].message.content.strip()