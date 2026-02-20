# DesignSynapse 🏗️

## Overview
DesignSynapse is an AI-driven platform revolutionizing the DAEC (Design, Architecture, Engineering, Construction) industry by streamlining built environment. it combines cutting-edge AI technology with industry-specific tools to enhance tool efficiency, improve collaboration, and drive innovation in construction projects.

### Key Features
- 🤖 AI-powered design assistance and validation
- 🏢 BIM (Building Information Modeling) integration
- 👥 Collaborative project management
- 📊 Real-time analytics and insights
- 🔐 Role-based access control

# DesignSynapse Project Structure

```
designsynapse/
│
├── apps/                           # Microservices
│   ├── api-gateway/               # API Gateway & Request Routing
│   ├── architectural-service/     # Design Management & Analysis
│   ├── design-service/            # AI-Powered Design Generation
│   ├── engineering-service/       # Engineering Calculations (In Progress)
│   ├── knowledge-service/         # Knowledge Base & Vector Search
│   ├── labor-service/             # Labor Marketplace
│   ├── project-service/           # Project Management
│   ├── user-service/              # Authentication & User Management
│   └── vendor-service/            # Vendor & Product Management
│
├── packages/common/               # Shared Libraries
│   ├── auth/                      # JWT Authentication & RBAC
│   ├── config/                    # Configuration Management
│   ├── database/                  # Database Utilities & Health Checks
│   ├── errors/                    # Error Handling Framework
│   ├── http/                      # HTTP Clients & Service Communication
│   ├── monitoring/                # Logging, Metrics & Tracing
│   ├── performance/               # Caching, CDN & Connection Pooling
│   ├── rate_limiting/             # Rate Limiting Middleware
│   ├── resilience/                # Circuit Breaker & Retry Patterns
│   ├── security/                  # Input Validation & Threat Detection
│   ├── service_registry/          # Service Discovery
│   ├── storage/                   # Object Storage Client
│   └── testing/                   # Test Utilities & Fixtures
│
├── tests/                         # Integration Tests
│   └── integration/               # Cross-Service Integration Tests
│
├── docs/                          # Documentation
│   ├── ENV.md                     # Environment Configuration Guide
│   ├── TIDB_MIGRATION.md          # Database Migration Documentation
│   └── FUTURE_VISION_ROADMAP.md   # Product Roadmap
│
├── scripts/                       # Utility Scripts
│   └── init-databases.sh          # Database Initialization
│
├── .github/                       # CI/CD Workflows
│   └── workflows/                 # GitHub Actions
│
├── .kiro/                         # Kiro AI Configuration
│   ├── specs/                     # Feature Specifications
│   └── settings/                  # Kiro Settings
│
├── docker-compose.yml             # Docker Services Configuration
├── requirements-dev.txt           # Development Dependencies
└── README.md                      # Project Overview
```


## Technology Stack

### Backend
- **Framework**: FastAPI (Python 3.13+)
- **Database**: TiDB Serverless (MySQL-compatible)
- **Caching**: Redis 7+
- **Task Queue**: Celery
- **ORM**: SQLAlchemy (async)
- **Validation**: Pydantic v2

### Frontend
- **Framework**: Next.js
- **Language**: TypeScript
- **Styling**: TailwindCSS

### Infrastructure
- **Containerization**: Docker & Docker Compose
- **Database**: TiDB Cloud (Serverless)
- **Storage**: S3-compatible object storage
- **Monitoring**: Prometheus & Grafana (planned)

### Development
- **Testing**: pytest, Hypothesis (property-based testing)
- **Code Quality**: Black, Flake8, isort, ESLint
- **Version Control**: Git with conventional commits
- **CI/CD**: GitHub Actions

## Common Packages

### Authentication & Security
- `auth/` - JWT validation, RBAC, service-to-service auth
- `security/` - Input validation, threat detection, audit logging

### Infrastructure
- `database/` - Connection management, health checks, migrations
- `http/` - Service clients, retry logic, circuit breakers
- `service_registry/` - Service discovery and health monitoring
- `storage/` - Object storage abstraction

### Observability
- `monitoring/` - Structured logging, metrics, distributed tracing
- `performance/` - Caching strategies, CDN integration, connection pooling

### Resilience
- `resilience/` - Circuit breakers, exponential backoff, retry policies
- `rate_limiting/` - Token bucket, sliding window algorithms
- `errors/` - Standardized error handling and responses

### Development
- `testing/` - Test fixtures, factories, database utilities
- `config/` - Configuration management, secrets handling

## Key Features by Service

### Architectural Service
- Design version control & management
- Building code compliance checking
- Structural analysis (loads, beams, columns)
- Energy performance analysis
- Accessibility validation (ADA/WCAG)
- Space planning & optimization
- Material specification
- Real-time collaboration (WebSocket)

### Design Service
- AI-powered design generation
- Design validation & optimization
- Visual output generation (renders, diagrams)
- Building code validation
- Design file management
- Comment & feedback system

### Knowledge Service
- Vector-based semantic search
- PDF processing & content extraction
- Building code database
- AI-powered recommendations
- Citation management
- Project-specific knowledge bases

### Project Service
- Project lifecycle management
- Team collaboration
- Resource allocation
- Timeline tracking
- Activity logging
- Comment threads

### User Service
- JWT-based authentication
- Role-based access control (RBAC)
- User profile management
- Organization management
- Permission system

### Vendor Service
- Vendor directory
- Product catalog
- Material specifications
- Order management
- Review & rating system
- Staging area for approvals

### Labor Service
- Service provider marketplace
- Service request management
- Quote & booking system
- Provider matching algorithm
- Review & rating system

## Development Approach

### Spec-Driven Development
All features follow a structured specification process:
1. **Requirements** - User stories & acceptance criteria
2. **Design** - Technical design & architecture
3. **Tasks** - Implementation plan with TDD approach

### Testing Approch
- Unit tests for all business logic
- Property-based tests using Hypothesis
- Integration tests for API endpoints
- Load tests for performance validation
- Minimum 80% code coverage


## Getting Started

See [README.md](README.md) for detailed setup instructions.

## Documentation

- [Environment Setup](docs/ENV.md)
- [TiDB Migration Guide](docs/TIDB_MIGRATION.md)
- [Future Roadmap](docs/FUTURE_VISION_ROADMAP.md)
- [API Documentation](http://localhost:8000/docs) (when services are running)

## License

MIT License - See [LICENSE](LICENSE) for details.

