# Data Models Documentation

## Knowledge Service Models

### Resource Model
Represents knowledge resources like papers, articles, and other content.

```typescript
Resource {
  id: Integer (Primary Key)
  title: String(255) (Required)
  description: String(1000) (Required)
  content_type: String(50) (Required) // pdf, html, etc.
  source_url: String(500) (Required)
  source_platform: String(100) (Optional) // SSRN, MDPI, etc.
  vector_embedding: JSON (Optional)
  
  // Additional metadata
  author: String(255) (Optional)
  publication_date: DateTime (Optional)
  doi: String(100) (Optional)
  license_type: String(100) (Optional)
  
  // Generated content
  summary: Text (Optional)
  key_takeaways: JSON (Optional)
  keywords: JSON (Optional)
  
  // Storage info
  storage_path: String(500) (Required)
  file_size: Integer (Optional) // in bytes
  
  // Timestamps
  created_at: DateTime (Required)
  updated_at: DateTime (Required)
  
  // Relationships
  topics: Many-to-Many(Topic)
  bookmarks: One-to-Many(Bookmark)
  citations: One-to-Many(Citation)
  
  // Validations
  - source_url: Must be a valid URL format
  - file_size: Must be non-negative if provided
}

### Topic Model
Represents knowledge topics or categories.

```typescript
Topic {
  id: Integer (Primary Key)
  name: String(100) (Required, Unique)
  description: String(500) (Required)
  parent_id: Integer (Optional, Foreign Key to Topic)
  
  // Relationships
  children: One-to-Many(Topic)
  resources: Many-to-Many(Resource)
}
```

### Bookmark Model
Represents user bookmarks of resources.

```typescript
Bookmark {
  id: Integer (Primary Key)
  user_id: Integer (Required) // Foreign key to user service
  resource_id: Integer (Required, Foreign Key to Resource)
  notes: Text (Optional)
  created_at: DateTime (Required)
  
  // Relationships
  resource: Many-to-One(Resource)
  
  // Constraints
  - Unique(user_id, resource_id) // One bookmark per resource per user
  - Check(user_id > 0)
}
```

### Citation Model
Represents resource citations in projects.

```typescript
Citation {
  id: Integer (Primary Key)
  resource_id: Integer (Required, Foreign Key to Resource)
  project_id: Integer (Required) // Foreign key to project service
  context: Text (Required) // Where/how it's cited
  created_at: DateTime (Required)
  created_by: Integer (Required) // User who created the citation (no default)
  
  // Relationships
  resource: Many-to-One(Resource)
  
  // On Delete
  - Cascade delete when parent resource is deleted
}
```

## Data Relationships

### Resource-Topic Relationship
- Many-to-many relationship through `resource_topics` table
- A resource can belong to multiple topics
- A topic can have multiple resources

### Resource-Bookmark Relationship
- One-to-many from Resource to Bookmark
- A resource can have multiple bookmarks
- A bookmark belongs to one resource
- Cascade delete: When a resource is deleted, all its bookmarks are deleted

### Resource-Citation Relationship
- One-to-many from Resource to Citation
- A resource can have multiple citations
- A citation belongs to one resource
- Cascade delete: When a resource is deleted, all its citations are deleted

## Validation & API Schemas

### Pydantic Schemas
All API endpoints use Pydantic models for request and response validation. See `knowledge_service/schemas.py` for details.

#### Resource
- Source URL must be a valid URL format
- File size must be non-negative if provided
- Required fields: title, description, content_type, source_url, storage_path

#### Topic
- Name must be unique
- Required fields: name, description

#### Bookmark
- One bookmark per resource per user (unique constraint)
- User ID must be positive
- Required fields: user_id, resource_id

#### Citation
- Required fields: resource_id, project_id, context, created_by (no default)

Validation is enforced both at the database level and at the API layer using Pydantic.

## Vector & Semantic Search

The Resource model supports vector embeddings (`vector_embedding` field) for semantic search. The knowledge service implements vector-based search using sentence transformers and LLM similarity scoring.