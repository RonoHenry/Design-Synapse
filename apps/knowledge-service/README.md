# Knowledge Service

Intelligent knowledge management and search service for DesignSynapse, providing AI-powered content analysis, vector search, and recommendation capabilities.

## Overview

The Knowledge Service manages and analyzes design-related resources including:
- **Resource Management**: Store and organize documents, papers, and design resources
- **AI Content Analysis**: Automatic summarization and key insight extraction
- **Vector Search**: Semantic search across knowledge base using embeddings
- **Recommendations**: Intelligent resource recommendations based on user activity
- **Citations**: Track resource usage in projects with context
- **Bookmarks**: Personal resource organization and note-taking

## Features

- **Intelligent Search**: Vector-based semantic search with relevance ranking
- **Content Processing**: Automatic PDF processing and text extraction
- **AI Insights**: LLM-powered summarization and keyword extraction
- **Caching**: Advanced caching for improved search performance
- **Batch Processing**: Efficient bulk resource processing
- **Topic Organization**: Hierarchical topic categorization

## Setup

### Prerequisites

- Python 3.11+
- PostgreSQL or TiDB database
- Vector database (Pinecone or Chroma)
- LLM API access (OpenAI, Anthropic, or Groq)

### Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. Set up the database:
```bash
# Run database migrations
alembic upgrade head
```

4. Run the service:
```bash
uvicorn knowledge_service.main:app --reload --port 8002
```

## Configuration

### Required Environment Variables

```bash
# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_USERNAME=your_username
DB_PASSWORD=your_password
DB_DATABASE=knowledge_service

# Vector Database (Pinecone)
VECTOR_PROVIDER=pinecone
PINECONE_API_KEY=your-pinecone-api-key
PINECONE_ENVIRONMENT=your-environment
PINECONE_INDEX_NAME=knowledge-base

# Alternative: Chroma (local vector database)
VECTOR_PROVIDER=chroma
VECTOR_CHROMA_HOST=localhost
VECTOR_CHROMA_PORT=8000

# LLM Configuration
LLM_PRIMARY_PROVIDER=openai
LLM_OPENAI_API_KEY=your-openai-api-key
LLM_ANTHROPIC_API_KEY=your-anthropic-api-key  # Optional fallback
LLM_GROQ_API_KEY=your-groq-api-key            # Optional fallback
```

### Optional Environment Variables

```bash
# Service Configuration
MAX_FILE_SIZE_MB=50
SUPPORTED_FILE_TYPES=pdf,txt,docx,md
CACHE_TTL_SECONDS=3600

# AI Processing
ENABLE_AUTO_PROCESSING=true
BATCH_SIZE=10
MAX_RETRIES=3

# Performance
VECTOR_SEARCH_CACHE_SIZE=1000
SEARCH_RESULTS_LIMIT=50
```

## API Documentation

Once running, visit:
- **Swagger UI**: http://localhost:8002/docs
- **ReDoc**: http://localhost:8002/redoc

### Key Endpoints

#### Resource Management
- `POST /api/v1/resources` - Upload and create new resource
- `GET /api/v1/resources` - List resources with filtering
- `GET /api/v1/resources/{id}` - Get specific resource
- `PUT /api/v1/resources/{id}` - Update resource
- `DELETE /api/v1/resources/{id}` - Delete resource

#### Search and Discovery
- `GET /api/v1/search` - Semantic search across resources
- `GET /api/v1/search/advanced` - Advanced search with filters
- `GET /api/v1/recommendations` - Get personalized recommendations

#### Citations and Bookmarks
- `POST /api/v1/citations` - Create citation for project
- `GET /api/v1/citations` - List citations
- `POST /api/v1/bookmarks` - Bookmark a resource
- `GET /api/v1/bookmarks` - List user bookmarks

#### Topics
- `GET /api/v1/topics` - List topic hierarchy
- `POST /api/v1/topics` - Create new topic
- `GET /api/v1/topics/{id}/resources` - Get resources by topic

### Example API Usage

#### Upload a resource
```bash
curl -X POST "http://localhost:8002/api/v1/resources" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "title": "Sustainable Architecture Principles",
    "description": "Comprehensive guide to sustainable design practices",
    "content_type": "pdf",
    "source_url": "https://example.com/sustainable-architecture.pdf",
    "author": "Dr. Jane Smith",
    "topic_ids": [1, 3]
  }'
```

#### Search for resources
```bash
curl -X GET "http://localhost:8002/api/v1/search?q=sustainable%20building%20materials&limit=10" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

#### Create a citation
```bash
curl -X POST "http://localhost:8002/api/v1/citations" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "resource_id": 123,
    "project_id": 456,
    "context": "Referenced for sustainable material selection in section 3.2"
  }'
