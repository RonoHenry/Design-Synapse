# DesignSynapse System Architecture

## 1. System Overview
DesignSynapse is an AI-driven platform for the global DAEC (Design, Architecture, Engineering, Construction) industry, aimed at streamlining built environment workflows worldwide.

## 2. High-Level Architecture
```
[Client Layer]
Web App (Next.js) ←→ Mobile PWA
         ↓
[API Gateway Layer]
   API Gateway (Kong/Traefik)
         ↓
[Service Layer]
┌─────────────────┬──────────────────┬────────────────┬────────────────┐
│  User Service   │  Design Service  │ Project Service│ Knowledge      │
│  (FastAPI)      │   (FastAPI/ML)   │  (FastAPI)     │  Service       │
└─────────────────┴──────────────────┴────────────────┴────────────────┘
         ↓                 ↓                 ↓                ↓
[Data Layer]
┌──────────────────────────────────────────────────────────────────────┐
│                    TiDB Serverless Cluster                           │
│                  (EU Central 1 - Frankfurt)                          │
│  ┌─────────────────────┐  ┌─────────────────────┐  ┌──────────────────┐│
│  │design_synapse_user_db│  │design_synapse_project│  │design_synapse_   ││
│  │- Users & Auth       │  │_db                  │  │knowledge_db      ││
│  │- Roles & Permissions│  │- Projects & Tasks   │  │- Resources       ││
│  │- User Profiles      │  │- Comments & Collab  │  │- Bookmarks       ││
│  └─────────────────────┘  └─────────────────────┘  └──────────────────┘│
│  Gateway: gateway01.eu-central-1.prod.aws.tidbcloud.com:4000        │
│  SSL/TLS Required (ca.pem) | MySQL Compatible | Auto-scaling        │
└──────────────────────────────────────────────────────────────────────┘
         ↓                 ↓                 ↓
┌─────────────────┬──────────────────┬────────────────┐
│    MinIO/S3     │     MongoDB      │     Redis      │
│ (Design Files)  │  (Future Use)    │    (Cache)     │
└─────────────────┴──────────────────┴────────────────┘
```

## 3. Core Components

### 3.1 Frontend Layer
- **Web Application**
  - Next.js for SSR and optimal performance
  - Three.js for 3D rendering
  - WebSocket for real-time collaboration
  - Progressive Web App (PWA) support

### 3.2 Backend Services
#### User Service
- Authentication & Authorization
- User Profile Management
- Role-based Access Control
- Professional Networking

#### Design Service
- AI Design Generation
- 3D Model Processing
- Drone Data Integration
- Design Optimization
- CAD Integration

#### Project Service
- Project Management
- Task Scheduling
- Resource Allocation
- Timeline Tracking
- Real-time Collaboration

#### Marketplace Service
- Vendor Management
- Product Catalogs
- Bidding System
- Payment Processing

### 3.3 AI Components
- Design Generation Models
- Cost Estimation ML
- Project Timeline Prediction
- Resource Optimization
- Computer Vision for Drone Data

### 3.4 Data Storage
- **TiDB Serverless** (MySQL-compatible distributed SQL database)
  - **Connection**: gateway01.eu-central-1.prod.aws.tidbcloud.com:4000
  - **SSL/TLS**: Required for all connections (ca.pem certificate)
  - **Service Databases**:
    - `design_synapse_user_db` - User accounts, authentication, roles
    - `design_synapse_project_db` - Projects, tasks, collaboration data
    - `design_synapse_knowledge_db` - Resources, bookmarks, citations
  - **Features**:
    - Auto-scaling based on workload (serverless)
    - HTAP capabilities (transactional + analytical)
    - Built-in high availability and disaster recovery
    - Pay-per-use pricing model
    - MySQL compatibility for ecosystem integration
    - Distributed architecture for global scale
- **MongoDB** (Future consideration)
  - Complex document structures
  - Design metadata
  - Vendor catalogs
- **MinIO/S3**
  - Design files
  - 3D models
  - Drone imagery
- **Redis**
  - Session management
  - Real-time data
  - Caching

## 4. Security Architecture
- JWT-based authentication
- Role-Based Access Control (RBAC)
- API rate limiting
- Data encryption at rest and in transit
- Regular security audits
- GDPR compliance

## 5. Scalability & Performance
### Horizontal Scaling
- Kubernetes orchestration
- Microservices architecture
- Load balancing
- Auto-scaling groups

### Performance Optimization
- CDN integration
- Redis caching
- Database optimization
- Asset optimization

## 6. Integration Points
- CAD Software APIs (AutoCAD, Revit)
- Drone Data Systems
- Payment Gateways
- Cloud Storage Services
- Analytics Platforms

## 7. Monitoring & Logging
- Prometheus for metrics
- Grafana for visualization
- ELK Stack for logging
- Alert management
- Performance monitoring

## 8. Deployment Architecture
### Development
- Local Docker development
- Testing environments
- CI/CD pipelines

### Production
- Kubernetes clusters
- Load balancers
- Auto-scaling
- Backup systems

## 9. Disaster Recovery
- Regular backups
- Failover systems
- Data replication
- Recovery procedures

## 10. Future Considerations
- Blockchain integration for contracts
- AI model expansion
- AR/VR capabilities
- Mobile native apps
