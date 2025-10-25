# Visual Outputs Enhancement - Requirements Document

## Introduction

This document extends the Design Service to include AI-generated visual outputs (floor plans, renderings, and 3D models) as part of the complete design generation feature. This enhancement aligns with the original vision of providing full end-to-end automated design generation.

**Parent Spec:** `.kiro/specs/design-service/`
**Status:** Extension (Non-Breaking)
**Timeline:** 4-5 weeks after Phase 1 completion

---

## Design Principles

### Non-Breaking Changes
1. All existing API endpoints continue to work unchanged
2. Existing database records remain valid
3. New fields are nullable (optional)
4. Visual generation can be disabled via feature flags
5. Failures in visual generation don't block design creation

### Backward Compatibility
- Existing clients get same responses (with additional optional fields)
- New visual fields return `null` if not generated
- API versioning maintained (v1)

---

## Requirements

### Requirement 1: AI-Generated Floor Plans

**User Story:** As an architect, I want AI-generated 2D floor plans automatically created with my design, so that I can visualize the layout immediately without manual drafting.

#### Acceptance Criteria

1. WHEN a design is created THEN the system SHALL automatically generate a 2D floor plan image
2. WHEN floor plan generation succeeds THEN the system SHALL store the image URL in the design record
3. IF floor plan generation fails THEN the system SHALL log the error and continue with design creation
4. WHEN a floor plan is generated THEN the system SHALL complete within 30 seconds
5. WHEN a user requests an existing design THEN the system SHALL include the floor_plan_url in the response
6. WHEN a user wants to regenerate a floor plan THEN the system SHALL provide an endpoint to do so

---

### Requirement 2: AI-Generated Photorealistic Renderings

**User Story:** As a client, I want to see photorealistic renderings of my building design, so that I can visualize how the final structure will look.

#### Acceptance Criteria

1. WHEN a design is created THEN the system SHALL automatically generate a photorealistic rendering
2. WHEN rendering generation succeeds THEN the system SHALL store the image URL in the design record
3. IF rendering generation fails THEN the system SHALL log the error and continue with design creation
4. WHEN a rendering is generated THEN the system SHALL complete within 45 seconds
5. WHEN a user specifies a rendering style THEN the system SHALL support multiple styles (photorealistic, sketch, modern)
6. WHEN a user wants multiple views THEN the system SHALL support generating front, side, and aerial views

---

### Requirement 3: Parametric 3D Model Generation

**User Story:** As an engineer, I want to download 3D models in standard CAD formats, so that I can import them into my CAD software for detailed work.

#### Acceptance Criteria

1. WHEN a user requests 3D model generation THEN the system SHALL create a parametric model from the design specification
2. WHEN a 3D model is generated THEN the system SHALL support STEP and IFC formats
3. WHEN model generation succeeds THEN the system SHALL store the file URL in the design record
4. IF model generation fails THEN the system SHALL return a clear error message
5. WHEN a 3D model is generated THEN the system SHALL complete within 60 seconds
6. WHEN a model is downloaded THEN the system SHALL provide a valid CAD file that opens in standard tools

---

### Requirement 4: Visual Generation Configuration

**User Story:** As a system administrator, I want to configure visual generation settings, so that I can control costs and quality.

#### Acceptance Criteria

1. WHEN visual generation is configured THEN the system SHALL support enabling/disabling each visual type independently
2. WHEN auto-generation is disabled THEN the system SHALL still allow on-demand generation
3. WHEN quality settings are configured THEN the system SHALL apply them to all new generations
4. WHEN rate limits are set THEN the system SHALL enforce them per user/project
5. WHEN costs exceed budget THEN the system SHALL disable auto-generation and notify administrators

---

### Requirement 5: Visual Regeneration and Versioning

**User Story:** As a designer, I want to regenerate visuals when I update my design, so that the visuals stay in sync with my specifications.

#### Acceptance Criteria

1. WHEN a design is updated THEN the system SHALL offer to regenerate visuals
2. WHEN visuals are regenerated THEN the system SHALL replace old URLs with new ones
3. WHEN a design version is created THEN the system SHALL copy visual URLs to the new version
4. WHEN a user wants to keep old visuals THEN the system SHALL provide an option to skip regeneration
5. WHEN regeneration is requested THEN the system SHALL process it asynchronously

---

### Requirement 6: Visual Storage and Delivery

**User Story:** As a user, I want fast access to my design visuals, so that I can share them with clients quickly.

#### Acceptance Criteria

1. WHEN visuals are generated THEN the system SHALL store them in cloud storage (S3/equivalent)
2. WHEN a visual is accessed THEN the system SHALL serve it via CDN for fast delivery
3. WHEN a visual URL is returned THEN the system SHALL include a signed URL valid for 24 hours
4. WHEN storage costs are optimized THEN the system SHALL compress images without visible quality loss
5. WHEN old visuals are no longer needed THEN the system SHALL implement cleanup policies (90 days)

---

### Requirement 7: Error Handling and Fallbacks

