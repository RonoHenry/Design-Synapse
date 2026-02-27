# Cleanup Unnecessary Markdown Files - Design

## Overview
This design outlines the approach to systematically identify and remove development artifact markdown files while preserving essential documentation.

## Design Decisions

### DD-1: Categorization Strategy
**Decision:** Group files by pattern and location for systematic removal

**Rationale:**
- Makes it easier to verify what's being removed
- Allows for batch operations
- Reduces risk of accidentally removing important files

**Categories:**
1. Root-level artifacts
2. Service-level summaries/reports
3. Spec directory temporary files
4. Test directory summaries
5. Package implementation summaries

### DD-2: Preservation Rules
**Decision:** Use explicit whitelist approach for files to keep

**Rationale:**
- Safer than blacklist approach
- Clear documentation of what's essential
- Easy to verify nothing important is removed

**Whitelist Patterns:**
- `README.md` (all locations)
- `docs/*.md` (all documentation)
- `.kiro/specs/*/requirements.md`
- `.kiro/specs/*/design.md`
- `.kiro/specs/*/tasks.md`
- `apps/architectural-service/MANUAL_TESTING_GUIDE.md`
- `apps/design-service/docs/CACHING_STRATEGY.md`
- `.github/pull_request_template.md`

### DD-3: Removal Approach
**Decision:** Use git rm for tracked files, regular deletion for untracked

**Rationale:**
- Properly removes files from git history
- Creates clean commit
- Allows for easy rollback if needed

## Implementation Approach

### Phase 1: Identification
1. Generate complete list of markdown files
2. Categorize by pattern
3. Verify against whitelist
4. Create removal list

### Phase 2: Verification
1. Review removal list with user
2. Confirm no essential files are included
3. Get approval to proceed

### Phase 3: Removal
1. Remove files using git rm
2. Verify removal
3. Create commit with clear message

### Phase 4: Validation
1. Verify essential files remain
2. Check repository structure
3. Confirm git status is clean

## File Removal List

### Root Level (5 files)
```
FINAL_VALIDATION_REPORT.md
TEST_VALIDATION_SUMMARY.md
HEALTH_ENDPOINTS_IMPLEMENTATION_SUMMARY.md
health_endpoints_summary.md
PROJECT_STRUCTURE.md
```

### Architectural Service (11 files)
```
apps/architectural-service/CHECKPOINT_CORE_DESIGN_MANAGEMENT.md
apps/architectural-service/DOCUMENTATION_SUMMARY.md
apps/architectural-service/FINAL_CHECKPOINT_REPORT.md
apps/architectural-service/FINAL_SERVICE_VALIDATION.md
apps/architectural-service/FINAL_TEST_VALIDATION_REPORT.md
apps/architectural-service/INTEGRATION_CHECKPOINT_SUMMARY.md
apps/architectural-service/LOAD_TEST_REPORT.md
apps/architectural-service/LOAD_TEST_SUMMARY.md
apps/architectural-service/MANUAL_TESTING_REPORT.md
apps/architectural-service/MANUAL_TESTING_SUMMARY.md
apps/architectural-service/TEST_VALIDATION_SUMMARY.md
```

### Design Service (8 files)
```
apps/design-service/AUTH_FIX_SUMMARY.md
apps/design-service/ERROR_HANDLING_SUMMARY.md
apps/design-service/MIGRATION_SUMMARY.md
apps/design-service/OPTIMIZATION_SERVICE_SUMMARY.md
apps/design-service/TEST_FIXES_SUMMARY.md
apps/design-service/tests/TEST_INFRASTRUCTURE_SUMMARY.md
apps/design-service/tests/integration/BACKWARD_COMPATIBILITY_TESTS.md
apps/design-service/tests/integration/VISUAL_GENERATION_INTEGRATION_TESTS.md
```

