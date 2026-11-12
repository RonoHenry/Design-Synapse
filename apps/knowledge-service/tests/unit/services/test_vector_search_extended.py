"""Additional test cases for vector search functionality."""

import pytest
import numpy as np
from unittest.mock import Mock, patch
from knowledge_service.services.vector_search import VectorSearchService


@pytest.fixture
def mock_pinecone():
    """Create a mock Pinecone instance."""
    with patch('pinecone.init') as mock_init, \
         patch('pinecone.Index') as mock_index:
        mock_index_instance = Mock()
        mock_index.return_value = mock_index_instance
        yield mock_index_instance


@pytest.fixture
def vector_service(mock_pinecone):
    """Create a VectorSearchService instance with mocked Pinecone."""
    return VectorSearchService(
        api_key="test_key",
        environment="test-env",
        index_name="test-index"
    )


def test_index_document(vector_service, mock_pinecone):
    """Test indexing a document."""
    # Test data
    doc_id = "doc1"
    content = "Test document content"
    metadata = {"type": "pdf", "author": "Test Author"}

    # Index document
    vector_service.index_document(doc_id, content, metadata)

    # Verify Pinecone upsert was called
    mock_pinecone.upsert.assert_called_once()
    call_args = mock_pinecone.upsert.call_args[1]
    
    assert "vectors" in call_args
    vectors = call_args["vectors"]
    assert len(vectors) == 1
    assert vectors[0]["id"] == doc_id
    assert "values" in vectors[0]  # Check embedding was created
    assert vectors[0]["metadata"] == metadata


def test_search_documents(vector_service, mock_pinecone):
    """Test searching documents."""
    # Mock search results
    mock_pinecone.query.return_value = {
        "matches": [
            {
                "id": "doc1",
                "score": 0.95,
                "metadata": {"type": "pdf", "author": "Test Author"}
            },
            {
                "id": "doc2",
                "score": 0.85,
                "metadata": {"type": "pdf", "author": "Another Author"}
            }
        ]
    }

    # Perform search
    results = vector_service.search("test query", limit=2)

    # Verify results
    assert len(results) == 2
    assert results[0]["id"] == "doc1"
    assert results[0]["score"] == 0.95
    assert results[1]["id"] == "doc2"
    assert results[1]["score"] == 0.85


def test_batch_indexing(vector_service, mock_pinecone):
    """Test batch indexing of documents."""
    # Test data
    documents = [
        {
            "id": f"doc{i}",
            "content": f"Test content {i}",
            "metadata": {"type": "pdf", "number": i}
        }
        for i in range(3)
    ]

    # Batch index
    vector_service.batch_index(documents)

    # Verify batch upsert
    mock_pinecone.upsert.assert_called_once()
    call_args = mock_pinecone.upsert.call_args[1]
    vectors = call_args["vectors"]
    
    assert len(vectors) == 3
    assert all("values" in vec for vec in vectors)
    assert [vec["id"] for vec in vectors] == ["doc0", "doc1", "doc2"]


def test_delete_document(vector_service, mock_pinecone):
    """Test deleting a document."""
    doc_id = "doc1"
    vector_service.delete_document(doc_id)
    mock_pinecone.delete.assert_called_once_with(ids=[doc_id])


def test_update_document(vector_service, mock_pinecone):
    """Test updating a document."""
    # Test data
    doc_id = "doc1"
    new_content = "Updated content"
    new_metadata = {"type": "pdf", "updated": True}

    # Update document
    vector_service.update_document(doc_id, new_content, new_metadata)

    # Verify delete and upsert calls
    mock_pinecone.delete.assert_called_once_with(ids=[doc_id])
    mock_pinecone.upsert.assert_called_once()


def test_similarity_search(vector_service, mock_pinecone):
    """Test similarity search between documents."""
    # Mock similarity search results
    mock_pinecone.query.return_value = {
        "matches": [
            {"id": "doc2", "score": 0.88},
            {"id": "doc3", "score": 0.75}
        ]
    }

    results = vector_service.find_similar("doc1", limit=2)
    assert len(results) == 2
    assert results[0]["score"] == 0.88
    assert results[1]["score"] == 0.75


def test_error_handling(vector_service, mock_pinecone):
    """Test error handling in vector search operations."""
    # Test index failure
    mock_pinecone.upsert.side_effect = Exception("Indexing failed")
    with pytest.raises(Exception, match="Indexing failed"):
        vector_service.index_document("doc1", "content", {})

    # Test search failure
    mock_pinecone.query.side_effect = Exception("Search failed")
    with pytest.raises(Exception, match="Search failed"):
        vector_service.search("query")


def test_embedding_generation(vector_service):
    """Test embedding generation for documents."""
    content = "Test content for embedding"
    embedding = vector_service._generate_embedding(content)
    
    assert isinstance(embedding, np.ndarray)
    assert embedding.shape[0] == 384  # Default embedding size
    assert not np.any(np.isnan(embedding))  # No NaN values


def test_metadata_handling(vector_service, mock_pinecone):
    """Test handling of different metadata types."""
    # Test with various metadata types
    metadata = {
        "str_field": "text",
        "int_field": 123,
        "float_field": 123.45,
        "bool_field": True,
        "list_field": ["a", "b", "c"],
        "nested": {"key": "value"}
    }

    vector_service.index_document("doc1", "content", metadata)
    
    # Verify metadata was properly handled
    call_args = mock_pinecone.upsert.call_args[1]
    assert "vectors" in call_args
    actual_metadata = call_args["vectors"][0]["metadata"]
    
    # Verify metadata types were preserved or properly converted
    assert isinstance(actual_metadata["str_field"], str)
    assert isinstance(actual_metadata["int_field"], (int, float))
    assert isinstance(actual_metadata["float_field"], float)
    assert isinstance(actual_metadata["bool_field"], bool)