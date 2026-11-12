# Visual Outputs Enhancement - Spec Overview

## Quick Links

- **Requirements:** [requirements.md](./requirements.md) - What we're building
- **Design:** [design.md](./design.md) - How we're building it
- **Tasks:** [tasks.md](./tasks.md) - Step-by-step implementation plan

---

## What This Spec Does

Extends the Design Service to include AI-generated visual outputs:
- ✅ 2D Floor Plans (AI-generated)
- ✅ Photorealistic Renderings (AI-generated)
- ✅ Parametric 3D Models (STEP/IFC format)

---

## Why This Matters

This completes the original vision of **full end-to-end automated design generation**. Users will get:
1. Design specifications (already working)
2. Building code validation (already working)
3. Cost optimization (already working)
4. **Floor plans** (NEW)
5. **Renderings** (NEW)
6. **3D models** (NEW)

All from ONE API call!

---

## Key Principles

### Non-Breaking
- All existing code continues to work
- New fields are optional (nullable)
- Backward compatible API
- Feature flags for gradual rollout

### Async Processing
- Visual generation happens in background
- Users get immediate response
- Status polling for completion
- No blocking operations

### Cost Controlled
- Budget limits and alerts
- Rate limiting per user
- Caching for efficiency
- Target: $0.18 per design with all visuals

---

## Implementation Timeline

| Sprint | Duration | Focus | Deliverable |
|--------|----------|-------|-------------|
| Sprint 1 | Week 1 | Infrastructure | Database, Celery, S3 setup |
| Sprint 2 | Week 2 | Visual Services | Floor plans & renderings working |
| Sprint 3 | Week 3 | 3D & API | 3D models & API endpoints |
| Sprint 4 | Week 4 | Testing & Deploy | Production deployment |
| Sprint 5 | Week 5 | Polish (Optional) | Advanced features |

**Total:** 4-5 weeks

---

## Architecture at a Glance

```
User Request
    ↓
Design Service (creates design spec)
    ↓
Visual Generator Service (queues tasks)
    ↓
Celery Task Queue (async processing)
    ↓
AI Providers (DALL-E 3, Stable Diffusion)
    ↓
Cloud Storage (S3 + CDN)
    ↓
Design Record Updated (URLs added)
```

---

## What Gets Added

### Database
```sql
ALTER TABLE designs ADD COLUMN
    floor_plan_url VARCHAR(500) NULL,
    rendering_url VARCHAR(500) NULL,
    model_file_url VARCHAR(500) NULL;
```

### New Services
- `VisualGeneratorService` - Orchestrates visual generation
- `ModelGeneratorService` - Creates 3D models
- `StorageClient` - Handles S3 uploads

### New Endpoints
- `POST /api/v1/designs/{id}/generate-floor-plan`
- `POST /api/v1/designs/{id}/generate-rendering`
- `POST /api/v1/designs/{id}/generate-3d-model`
- `GET /api/v1/tasks/{task_id}` - Check generation status

### Enhanced Endpoints
- `POST /api/v1/designs?generate_visuals=true` - Auto-generate visuals

---

## Dependencies

### External Services
- OpenAI API (DALL-E 3) - Already have
- AWS S3 - For storage
- Redis - For task queue
- CloudFront - For CDN (optional)

### Python Packages
```
celery>=5.3.0
redis>=5.0.0
boto3>=1.28.0  # AWS SDK
pillow>=10.0.0  # Image processing
cadquery>=2.3.0  # 3D modeling
pythonOCC-core>=7.7.0  # CAD kernel
```

---

## Cost Breakdown

| Component | Cost per Design |
|-----------|----------------|
| Floor Plan (DALL-E 3 HD) | $0.080 |
| Rendering (DALL-E 3 HD) | $0.080 |
| 3D Model (compute) | $0.010 |
| Storage + CDN | $0.015 |
| **Total** | **$0.185** |

**Monthly at scale:**
- 1,000 designs: $185/month
- 10,000 designs: $1,850/month
- 100,000 designs: $18,500/month

---

## Success Metrics

### Technical
- ✅ 95% of designs include floor plans
- ✅ 90% of designs include renderings
- ✅ Visual generation < 60 seconds (p95)
- ✅ Failure rate < 5%
- ✅ Zero breaking changes

### Business
- ✅ Cost per design < $0.50
- ✅ User satisfaction > 4/5
- ✅ Adoption rate > 80%

---

## Next Steps

1. **Review** - Chief Architect reviews requirements, design, tasks
2. **Approve** - Get sign-off to proceed
3. **Sprint 1** - Begin infrastructure setup
4. **Iterate** - Build incrementally over 4-5 weeks
5. **Deploy** - Gradual rollout with feature flags

---

## Questions?

- **Technical questions:** Review [design.md](./design.md)
- **Feature questions:** Review [requirements.md](./requirements.md)
- **Implementation questions:** Review [tasks.md](./tasks.md)

---

**Status:** Ready for review
**Created:** 2025-10-14
**Owner:** Technical Lead
**Approver:** Chief Architect
