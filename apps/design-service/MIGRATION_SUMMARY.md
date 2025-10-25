# Design Service Migration Summary

## Migration Details

**Migration ID:** `b6576f89ece0`  
**Migration Name:** Initial design service schema  
**Date:** 2025-10-13

## Tables Created

### 1. designs
Main table for storing design information.

**Columns:**
- `id` (INTEGER, PK, AUTO_INCREMENT)
- `project_id` (INTEGER, NOT NULL)
- `name` (VARCHAR(255), NOT NULL)
- `description` (TEXT, NULLABLE)
- `specification` (JSON, NOT NULL)
- `building_type` (VARCHAR(100), NOT NULL)
- `total_area` (FLOAT, NULLABLE)
- `num_floors` (INTEGER, NULLABLE)
- `materials` (JSON, NULLABLE)
- `generation_prompt` (TEXT, NULLABLE)
- `confidence_score` (FLOAT, NULLABLE)
- `ai_model_version` (VARCHAR(50), NULLABLE)
- `version` (INTEGER, NOT NULL)
- `parent_design_id` (INTEGER, NULLABLE, FK to designs.id)
- `status` (VARCHAR(50), NOT NULL)
- `is_archived` (BOOLEAN, NOT NULL, DEFAULT 0)
- `created_by` (INTEGER, NOT NULL)
- `created_at` (DATETIME, NOT NULL)
- `updated_at` (DATETIME, NOT NULL)

**Indexes:**
- `ix_designs_building_type` on `building_type`
- `ix_designs_created_by` on `created_by`
- `ix_designs_project_id` on `project_id`
- `ix_designs_status` on `status`

**Foreign Keys:**
- `parent_design_id` → `designs.id`

### 2. design_comments
Table for storing comments on designs.

**Columns:**
- `id` (INTEGER, PK, AUTO_INCREMENT)
- `design_id` (INTEGER, NOT NULL, FK to designs.id)
- `content` (TEXT, NOT NULL)
- `position_x` (FLOAT, NULLABLE)
- `position_y` (FLOAT, NULLABLE)
- `position_z` (FLOAT, NULLABLE)
- `created_by` (INTEGER, NOT NULL)
- `created_at` (DATETIME, NOT NULL)
- `updated_at` (DATETIME, NOT NULL)
- `is_edited` (BOOLEAN, NOT NULL, DEFAULT 0)

**Foreign Keys:**
- `design_id` → `designs.id` (ON DELETE CASCADE)

### 3. design_files
Table for storing file attachments for designs.

**Columns:**
- `id` (INTEGER, PK, AUTO_INCREMENT)
- `design_id` (INTEGER, NOT NULL, FK to designs.id)
- `filename` (VARCHAR(255), NOT NULL)
- `file_type` (VARCHAR(50), NOT NULL)
- `file_size` (INTEGER, NOT NULL)
- `storage_path` (VARCHAR(500), NOT NULL)
- `description` (TEXT, NULLABLE)
- `uploaded_by` (INTEGER, NOT NULL)
- `uploaded_at` (DATETIME, NOT NULL)

**Foreign Keys:**
- `design_id` → `designs.id` (ON DELETE CASCADE)

### 4. design_optimizations
Table for storing optimization suggestions for designs.

**Columns:**
- `id` (INTEGER, PK, AUTO_INCREMENT)
- `design_id` (INTEGER, NOT NULL, FK to designs.id)
- `optimization_type` (VARCHAR(100), NOT NULL)
- `title` (VARCHAR(255), NOT NULL)
- `description` (TEXT, NOT NULL)
- `estimated_cost_impact` (FLOAT, NULLABLE)
- `implementation_difficulty` (VARCHAR(50), NOT NULL)
- `priority` (VARCHAR(50), NOT NULL)
- `status` (VARCHAR(50), NOT NULL)
- `applied_at` (DATETIME, NULLABLE)
- `applied_by` (INTEGER, NULLABLE)
- `created_at` (DATETIME, NOT NULL)

**Foreign Keys:**
- `design_id` → `designs.id` (ON DELETE CASCADE)

### 5. design_validations
Table for storing validation results for designs.

**Columns:**
- `id` (INTEGER, PK, AUTO_INCREMENT)
- `design_id` (INTEGER, NOT NULL, FK to designs.id)
- `validation_type` (VARCHAR(100), NOT NULL)
- `rule_set` (VARCHAR(100), NOT NULL)
- `is_compliant` (BOOLEAN, NOT NULL)
- `violations` (JSON, NOT NULL)
- `warnings` (JSON, NOT NULL)
- `validated_at` (DATETIME, NOT NULL)
- `validated_by` (INTEGER, NOT NULL)

**Foreign Keys:**
- `design_id` → `designs.id` (ON DELETE CASCADE)

## Key Features

1. **Proper Indexing:** All frequently queried columns have indexes for optimal performance
2. **CASCADE Deletes:** All child tables have CASCADE delete constraints to maintain referential integrity
3. **JSON Support:** Uses JSON columns for flexible data storage (specification, materials, violations, warnings)
4. **Version Control:** Supports design versioning through `version` and `parent_design_id` fields
5. **Audit Trail:** All tables include timestamp fields for tracking creation and updates

## Migration Scripts

### Helper Scripts Created

1. **generate_migration.py** - Generates migrations while handling shared database
2. **apply_migration.py** - Applies migrations while preserving other service versions
3. **test_rollback.py** - Tests migration rollback functionality

### Verification Scripts

1. **verify_design_schema.py** - Verifies table schema and constraints
2. **check_cascade.py** - Verifies CASCADE delete constraints
3. **restore_versions.py** - Restores all service versions in alembic_version table

## Testing Results

✅ Migration generated successfully  
✅ Migration applied successfully  
✅ All tables created with correct schema  
✅ Indexes created correctly  
✅ CASCADE delete constraints verified  
✅ Migration rollback tested successfully  
✅ Migration re-applied successfully  

## Notes

- The migration was designed to work with a shared TiDB database containing multiple services
- Special handling was implemented to manage the shared `alembic_version` table
- Boolean fields use `server_default=sa.text('0')` for TiDB/MySQL compatibility
- All foreign key constraints include CASCADE delete for proper cleanup

## Rollback

To rollback this migration:

```bash
cd apps/design-service
python test_rollback.py
```

This will drop all design service tables and remove the migration version from the database.
