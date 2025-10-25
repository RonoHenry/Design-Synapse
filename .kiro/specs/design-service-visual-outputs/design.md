# Visual Outputs Enhancement - Design Document

## Overview

This document details the architecture and implementation approach for adding AI-generated visual outputs (floor plans, renderings, and 3D models) to the Design Service. The design ensures backward compatibility while extending functionality to match the original vision of full end-to-end automated design generation.

**Parent Spec:** `.kiro/specs/design-service/`
**Requirements:** `.kiro/specs/design-service-visual-outputs/requirements.md`
**Status:** Design Phase
**Last Updated:** 2025-10-14

---

## Architecture Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Design Service (Enhanced)                │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐      ┌──────────────┐                    │
│  │   Existing   │      │     NEW      │                    │
│  │  Components  │      │  Components  │                    │
│  ├──────────────┤      ├──────────────┤                    │
│  │ LLM Client   │      │ Visual Gen   │                    │
│  │ Design Gen   │──────│ Service      │                    │
│  │ Validation   │      │              │                    │
│  │ Optimization │      │ Model Gen    │                    │
│  └──────────────┘      │ Service      │                    │
│                        └──────────────┘                    │
│                               │                              │
│                               ↓                              │
│                        ┌──────────────┐                    │
│                        │ Task Queue   │                    │
│                        │ (Celery)     │                    │
│                        └──────────────┘                    │
└─────────────────────────────────────────────────────────────┘
                               │
                               ↓
                    ┌──────────────────────┐
                    │   External Services   │
                    ├──────────────────────┤
                    │ • OpenAI (DALL-E 3)  │
                    │ • Stable Diffusion   │
                    │ • Cloud Storage (S3) │
                    │ • CDN                │
                    └──────────────────────┘
```

### Component Interaction Flow

```
User Request
    │
    ↓
┌─────────────────────┐
│ POST /api/v1/designs│
└─────────────────────┘
    │
    ↓
┌─────────────────────────────────────┐
│ DesignGeneratorService (Existing)   │
│ - Generate specification            │
│ - Validate & optimize               │
│ - Save to database                  │
└─────────────────────────────────────┘
    │
    ↓
┌─────────────────────────────────────┐
│ VisualGeneratorService (NEW)        │
│ - Check feature flags               │
│ - Queue visual generation tasks     │
│ - Return immediately (async)        │
└─────────────────────────────────────┘
    │
    ↓
┌─────────────────────────────────────┐
│ Celery Task Queue (NEW)             │
│ - generate_floor_plan_task()        │
│ - generate_rendering_task()         │
│ - generate_3d_model_task()          │
└─────────────────────────────────────┘
    │
    ↓
┌─────────────────────────────────────┐
│ AI Providers & Storage              │
│ - DALL-E 3 / Stable Diffusion       │
│ - S3 Storage                        │
│ - Update design record with URLs    │
└─────────────────────────────────────┘
```

---

## Database Schema Changes

### Design Table Extension (Non-Breaking)

```sql
-- Add nullable columns to existing designs table
ALTER TABLE designs ADD COLUMN IF NOT EXISTS
    floor_plan_url VARCHAR(500) NULL
    COMMENT 'URL to AI-generated 2D floor plan image';

ALTER TABLE designs ADD COLUMN IF NOT EXISTS
    rendering_url VARCHAR(500) NULL
    COMMENT 'URL to AI-generated photorealistic rendering';

ALTER TABLE designs ADD COLUMN IF NOT EXISTS
    model_file_url VARCHAR(500) NULL
    COMMENT 'URL to generated 3D model file (STEP/IFC)';

ALTER TABLE designs ADD COLUMN IF NOT EXISTS
    visual_generation_status VARCHAR(50) DEFAULT 'pending'
    COMMENT 'Status: pending, processing, completed, failed';

ALTER TABLE designs ADD COLUMN IF NOT EXISTS
    visual_generation_error TEXT NULL
    COMMENT 'Error message if visual generation fails';

