# Design Document: Architectural Service

## Overview

The Architectural Service is a FastAPI-based microservice that provides comprehensive architectural design management, building code compliance checking, structural analysis, and material specification capabilities. It follows a layered architecture with clear separation between API, business logic, data access, and external service integration layers.

The service uses async/await patterns throughout for optimal performance, SQLAlchemy with async support for database operations, and Pydantic v2 for request/response validation. It integrates with existing DesignSynapse services (Design, Knowledge, Project, Vendor) through HTTP clients with circuit breakers and retry logic.

## Architecture

### High-Level Architecture

```mermaid
graph TB
    Client[Client Applications]
    API[FastAPI Application]
    Auth[Auth Middleware]
    Services[Service Layer]
    Repos[Repository Layer]
    DB[(TiDB/MySQL)]

    ExtDesign[Design Service]
    ExtKnowledge[Knowledge Service]
    ExtProject[Project Service]
    ExtVendor[Vendor Service]

    Client --> API
    API --> Auth
    Auth --> Services
    Services --> Repos
    Repos --> DB

    Services --> ExtDesign
    Services --> ExtKnowledge
    Services --> ExtProject
    Services --> ExtVendor
```

### Layered Architecture

1. **API Layer** (`src/api/v1/`): FastAPI routes, request/response schemas, dependencies
2. **Service Layer** (`src/services/`): Business logic, orchestration, external service integration
3. **Repository Layer** (`src/repositories/`): Data access, query building, transaction management
4. **Model Layer** (`src/models/`): SQLAlchemy ORM models, database schema
5. **Core Layer** (`src/core/`): Configuration, database setup, error handling
6. **Infrastructure Layer** (`src/infrastructure/`): External clients, utilities, helpers

### Technology Stack

- **Framework**: FastAPI 0.104+
- **ORM**: SQLAlchemy 2.0+ (async)
- **Validation**: Pydantic v2
- **Database**: TiDB/MySQL 8.0+
- **Testing**: pytest, pytest-asyncio, Hypothesis
- **Migrations**: Alembic
- **HTTP Client**: httpx (async)
- **Caching**: Redis (via common packages)

## Components and Interfaces

### 1. API Endpoints

#### Design Document Endpoints

```python
# POST /api/v1/designs
# Create a new architectural design document
Request: CreateDesignRequest
  - project_id: UUID
  - name: str
  - description: Optional[str]
  - building_type: BuildingType (enum)
  - location: LocationData
  - metadata: Dict[str, Any]

Response: DesignResponse
  - id: UUID
  - version: str (e.g., "1.0")
  - status: DesignStatus
  - created_at: datetime
  - updated_at: datetime

# GET /api/v1/designs/{design_id}
# Retrieve a design document
Response: DesignDetailResponse (includes all design data)

# PUT /api/v1/designs/{design_id}
# Update a design document (creates new version)
Request: UpdateDesignRequest
Response: DesignResponse (with incremented version)

# GET /api/v1/designs/{design_id}/versions
# List all versions of a design
Response: List[DesignVersionResponse]

# GET /api/v1/designs/{design_id}/versions/{version}
# Retrieve a specific version
Response: DesignDetailResponse

# DELETE /api/v1/designs/{design_id}
# Soft delete a design document
Response: 204 No Content
```

#### Drawing Endpoints

```python
# POST /api/v1/designs/{design_id}/drawings
# Upload architectural drawings
Request: Multipart form with file and metadata
  - file: UploadFile
  - drawing_type: DrawingType (floor_plan, elevation, section, etc.)
  - scale: str
  - sheet_number: str
  - metadata: JSON

Response: DrawingResponse
  - id: UUID
  - design_id: UUID
  - file_url: str
  - drawing_type: DrawingType
  - created_at: datetime

# GET /api/v1/designs/{design_id}/drawings
# List all drawings for a design
Response: List[DrawingResponse]

# GET /api/v1/drawings/{drawing_id}
# Retrieve a specific drawing
Response: DrawingDetailResponse

# DELETE /api/v1/drawings/{drawing_id}
# Delete a drawing
Response: 204 No Content
```

#### Compliance Endpoints

```python
# POST /api/v1/designs/{design_id}/compliance-checks
# Request a building code compliance check
Request: ComplianceCheckRequest
  - code_standards: List[str] (e.g., ["IBC-2021", "ADA"])
  - jurisdiction: Optional[str]
  - check_types: List[ComplianceCheckType]

Response: ComplianceCheckResponse
  - id: UUID
  - status: CheckStatus (pending, in_progress, completed, failed)
  - started_at: datetime

# GET /api/v1/compliance-checks/{check_id}
# Get compliance check results
Response: ComplianceCheckDetailResponse
  - id: UUID
  - status: CheckStatus
  - violations: List[ViolationDetail]
  - warnings: List[WarningDetail]
  - passed: bool
  - report_url: Optional[str]
  - completed_at: Optional[datetime]

# GET /api/v1/designs/{design_id}/compliance-checks
# List all compliance checks for a design
Response: List[ComplianceCheckResponse]
```

#### Structural Analysis Endpoints

```python
# POST /api/v1/designs/{design_id}/structural-analysis
# Request structural analysis
Request: StructuralAnalysisRequest
  - structural_system: StructuralSystem
  - load_parameters: LoadParameters
  - analysis_type: AnalysisType

Response: StructuralAnalysisResponse
  - id: UUID
  - status: AnalysisStatus
  - started_at: datetime

# GET /api/v1/structural-analysis/{analysis_id}
# Get structural analysis results
Response: StructuralAnalysisDetailResponse
  - id: UUID
  - status: AnalysisStatus
  - loads: LoadCalculations
  - issues: List[StructuralIssue]
  - recommendations: List[str]
  - report_url: Optional[str]
```

#### Material Specification Endpoints

