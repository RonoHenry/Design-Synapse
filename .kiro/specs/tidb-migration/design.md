# TiDB Serverless Migration - Design

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                   TiDB Serverless Cluster               │
│                  (EU Central 1 - Frankfurt)             │
│                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │   user_db    │  │  project_db  │  │ knowledge_db │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
│                                                         │
│  Gateway: gateway01.eu-central-1.prod.aws.tidbcloud.com│
│  Port: 4000 | SSL/TLS Required                        │
└─────────────────────────────────────────────────────────┘
                          ▲
                          │ mysql+pymysql://
                          │ (SSL encrypted)
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
   ┌────▼────┐      ┌────▼────┐      ┌────▼────┐
   │  User   │      │ Project │      │Knowledge│
   │ Service │      │ Service │      │ Service │
   └─────────┘      └─────────┘      └─────────┘
```

## Database Configuration Changes

### Current (PostgreSQL)
```python
DATABASE_URL = "postgresql://user:pass@localhost:5432/dbname"
driver = "psycopg2"
```

### New (TiDB/MySQL)
```python
DATABASE_URL = "mysql+pymysql://user:pass@gateway01.eu-central-1.prod.aws.tidbcloud.com:4000/dbname?ssl_ca=/path/to/ca.pem&ssl_verify_cert=true&ssl_verify_identity=true"
driver = "pymysql"
```

## Component Changes

### 1. Database Configuration (`packages/common/config/database.py`)

**Changes**:
- Add `database_type` field (postgresql/mysql/tidb)
- Update `get_connection_url()` to support MySQL dialect
- Add SSL certificate configuration
- Add TiDB-specific connection parameters

**New Fields**:
```python
database_type: str = "tidb"  # postgresql, mysql, tidb
ssl_ca_path: Optional[str] = None
ssl_verify_cert: bool = True
ssl_verify_identity: bool = True
```

### 2. SQLAlchemy Models

**PostgreSQL-Specific Types to Replace**:

| PostgreSQL Type | MySQL/TiDB Equivalent |
|----------------|----------------------|
| `JSONB` | `JSON` |
| `ARRAY(String)` | `JSON` (store as array) |
| `ARRAY(Integer)` | `JSON` (store as array) |
| `UUID` | `CHAR(36)` or `BINARY(16)` |

**Example Migration**:
```python
# Before (PostgreSQL)
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
metadata = Column(JSONB)
tags = Column(ARRAY(String))

# After (MySQL/TiDB)
from sqlalchemy import JSON, Text
metadata = Column(JSON)
tags = Column(JSON)  # Store as ["tag1", "tag2"]
```

### 3. Connection String Format

**Structure**:
```
mysql+pymysql://{username}:{password}@{host}:{port}/{database}?{params}
```

**Required Parameters**:
- `ssl_ca`: Path to CA certificate
- `ssl_verify_cert=true`: Verify server certificate
- `ssl_verify_identity=true`: Verify server identity
- `charset=utf8mb4`: Use UTF-8 encoding

**Example**:
```
mysql+pymysql://kbFV66oHabEtRud.root:PASSWORD@gateway01.eu-central-1.prod.aws.tidbcloud.com:4000/test?ssl_ca=/path/to/ca.pem&ssl_verify_cert=true&ssl_verify_identity=true&charset=utf8mb4
```

### 4. Alembic Migrations

**Changes**:
- Update `alembic.ini` to use MySQL dialect
- Regenerate all migrations for MySQL
- Test migrations on TiDB cluster

**Migration Strategy**:
1. Backup existing migration history (for reference)
2. Clear `versions/` directory
3. Run `alembic revision --autogenerate -m "Initial TiDB schema"`
4. Review generated migrations
5. Test on TiDB cluster
6. Apply to all service databases

### 5. Service-Specific Databases

**Database Naming**:
- User Service: `design_synapse_user_db`
- Project Service: `design_synapse_project_db`
- Knowledge Service: `design_synapse_knowledge_db`

**Creation Script**:
```sql
CREATE DATABASE IF NOT EXISTS design_synapse_user_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS design_synapse_project_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS design_synapse_knowledge_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

## Implementation Phases

### Phase 1: Infrastructure Setup
1. Install MySQL drivers (pymysql, cryptography)
2. Download and configure SSL certificate
3. Update database configuration classes
4. Test basic connectivity

### Phase 2: Model Updates
1. Audit all models for PostgreSQL-specific types
2. Replace with MySQL-compatible types
3. Update type hints and imports
4. Run model validation tests

### Phase 3: Migration Generation
1. Update Alembic configuration
2. Generate new migrations
3. Review and test migrations
4. Apply to TiDB databases

### Phase 4: Service Integration
1. Update each service's database configuration
2. Test CRUD operations
3. Run test suites
4. Verify connection pooling

### Phase 5: Validation
1. Run all unit tests
2. Run all integration tests
3. Test health check endpoints
4. Verify performance

## TiDB-Specific Optimizations

### 1. Connection Pooling
```python
engine = create_engine(
    connection_url,
    pool_size=10,  # TiDB can handle more connections
    max_overflow=20,
    pool_pre_ping=True,  # Verify connections
    pool_recycle=3600,  # Recycle after 1 hour
)
```

### 2. Character Set
Always use `utf8mb4` for full Unicode support:
```python
connection_url += "?charset=utf8mb4"
```

### 3. SSL/TLS Configuration
```python
connect_args = {
    "ssl": {
        "ca": "/path/to/ca.pem",
        "check_hostname": True,
        "verify_mode": ssl.CERT_REQUIRED,
    }
}
```

## Testing Strategy

### Unit Tests
- Test database configuration generation
- Test connection string formatting
- Test SSL parameter handling
- Test model type compatibility

### Integration Tests
- Test actual TiDB connection
- Test CRUD operations
- Test transactions and rollbacks
- Test connection pool behavior

### Migration Tests
- Test migration generation
- Test migration application
- Test migration rollback
- Test data integrity

## Rollback Plan

If issues arise:
1. Keep PostgreSQL configuration as fallback
2. Use environment variable to switch database type
3. Maintain both driver dependencies temporarily
4. Can switch back by changing `DATABASE_TYPE=postgresql`

## Security Considerations

1. **SSL/TLS**: Always use encrypted connections
2. **Credentials**: Store in environment variables, never in code
3. **CA Certificate**: Secure storage and access control
4. **Connection Limits**: Configure appropriate pool sizes
5. **Access Control**: Use principle of least privilege

## Performance Expectations

**TiDB Advantages**:
- Horizontal scalability
- Auto-scaling based on load
- Better performance for analytical queries (HTAP)
- No single point of failure

**Monitoring**:
- Connection pool utilization
- Query performance
- Transaction latency
- Error rates

## Documentation Updates

1. Update README with TiDB setup instructions
2. Update .env.example with TiDB connection parameters
3. Create TiDB migration guide
4. Update deployment documentation
5. Add TiDB monitoring guide