ALTER TABLE designs ADD COLUMN IF NOT EXISTS
    visual_generated_at TIMESTAMP NULL
    COMMENT 'Timestamp when visuals were last generated';

-- Add index for status queries
CREATE INDEX idx_designs_visual_status
ON designs(visual_generation_status);
```

### Migration Strategy

```python
# migrations/versions/xxx_add_visual_outputs.py
"""add visual outputs to designs

Revision ID: xxx
"""

def upgrade():
    # Add columns with NULL default - existing records unaffected
    op.add_column('designs',
        sa.Column('floor_plan_url', sa.String(500), nullable=True))
    op.add_column('designs',
        sa.Column('rendering_url', sa.String(500), nullable=True))
    op.add_column('designs',
        sa.Column('model_file_url', sa.String(500), nullable=True))
    op.add_column('designs',
        sa.Column('visual_generation_status', sa.String(50),
                  server_default='pending'))
    op.add_column('designs',
        sa.Column('visual_generation_error', sa.Text(), nullable=True))
    op.add_column('designs',
        sa.Column('visual_generated_at', sa.DateTime(), nullable=True))

    # Add index
    op.create_index('idx_designs_visual_status', 'designs',
                    ['visual_generation_status'])

def downgrade():
    op.drop_index('idx_designs_visual_status', 'designs')
    op.drop_column('designs', 'visual_generated_at')
    op.drop_column('designs', 'visual_generation_error')
    op.drop_column('designs', 'visual_generation_status')
    op.drop_column('designs', 'model_file_url')
    op.drop_column('designs', 'rendering_url')
    op.drop_column('designs', 'floor_plan_url')
```

---

## Component Design

### 1. VisualGeneratorService (NEW)

**Location:** `apps/design-service/src/services/visual_generator.py`

**Purpose:** Orchestrate AI-generated visual outputs

**Key Methods:**

```python
class VisualGeneratorService:
    """Service for generating visual outputs from design specifications."""

    def __init__(
        self,
        llm_client: LLMClient,
        storage_client: StorageClient,
        config: VisualConfig
    ):
        self.llm_client = llm_client
        self.storage = storage_client
        self.config = config

    async def generate_floor_plan(
        self,
        design_id: int,
        design_spec: Dict[str, Any]
    ) -> str:
        """
        Generate 2D floor plan from design specification.

        Returns:
            URL to generated floor plan image
        """
        # Build prompt from design spec
        prompt = self._build_floor_plan_prompt(design_spec)

        # Generate image using DALL-E 3
        image_data = await self.llm_client.generate_image(
            prompt=prompt,
            size="1024x1024",
            quality="hd"
        )

        # Upload to storage
        filename = f"floor_plan_{design_id}_{timestamp()}.png"
        url = await self.storage.upload(filename, image_data)

        return url

    async def generate_rendering(
        self,
        design_id: int,
        design_spec: Dict[str, Any],
        style: str = "photorealistic"
    ) -> str:
        """
        Generate photorealistic rendering from design specification.

        Returns:
            URL to generated rendering image
        """
        prompt = self._build_rendering_prompt(design_spec, style)

        # Try DALL-E 3 first, fallback to Stable Diffusion
        try:
            image_data = await self.llm_client.generate_image(
                prompt=prompt,
                size="1792x1024",  # Landscape for building
                quality="hd"
            )
        except Exception as e:
            logger.warning(f"DALL-E failed, trying Stable Diffusion: {e}")
            image_data = await self._generate_with_stable_diffusion(prompt)

        filename = f"rendering_{design_id}_{timestamp()}.png"
        url = await self.storage.upload(filename, image_data)

        return url

    def _build_floor_plan_prompt(self, spec: Dict) -> str:
        """Build detailed prompt for floor plan generation."""
        building_info = spec.get("building_info", {})
        spaces = spec.get("spaces", [])

        prompt = f"""
        Architectural 2D floor plan drawing for a {building_info.get('type')} building.

        Building Details:
        - Total Area: {building_info.get('total_area')} sqm
        - Floors: {building_info.get('num_floors')}

        Spaces:
        """

        for space in spaces:
            prompt += f"\n- {space['name']}: {space['area']} sqm"

        prompt += """

        Style: Professional architectural floor plan with:
        - Clean black lines on white background
        - Room labels and dimensions
        - Door and window symbols
        - North arrow and scale
        - Furniture layout suggestions
        """

        return prompt

    def _build_rendering_prompt(self, spec: Dict, style: str) -> str:
        """Build detailed prompt for rendering generation."""
        building_info = spec.get("building_info", {})
        structure = spec.get("structure", {})

        prompt = f"""
        Photorealistic architectural rendering of a {building_info.get('type')} building.

        Building Characteristics:
        - Type: {building_info.get('subtype', 'modern')}
        - Floors: {building_info.get('num_floors')}
        - Height: {building_info.get('height')} meters
        - Wall Material: {structure.get('wall_material')}
        - Roof Type: {structure.get('roof_type')}
        - Roof Material: {structure.get('roof_material')}

        Setting: African architecture, modern design, natural lighting,
        landscaped surroundings, clear blue sky, professional photography quality.

        Style: {style}
        View: Front elevation, 3/4 perspective
        """

        return prompt