```python
# POST /api/v1/designs/{design_id}/materials
# Add material specification
Request: MaterialSpecificationRequest
  - category: MaterialCategory
  - type: str
  - properties: MaterialProperties
  - design_elements: List[UUID]

Response: MaterialSpecificationResponse
  - id: UUID
  - vendor_info: Optional[VendorInfo]
  - cost_estimate: Optional[Decimal]

# GET /api/v1/designs/{design_id}/materials
# List all materials for a design
Response: List[MaterialSpecificationResponse]

# GET /api/v1/materials/search
# Search for materials
Query: MaterialSearchQuery
Response: List[MaterialSpecificationResponse]
```

#### Space Planning Endpoints

```python
# POST /api/v1/designs/{design_id}/space-planning
# Request space planning analysis
Request: SpacePlanningRequest
  - requirements: List[SpaceRequirement]
  - constraints: PlanningConstraints
  - optimization_goals: List[OptimizationGoal]

Response: SpacePlanningResponse
  - id: UUID
  - status: PlanningStatus
  - started_at: datetime

# GET /api/v1/space-planning/{planning_id}
# Get space planning results
Response: SpacePlanningDetailResponse
  - id: UUID
  - recommendations: List[LayoutRecommendation]
  - metrics: SpaceMetrics
  - space_program: SpaceProgramDocument
```

#### Accessibility Endpoints

```python
# POST /api/v1/designs/{design_id}/accessibility-checks
# Request accessibility compliance check
Request: AccessibilityCheckRequest
  - standards: List[str] (e.g., ["ADA", "ANSI-A117.1"])
  - check_areas: List[DesignArea]

Response: AccessibilityCheckResponse
  - id: UUID
  - status: CheckStatus
  - started_at: datetime

# GET /api/v1/accessibility-checks/{check_id}
# Get accessibility check results
Response: AccessibilityCheckDetailResponse
  - id: UUID
  - violations: List[AccessibilityViolation]
  - accessible_routes: List[RouteValidation]
  - passed: bool
```

#### Energy Analysis Endpoints

```python
# POST /api/v1/designs/{design_id}/energy-analysis
# Request energy efficiency analysis
Request: EnergyAnalysisRequest
  - standards: List[str] (e.g., ["ASHRAE-90.1", "LEED"])
  - climate_zone: str
  - building_parameters: BuildingParameters

Response: EnergyAnalysisResponse
  - id: UUID
  - status: AnalysisStatus
  - started_at: datetime

# GET /api/v1/energy-analysis/{analysis_id}
# Get energy analysis results
Response: EnergyAnalysisDetailResponse
  - id: UUID
  - envelope_performance: EnvelopeMetrics
  - energy_consumption: EnergyEstimate
  - recommendations: List[EfficiencyRecommendation]
  - certificate_url: Optional[str]
```

#### Collaboration Endpoints

```python
# POST /api/v1/designs/{design_id}/collaboration/join
# Join a collaboration session
Response: CollaborationSessionResponse
  - session_id: UUID
  - active_users: List[UserInfo]
  - websocket_url: str

# WebSocket /api/v1/collaboration/{session_id}/ws
# Real-time collaboration WebSocket
Messages:
  - design_update: Design change events
  - cursor_move: User cursor position
  - user_join: User joined session
  - user_leave: User left session
```

### 2. Service Layer Components

#### DesignService

Manages architectural design documents and versions.

```python
class DesignService:
    async def create_design(
        self,
        project_id: UUID,
        user_id: UUID,
        data: CreateDesignRequest
    ) -> Design:
        """Create a new design document with version 1.0"""

    async def update_design(
        self,
        design_id: UUID,
        user_id: UUID,
        data: UpdateDesignRequest
    ) -> Design:
        """Update design and create new version"""

    async def get_design(
        self,
        design_id: UUID,
        version: Optional[str] = None
    ) -> Design:
        """Retrieve design by ID and optional version"""

    async def list_versions(
        self,
        design_id: UUID
    ) -> List[DesignVersion]:
        """List all versions of a design"""

    async def soft_delete(
        self,
        design_id: UUID,
        user_id: UUID
    ) -> None:
        """Soft delete a design document"""
```

#### ComplianceService

Handles building code compliance checking.

```python
class ComplianceService:
    async def check_compliance(
        self,
        design_id: UUID,
        standards: List[str],
        jurisdiction: Optional[str]
    ) -> ComplianceCheck:
        """Initiate compliance check against building codes"""

    async def get_check_results(
        self,
        check_id: UUID
    ) -> ComplianceCheckDetail:
        """Retrieve compliance check results"""

    async def validate_against_code(
        self,
        design: Design,
        code_data: Dict[str, Any]
    ) -> List[Violation]:
        """Validate design against specific code requirements"""

    async def generate_compliance_report(
        self,
        check_id: UUID
    ) -> str:
        """Generate PDF compliance report"""
```

#### StructuralAnalysisService

Performs structural analysis calculations.

```python
class StructuralAnalysisService:
    async def analyze_structure(
        self,
        design_id: UUID,
        parameters: StructuralAnalysisRequest
    ) -> StructuralAnalysis:
        """Perform structural analysis"""

    async def calculate_loads(
        self,
        design: Design,
        load_params: LoadParameters
    ) -> LoadCalculations:
        """Calculate dead, live, wind, and seismic loads"""

    async def identify_issues(
        self,
        analysis: StructuralAnalysis
    ) -> List[StructuralIssue]:
        """Identify structural integrity issues"""
```

#### MaterialService

Manages material specifications and vendor integration.

```python
class MaterialService:
    async def add_material(
        self,
        design_id: UUID,
        data: MaterialSpecificationRequest
    ) -> MaterialSpecification:
        """Add material specification to design"""

    async def search_materials(
        self,
        query: MaterialSearchQuery
    ) -> List[MaterialSpecification]:
        """Search for materials with vendor info"""

    async def get_vendor_info(
        self,
        material_id: UUID
    ) -> VendorInfo:
        """Retrieve vendor information from Vendor Service"""

    async def update_material_pricing(
        self,
        material_id: UUID
    ) -> MaterialSpecification:
        """Update pricing from Vendor Service"""
```

