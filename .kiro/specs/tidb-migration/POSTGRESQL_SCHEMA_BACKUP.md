# PostgreSQL Schema Backup Documentation

**Date**: October 8, 2025  
**Purpose**: Document the current PostgreSQL schema state before migration to TiDB/MySQL

## Backup Location

All PostgreSQL migration files have been backed up to:
- `apps/user-service/migrations/versions_postgresql_backup/`
- `apps/project-service/migrations/versions_postgresql_backup/`
- `apps/knowledge-service/migrations/versions_postgresql_backup/`

## User Service Schema

### Migration History
1. **9870d0009d8d_initial_migration.py** (Initial)
   - Created `users` table
   
2. **20eb6872f89d_add_role_based_access_control.py** (Revises: 9870d0009d8d)
   - Created `roles` table
   - Created `user_roles` junction table
   - Removed `roles` column from `users` table
   
3. **add_user_profile.py** (Revises: 20eb6872f89d)
   - Created `user_profiles` table

### Tables

#### users
- **id**: Integer, Primary Key
- **email**: String, Unique Index
- **username**: String, Unique Index
- **password**: String
- **first_name**: String, Nullable
- **last_name**: String, Nullable
- **created_at**: DateTime, Nullable
- **updated_at**: DateTime, Nullable
- **is_active**: Boolean, Nullable

#### roles
- **id**: Integer, Primary Key, Indexed
- **name**: String, Unique Index
- **description**: String, Nullable

#### user_roles (Junction Table)
- **user_id**: Integer, Foreign Key → users.id
- **role_id**: Integer, Foreign Key → roles.id
- **Primary Key**: (user_id, role_id)

#### user_profiles
- **id**: Integer, Primary Key
- **user_id**: Integer, Foreign Key → users.id (CASCADE DELETE)
- **display_name**: String, Nullable
- **bio**: String, Nullable
- **organization**: String, Nullable
- **phone_number**: String, Nullable
- **location**: String, Nullable
- **social_links**: JSON, Default: {}
- **preferences**: JSON, Default: {}
- **created_at**: DateTime(timezone=True), Default: now()
- **updated_at**: DateTime(timezone=True), Default: now()

### PostgreSQL-Specific Features
- Uses `now()` function for timestamps
- GRANT statements for `design_synapse_user` role
- Sequence permissions for auto-increment IDs

---

## Project Service Schema

### Migration History
1. **c4506401b7fe_create_projects_table.py** (Initial)
   - Created `projects` table
   - Created `project_collaborators` junction table
   
2. **e85c4469c39e_create_comments_table.py** (Revises: c4506401b7fe)
   - Created `comments` table
   
3. **55994d66387d_create_comments_table.py** (Revises: e85c4469c39e)
   - Empty migration (no operations)

### Tables

#### projects
- **id**: Integer, Primary Key
- **name**: String(255)
- **description**: Text, Nullable
- **owner_id**: Integer
- **status**: String(50), Default: 'draft'
- **is_public**: Boolean, Default: false
- **is_archived**: Boolean, Default: false
- **version**: Integer, Default: 1
- **project_metadata**: JSON, Default: {}
- **created_at**: DateTime(timezone=True), Default: now()
- **updated_at**: DateTime(timezone=True), Default: now()

#### project_collaborators (Junction Table)
- **project_id**: Integer, Foreign Key → projects.id (CASCADE DELETE)
- **user_id**: Integer
- **Primary Key**: (project_id, user_id)

#### comments
- **id**: Integer, Primary Key
- **content**: Text
- **author_id**: Integer
- **project_id**: Integer, Foreign Key → projects.id (CASCADE DELETE)
- **parent_id**: Integer, Foreign Key → comments.id (CASCADE DELETE), Nullable
- **created_at**: DateTime(timezone=True), Default: now()
- **updated_at**: DateTime(timezone=True), Default: now()

### PostgreSQL-Specific Features
- Uses `now()` function for timestamps
- Self-referencing foreign key for comment threading

---

## Knowledge Service Schema

### Migration History
1. **05ba133d512c_initial_migration.py** (Initial)
   - Created `resources` table
   - Created `topics` table
   - Created `bookmarks` table
   - Created `citations` table
   - Created `resource_topics` junction table

### Tables

#### resources
- **id**: Integer, Primary Key
- **title**: String(255)
- **description**: String(1000)
- **content_type**: String(50)
- **source_url**: String(500)
- **source_platform**: String(100), Nullable
- **vector_embedding**: JSON, Nullable
- **author**: String(255), Nullable
- **publication_date**: DateTime, Nullable
- **doi**: String(100), Nullable
- **license_type**: String(100), Nullable
- **summary**: Text, Nullable
- **key_takeaways**: JSON, Nullable
- **keywords**: JSON, Nullable
- **storage_path**: String(500)
- **file_size**: Integer, Nullable
- **created_at**: DateTime
- **updated_at**: DateTime

#### topics
- **id**: Integer, Primary Key
- **name**: String(100), Unique
- **description**: String(500)
- **parent_id**: Integer, Foreign Key → topics.id, Nullable

#### bookmarks
- **id**: Integer, Primary Key
- **user_id**: Integer, Check Constraint: user_id > 0
- **resource_id**: Integer, Foreign Key → resources.id (CASCADE DELETE)
- **notes**: Text, Nullable
- **created_at**: DateTime
- **Unique Constraint**: (user_id, resource_id)

#### citations
- **id**: Integer, Primary Key
- **resource_id**: Integer, Foreign Key → resources.id (CASCADE DELETE)
- **project_id**: Integer
- **context**: Text
- **created_at**: DateTime
- **created_by**: Integer, Default: 1

#### resource_topics (Junction Table)
- **resource_id**: Integer, Foreign Key → resources.id
- **topic_id**: Integer, Foreign Key → topics.id
- **Primary Key**: (resource_id, topic_id)

### PostgreSQL-Specific Features
- Check constraints (user_id > 0)
- Self-referencing foreign key for topic hierarchy

---

## MySQL/TiDB Compatibility Notes

### Compatible Features (No Changes Needed)
- ✅ All column types (Integer, String, Text, Boolean, DateTime, JSON)
- ✅ Foreign key constraints with CASCADE DELETE
- ✅ Unique constraints and indexes
- ✅ Junction tables
- ✅ Self-referencing foreign keys
- ✅ Check constraints (MySQL 8.0+)

### Features Requiring Adjustment
- ⚠️ `now()` function → Use `CURRENT_TIMESTAMP` or SQLAlchemy's `func.now()`
- ⚠️ GRANT statements → Remove (TiDB Serverless handles permissions)
- ⚠️ Sequence permissions → Not needed in MySQL/TiDB
- ⚠️ `timezone=True` in DateTime → MySQL stores as UTC, handle in application

### No PostgreSQL-Specific Types Found
- ✅ No JSONB (using JSON)
- ✅ No ARRAY types
- ✅ No UUID columns
- ✅ No PostgreSQL-specific functions

## Migration Strategy

1. **Backup Complete**: All PostgreSQL migrations backed up ✅
2. **Schema Documented**: Current state fully documented ✅
3. **Next Steps**:
   - Clear versions directories
   - Generate fresh MySQL-compatible migrations
   - Test against TiDB Serverless
   - Verify all constraints and relationships

## Rollback Plan

If migration issues occur:
1. Restore from `versions_postgresql_backup/` directories
2. Revert database configuration to PostgreSQL
3. All original migrations preserved for reference