```

### 2. ModelGeneratorService (NEW)

**Location:** `apps/design-service/src/services/model_generator.py`

**Purpose:** Generate parametric 3D models

**Key Methods:**

```python
from cadquery import Workplane
import pythonOCC

class ModelGeneratorService:
    """Service for generating parametric 3D models."""

    def generate_basic_model(
        self,
        design_id: int,
        design_spec: Dict[str, Any],
        format: str = "step"
    ) -> str:
        """
        Generate basic parametric 3D model.

        Args:
            design_id: Design ID
            design_spec: Design specification
            format: Output format (step, ifc)

        Returns:
            URL to generated model file
        """
        building_info = design_spec.get("building_info", {})

        # Extract dimensions
        length = building_info.get("dimensions", {}).get("length", 20)
        width = building_info.get("dimensions", {}).get("width", 15)
        height = building_info.get("height", 7.5)
        num_floors = building_info.get("num_floors", 2)

        # Create parametric model
        model = self._create_building_model(
            length, width, height, num_floors
        )

        # Export to file
        filename = f"model_{design_id}.{format}"
        filepath = f"/tmp/{filename}"

        if format == "step":
            model.exportStep(filepath)
        elif format == "ifc":
            self._export_to_ifc(model, filepath)

        # Upload to storage
        url = self.storage.upload_file(filepath, filename)

        return url

    def _create_building_model(
        self,
        length: float,
        width: float,
        height: float,
        num_floors: int
    ) -> Workplane:
        """Create basic building geometry."""
        floor_height = height / num_floors

        # Create base
        model = Workplane("XY").box(length, width, floor_height)

        # Add floors
        for i in range(1, num_floors):
            floor = (
                Workplane("XY")
                .workplane(offset=i * floor_height)
                .box(length, width, floor_height)
            )
            model = model.union(floor)

        # Add roof
        roof = (
            Workplane("XY")
            .workplane(offset=height)
            .polygon(4, length * 1.2)
            .extrude(2)
        )
        model = model.union(roof)

        return model