#### SpacePlanningService

Provides space planning and optimization.

```python
class SpacePlanningService:
    async def plan_spaces(
        self,
        design_id: UUID,
        requirements: List[SpaceRequirement]
    ) -> SpacePlanning:
        """Generate space planning recommendations"""

    async def calculate_metrics(
        self,
        design: Design
    ) -> SpaceMetrics:
        """Calculate space utilization metrics"""

    async def optimize_layout(
        self,
        design: Design,
        goals: List[OptimizationGoal]
    ) -> List[LayoutRecommendation]:
        """Optimize layout based on goals"""

    async def validate_circulation(
        self,
        design: Design
    ) -> CirculationValidation:
        """Validate circulation paths and egress"""
```

#### AccessibilityService

Handles accessibility compliance checking.

```python
class AccessibilityService:
    async def check_accessibility(
        self,
        design_id: UUID,
        standards: List[str]
    ) -> AccessibilityCheck:
        """Check accessibility compliance"""

    async def validate_routes(
        self,
        design: Design
    ) -> List[RouteValidation]:
        """Validate accessible routes"""

    async def check_clearances(
        self,
        design: Design
    ) -> List[ClearanceViolation]:
        """Check door widths, corridors, clearances"""
```

#### EnergyAnalysisService

Performs energy efficiency analysis.

```python
class EnergyAnalysisService:
    async def analyze_energy(
        self,
        design_id: UUID,
        parameters: EnergyAnalysisRequest
    ) -> EnergyAnalysis:
        """Perform energy efficiency analysis"""

    async def calculate_envelope_performance(
        self,
        design: Design
    ) -> EnvelopeMetrics:
        """Calculate R-values, U-factors"""

    async def estimate_consumption(
        self,
        design: Design,
        climate_zone: str
    ) -> EnergyEstimate:
        """Estimate annual energy consumption"""
```

#### CollaborationService

Manages real-time collaboration sessions.

```python
class CollaborationService:
    async def create_session(
        self,
        design_id: UUID,
        user_id: UUID
    ) -> CollaborationSession:
        """Create or join collaboration session"""

    async def broadcast_change(
        self,
        session_id: UUID,
        change: DesignChange
    ) -> None:
        """Broadcast design change to all participants"""

    async def resolve_conflict(
        self,
        session_id: UUID,
        conflicts: List[DesignConflict]
    ) -> Design:
        """Resolve concurrent edit conflicts"""

    async def handle_disconnect(
        self,
        session_id: UUID,
        user_id: UUID
    ) -> None:
        """Handle user disconnection"""
```

### 3. External Service Integration

#### DesignServiceClient

Integrates with Design Service for visual rendering.

```python
class DesignServiceClient:
    async def request_rendering(
        self,
        design_id: UUID,
        render_type: RenderType,
        parameters: RenderParameters
    ) -> RenderJob:
        """Request visual rendering from Design Service"""

    async def get_render_status(
        self,
        job_id: UUID
    ) -> RenderStatus:
        """Check rendering job status"""

    async def retrieve_outputs(
        self,
        job_id: UUID
    ) -> List[VisualOutput]:
        """Retrieve completed visual outputs"""
```

#### KnowledgeServiceClient

Integrates with Knowledge Service for building codes.

```python
class KnowledgeServiceClient:
    async def search_codes(
        self,
        query: str,
        filters: CodeFilters
    ) -> List[CodeSection]:
        """Search for building code sections"""

    async def get_applicable_codes(
        self,
        location: str,
        building_type: str
    ) -> List[CodeStandard]:
        """Get applicable codes for location and type"""

    async def get_code_section(
        self,
        code_id: str,
        section: str
    ) -> CodeSectionDetail:
        """Retrieve specific code section"""
```

#### ProjectServiceClient

Integrates with Project Service for project management.

```python
class ProjectServiceClient:
    async def validate_project(
        self,
        project_id: UUID,
        user_id: UUID
    ) -> ProjectValidation:
        """Validate project exists and user has access"""

    async def log_activity(
        self,
        project_id: UUID,
        activity: ActivityLog
    ) -> None:
        """Log design activity to project timeline"""

    async def get_project_status(
        self,
        project_id: UUID
    ) -> ProjectStatus:
        """Get current project status"""
```

#### VendorServiceClient

Integrates with Vendor Service for material information.

```python
class VendorServiceClient:
    async def search_materials(
        self,
        query: MaterialQuery
    ) -> List[VendorMaterial]:
        """Search for materials in vendor catalog"""

    async def get_supplier_info(
        self,
        material_id: UUID
    ) -> SupplierInfo:
        """Get supplier information and pricing"""

    async def check_availability(
        self,
        material_id: UUID,
        quantity: Decimal
    ) -> AvailabilityInfo:
        """Check material availability"""
```

## Data Models

### Core Models

