# TiDB Serverless Migration Guide

## Overview

This guide documents the migration of DesignSynapse from PostgreSQL to TiDB Serverless, including key differences, troubleshooting steps, and performance optimization tips.

## Table of Contents
1. [Why TiDB Serverless?](#why-tidb-serverless)
2. [Key Differences: PostgreSQL vs TiDB/MySQL](#key-differences-postgresql-vs-tidbmysql)
3. [Migration Process](#migration-process)
4. [Connection Configuration](#connection-configuration)
5. [Troubleshooting Guide](#troubleshooting-guide)
6. [Performance Optimization](#performance-optimization)
7. [TiDB Features & Limitations](#tidb-features--limitations)

---

## Why TiDB Serverless?

TiDB Serverless provides several advantages over traditional PostgreSQL:

### Benefits
- **Auto-scaling**: Automatically scales compute and storage based on workload
- **Pay-per-use**: Only pay for what you use, with a generous free tier
- **High Availability**: Built-in replication and failover
- **HTAP Capabilities**: Handles both transactional (OLTP) and analytical (OLAP) workloads
- **MySQL Compatibility**: Works with existing MySQL tools and drivers
- **Cloud-Native**: No infrastructure management required
- **Global Distribution**: Deploy close to your users

### Free Tier
- 5 GB storage
- 50 million Request Units (RUs) per month
- Automatic pause after inactivity
- Perfect for development and small production workloads

---

## Key Differences: PostgreSQL vs TiDB/MySQL

### Data Types

| PostgreSQL | TiDB/MySQL | Notes |
|------------|------------|-------|
| `JSONB` | `JSON` | TiDB uses standard JSON (no binary format) |
| `ARRAY(String)` | `JSON` | Store arrays as JSON: `["item1", "item2"]` |
| `ARRAY(Integer)` | `JSON` | Store arrays as JSON: `[1, 2, 3]` |
| `UUID` | `CHAR(36)` or `BINARY(16)` | Store as string or binary |
| `SERIAL` | `AUTO_INCREMENT` | Auto-incrementing integers |
| `BOOLEAN` | `TINYINT(1)` | 0 = false, 1 = true |
| `TEXT` | `TEXT` | Same in both |
| `VARCHAR(n)` | `VARCHAR(n)` | Same in both |
| `INTEGER` | `INT` | Same in both |
| `TIMESTAMP` | `DATETIME` or `TIMESTAMP` | TIMESTAMP has timezone support |

### SQL Syntax Differences

#### String Concatenation
```sql
-- PostgreSQL
SELECT first_name || ' ' || last_name FROM users;

-- TiDB/MySQL
SELECT CONCAT(first_name, ' ', last_name) FROM users;
```

#### LIMIT/OFFSET
```sql
-- PostgreSQL
SELECT * FROM users LIMIT 10 OFFSET 20;

-- TiDB/MySQL (same syntax works)
SELECT * FROM users LIMIT 10 OFFSET 20;
-- Or: SELECT * FROM users LIMIT 20, 10;
```

#### Boolean Values
```sql
-- PostgreSQL
SELECT * FROM users WHERE is_active = TRUE;

-- TiDB/MySQL
SELECT * FROM users WHERE is_active = 1;
-- Or: SELECT * FROM users WHERE is_active = TRUE; (also works)
```

#### JSON Operations
```sql
-- PostgreSQL
SELECT metadata->>'key' FROM resources;
SELECT metadata->'nested'->'key' FROM resources;

-- TiDB/MySQL
SELECT JSON_EXTRACT(metadata, '$.key') FROM resources;
SELECT JSON_UNQUOTE(JSON_EXTRACT(metadata, '$.key')) FROM resources;
-- Or use shorthand: SELECT metadata->>'$.key' FROM resources;
```

### SQLAlchemy Differences

#### Connection String
```python
# PostgreSQL
DATABASE_URL = "postgresql://user:pass@host:5432/dbname"

# TiDB/MySQL
DATABASE_URL = "mysql+pymysql://user:pass@host:4000/dbname?ssl_ca=/path/to/ca.pem&ssl_verify_cert=true&ssl_verify_identity=true&charset=utf8mb4"
```

#### Model Definitions
```python
# PostgreSQL-specific
from sqlalchemy.dialects.postgresql import JSONB, ARRAY

class Resource(Base):
    metadata = Column(JSONB)
    tags = Column(ARRAY(String))

# TiDB/MySQL-compatible
from sqlalchemy import JSON, Text

class Resource(Base):
    metadata = Column(JSON)
    tags = Column(JSON)  # Store as ["tag1", "tag2"]
```

---

## Migration Process

This section documents the actual migration process followed for DesignSynapse.

### Phase 1: Driver Migration
1. **Removed PostgreSQL drivers**
   ```bash
   # Removed from requirements.txt
   - psycopg2-binary
   ```

2. **Added MySQL drivers**
   ```bash
   # Added to requirements.txt
   + pymysql>=1.1.0
   + cryptography>=41.0.0
   ```

### Phase 2: Configuration Updates
1. **Updated DatabaseConfig class** (`packages/common/config/database.py`)
   - Changed dialect from `postgresql` to `mysql+pymysql`
   - Added SSL/TLS configuration parameters
   - Updated connection string builder

2. **Updated environment variables**
   - Replaced `POSTGRES_*` with `DATABASE_*` variables
   - Added SSL certificate configuration
   - Updated `.env.example` with TiDB connection details

### Phase 3: Model Verification
1. **Audited all SQLAlchemy models**
   - User Service: ✅ No PostgreSQL-specific types found
   - Project Service: ✅ No PostgreSQL-specific types found
   - Knowledge Service: ✅ No PostgreSQL-specific types found

2. **Verified data types**
   - All models already used MySQL-compatible types
   - No JSONB, ARRAY, or UUID columns found
   - JSON columns work identically in TiDB

### Phase 4: Migration Regeneration
1. **Backed up PostgreSQL migrations**
   - Created `POSTGRESQL_SCHEMA_BACKUP.md` for reference
   - Documented existing schema structure

2. **Updated Alembic configuration**
   - Modified `alembic.ini` to use MySQL connection strings
   - Updated `env.py` to handle MySQL-specific features

3. **Generated fresh migrations**
   ```bash
   # For each service:
   cd apps/user-service
   rm -rf migrations/versions/*
   alembic revision --autogenerate -m "Initial migration TiDB"
   alembic upgrade head
   ```

### Phase 5: Testing Infrastructure
1. **Updated test configuration**
   - Modified `conftest.py` in each service
   - Added TiDB test database support
   - Maintained SQLite for fast unit tests

2. **Ran test suites**
   - User Service: ✅ All tests passing
   - Project Service: ✅ All tests passing
   - Knowledge Service: ✅ All tests passing

### Phase 6: Health Checks
1. **Created health check utilities** (`packages/common/database/health.py`)
   - Connection verification
   - SSL certificate validation
   - Retry logic with exponential backoff

2. **Integrated into services**
   - Added database health checks to service endpoints
   - Included connection details in responses

### Phase 7: Docker Configuration
1. **Removed PostgreSQL container**
   - Removed `postgres` service from `docker-compose.yml`
   - Removed PostgreSQL volume definitions
   - Updated service dependencies

---

## Connection Configuration

### Environment Variables

```bash
# TiDB Connection
DATABASE_HOST=gateway01.eu-central-1.prod.aws.tidbcloud.com
DATABASE_PORT=4000
DATABASE_USER=your_cluster_id.root
DATABASE_PASSWORD=your_secure_password

# SSL Configuration (required)
DATABASE_SSL_CA=./ca.pem
DATABASE_SSL_VERIFY_CERT=true
DATABASE_SSL_VERIFY_IDENTITY=true

# Service Databases
USER_SERVICE_DB=design_synapse_user_db
PROJECT_SERVICE_DB=design_synapse_project_db
KNOWLEDGE_SERVICE_DB=design_synapse_knowledge_db
```

### Connection String Format

```python
# Basic format
mysql+pymysql://{username}:{password}@{host}:{port}/{database}

# With SSL parameters
mysql+pymysql://{username}:{password}@{host}:{port}/{database}?ssl_ca={ca_path}&ssl_verify_cert=true&ssl_verify_identity=true&charset=utf8mb4

# Example
mysql+pymysql://kbFV66oHabEtRud.root:mypassword@gateway01.eu-central-1.prod.aws.tidbcloud.com:4000/design_synapse_user_db?ssl_ca=./ca.pem&ssl_verify_cert=true&ssl_verify_identity=true&charset=utf8mb4
```

### SQLAlchemy Engine Configuration

```python
from sqlalchemy import create_engine

engine = create_engine(
    connection_url,
    pool_size=10,              # Connection pool size
    max_overflow=20,           # Max connections beyond pool_size
    pool_pre_ping=True,        # Verify connections before use
    pool_recycle=3600,         # Recycle connections after 1 hour
    echo=False,                # Set to True for SQL logging
    connect_args={
        "ssl": {
            "ca": "/path/to/ca.pem",
            "check_hostname": True,
            "verify_mode": ssl.CERT_REQUIRED,
        }
    }
)
```

---

## Troubleshooting Guide

### Connection Issues

#### Error: "Can't connect to MySQL server"
**Symptoms**: Connection timeout or refused

**Solutions**:
1. Verify TiDB cluster is active in TiDB Cloud console
2. Check network connectivity: `ping gateway01.eu-central-1.prod.aws.tidbcloud.com`
3. Ensure firewall allows outbound connections on port 4000
4. Verify your IP is whitelisted (Serverless allows all IPs by default)

#### Error: "SSL connection error"
**Symptoms**: SSL handshake failure, certificate verification failed

**Solutions**:
1. Verify `ca.pem` file exists and is readable
   ```bash
   ls -la ca.pem
   chmod 644 ca.pem
   ```

2. Download fresh certificate:
   ```bash
   curl -o ca.pem https://letsencrypt.org/certs/isrgrootx1.pem
   ```

3. Check SSL parameters in connection string:
   ```python
   # Ensure these are set correctly
   ssl_ca=./ca.pem
   ssl_verify_cert=true
   ssl_verify_identity=true
   ```

4. Try with SSL verification disabled (development only):
   ```python
   # NOT recommended for production
   ssl_verify_cert=false
   ssl_verify_identity=false
   ```

#### Error: "Access denied for user"
**Symptoms**: Authentication failure, wrong password

**Solutions**:
1. Verify username format includes cluster ID:
   ```bash
   # Correct format
   DATABASE_USER=kbFV66oHabEtRud.root
   
   # Wrong format
   DATABASE_USER=root
   ```

2. Regenerate password in TiDB Cloud console if forgotten

3. Check for extra spaces or special characters in `.env` file

4. Test connection with MySQL client:
   ```bash
   mysql -h gateway01.eu-central-1.prod.aws.tidbcloud.com \
         -P 4000 \
         -u your_cluster_id.root \
         -p \
         --ssl-ca=./ca.pem
   ```

### Migration Issues

#### Error: "Table already exists"
**Symptoms**: Alembic migration fails with duplicate table error

**Solutions**:
1. Check if tables were created manually:
   ```sql
   SHOW TABLES;
   ```

2. Reset Alembic version table:
   ```sql
   DROP TABLE IF EXISTS alembic_version;
   ```

3. Regenerate migrations:
   ```bash
   rm -rf migrations/versions/*
   alembic revision --autogenerate -m "Initial migration"
   alembic upgrade head
   ```

#### Error: "Unknown column type"
**Symptoms**: Migration fails with unsupported column type

**Solutions**:
1. Check for PostgreSQL-specific types in models:
   ```python
   # Replace these
   from sqlalchemy.dialects.postgresql import JSONB, ARRAY, UUID
   
   # With these
   from sqlalchemy import JSON, String, Text
   ```

2. Update model definitions to use MySQL-compatible types

3. Regenerate migrations after fixing models

### Performance Issues

#### Slow Query Performance
**Symptoms**: Queries taking longer than expected

**Solutions**:
1. Add indexes to frequently queried columns:
   ```python
   class User(Base):
       email = Column(String(255), unique=True, index=True)
       created_at = Column(DateTime, index=True)
   ```

2. Use EXPLAIN to analyze queries:
   ```sql
   EXPLAIN SELECT * FROM users WHERE email = 'test@example.com';
   ```

3. Enable query logging to identify slow queries:
   ```python
   engine = create_engine(connection_url, echo=True)
   ```

4. Consider adding composite indexes:
   ```python
   __table_args__ = (
       Index('idx_user_email_active', 'email', 'is_active'),
   )
   ```

#### Connection Pool Exhaustion
**Symptoms**: "QueuePool limit exceeded" errors

**Solutions**:
1. Increase pool size:
   ```python
   engine = create_engine(
       connection_url,
       pool_size=20,
       max_overflow=40
   )
   ```

2. Ensure connections are properly closed:
   ```python
   # Use context managers
   with Session(engine) as session:
       # Your code here
       pass  # Connection automatically closed
   ```

3. Enable pool pre-ping to detect stale connections:
   ```python
   engine = create_engine(
       connection_url,
       pool_pre_ping=True
   )
   ```

---

## Performance Optimization

### Connection Pooling

```python
# Optimal settings for TiDB Serverless
engine = create_engine(
    connection_url,
    pool_size=10,              # Base pool size
    max_overflow=20,           # Additional connections when needed
    pool_pre_ping=True,        # Verify connections before use
    pool_recycle=3600,         # Recycle after 1 hour
    pool_timeout=30,           # Wait 30s for available connection
)
```

### Indexing Strategy

```python
class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, index=True)  # Single column index
    username = Column(String(100), unique=True, index=True)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Composite index for common query patterns
    __table_args__ = (
        Index('idx_user_active_created', 'is_active', 'created_at'),
        Index('idx_user_email_active', 'email', 'is_active'),
    )
```

### Query Optimization

#### Use Eager Loading
```python
# Bad: N+1 query problem
users = session.query(User).all()
for user in users:
    print(user.profile.bio)  # Separate query for each user

# Good: Eager loading
from sqlalchemy.orm import joinedload

users = session.query(User).options(joinedload(User.profile)).all()
for user in users:
    print(user.profile.bio)  # Single query with JOIN
```

#### Batch Operations
```python
# Bad: Individual inserts
for data in bulk_data:
    session.add(User(**data))
    session.commit()

# Good: Bulk insert
session.bulk_insert_mappings(User, bulk_data)
session.commit()
```

#### Use Pagination
```python
# Paginate large result sets
def get_users_paginated(page=1, per_page=50):
    offset = (page - 1) * per_page
    return session.query(User).limit(per_page).offset(offset).all()
```

### Character Set Configuration

Always use `utf8mb4` for full Unicode support:

```python
# In connection string
connection_url += "?charset=utf8mb4"

# When creating databases
CREATE DATABASE design_synapse_user_db 
CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;
```

### Monitoring Queries

```python
# Enable SQL logging in development
import logging
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

# Or use echo parameter
engine = create_engine(connection_url, echo=True)
```

---

## TiDB Features & Limitations

### Supported Features

✅ **ACID Transactions**: Full ACID compliance
✅ **Foreign Keys**: Full support with CASCADE options
✅ **Indexes**: B-tree, unique, composite indexes
✅ **JSON**: Native JSON data type with functions
✅ **Full-Text Search**: MyISAM and InnoDB full-text indexes
✅ **Stored Procedures**: MySQL-compatible procedures
✅ **Triggers**: BEFORE and AFTER triggers
✅ **Views**: Standard SQL views
✅ **CTEs**: Common Table Expressions (WITH clause)
✅ **Window Functions**: RANK, ROW_NUMBER, etc.
✅ **Partitioning**: Range, hash, list partitioning

### Limitations & Differences

❌ **PostgreSQL Extensions**: No PostGIS, pg_trgm, etc.
❌ **JSONB**: Use JSON instead (no binary format)
❌ **Arrays**: Use JSON arrays instead
❌ **Custom Types**: Limited enum and composite type support
⚠️ **Case Sensitivity**: Table/column names are case-insensitive by default
⚠️ **String Comparison**: Case-insensitive by default (use BINARY for case-sensitive)
⚠️ **Date/Time**: Different timezone handling than PostgreSQL

### TiDB-Specific Features

#### HTAP Capabilities
TiDB can handle both transactional and analytical workloads:

```sql
-- Transactional query (uses TiKV)
SELECT * FROM users WHERE id = 123;

-- Analytical query (uses TiFlash if enabled)
SELECT DATE(created_at), COUNT(*) 
FROM users 
GROUP BY DATE(created_at);
```

#### Auto-Scaling
TiDB Serverless automatically scales based on workload:
- Scales up during high traffic
- Scales down during low traffic
- Pauses after inactivity (free tier)

#### Global Distribution
Deploy TiDB clusters in multiple regions:
- Low-latency access for global users
- Data replication across regions
- Automatic failover

### Best Practices

1. **Use utf8mb4**: Always use utf8mb4 character set for full Unicode support

2. **Index Wisely**: Add indexes to frequently queried columns, but don't over-index

3. **Connection Pooling**: Configure appropriate pool sizes for your workload

4. **Monitor Performance**: Use TiDB Cloud dashboard to monitor query performance

5. **Test Migrations**: Always test migrations on a development cluster first

6. **Backup Regularly**: Use TiDB Cloud's backup features or export data regularly

7. **SSL/TLS**: Always use encrypted connections in production

8. **Optimize Queries**: Use EXPLAIN to analyze and optimize slow queries

---

## Additional Resources

- [TiDB Documentation](https://docs.pingcap.com/tidb/stable)
- [TiDB Cloud Console](https://tidbcloud.com)
- [MySQL to TiDB Migration Guide](https://docs.pingcap.com/tidb/stable/migrate-from-mysql)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [PyMySQL Documentation](https://pymysql.readthedocs.io/)

---

## Support

For issues specific to DesignSynapse's TiDB integration:
1. Check this troubleshooting guide
2. Review service logs for error details
3. Test connection with `test_tidb_connection.py`
4. Check TiDB Cloud console for cluster status

For TiDB-specific issues:
- [TiDB Community Forum](https://ask.pingcap.com/)
- [TiDB GitHub Issues](https://github.com/pingcap/tidb/issues)
- TiDB Cloud Support (for paid tiers)