```

### 3. Enhanced LLMClient

**Location:** `apps/design-service/src/services/llm_client.py` (extend existing)

**New Methods:**

```python
class LLMClient:
    # ... existing methods ...

    async def generate_image(
        self,
        prompt: str,
        size: str = "1024x1024",
        quality: str = "standard"
    ) -> bytes:
        """
        Generate image using DALL-E 3.

        Args:
            prompt: Image generation prompt
            size: Image size (1024x1024, 1792x1024, 1024x1792)
            quality: Quality (standard, hd)

        Returns:
            Image data as bytes
        """
        try:
            response = self._openai_client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size=size,
                quality=quality,
                n=1
            )

            # Download image
            image_url = response.data[0].url
            image_data = await self._download_image(image_url)

            # Track usage
            self._track_image_generation(prompt, size, quality)

            return image_data

        except Exception as e:
            logger.error(f"Image generation failed: {e}")
            raise LLMGenerationError(f"Failed to generate image: {e}")
```

### 4. Async Task Queue (NEW)

**Location:** `apps/design-service/src/tasks/visual_tasks.py`

**Purpose:** Handle long-running visual generation asynchronously

```python
from celery import Celery, Task
from src.services.visual_generator import VisualGeneratorService
from src.repositories.design_repository import DesignRepository

celery_app = Celery('design_service')

@celery_app.task(bind=True, max_retries=3)
def generate_floor_plan_task(self: Task, design_id: int):
    """Async task to generate floor plan."""
    try:
        # Get design
        repo = DesignRepository(get_db())
        design = repo.get_design_by_id(design_id)

        # Generate floor plan
        visual_service = VisualGeneratorService()
        floor_plan_url = await visual_service.generate_floor_plan(
            design_id,
            design.specification
        )

        # Update design
        repo.update_design(design_id, floor_plan_url=floor_plan_url)

        logger.info(f"Floor plan generated for design {design_id}")

    except Exception as e:
        logger.error(f"Floor plan generation failed: {e}")
        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))

@celery_app.task(bind=True, max_retries=3)
def generate_rendering_task(self: Task, design_id: int, style: str = "photorealistic"):
    """Async task to generate rendering."""
    # Similar implementation
    pass

@celery_app.task(bind=True, max_retries=2)
def generate_3d_model_task(self: Task, design_id: int, format: str = "step"):
    """Async task to generate 3D model."""
    # Similar implementation
    pass
```

---

## API Changes (Backward Compatible)

### Enhanced Design Response Schema

```python
# src/api/v1/schemas/responses.py

class DesignResponse(BaseModel):
    # ... existing fields ...

    # NEW: Visual output fields (nullable for backward compatibility)
    floor_plan_url: Optional[str] = None
    rendering_url: Optional[str] = None
    model_file_url: Optional[str] = None
    visual_generation_status: Optional[str] = "pending"
    visual_generated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
```

### Enhanced Create Design Endpoint

```python
# src/api/v1/routes/designs.py

@router.post("/api/v1/designs", status_code=201)
async def create_design(
    request: DesignGenerationRequest,
    generate_visuals: bool = Query(
        True,
        description="Auto-generate floor plans and renderings"
    ),  # NEW parameter
    user_id: CurrentUserId,
    design_service: DesignGeneratorService = Depends(...),
    visual_service: VisualGeneratorService = Depends(...)  # NEW dependency
):
    """
    Create a new design with optional visual generation.

    BACKWARD COMPATIBLE: Existing clients can omit generate_visuals parameter.
    """
    # Step 1: Generate design specification (existing code)
    design = await design_service.generate_design(request, user_id)

    # Step 2: Queue visual generation if enabled (NEW)
    if generate_visuals and feature_flags.ENABLE_AUTO_VISUALS:
        try:
            # Queue async tasks
            generate_floor_plan_task.delay(design.id)
            generate_rendering_task.delay(design.id)

            logger.info(f"Queued visual generation for design {design.id}")
        except Exception as e:
            # Don't fail the request if visual generation fails
            logger.warning(f"Failed to queue visual generation: {e}")

    return design