```python
class Design(Base):
    """Main architectural design document"""
    __tablename__ = "designs"

    id: UUID = Column(UUID(as_uuid=True), primary_key=True)
    project_id: UUID = Column(UUID(as_uuid=True), nullable=False, index=True)
    name: str = Column(String(255), nullable=False)
    description: Optional[str] = Column(Text)
    building_type: str = Column(String(50), nullable=False)
    location_data: dict = Column(JSON, nullable=False)

    # Version control
    current_version: str = Column(String(20), nullable=False, default="1.0")
    version_number: int = Column(Integer, nullable=False, default=1)

    # Status
    status: str = Column(String(50), nullable=False, default="draft")
    is_deleted: bool = Column(Boolean, default=False, index=True)

    # Metadata
    metadata: dict = Column(JSON, default={})
    created_by: UUID = Column(UUID(as_uuid=True), nullable=False)
    created_at: datetime = Column(DateTime, nullable=False)
    updated_at: datetime = Column(DateTime, nullable=False)
    deleted_at: Optional[datetime] = Column(DateTime)

    # Relationships
    versions: List["DesignVersion"] = relationship(back_populates="design")
    drawings: List["Drawing"] = relationship(back_populates="design")
    materials: List["MaterialSpecification"] = relationship(back_populates="design")
    compliance_checks: List["ComplianceCheck"] = relationship(back_populates="design")
    structural_analyses: List["StructuralAnalysis"] = relationship(back_populates="design")

class DesignVersion(Base):
    """Version history for designs"""
    __tablename__ = "design_versions"

    id: UUID = Column(UUID(as_uuid=True), primary_key=True)
    design_id: UUID = Column(UUID(as_uuid=True), ForeignKey("designs.id"), nullable=False)
    version: str = Column(String(20), nullable=False)
    version_number: int = Column(Integer, nullable=False)

    # Snapshot of design data at this version
    design_data: dict = Column(JSON, nullable=False)
    change_summary: Optional[str] = Column(Text)

    created_by: UUID = Column(UUID(as_uuid=True), nullable=False)
    created_at: datetime = Column(DateTime, nullable=False)

    design: "Design" = relationship(back_populates="versions")

    __table_args__ = (
        Index("idx_design_version", "design_id", "version"),
        UniqueConstraint("design_id", "version_number"),
    )

class Drawing(Base):
    """Architectural drawings (floor plans, elevations, etc.)"""
    __tablename__ = "drawings"

    id: UUID = Column(UUID(as_uuid=True), primary_key=True)
    design_id: UUID = Column(UUID(as_uuid=True), ForeignKey("designs.id"), nullable=False)
    design_version: str = Column(String(20), nullable=False)

    drawing_type: str = Column(String(50), nullable=False)
    file_url: str = Column(String(500), nullable=False)
    file_size: int = Column(BigInteger, nullable=False)
    mime_type: str = Column(String(100), nullable=False)

    scale: Optional[str] = Column(String(50))
    sheet_number: Optional[str] = Column(String(50))
    metadata: dict = Column(JSON, default={})

    created_by: UUID = Column(UUID(as_uuid=True), nullable=False)
    created_at: datetime = Column(DateTime, nullable=False)

    design: "Design" = relationship(back_populates="drawings")

    __table_args__ = (
        Index("idx_design_drawings", "design_id", "drawing_type"),
    )

class ComplianceCheck(Base):
    """Building code compliance check results"""
    __tablename__ = "compliance_checks"

    id: UUID = Column(UUID(as_uuid=True), primary_key=True)
    design_id: UUID = Column(UUID(as_uuid=True), ForeignKey("designs.id"), nullable=False)
    design_version: str = Column(String(20), nullable=False)

    code_standards: list = Column(JSON, nullable=False)
    jurisdiction: Optional[str] = Column(String(100))

    status: str = Column(String(50), nullable=False, default="pending")
    passed: Optional[bool] = Column(Boolean)

    violations: list = Column(JSON, default=[])
    warnings: list = Column(JSON, default=[])
    recommendations: list = Column(JSON, default=[])

    report_url: Optional[str] = Column(String(500))

    started_at: datetime = Column(DateTime, nullable=False)
    completed_at: Optional[datetime] = Column(DateTime)

    design: "Design" = relationship(back_populates="compliance_checks")

    __table_args__ = (
        Index("idx_design_compliance", "design_id", "status"),
    )

class StructuralAnalysis(Base):
    """Structural analysis results"""
    __tablename__ = "structural_analyses"

    id: UUID = Column(UUID(as_uuid=True), primary_key=True)
    design_id: UUID = Column(UUID(as_uuid=True), ForeignKey("designs.id"), nullable=False)
    design_version: str = Column(String(20), nullable=False)

    structural_system: str = Column(String(100), nullable=False)
    analysis_type: str = Column(String(50), nullable=False)

    status: str = Column(String(50), nullable=False, default="pending")

    load_calculations: dict = Column(JSON, default={})
    issues: list = Column(JSON, default=[])
    recommendations: list = Column(JSON, default=[])

    report_url: Optional[str] = Column(String(500))

    started_at: datetime = Column(DateTime, nullable=False)
    completed_at: Optional[datetime] = Column(DateTime)

    design: "Design" = relationship(back_populates="structural_analyses")

class MaterialSpecification(Base):
    """Material specifications for design"""
    __tablename__ = "material_specifications"

    id: UUID = Column(UUID(as_uuid=True), primary_key=True)
    design_id: UUID = Column(UUID(as_uuid=True), ForeignKey("designs.id"), nullable=False)

    category: str = Column(String(100), nullable=False)
    material_type: str = Column(String(100), nullable=False)
    properties: dict = Column(JSON, nullable=False)

    # Vendor integration
    vendor_material_id: Optional[UUID] = Column(UUID(as_uuid=True))
    vendor_info: Optional[dict] = Column(JSON)
    cost_estimate: Optional[Decimal] = Column(Numeric(12, 2))

    # Design element associations
    design_elements: list = Column(JSON, default=[])

    created_at: datetime = Column(DateTime, nullable=False)
    updated_at: datetime = Column(DateTime, nullable=False)

    design: "Design" = relationship(back_populates="materials")

    __table_args__ = (
        Index("idx_design_materials", "design_id", "category"),
    )

class SpacePlanning(Base):
    """Space planning analysis results"""
    __tablename__ = "space_planning"

    id: UUID = Column(UUID(as_uuid=True), primary_key=True)
    design_id: UUID = Column(UUID(as_uuid=True), ForeignKey("designs.id"), nullable=False)

    status: str = Column(String(50), nullable=False, default="pending")

    requirements: list = Column(JSON, nullable=False)
    recommendations: list = Column(JSON, default=[])
    metrics: dict = Column(JSON, default={})
    space_program: dict = Column(JSON, default={})

    started_at: datetime = Column(DateTime, nullable=False)
    completed_at: Optional[datetime] = Column(DateTime)

class AccessibilityCheck(Base):
    """Accessibility compliance check results"""
    __tablename__ = "accessibility_checks"

    id: UUID = Column(UUID(as_uuid=True), primary_key=True)
    design_id: UUID = Column(UUID(as_uuid=True), ForeignKey("designs.id"), nullable=False)
    design_version: str = Column(String(20), nullable=False)

    standards: list = Column(JSON, nullable=False)
    status: str = Column(String(50), nullable=False, default="pending")
    passed: Optional[bool] = Column(Boolean)

    violations: list = Column(JSON, default=[])
    accessible_routes: list = Column(JSON, default=[])

    started_at: datetime = Column(DateTime, nullable=False)
    completed_at: Optional[datetime] = Column(DateTime)

class EnergyAnalysis(Base):
    """Energy efficiency analysis results"""
    __tablename__ = "energy_analyses"

    id: UUID = Column(UUID(as_uuid=True), primary_key=True)
    design_id: UUID = Column(UUID(as_uuid=True), ForeignKey("designs.id"), nullable=False)
    design_version: str = Column(String(20), nullable=False)

    standards: list = Column(JSON, nullable=False)
    climate_zone: str = Column(String(50), nullable=False)

    status: str = Column(String(50), nullable=False, default="pending")

    envelope_performance: dict = Column(JSON, default={})
    energy_consumption: dict = Column(JSON, default={})
    recommendations: list = Column(JSON, default=[])

    certificate_url: Optional[str] = Column(String(500))

    started_at: datetime = Column(DateTime, nullable=False)
    completed_at: Optional[datetime] = Column(DateTime)

class CollaborationSession(Base):
    """Real-time collaboration sessions"""
    __tablename__ = "collaboration_sessions"

    id: UUID = Column(UUID(as_uuid=True), primary_key=True)
    design_id: UUID = Column(UUID(as_uuid=True), ForeignKey("designs.id"), nullable=False)

    active_users: list = Column(JSON, default=[])
    is_active: bool = Column(Boolean, default=True)

    created_at: datetime = Column(DateTime, nullable=False)
    ended_at: Optional[datetime] = Column(DateTime)

    __table_args__ = (
        Index("idx_active_sessions", "design_id", "is_active"),
    )
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*


### Property Reflection

After analyzing all acceptance criteria, I've identified several areas where properties can be consolidated:

**Consolidation Opportunities:**
1. Properties about "result persistence and association with design version" (2.6, 3.3) can be combined into one comprehensive property
2. Properties about "completeness of analysis reports" (2.3, 6.6, 7.3) share similar structure and can use a common pattern
3. Properties about "supporting multiple standards/types" (2.4, 3.5, 4.6, 7.4, 8.2) can be tested with a single parameterized property
4. Properties about "metadata/audit trail completeness" (1.7, 3.6, 9.5, 11.5) share the same invariant pattern
5. Properties about "validation and error responses" (12.3, 12.4) can be combined into comprehensive error handling property

**Redundancy Elimination:**
- Property 1.2 (file association) is subsumed by Property 1.7 (metadata completeness) since associations are part of metadata
- Property 8.5 (status tracking) is redundant with general status tracking that applies to all async operations
- Properties 12.7 and 12.8 are specific examples, not general properties - they should be unit tests

**Final Property Set:**
After reflection, we have approximately 45 unique, non-redundant properties that provide comprehensive coverage.

### Correctness Properties

Property 1: Design initialization consistency
*For any* new design document creation request, the created design should have a unique identifier, version "1.0", version_number 1, and all required metadata fields populated.
**Validates: Requirements 1.1, 1.7**

Property 2: Version increment consistency
*For any* design document update, the new version should have version_number incremented by 1, and the version string should reflect the new number.
**Validates: Requirements 1.3**

Property 3: Version history preservation
*For any* design document with N updates, there should exist exactly N+1 versions (original plus N updates), and all versions should be retrievable.
**Validates: Requirements 1.3**

Property 4: Version retrieval round-trip
*For any* design document and any valid version number, retrieving that version should return design data that matches the snapshot stored when that version was created.
**Validates: Requirements 1.4**

Property 5: Drawing type support
*For any* valid drawing type (floor_plan, elevation, section, site_plan, detail), creating a drawing of that type should succeed and be retrievable.
**Validates: Requirements 1.5**

Property 6: Soft delete preservation
*For any* design document, after soft deletion, the document should be marked as deleted (is_deleted=True) but still retrievable with all data intact.
**Validates: Requirements 1.6**

Property 7: Compliance check initiation
*For any* design document and valid compliance check request, a compliance check should be created with status "pending" and associated with the current design version.
**Validates: Requirements 2.1**

Property 8: Violation reference completeness
*For any* completed compliance check with violations, every violation should include a non-empty code section reference.
**Validates: Requirements 2.2**

Property 9: Compliance report completeness
*For any* completed compliance check, the result should include violations list, warnings list, and recommendations list (even if empty).
**Validates: Requirements 2.3**

Property 10: Analysis result persistence
*For any* completed analysis (compliance, structural, accessibility, energy), the result should be persisted in the database and associated with the specific design version that was analyzed.
**Validates: Requirements 2.6, 3.3**

Property 11: Compliance success marking
*For any* compliance check where all validations pass (violations list is empty), the check should be marked as passed=True and status="completed".
**Validates: Requirements 2.7**

Property 12: Structural load calculation completeness
*For any* structural analysis request, the completed analysis should include calculations for dead loads, live loads, wind loads, and seismic loads.
**Validates: Requirements 3.2**

Property 13: Structural issue flagging
*For any* structural analysis that identifies issues, each issue should reference specific design elements and include recommendations.
**Validates: Requirements 3.4**

Property 14: Audit trail completeness
*For any* completed structural analysis, the result should include a complete audit trail with all calculations, assumptions, and intermediate results.
**Validates: Requirements 3.6**

Property 15: Material validation
*For any* material specification creation request, if required properties (type, grade, dimensions, finish) are missing, the request should be rejected with validation errors.
**Validates: Requirements 4.1**

Property 16: Material search result completeness
*For any* material search query that returns results, each result should include availability data and cost data (or explicit null if unavailable).
**Validates: Requirements 4.3**

Property 17: Material-element relationship preservation
*For any* material specification associated with design elements, the relationship should be bidirectional: the material should reference the elements, and querying by element should return the material.
**Validates: Requirements 4.4**

Property 18: Material change tracking
*For any* material specification update, a new entry should be added to the change history with timestamp, user, and changed fields.
**Validates: Requirements 4.5**

Property 19: Space planning metric completeness
*For any* completed space planning analysis, the metrics should include area efficiency, circulation ratios, and density calculations.
**Validates: Requirements 5.2**

Property 20: Space requirement validation
*For any* space plan, all room types should meet or exceed minimum space requirements defined in applicable building codes.
**Validates: Requirements 5.4**

Property 21: Circulation path validation
*For any* space plan, there should exist valid circulation paths from all spaces to exits, and emergency egress routes should meet code requirements.
**Validates: Requirements 5.5**

Property 22: Space program document completeness
*For any* completed space planning analysis, the space program document should include areas, functional relationships, and requirements for all spaces.
**Validates: Requirements 5.6**

Property 23: Accessibility check completeness
*For any* accessibility check, the analysis should validate door widths, corridor widths, ramp slopes, handrail requirements, and clearances.
**Validates: Requirements 6.2**

Property 24: Accessibility violation location specificity
*For any* accessibility check with violations, each violation should include specific location information (coordinates, room ID, or element ID) and remediation guidance.
**Validates: Requirements 6.3**

Property 25: Accessible route validation
*For any* accessibility check, the analysis should validate that accessible routes exist from all entrances to all public and common use areas.
**Validates: Requirements 6.4**

Property 26: Restroom accessibility validation
*For any* design with restroom spaces, accessibility checks should verify fixture counts, clearances, and grab bar locations meet ADA requirements.
**Validates: Requirements 6.5**

Property 27: Energy envelope calculation completeness
*For any* energy analysis, the envelope performance calculations should include R-values and U-factors for all building envelope components.
**Validates: Requirements 7.1**

Property 28: Energy consumption estimation
*For any* energy analysis, the result should include estimated annual energy consumption based on building type, location, and design parameters.
**Validates: Requirements 7.2**

Property 29: Energy cost calculation completeness
*For any* energy analysis, the result should include estimated annual energy costs and potential savings from recommended improvements.
**Validates: Requirements 7.5**

Property 30: Energy certificate generation
*For any* energy analysis where the design meets all efficiency targets, a performance certificate should be generated and accessible via URL.
**Validates: Requirements 7.6**

Property 31: Rendering request parameter completeness
*For any* rendering request to Design Service, the request should include design_id, render_type, and all required parameters for that render type.
**Validates: Requirements 8.1**

Property 32: Rendering output association
*For any* completed rendering job, the visual outputs should be retrieved and associated with the design version that was rendered.
**Validates: Requirements 8.3**

Property 33: Rendering retry with exponential backoff
*For any* rendering request that fails, the service should retry with exponentially increasing delays (e.g., 1s, 2s, 4s, 8s) up to a maximum number of attempts.
**Validates: Requirements 8.4**

Property 34: Rendering cache reuse
*For any* design document, if a rendering is requested with identical parameters to a previous request and the design has not changed, the cached output should be reused.
**Validates: Requirements 8.6**

Property 35: Code search integration
*For any* building code search query, the service should query Knowledge Service and return code sections with complete metadata.
**Validates: Requirements 9.1**

Property 36: Code citation completeness
*For any* code reference used in compliance checks or documentation, the citation should include code standard name, section number, and edition date.
**Validates: Requirements 9.5**

Property 37: Project association validation
*For any* design document creation, the service should validate that the project exists and the user has appropriate permissions before creating the design.
**Validates: Requirements 10.1, 10.2**

Property 38: Project summary calculation
*For any* project with associated designs, the project summary should include accurate counts of designs, compliance status distribution, and completion percentage.
**Validates: Requirements 10.4**

Property 39: Activity logging
*For any* design operation (create, update, delete, analyze), an activity log entry should be created and sent to Project Service.
**Validates: Requirements 10.5**

Property 40: Cascading archive
*For any* project that is archived, all associated design documents should be marked as archived within the same transaction.
**Validates: Requirements 10.6**

Property 41: Collaboration session establishment
*For any* user opening a design document, a collaboration session should be created (or existing session joined) and other active users should be notified.
**Validates: Requirements 11.1**

Property 42: Conflict resolution consistency
*For any* collaboration session with concurrent edits to the same element, the last write should win and all participants should converge to the same state.
**Validates: Requirements 11.3**

Property 43: Collaboration history completeness
*For any* collaboration session, the change history should include all changes with timestamps, user attribution, and change details.
**Validates: Requirements 11.5**

Property 44: User disconnect handling
*For any* user disconnecting from a collaboration session, they should be removed from active_users list and remaining participants should be notified.
**Validates: Requirements 11.6**

Property 45: Error response format
*For any* API request that results in an error, the response should include appropriate HTTP status code, error message, and error details.
**Validates: Requirements 12.3**

Property 46: Input validation error details
*For any* API request with invalid input, the validation error response should include field-level details indicating which fields failed validation and why.
**Validates: Requirements 12.4**

Property 47: Response header completeness
*For any* API response, the headers should include appropriate cache-control, rate-limit information, and CORS headers.
**Validates: Requirements 12.5**

Property 48: Pagination consistency
*For any* list endpoint, pagination should work correctly: page size should be respected, cursors should be stable, and iterating through all pages should return all items exactly once.
**Validates: Requirements 12.6**

Property 49: Transaction atomicity
*For any* multi-step database operation, either all steps should succeed and be committed, or all steps should fail and be rolled back.
**Validates: Requirements 13.3**

Property 50: Transaction rollback completeness
*For any* failed transaction, the database state should be identical to the state before the transaction began (no partial changes).
**Validates: Requirements 13.4**

Property 51: Optimistic locking conflict detection
*For any* concurrent update to the same design document, if version numbers don't match, the update should fail with a conflict error.
**Validates: Requirements 13.5**

## Error Handling

### Error Categories

1. **Validation Errors** (400 Bad Request)
   - Invalid input data
   - Missing required fields
   - Type mismatches
   - Business rule violations

2. **Authentication Errors** (401 Unauthorized)
   - Missing authentication token
   - Invalid token
   - Expired token

3. **Authorization Errors** (403 Forbidden)
   - Insufficient permissions
   - Project access denied
   - Resource ownership violations

4. **Not Found Errors** (404 Not Found)
   - Design document not found
   - Version not found
   - Analysis result not found

5. **Conflict Errors** (409 Conflict)
   - Optimistic locking failures
   - Concurrent modification conflicts
   - Duplicate resource creation

6. **External Service Errors** (502 Bad Gateway, 503 Service Unavailable)
   - Design Service unavailable
   - Knowledge Service timeout
   - Project Service errors
   - Vendor Service failures

7. **Internal Errors** (500 Internal Server Error)
   - Database errors
   - Unexpected exceptions
   - System failures

### Error Response Format

All errors follow a consistent format:

```python
{
    "error": {
        "code": "ERROR_CODE",
        "message": "Human-readable error message",
        "details": {
            # Additional context-specific details
        },
        "timestamp": "2024-01-15T10:30:00Z",
        "request_id": "uuid"
    }
}
```

### Retry and Circuit Breaker Patterns

**External Service Integration:**
- Use exponential backoff for retries: 1s, 2s, 4s, 8s, 16s
- Maximum 5 retry attempts
- Circuit breaker opens after 5 consecutive failures
- Circuit breaker half-open after 60 seconds
- Circuit breaker closes after 3 successful requests

**Database Operations:**
- Retry transient errors (connection timeouts, deadlocks)
- Maximum 3 retry attempts with 100ms, 200ms, 400ms delays
- No retry for constraint violations or data errors

### Graceful Degradation

When external services are unavailable:
- **Design Service down**: Queue rendering requests, return 202 Accepted
- **Knowledge Service down**: Use cached code data, warn about potential staleness
- **Project Service down**: Allow design operations, queue activity logs
- **Vendor Service down**: Return material specs without vendor info

## Testing Strategy

### Dual Testing Approach

The Architectural Service uses both unit testing and property-based testing for comprehensive coverage:

**Unit Tests:**
- Specific examples demonstrating correct behavior
- Edge cases (empty lists, null values, boundary conditions)
- Error conditions (invalid input, missing data, constraint violations)
- Integration points between components
- Mock external services for isolated testing

**Property-Based Tests:**
- Universal properties that hold for all inputs
- Comprehensive input coverage through randomization
- Minimum 100 iterations per property test
- Use Hypothesis library for Python
- Each property test references its design document property

### Testing Layers

**1. Unit Tests (pytest)**

Test individual components in isolation:

```python
# Example: Test design service
async def test_create_design_success():
    """Test successful design creation"""
    service = DesignService(mock_repo, mock_project_client)
    design = await service.create_design(
        project_id=uuid4(),
        user_id=uuid4(),
        data=CreateDesignRequest(...)
    )
    assert design.version == "1.0"
    assert design.version_number == 1