```

## Project Structure

```
apps/knowledge-service/
├── knowledge_service/
│   ├── api/
│   │   └── v1/
│   │       ├── resources.py      # Resource management endpoints
│   │       ├── search.py         # Search endpoints
│   │       ├── citations.py      # Citation endpoints
│   │       └── schemas.py        # API schemas
│   ├── core/
│   │   ├── config.py            # Configuration settings
│   │   ├── llm.py               # LLM integration
│   │   └── vector_search.py     # Vector search utilities
│   ├── models/
│   │   ├── resource.py          # Resource SQLAlchemy model
│   │   └── bookmark.py          # Bookmark SQLAlchemy model
│   ├── services/
│   │   ├── content_analysis.py  # AI content processing
│   │   ├── vector_search.py     # Vector search service
│   │   ├── recommendation.py    # Recommendation engine
│   │   ├── pdf_processing.py    # PDF text extraction
│   │   └── batch_processing.py  # Bulk operations
│   └── main.py                  # FastAPI application
├── tests/
│   ├── unit/                    # Unit tests
│   ├── integration/             # Integration tests
│   └── fixtures/                # Test data
├── migrations/                  # Database migrations
├── storage/                     # File storage
└── requirements.txt             # Dependencies
```

## Advanced Features

### Vector Search Caching

The service implements intelligent caching for vector search operations:

```python
# Cache configuration
VECTOR_SEARCH_CACHE_SIZE=1000      # Number of cached queries
CACHE_TTL_SECONDS=3600             # Cache expiration time
ENABLE_CACHE_COMPRESSION=true      # Compress cached results
```

Benefits:
- **Performance**: 10x faster response times for repeated queries
- **Cost Reduction**: Reduces vector database API calls
- **Scalability**: Handles high query volumes efficiently

### Batch Processing

Efficient bulk operations for large-scale content processing:

```bash
# Process multiple files
python -m knowledge_service.services.batch_processing \
  --input-dir /path/to/files \
  --batch-size 10 \
  --parallel-workers 4
```

### Content Analysis Pipeline

Automated AI-powered content processing:

1. **Text Extraction**: PDF, DOCX, and other formats
2. **Summarization**: Key insights and takeaways
3. **Keyword Extraction**: Relevant tags and topics
4. **Vector Embedding**: Semantic search preparation
5. **Topic Classification**: Automatic categorization

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=knowledge_service --cov-report=html

# Run specific test suites
pytest tests/unit/services/test_vector_search.py -v
pytest tests/integration/api/v1/test_search.py -v
```

### Performance Testing

```bash
# Search performance tests
pytest tests/integration/api/v1/test_search_performance.py -v

# Cache performance tests
pytest tests/unit/services/test_vector_search_caching.py -v
```

### Database Migrations

```bash
# Create migration
alembic revision --autogenerate -m "Add new feature"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Performance Optimization

### Caching Strategy

- **Vector Search Cache**: In-memory LRU cache for search results
- **Content Cache**: Redis-based caching for processed content
- **Database Query Cache**: SQLAlchemy query result caching

### Search Optimization

- **Index Optimization**: Proper database indexing for fast queries
- **Vector Similarity**: Optimized similarity calculations
- **Result Ranking**: Advanced relevance scoring algorithms

### Monitoring

- **Search Metrics**: Query performance and result quality
- **Cache Metrics**: Hit rates and memory usage
- **Processing Metrics**: Content analysis pipeline performance

## Troubleshooting

### Common Issues

1. **Vector Database Connection**
   ```bash
   # Test Pinecone connection
   python -c "import pinecone; pinecone.init(api_key='your-key'); print('Connected')"

   # Test Chroma connection
   curl http://localhost:8000/api/v1/heartbeat
   ```

2. **LLM API Issues**
   ```bash
   # Test OpenAI connection
   python -c "import openai; openai.api_key='your-key'; print(openai.Model.list())"
   ```

3. **File Processing Errors**
   - Check file format support
   - Verify file size limits
   - Ensure proper permissions

### Performance Issues

- Monitor cache hit rates
- Check vector database performance
- Analyze query patterns
- Review batch processing logs

## Monitoring and Health

- **Health Check**: `GET /health` - Service status
- **Ready Check**: `GET /ready` - Database and external service connectivity
- **Cache Stats**: `GET /api/v1/cache/stats` - Cache performance metrics

## Contributing

1. Follow existing code patterns
2. Add comprehensive tests
3. Update documentation
4. Ensure performance benchmarks pass
5. Test with different LLM providers
