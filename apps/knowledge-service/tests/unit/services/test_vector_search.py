"""Tests for vector search service."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from knowledge_service.services.vector_search import VectorSearchService


@pytest.fixture
def mock_pinecone():
    """Mock Pinecone initialization and index."""
    with patch('pinecone.init') as mock_init, \
         patch('pinecone.Index') as mock_index_class:
        
        # Mock index instance
        mock_index = MagicMock()
        mock_index_class.return_value = mock_index
        
        # Set up list_indexes to simulate index doesn't exist
        mock_list_indexes = MagicMock(return_value=[])
        with patch('pinecone.list_indexes', mock_list_indexes):
            yield {
                'init': mock_init,
                'Index': mock_index_class,
                'index': mock_index,
                'list_indexes': mock_list_indexes
            }


@pytest.fixture
def mock_sentence_transformer():
    """Mock SentenceTransformer."""
    with patch('sentence_transformers.SentenceTransformer') as mock_st:
        model = MagicMock()
        model.encode.return_value = [0.1] * 384  # Match dimension in service
        mock_st.return_value = model
        yield model


@pytest.fixture
def vector_service(mock_pinecone, mock_sentence_transformer):
    """Create VectorSearchService with mocked dependencies."""
    return VectorSearchService()


@pytest.mark.asyncio
async def test_index_resource(vector_service, mock_pinecone):
    """Test indexing a resource."""
    # Test data
    resource_id = 1
    title = "Test Resource"
    description = "Test Description"
    content = "Test Content"
    metadata = {
        "author": "Test Author",
        "topics": ["Test Topic"]
    }

    # Index the resource
    await vector_service.index_resource(
        resource_id,
        title,
        description,
        content,
        metadata
    )

    # Verify Pinecone upsert was called correctly
    mock_pinecone['index'].upsert.assert_called_once()
    call_args = mock_pinecone['index'].upsert.call_args[1]
    
    # Check the vectors argument
    vectors = call_args['vectors']
    assert len(vectors) == 1
    vector_id, embedding, vector_metadata = vectors[0]
    
    assert vector_id == "1"
    assert len(embedding) == 384
    assert vector_metadata['title'] == title
    assert vector_metadata['description'] == description
    assert vector_metadata['author'] == metadata['author']
    assert vector_metadata['topics'] == metadata['topics']


@pytest.mark.asyncio
async def test_search_resources(vector_service, mock_pinecone):
    """Test searching resources."""
    # Mock search results
    mock_match = MagicMock()
    mock_match.id = "1"
    mock_match.score = 0.95
    mock_match.metadata = {
        "title": "Test Resource",
        "description": "Test Description",
        "author": "Test Author"
    }
    
    mock_results = MagicMock()
    mock_results.matches = [mock_match]
    mock_pinecone['index'].query.return_value = mock_results

    # Perform search
    results = await vector_service.search_resources(
        query="test query",
        filter_metadata={"topic": "Test Topic"},
        top_k=5
    )

    # Verify Pinecone query was called correctly
    mock_pinecone['index'].query.assert_called_once()
    call_args = mock_pinecone['index'].query.call_args[1]
    
    assert len(call_args['vector']) == 384
    assert call_args['filter'] == {"topic": "Test Topic"}
    assert call_args['top_k'] == 5
    assert call_args['include_metadata'] is True

    # Verify results format
    assert len(results) == 1
    result = results[0]
    assert result['resource_id'] == 1
    assert result['score'] == 0.95
    assert result['metadata'] == mock_match.metadata


@pytest.mark.asyncio
async def test_delete_resource(vector_service, mock_pinecone):
    """Test deleting a resource."""
    resource_id = 1
    await vector_service.delete_resource(resource_id)

    # Verify Pinecone delete was called correctly
    mock_pinecone['index'].delete.assert_called_once_with(ids=["1"])


@pytest.mark.asyncio
async def test_update_resource(vector_service, mock_pinecone):
    """Test updating a resource."""
    resource_id = 1
    title = "Updated Resource"
    description = "Updated Description"
    content = "Updated Content"
    metadata = {
        "author": "Updated Author",
        "topics": ["Updated Topic"]
    }

    # Update the resource
    await vector_service.update_resource(
        resource_id,
        title,
        description,
        content,
        metadata
    )

    # Verify Pinecone delete and upsert were called correctly
    mock_pinecone['index'].delete.assert_called_once_with(ids=["1"])
    mock_pinecone['index'].upsert.assert_called_once()
    
    # Check the upsert call
    call_args = mock_pinecone['index'].upsert.call_args[1]
    vectors = call_args['vectors']
    assert len(vectors) == 1
    vector_id, embedding, vector_metadata = vectors[0]
    
    assert vector_id == "1"
    assert len(embedding) == 384
    assert vector_metadata['title'] == title
    assert vector_metadata['description'] == description
    assert vector_metadata['author'] == metadata['author']
    assert vector_metadata['topics'] == metadata['topics']