async def test_create_design_invalid_project():
    """Test design creation with invalid project"""
    service = DesignService(mock_repo, mock_project_client)
    with pytest.raises(ProjectNotFoundError):
        await service.create_design(
            project_id=uuid4(),
            user_id=uuid4(),
            data=CreateDesignRequest(...)
        )
```

**2. Property-Based Tests (Hypothesis)**

Test universal properties across many generated inputs:

```python
from hypothesis import given, strategies as st

# Feature: architectural-service, Property 1: Design initialization consistency
@given(
    project_id=st.uuids(),
    user_id=st.uuids(),
    name=st.text(min_size=1, max_size=255),
    building_type=st.sampled_from(["residential", "commercial", "industrial"])
)
async def test_property_design_initialization(project_id, user_id, name, building_type):
    """
    Property: For any new design document creation request, the created design
    should have a unique identifier, version "1.0", version_number 1, and all
    required metadata fields populated.
    """
    service = DesignService(repo, project_client)
    design = await service.create_design(
        project_id=project_id,
        user_id=user_id,
        data=CreateDesignRequest(name=name, building_type=building_type, ...)
    )

    assert design.id is not None
    assert design.version == "1.0"
    assert design.version_number == 1
    assert design.created_at is not None
    assert design.updated_at is not None
    assert design.created_by == user_id
    assert design.project_id == project_id