```

### New Endpoints for On-Demand Generation

```python
@router.post("/api/v1/designs/{design_id}/generate-floor-plan")
async def generate_floor_plan(
    design_id: int,
    user_id: CurrentUserId,
    visual_service: VisualGeneratorService = Depends(...)
):
    """Generate floor plan for existing design."""
    # Queue task
    task = generate_floor_plan_task.delay(design_id)

    return {
        "message": "Floor plan generation started",
        "task_id": task.id,
        "status_url": f"/api/v1/tasks/{task.id}"
    }

@router.post("/api/v1/designs/{design_id}/generate-rendering")
async def generate_rendering(
    design_id: int,
    style: str = Query("photorealistic", description="Rendering style"),
    user_id: CurrentUserId,
    visual_service: VisualGeneratorService = Depends(...)
):
    """Generate rendering for existing design."""
    task = generate_rendering_task.delay(design_id, style)

    return {
        "message": "Rendering generation started",
        "task_id": task.id,
        "status_url": f"/api/v1/tasks/{task.id}"
    }

@router.get("/api/v1/tasks/{task_id}")
async def get_task_status(task_id: str):
    """Get status of async task."""
    task = celery_app.AsyncResult(task_id)

    return {
        "task_id": task_id,
        "status": task.state,
        "result": task.result if task.ready() else None
    }
```

---

## Configuration

### New Configuration Class

```python
# packages/common/config/visual.py

class VisualConfig(BaseSettings):
    """Configuration for visual generation services."""

    # Feature Flags
    enable_auto_floor_plans: bool = True
    enable_auto_renderings: bool = True
    enable_3d_models: bool = False  # Start disabled

    # AI Provider Settings
    image_provider: str = "openai"  # or "replicate", "stability"
    image_model: str = "dall-e-3"
    image_quality: str = "hd"  # or "standard"
    image_size_floor_plan: str = "1024x1024"
    image_size_rendering: str = "1792x1024"

    # Storage Settings
    storage_provider: str = "s3"  # or "azure", "gcs"
    storage_bucket: str = "designsynapse-visuals"
    storage_region: str = "us-east-1"
    cdn_url: str = "https://cdn.designsynapse.com"

    # Performance Settings
    max_concurrent_generations: int = 5
    generation_timeout: int = 120  # seconds
    retry_attempts: int = 3

    # Cost Controls
    max_cost_per_design: float = 0.50
    daily_budget: float = 100.00
    enable_caching: bool = True
    cache_ttl: int = 3600  # 1 hour

    class Config:
        env_prefix = "VISUAL_"
```

---

## Error Handling

### Visual Generation Errors

```python
# src/services/visual_generator.py

class VisualGenerationError(Exception):
    """Base exception for visual generation errors."""
    pass

class ImageGenerationError(VisualGenerationError):
    """Raised when image generation fails."""
    pass

class ModelGenerationError(VisualGenerationError):
    """Raised when 3D model generation fails."""
    pass

class StorageError(VisualGenerationError):
    """Raised when storage upload fails."""
    pass

# Error handling in service
async def generate_floor_plan(self, design_id: int, design_spec: Dict) -> str:
    try:
        # Generate image
        image_data = await self.llm_client.generate_image(prompt)
    except LLMGenerationError as e:
        logger.error(f"Image generation failed for design {design_id}: {e}")
        raise ImageGenerationError(f"Failed to generate floor plan: {e}")

    try:
        # Upload to storage
        url = await self.storage.upload(filename, image_data)
    except Exception as e:
        logger.error(f"Storage upload failed for design {design_id}: {e}")
        raise StorageError(f"Failed to upload floor plan: {e}")

    return url
```

---

## Testing Strategy

### Unit Tests

```python
# tests/unit/services/test_visual_generator.py

