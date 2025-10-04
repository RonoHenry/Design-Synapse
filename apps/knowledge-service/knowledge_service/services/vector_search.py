"""Vector search service for knowledge resources."""

import os
from typing import Dict, List, Optional
import pinecone
from sentence_transformers import SentenceTransformer

class VectorSearchService:
    """Service for managing vector search operations."""

    def __init__(self):
        """Initialize vector search service."""
        # Initialize Pinecone
        pinecone.init(
            api_key=os.getenv("PINECONE_API_KEY"),
            environment=os.getenv("PINECONE_ENVIRONMENT")
        )
        self.index_name = "knowledge-resources"
        self.dimension = 384  # Using all-MiniLM-L6-v2 model dimension

        # Create index if it doesn't exist
        if self.index_name not in pinecone.list_indexes():
            pinecone.create_index(
                name=self.index_name,
                dimension=self.dimension,
                metric="cosine"
            )
        
        # Get the index instance
        self.index = pinecone.Index(self.index_name)
        
        # Load the sentence transformer model
        self.model = SentenceTransformer('all-MiniLM-L6-v2')

    async def index_resource(
        self,
        resource_id: int,
        title: str,
        description: str,
        content: str,
        metadata: Dict
    ) -> None:
        """Index a resource in Pinecone.
        
        Args:
            resource_id: The ID of the resource
            title: The resource title
            description: The resource description
            content: The extracted text content
            metadata: Additional metadata about the resource
        """
        # Create text to embed (combine relevant fields)
        text_to_embed = f"{title}\n{description}\n{content}"
        
        # Generate embedding
        embedding = self.model.encode(text_to_embed).tolist()
        
        # Upsert to Pinecone
        self.index.upsert(
            vectors=[
                (
                    str(resource_id),
                    embedding,
                    {
                        "title": title,
                        "description": description,
                        **metadata
                    }
                )
            ]
        )
    
    async def search_resources(
        self,
        query: str,
        filter_metadata: Optional[Dict] = None,
        top_k: int = 10
    ) -> List[Dict]:
        """Search for resources using semantic similarity.
        
        Args:
            query: The search query
            filter_metadata: Optional metadata filters
            top_k: Number of results to return
            
        Returns:
            List of matched resources with scores
        """
        # Generate query embedding
        query_embedding = self.model.encode(query).tolist()
        
        # Search in Pinecone
        results = self.index.query(
            vector=query_embedding,
            filter=filter_metadata,
            top_k=top_k,
            include_metadata=True
        )
        
        # Format results
        return [
            {
                "resource_id": int(match.id),
                "score": match.score,
                "metadata": match.metadata
            }
            for match in results.matches
        ]
    
    async def delete_resource(self, resource_id: int) -> None:
        """Delete a resource from the vector index.
        
        Args:
            resource_id: The ID of the resource to delete
        """
        self.index.delete(ids=[str(resource_id)])
    
    async def update_resource(
        self,
        resource_id: int,
        title: str,
        description: str,
        content: str,
        metadata: Dict
    ) -> None:
        """Update a resource in the vector index.
        
        This is implemented as a delete followed by an insert to ensure
        consistency.
        
        Args:
            resource_id: The ID of the resource
            title: The updated title
            description: The updated description
            content: The updated content
            metadata: The updated metadata
        """
        await self.delete_resource(resource_id)
        await self.index_resource(
            resource_id,
            title,
            description,
            content,
            metadata
        )