# Feature: architectural-service, Property 4: Version retrieval round-trip
@given(
    design=st.builds(Design),
    num_updates=st.integers(min_value=1, max_value=10)
)
async def test_property_version_round_trip(design, num_updates):
    """
    Property: For any design document and any valid version number, retrieving
    that version should return design data that matches the snapshot stored when
    that version was created.
    """
    service = DesignService(repo, project_client)

    # Create design and make updates
    created = await service.create_design(...)
    versions = [created]

    for i in range(num_updates):
        updated = await service.update_design(created.id, ...)
        versions.append(updated)

    # Verify each version retrieves correct snapshot
    for i, expected_version in enumerate(versions):
        retrieved = await service.get_design(
            created.id,
            version=expected_version.version
        )
        assert retrieved.version == expected_version.version
        assert retrieved.design_data == expected_version.design_data
```

**3. Integration Tests**

Test API endpoints with real database:

```python
async def test_create_design_endpoint(client, auth_headers):
    """Test POST /api/v1/designs endpoint"""
    response = await client.post(
        "/api/v1/designs",
        json={
            "project_id": str(uuid4()),
            "name": "Test Design",
            "building_type": "residential",
            ...
        },
        headers=auth_headers
    )
    assert response.status_code == 201
    data = response.json()
    assert data["version"] == "1.0"
    assert "id" in data

