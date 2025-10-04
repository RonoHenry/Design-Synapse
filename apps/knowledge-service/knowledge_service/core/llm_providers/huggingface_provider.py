"""HuggingFace LLM provider implementation."""
from typing import List, Optional, Union
from transformers import pipeline
from .base import BaseLLMProvider


class HuggingFaceProvider(BaseLLMProvider):
    """HuggingFace-based LLM provider implementation."""

    def __init__(self, **config):
        """Initialize HuggingFace provider with model settings."""
        super().__init__()
        self.summarization_model = config.get('summarization_model', 'facebook/bart-large-cnn')
        self.classification_model = config.get('classification_model', 'facebook/bart-large-mnli')
        self.embedding_model = config.get('embedding_model', 'sentence-transformers/all-mpnet-base-v2')
        
        # Initialize pipelines
        self.summarizer = pipeline("summarization", model=self.summarization_model)
        self.classifier = pipeline("zero-shot-classification", model=self.classification_model)
        self.embedder = pipeline("feature-extraction", model=self.embedding_model)

    def summarize(self, text: str, max_length: Optional[int] = None) -> str:
        """Generate a summary using HuggingFace model."""
        max_length = max_length or 130
        min_length = min(30, max_length // 2)
        
        summary = self.summarizer(
            text,
            max_length=max_length,
            min_length=min_length,
            do_sample=False
        )[0]['summary_text']
        
        return summary

    def extract_key_points(self, text: str, max_points: Optional[int] = None) -> List[str]:
        """Extract key points using HuggingFace model."""
        # Using zero-shot classification for key points
        candidate_labels = ["main point", "supporting detail", "conclusion"]
        results = self.classifier(
            text,
            candidate_labels,
            multi_label=True
        )
        
        # Extract sentences classified as main points
        import nltk
        nltk.download('punkt', quiet=True)
        sentences = nltk.sent_tokenize(text)
        
        key_points = [
            sent for sent, label, score in zip(sentences, results['labels'], results['scores'])
            if label == "main point" and score > 0.5
        ]
        
        return key_points[:max_points] if max_points else key_points

    def classify_content(self, text: str, categories: Optional[List[str]] = None) -> List[str]:
        """Classify content using HuggingFace model."""
        if not categories:
            categories = [
                "technology", "science", "business", "politics",
                "health", "education", "entertainment", "sports"
            ]
        
        results = self.classifier(
            text,
            candidate_labels=categories,
            multi_label=True
        )
        
        # Return categories with confidence above threshold
        return [
            label for label, score in zip(results['labels'], results['scores'])
            if score > 0.5
        ]

    def extract_topics(self, text: str) -> List[str]:
        """Extract topics using HuggingFace model."""
        from keybert import KeyBERT
        kw_model = KeyBERT(model=self.embedding_model)
        
        # Extract keywords/phrases as topics
        keywords = kw_model.extract_keywords(
            text,
            keyphrase_ngram_range=(1, 2),
            stop_words='english',
            use_maxsum=True,
            top_n=5
        )
        
        return [keyword for keyword, _ in keywords]

    def calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity using HuggingFace embeddings."""
        import numpy as np
        from sklearn.metrics.pairwise import cosine_similarity
        
        # Get embeddings
        embedding1 = self.embedder(text1, padding=True, truncation=True)
        embedding2 = self.embedder(text2, padding=True, truncation=True)
        
        # Calculate similarity
        similarity = cosine_similarity(
            np.mean(embedding1, axis=1),
            np.mean(embedding2, axis=1)
        )[0][0]
        
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
        """Detect language using HuggingFace model."""
        from transformers import pipeline
        language_detector = pipeline("text-classification", model="papluca/xlm-roberta-base-language-detection")
        result = language_detector(text)[0]
        return result['label']