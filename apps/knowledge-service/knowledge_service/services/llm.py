"""Service for generating resource summaries and insights using LLMs."""

import os
from typing import Dict, List, Tuple
import httpx
from sqlalchemy.orm import Session
import numpy as np
from sentence_transformers import SentenceTransformer

from ..models import Resource


class LLMService:
    """Service for LLM-based text analysis and generation."""

    def __init__(self):
        """Initialize the service."""
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.api_url = "https://api.openai.com/v1/chat/completions"
        self.model = "gpt-4"
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        self._client = httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
        )
    
    async def generate_insights(
        self,
        text: str,
        resource: Resource,
        db: Session
    ) -> Tuple[str, List[str], List[str]]:
        """Generate summary, key takeaways, and keywords for a resource.
        
        Args:
            text: The text content to analyze
            resource: The resource model
            db: Database session
        
        Returns:
            Tuple of (summary, key_takeaways, keywords)
        """
        # Prepare the system message with context
        system_message = (
            "You are an expert in architecture, engineering, and construction. "
            "Analyze the following text from a technical resource and provide:\n"
            "1. A concise summary (max 2000 chars)\n"
            "2. Key takeaways (5-7 bullet points)\n"
            "3. Relevant keywords/tags (5-10 terms)\n\n"
            "Focus on practical implications for DAEC professionals."
        )
        
        # Make API request
        response = await self._client.post(
            self.api_url,
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": text}
                ],
                "temperature": 0.7,
                "max_tokens": 1000
            }
        )
        response.raise_for_status()
        result = response.json()
        
        # Parse the response
        output = result["choices"][0]["message"]["content"]
        sections = output.split("\n\n")
        
        # Extract insights
        summary = sections[0].strip()
        key_takeaways = [
            point.replace("- ", "").strip()
            for point in sections[1].strip().split("\n")
            if point.strip()
        ]
        keywords = [
            keyword.strip()
            for keyword in sections[2].strip().split(",")
        ]
        
        # Update resource
        resource.summary = summary
        resource.key_takeaways = key_takeaways
        resource.keywords = keywords
        db.commit()
        
        return summary, key_takeaways, keywords
    
    async def generate_recommendations(
        self,
        user_id: int,
        user_role: str,
        project_context: Dict,
        db: Session
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
        
    async def extract_topics(self, content: str) -> List[str]:
        """Extract relevant topics from the content."""
        if not content:
            raise ValueError("Content cannot be empty")
        
        # Make API request
        response = await self._client.post(
            self.api_url,
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "Extract the main topics discussed in the content. Return them as a bullet list."},
                    {"role": "user", "content": f"Extract the main topics from this content:\n\n{content}"}
                ],
                "temperature": 0.3
            }
        )
        response.raise_for_status()
        result = response.json()
        
        topics = result["choices"][0]["message"]["content"].strip().split('\n')
        return [t.lstrip('•- ').strip() for t in topics if t.strip()]
    
    async def classify_resource(self, content: str) -> List[str]:
        """Classify the resource content into categories."""
        if not content:
            raise ValueError("Content cannot be empty")
        
        response = await self._client.post(
            self.api_url,
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "Classify the content into relevant technical categories."},
                    {"role": "user", "content": f"Classify this content into relevant categories:\n\n{content}"}
                ],
                "temperature": 0.3
            }
        )
        response.raise_for_status()
        result = response.json()
        
        categories = result["choices"][0]["message"]["content"].strip().split('\n')
        return [c.lstrip('•- ').strip() for c in categories if c.strip()]
    
    async def extract_keywords(self, content: str) -> List[str]:
        """Extract important keywords from the content."""
        if not content:
            raise ValueError("Content cannot be empty")
        
        response = await self._client.post(
            self.api_url,
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "Extract important technical keywords and terms. Return them as a comma-separated list."},
                    {"role": "user", "content": f"Extract key technical terms from this content:\n\n{content}"}
                ],
                "temperature": 0.3
            }
        )
        response.raise_for_status()
        result = response.json()
        
        keywords = result["choices"][0]["message"]["content"].strip().split(',')
        return [k.strip() for k in keywords if k.strip()]
    
    def compare_similarity(self, text1: str, text2: str) -> float:
        """Compare the semantic similarity between two texts."""
        if not text1 or not text2:
            raise ValueError("Both texts must be non-empty")
        
        # Generate embeddings
        embedding1 = self.embedding_model.encode(text1)
        embedding2 = self.embedding_model.encode(text2)
        
        # Compute cosine similarity
        similarity = np.dot(embedding1, embedding2) / (np.linalg.norm(embedding1) * np.linalg.norm(embedding2))
        return float(similarity)
    
    async def batch_summarize(self, texts: List[str]) -> List[str]:
        """Summarize multiple texts in batch."""
        if not texts:
            raise ValueError("Text list cannot be empty")
        
        summaries = []
        for text in texts:
            class MockResource:
                pass
            
            class MockDb:
                def commit(self):
                    pass
                    
            resource = MockResource()
            db = MockDb()
            summary, _, _ = await self.generate_insights(text, resource, db)
            summaries.append(summary)
        return summaries
    
    async def detect_language(self, content: str) -> str:
        """Detect the language of the content."""
        if not content:
            raise ValueError("Content cannot be empty")
        
        response = await self._client.post(
            self.api_url,
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "Detect the language of the given text. Respond with just the language name."},
                    {"role": "user", "content": f"What language is this text in:\n\n{content}"}
                ],
                "temperature": 0.3
            }
        )
        response.raise_for_status()
        result = response.json()
        
        return result["choices"][0]["message"]["content"].strip()