# TiDB Serverless Migration - Requirements

## Overview
Migrate DesignSynapse platform from PostgreSQL to TiDB Serverless for improved scalability, auto-scaling capabilities, and cloud-native architecture.

## Connection Details
- **Host**: gateway01.eu-central-1.prod.aws.tidbcloud.com
- **Port**: 4000
- **Username**: kbFV66oHabEtRud.root
- **Database**: test (will create service-specific databases)
- **Region**: EU Central 1 (Frankfurt)

## Requirements

### 1. Database Driver Migration
**ID**: TDB-1  
**Priority**: High  
**Description**: Replace PostgreSQL drivers with MySQL-compatible drivers for TiDB

**Acceptance Criteria**:
- Remove psycopg2-binary from all services
- Add pymysql and cryptography to all services
- Update SQLAlchemy connection strings to use mysql+pymysql dialect
- SSL/TLS connection configured with CA certificate

### 2. Configuration Updates
**ID**: TDB-2  
**Priority**: High  
**Description**: Update database configuration to support TiDB connection parameters

**Acceptance Criteria**:
- Update packages/common/config/database.py to support MySQL dialect
- Add SSL certificate path configuration
- Update environment variable examples
- Support both sync and async connections with appropriate drivers

### 3. Model Compatibility
**ID**: TDB-3  
**Priority**: High  
**Description**: Ensure SQLAlchemy models are MySQL/TiDB compatible

**Acceptance Criteria**:
- Replace PostgreSQL-specific types (JSONB, ARRAY) with MySQL-compatible types
- Verify all Mapped types work with MySQL
- Test cascade deletes and foreign key constraints
- Ensure datetime handling is consistent

### 4. Migration Scripts
**ID**: TDB-4  
**Priority**: High  
**Description**: Regenerate Alembic migrations for MySQL/TiDB

**Acceptance Criteria**:
- Clear existing PostgreSQL migrations
- Generate new migrations for MySQL dialect
- Test migrations on TiDB Serverless
- Verify all tables, indexes, and constraints are created correctly

### 5. Connection Testing
**ID**: TDB-5  
**Priority**: High  
**Description**: Verify connectivity and basic operations on TiDB

**Acceptance Criteria**:
- Test connection from all services
- Verify SSL/TLS connection works
- Test basic CRUD operations
- Verify connection pooling works correctly

### 6. Service-Specific Databases
**ID**: TDB-6  
**Priority**: Medium  
**Description**: Create separate databases for each service on TiDB

**Acceptance Criteria**:
- Create design_synapse_user_db
- Create design_synapse_project_db  
- Create design_synapse_knowledge_db
- Configure proper access controls

## Benefits
- ✅ Auto-scaling based on workload
- ✅ Pay-per-use pricing model
- ✅ HTAP capabilities (transactional + analytical)
- ✅ Distributed architecture for high availability
- ✅ Cloud-native with no infrastructure management
- ✅ Free tier for development/testing
- ✅ MySQL compatibility for easier ecosystem integration

## Risks & Mitigation
- **Risk**: PostgreSQL-specific features may not work
  - **Mitigation**: Audit models for PostgreSQL-specific types, replace with MySQL equivalents
  
- **Risk**: Migration downtime
  - **Mitigation**: This is a new setup, no existing data to migrate
  
- **Risk**: Performance differences
  - **Mitigation**: TiDB is designed for scale, should perform better under load

## Success Criteria
- All services connect successfully to TiDB Serverless
- All tests pass with TiDB backend
- CRUD operations work correctly
- Migrations run successfully
- No PostgreSQL-specific code remains