async def test_compliance_check_workflow(client, auth_headers):
    """Test complete compliance check workflow"""
    # Create design
    design_response = await client.post("/api/v1/designs", ...)
    design_id = design_response.json()["id"]

    # Request compliance check
    check_response = await client.post(
        f"/api/v1/designs/{design_id}/compliance-checks",
        json={"code_standards": ["IBC-2021"], ...}
    )
    assert check_response.status_code == 201
    check_id = check_response.json()["id"]

    # Poll for results
    result_response = await client.get(f"/api/v1/compliance-checks/{check_id}")
    assert result_response.status_code == 200
    assert "violations" in result_response.json()
```

**4. External Service Integration Tests**

Test integration with mocked external services:

```python
async def test_design_service_integration(client, mock_design_service):
    """Test integration with Design Service"""
    mock_design_service.request_rendering.return_value = RenderJob(...)

    response = await client.post(
        f"/api/v1/designs/{design_id}/render",
        json={"render_type": "floor_plan", ...}
    )

    assert response.status_code == 202
    mock_design_service.request_rendering.assert_called_once()

async def test_knowledge_service_integration(client, mock_knowledge_service):
    """Test integration with Knowledge Service"""
    mock_knowledge_service.search_codes.return_value = [CodeSection(...)]

    response = await client.get(
        "/api/v1/codes/search",
        params={"query": "egress requirements"}
    )

    assert response.status_code == 200
    assert len(response.json()) > 0