### Knowledge Service (6 files)
```
apps/knowledge-service/ADVANCED_SEARCH_IMPLEMENTATION.md
apps/knowledge-service/ERROR_HANDLING_IMPLEMENTATION_SUMMARY.md
apps/knowledge-service/RECOMMENDATION_SYSTEM_SUMMARY.md
apps/knowledge-service/UNIT_TESTING_SUMMARY.md
apps/knowledge-service/VECTOR_SEARCH_CACHING_IMPROVEMENTS.md
apps/knowledge-service/docs/BATCH_PROCESSING.md
```

### Labor Service (9 files)
```
apps/labor-service/API_INTEGRATION_ANALYSIS.md
apps/labor-service/API_INTEGRATION_PROGRESS.md
apps/labor-service/CONFIGURATION_FIX_SUMMARY.md
apps/labor-service/SYSTEMATIC_FIX_PROGRESS.md
apps/labor-service/TDD_GREEN_PHASE_SUMMARY.md
apps/labor-service/TDD_GREEN_PROGRESS_SUMMARY.md
apps/labor-service/TDD_REFACTOR_COMPLETION_SUMMARY.md
apps/labor-service/TDD_REFACTOR_PHASE_SUMMARY.md
apps/labor-service/TEST_STATUS_SUMMARY.md
```

### User Service (1 file)
```
apps/user-service/MYSQL_COMPATIBILITY_VERIFICATION.md
```

### Vendor Service (3 files)
```
apps/vendor-service/COMPREHENSIVE_TEST_RESULTS.md
apps/vendor-service/IMPLEMENTATION_SUMMARY.md
apps/vendor-service/VENDOR_PRODUCTS_COMPLETION_SUMMARY.md
```

### Project Service (2 files)
```
apps/project-service/tests/TEST_INFRASTRUCTURE_SUMMARY.md
apps/project-service/tests/VERIFICATION_CHECKLIST.md
```

### Spec Directory (7 files)
```
.kiro/specs/design-service/CURRENT_STATUS.md
.kiro/specs/design-service/INTEGRATION_PLAN.md
.kiro/specs/design-service-visual-outputs/README.md
.kiro/specs/knowledge-service-completion/TDD_COMPLETION_PLAN.md
.kiro/specs/knowledge-service-completion/TDD_TASK_TRACKER.md
.kiro/specs/tidb-migration/MIGRATION_SUMMARY.md
.kiro/specs/tidb-migration/POSTGRESQL_SCHEMA_BACKUP.md
.kiro/specs/tidb-migration/TASK_7_SUMMARY.md
```

### Test Directory (3 files)
```
tests/INTEGRATION_TEST_INFRASTRUCTURE_SUMMARY.md
tests/TASK_COMPLETION_SUMMARY.md
tests/integration/DATABASE_INTEGRATION_TDD_SUMMARY.md
```

### Common Packages (6 files)
```
packages/common/config/TIDB_MIGRATION_NOTES.md
packages/common/http/IMPLEMENTATION_SUMMARY.md
packages/common/monitoring/TRACING_IMPLEMENTATION_SUMMARY.md
packages/common/performance/IMPLEMENTATION_SUMMARY.md
packages/common/performance/tests/PERFORMANCE_SECURITY_TEST_SUMMARY.md
packages/common/rate_limiting/IMPLEMENTATION_SUMMARY.md
```

**Total Files to Remove: 61**

## Validation Criteria

### Pre-Removal Validation
- [ ] All files in removal list exist
- [ ] No essential files in removal list
- [ ] User approval obtained

### Post-Removal Validation
- [ ] All targeted files removed
- [ ] Essential files preserved
- [ ] Git status shows only deletions
- [ ] Repository structure intact

## Rollback Plan
If issues are discovered:
1. Use `git reset --hard HEAD~1` to undo commit
2. Review removal list
3. Adjust and retry

## Success Metrics
- 61 development artifact files removed
- All essential documentation preserved
- Clean git commit created
- Repository looks professional