class TestVisualGeneratorService:
    def test_build_floor_plan_prompt(self, visual_service, sample_design_spec):
        """Test floor plan prompt generation."""
        prompt = visual_service._build_floor_plan_prompt(sample_design_spec)

        assert "floor plan" in prompt.lower()
        assert str(sample_design_spec['building_info']['total_area']) in prompt

    @pytest.mark.asyncio
    async def test_generate_floor_plan_success(
        self, visual_service, mock_llm_client, mock_storage
    ):
        """Test successful floor plan generation."""
        mock_llm_client.generate_image.return_value = b"fake_image_data"
        mock_storage.upload.return_value = "https://cdn.example.com/floor_plan.png"

        url = await visual_service.generate_floor_plan(1, sample_design_spec)

        assert url == "https://cdn.example.com/floor_plan.png"
        mock_llm_client.generate_image.assert_called_once()
        mock_storage.upload.assert_called_once()
```

### Integration Tests

```python
# tests/integration/api/v1/test_visual_generation.py

class TestVisualGenerationEndpoints:
    def test_create_design_with_visuals(self, client, auth_headers):
        """Test design creation with visual generation enabled."""
        response = client.post(
            "/api/v1/designs?generate_visuals=true",
            json={
                "name": "Test Design",
                "description": "3-bedroom house",
                "building_type": "residential",
                "requirements": {}
            },
            headers=auth_headers
        )

        assert response.status_code == 201
        data = response.json()
        assert "floor_plan_url" in data
        assert "rendering_url" in data
        assert data["visual_generation_status"] == "processing"

    def test_create_design_without_visuals(self, client, auth_headers):
        """Test design creation with visual generation disabled."""
        response = client.post(
            "/api/v1/designs?generate_visuals=false",
            json={...},
            headers=auth_headers
        )

        assert response.status_code == 201
        data = response.json()
        assert data["floor_plan_url"] is None
        assert data["rendering_url"] is None
```

---

## Deployment Strategy

### Phase 1: Infrastructure Setup
1. Deploy Celery workers
2. Configure Redis for task queue
3. Set up S3 bucket and CDN
4. Deploy database migration

### Phase 2: Feature Flag Rollout
1. Deploy code with features disabled
2. Enable for internal testing (10% traffic)
3. Monitor performance and costs
4. Enable for beta users (50% traffic)
5. Full rollout (100% traffic)

### Phase 3: Monitoring
1. Track generation success rates
2. Monitor API costs
3. Track generation times
4. Monitor storage usage

---

## Performance Considerations

### Optimization Strategies

1. **Caching:** Cache similar prompts for 1 hour
2. **Batch Processing:** Group multiple generations
3. **CDN:** Serve images via CDN
4. **Compression:** Compress images without quality loss
5. **Lazy Loading:** Generate on-demand if auto-gen disabled

### Expected Performance

- Floor plan generation: 15-30 seconds
- Rendering generation: 20-45 seconds
- 3D model generation: 30-60 seconds
- Total (parallel): 45-60 seconds

---

## Cost Analysis

### Per-Design Costs

| Component | Cost | Provider |
|-----------|------|----------|
| Floor Plan (DALL-E 3 HD) | $0.080 | OpenAI |
| Rendering (DALL-E 3 HD) | $0.080 | OpenAI |
| 3D Model (compute) | $0.010 | Internal |
| Storage (S3) | $0.005 | AWS |
| CDN (bandwidth) | $0.010 | CloudFront |
| **Total** | **$0.185** | |

### Monthly Projections

- 1,000 designs/month: $185
- 10,000 designs/month: $1,850
- 100,000 designs/month: $18,500

---

## Security Considerations

1. **Signed URLs:** All visual URLs expire after 24 hours
2. **Access Control:** Verify user has access to design before serving visuals
3. **Rate Limiting:** Limit visual generation requests per user
4. **Input Validation:** Sanitize all prompts before sending to AI
5. **Storage Security:** Encrypt files at rest in S3

---

## Next Steps

1. Review and approve design
2. Create implementation tasks
3. Set up infrastructure (Celery, Redis, S3)
4. Begin implementation

---

**Status:** Awaiting approval
**Estimated Implementation:** 4-5 weeks
**Risk Level:** Low (non-breaking changes)