```

### Test Configuration

**pytest.ini:**
```ini
[pytest]
asyncio_mode = auto
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
markers =
    unit: Unit tests
    integration: Integration tests
    property: Property-based tests
    slow: Slow-running tests

# Hypothesis settings
hypothesis_profile = default
```

**Hypothesis Configuration:**
```python
from hypothesis import settings, Verbosity

settings.register_profile("default", max_examples=100, verbosity=Verbosity.normal)
settings.register_profile("ci", max_examples=200, verbosity=Verbosity.verbose)
settings.register_profile("dev", max_examples=50, verbosity=Verbosity.normal)
```

### Coverage Requirements

- Minimum 90% code coverage for all business logic
- 100% coverage for critical paths (design creation, version management, compliance checking)
- All API endpoints must have integration tests
- All correctness properties must have property-based tests
- All error conditions must have unit tests

### Test Execution

```bash
# Run all tests
pytest

# Run only unit tests
pytest -m unit

# Run only property-based tests
pytest -m property

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/unit/services/test_design_service.py

# Run with Hypothesis profile
pytest --hypothesis-profile=ci
```

## Deployment and Operations

### Database Migrations

Use Alembic for schema migrations:

```bash
# Generate migration
alembic revision --autogenerate -m "Add energy analysis table"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

### Environment Configuration

Required environment variables:

```bash
# Database
DATABASE_URL=mysql+aiomysql://user:pass@host:4000/architectural_service
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10

# External Services
DESIGN_SERVICE_URL=http://design-service:8000
KNOWLEDGE_SERVICE_URL=http://knowledge-service:8000
PROJECT_SERVICE_URL=http://project-service:8000
VENDOR_SERVICE_URL=http://vendor-service:8000

# Redis Cache
REDIS_URL=redis://redis:6379/0
CACHE_TTL=3600

# Authentication
JWT_SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256

# Service Configuration
SERVICE_NAME=architectural-service
LOG_LEVEL=INFO
ENABLE_CORS=true
```

### Monitoring and Observability

**Metrics to Track:**
- Request latency (p50, p95, p99)
- Error rates by endpoint
- External service call latency
- Database query performance
- Cache hit/miss rates
- Active collaboration sessions
- Compliance check queue depth

**Logging:**
- Structured JSON logging
- Request ID tracking
- User ID tracking
- Performance logging for slow operations
- Error logging with stack traces

**Health Checks:**
```python
@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "database": await check_database(),
        "redis": await check_redis(),
        "external_services": {
            "design_service": await check_design_service(),
            "knowledge_service": await check_knowledge_service(),
            "project_service": await check_project_service(),
            "vendor_service": await check_vendor_service()
        }
    }
```

## Security Considerations

1. **Authentication**: JWT-based authentication using common auth package
2. **Authorization**: Role-based access control (RBAC) for design operations
3. **Input Validation**: Pydantic v2 schemas for all inputs
4. **SQL Injection Prevention**: SQLAlchemy ORM with parameterized queries
5. **File Upload Security**: Validate file types, scan for malware, size limits
6. **Rate Limiting**: Per-user and per-IP rate limits
7. **CORS**: Configurable CORS policies
8. **Audit Logging**: Log all design modifications with user attribution

## Performance Optimization

1. **Database Indexing**: Indexes on frequently queried fields (design_id, project_id, status)
2. **Connection Pooling**: Async connection pool for database
3. **Caching**: Redis cache for building codes, rendered outputs, frequently accessed designs
4. **Pagination**: Cursor-based pagination for large result sets
5. **Async Operations**: Async/await throughout for non-blocking I/O
6. **Background Jobs**: Use Celery for long-running analyses (compliance, structural, energy)
7. **Query Optimization**: Eager loading for relationships, select only needed columns

## Future Enhancements

1. **3D Model Support**: Native 3D model storage and manipulation
2. **BIM Integration**: Import/export BIM models (IFC format)
3. **AI-Powered Design Suggestions**: ML models for design optimization
4. **Real-time Rendering**: WebGL-based real-time 3D visualization
5. **Mobile App Support**: Mobile-optimized APIs and offline support
6. **Advanced Collaboration**: Conflict-free replicated data types (CRDTs) for better collaboration
7. **Parametric Design**: Support for parametric design workflows
8. **Cost Estimation**: Integrated cost estimation based on materials and labor