**User Story:** As a developer, I want robust error handling for visual generation, so that failures don't impact the core design service.

#### Acceptance Criteria

1. WHEN visual generation fails THEN the system SHALL NOT fail the design creation request
2. WHEN an AI provider is unavailable THEN the system SHALL try fallback providers
3. WHEN all providers fail THEN the system SHALL queue the request for retry
4. WHEN errors occur THEN the system SHALL log detailed error information for debugging
5. WHEN a user checks generation status THEN the system SHALL provide clear status messages

---

### Requirement 8: Performance and Scalability

**User Story:** As a platform operator, I want visual generation to scale with demand, so that multiple users can generate designs simultaneously.

#### Acceptance Criteria

1. WHEN 10 concurrent visual generation requests are made THEN the system SHALL process all within 90 seconds
2. WHEN visual generation is slow THEN the system SHALL use async task queues (Celery/equivalent)
3. WHEN generation completes THEN the system SHALL notify the user via webhook or polling endpoint
4. WHEN system load is high THEN the system SHALL implement rate limiting per user
5. WHEN caching is enabled THEN the system SHALL cache similar visual requests for 1 hour

---

### Requirement 9: Cost Tracking and Optimization

**User Story:** As a finance manager, I want to track visual generation costs, so that I can manage the budget effectively.

#### Acceptance Criteria

1. WHEN visuals are generated THEN the system SHALL log the cost per generation
2. WHEN costs are tracked THEN the system SHALL break down by type (floor plan, rendering, 3D model)
3. WHEN budgets are set THEN the system SHALL alert when approaching limits
4. WHEN optimization is enabled THEN the system SHALL cache and reuse similar generations
5. WHEN reports are requested THEN the system SHALL provide cost analytics per project/user

---

### Requirement 10: API Backward Compatibility

**User Story:** As an API consumer, I want existing integrations to continue working, so that I don't need to update my code immediately.

#### Acceptance Criteria

1. WHEN existing API endpoints are called THEN the system SHALL return responses in the same format
2. WHEN new visual fields are added THEN the system SHALL include them as optional fields
3. WHEN old clients don't expect visual fields THEN the system SHALL still work correctly
4. WHEN API version is v1 THEN the system SHALL maintain v1 compatibility
5. WHEN breaking changes are needed THEN the system SHALL introduce them in v2 API

---

## Success Metrics

### Phase 2 Complete When:
- ✅ 95% of designs include floor plans
- ✅ 90% of designs include renderings
- ✅ 3D models can be generated on-demand
- ✅ Visual generation completes in <60 seconds (p95)
- ✅ Cost per design with visuals < $0.50
- ✅ Zero breaking changes to existing API
- ✅ All existing tests still pass
- ✅ Visual generation failure rate < 5%

---

## Technical Constraints

### AI Provider Limits
- DALL-E 3: 50 requests/minute
- Stable Diffusion: Variable based on provider
- Processing time: 10-45 seconds per image

### Storage Limits
- Max image size: 10MB per visual
- Storage retention: 90 days for unused visuals
- CDN bandwidth: Monitor and optimize

### Cost Constraints
- Target: $0.15 per design with all visuals
- Maximum: $0.50 per design
- Monthly budget: Track and alert

---

## Dependencies

### External Services
- OpenAI API (DALL-E 3) - Already integrated
- Stable Diffusion API (optional fallback)
- Cloud Storage (AWS S3 or equivalent)
- CDN for image delivery

### Internal Services
- Design Service (existing)
- File Storage Service (existing)
- Task Queue (new - Celery/Redis)

### Libraries
- `pillow` - Image processing
- `cadquery` - 3D modeling
- `pythonOCC-core` - CAD kernel
- `replicate` - AI model API (optional)

---

## Migration Strategy

### Database Migration
```sql
-- Add nullable columns (non-breaking)
ALTER TABLE designs
ADD COLUMN floor_plan_url VARCHAR(500) NULL,
ADD COLUMN rendering_url VARCHAR(500) NULL,
ADD COLUMN model_file_url VARCHAR(500) NULL,
ADD COLUMN visual_generation_status VARCHAR(50) DEFAULT 'pending',
ADD COLUMN visual_generation_error TEXT NULL;
```

### Feature Rollout
1. Week 1: Deploy with feature flag OFF
2. Week 2: Enable for internal testing (10% traffic)
3. Week 3: Enable for beta users (50% traffic)
4. Week 4: Enable for all users (100% traffic)

---

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| High AI costs | High | Rate limiting, caching, budget alerts |
| Slow generation | Medium | Async processing, status polling |
| Provider outages | Medium | Multiple fallback providers |
| Storage costs | Low | Compression, cleanup policies |
| Breaking changes | High | Extensive testing, feature flags |

---

## Next Steps

1. Review and approve requirements
2. Create design document
3. Create implementation tasks
4. Begin Phase 2 development

---

**Status:** Awaiting Chief Architect approval
**Created:** 2025-10-14
**Last Updated:** 2025-10-14
