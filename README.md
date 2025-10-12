# DesignSynapse 🏗️

## Overview
DesignSynapse is an AI-driven platform revolutionizing the DAEC (Design, Architecture, Engineering, Construction) industry by streamlining built environment workflows in Africa. Our platform combines cutting-edge AI technology with industry-specific tools to enhance productivity, improve collaboration, and drive innovation in construction projects.

### Key Features
- 🤖 AI-powered design assistance and validation
- 🏢 BIM (Building Information Modeling) integration
- 👥 Collaborative project management
- 📊 Real-time analytics and insights
- 🔐 Role-based access control
- 🌍 Africa-focused construction standards

## Vision
To transform Africa's construction industry by providing accessible, intelligent tools that bridge the gap between design and execution, making sustainable and efficient construction practices the norm rather than the exception.

## Project Structure
```
designsynapse/
├── apps/                          # Monorepo apps (services + frontend)
│   ├── frontend/                  # Next.js frontend
│   ├── design-service/           # AI/ML service (FastAPI)
│   ├── user-service/            # User management service
│   └── project-service/         # Project management service
├── packages/                      # Shared utilities
├── infra/                        # Infrastructure as Code
├── docs/                         # Documentation
└── tests/                        # Integration tests
```

## Getting Started

### Prerequisites

#### Required Software
- Python 3.13+
- Node.js 18+ & npm
- Docker & Docker Compose
- TiDB (MySQL-compatible)
- Redis 7+

#### Development Tools
- VS Code (recommended)
- Docker Desktop
- Git
- Pre-commit hooks

#### Environment Setup
We use pre-commit hooks for code quality. Install them with:
```bash
pip install pre-commit
pre-commit install
```

### Development Setup
1. Clone the repository
```bash
git clone https://github.com/RonoHenry/Design-Synapse.git
cd Design-Synapse
```

2. Install dependencies
```bash
# Install root dependencies
npm install

# Install backend dependencies
cd apps/design-service
python -m venv venv
source venv/Scripts/activate  # Windows
pip install -r requirements.txt

# Install frontend dependencies
cd ../frontend
npm install
```

3. Set up environment variables
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. Configure TiDB Serverless connection

#### Obtaining TiDB Credentials
1. Sign up for a free TiDB Cloud account at https://tidbcloud.com
2. Create a new Serverless Tier cluster (free tier available)
3. Select your preferred region (e.g., EU Central 1 - Frankfurt)
4. Once created, navigate to your cluster's "Connect" page
5. Copy the connection details:
   - Host (e.g., gateway01.eu-central-1.prod.aws.tidbcloud.com)
   - Port (typically 4000)
   - Username (e.g., your_cluster_id.root)
   - Password (generate and save securely)

#### SSL Certificate Setup
TiDB Serverless requires SSL/TLS connections. Download the CA certificate:

```bash
# Download the TiDB CA certificate
curl -o ca.pem https://letsencrypt.org/certs/isrgrootx1.pem

# Or download from TiDB Cloud console and place in project root
# The ca.pem file should be in the same directory as your .env file
```

#### Environment Configuration
Update your `.env` file with TiDB connection details:

```bash
# TiDB Connection Settings
DATABASE_HOST=gateway01.eu-central-1.prod.aws.tidbcloud.com
DATABASE_PORT=4000
DATABASE_USER=your_cluster_id.root
DATABASE_PASSWORD=your_secure_password

# SSL Configuration (required for TiDB Serverless)
DATABASE_SSL_CA=./ca.pem
DATABASE_SSL_VERIFY_CERT=true
DATABASE_SSL_VERIFY_IDENTITY=true

# Service-specific databases
USER_SERVICE_DB=design_synapse_user_db
PROJECT_SERVICE_DB=design_synapse_project_db
KNOWLEDGE_SERVICE_DB=design_synapse_knowledge_db
```

5. Start development servers
```bash
# Note: docker-compose.yml is available for future application services
# but does not include a database container (TiDB Serverless is used instead)

# Start frontend
cd apps/frontend
npm run dev

# Start backend services individually
cd ../design-service
uvicorn main:app --reload

cd ../user-service
uvicorn main:app --reload --port 8001

cd ../project-service
uvicorn main:app --reload --port 8002
```

### Database Setup

This project uses **TiDB Serverless** as the database backend. TiDB is a cloud-native, distributed SQL database that provides auto-scaling, high availability, and MySQL compatibility.

#### Step 1: Create Service Databases

Connect to your TiDB cluster using the MySQL client or TiDB Cloud console:

```bash
# Using MySQL client (install via: pip install pymysql or use mysql CLI)
mysql -h gateway01.eu-central-1.prod.aws.tidbcloud.com \
      -P 4000 \
      -u your_cluster_id.root \
      -p \
      --ssl-ca=./ca.pem \
      --ssl-mode=VERIFY_IDENTITY

# Once connected, create the service databases:
CREATE DATABASE IF NOT EXISTS design_synapse_user_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS design_synapse_project_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS design_synapse_knowledge_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

#### Step 2: Run Database Migrations

Each service has its own Alembic migrations. Run them in order:

```bash
# User Service migrations
cd apps/user-service
alembic upgrade head

# Project Service migrations
cd ../project-service
alembic upgrade head

# Knowledge Service migrations
cd ../knowledge-service
alembic upgrade head
```

#### Step 3: Verify Connection

Test your TiDB connection:

```bash
# Run the connection verification script
python test_tidb_connection.py

# Or check service health endpoints after starting services:
# User Service: http://localhost:8001/
# Project Service: http://localhost:8002/
# Knowledge Service: http://localhost:8003/health
```

**Note**: No local database container is required. All services connect directly to TiDB Serverless using the connection details in your `.env` file.

#### Troubleshooting Common Issues

**Connection Refused / Timeout**
- Verify your TiDB cluster is active in TiDB Cloud console
- Check that your IP address is whitelisted (TiDB Serverless allows all IPs by default)
- Ensure firewall allows outbound connections on port 4000

**SSL Certificate Errors**
- Verify `ca.pem` file exists in project root
- Check file permissions: `chmod 644 ca.pem`
- Ensure `DATABASE_SSL_CA` path in `.env` is correct (relative or absolute)
- Try downloading the certificate again if corrupted

**Authentication Failed**
- Double-check username format: `cluster_id.root` (not just `root`)
- Verify password is correct (regenerate if needed from TiDB Cloud console)
- Ensure no extra spaces in `.env` file values

**Database Not Found**
- Verify databases were created successfully
- Check database names match exactly in `.env` file
- Ensure you're connecting to the correct TiDB cluster

**Migration Errors**
- Ensure all dependencies are installed: `pip install -r requirements.txt`
- Check that Alembic configuration points to correct database
- Verify database user has CREATE/ALTER/DROP privileges
- Review migration files for MySQL compatibility

For more detailed troubleshooting, see [docs/TIDB_MIGRATION.md](docs/TIDB_MIGRATION.md)

### Environment Variables
Each service requires specific environment variables. Copy the example files and update them:

```bash
# User Service
cd apps/user-service
cp .env.example .env

# Design Service
cd ../design-service
cp .env.example .env

# Frontend
cd ../frontend
cp .env.local.example .env.local
```

## Testing

### Running Tests
```bash
# Run all tests
npm test

# Run specific service tests
cd apps/design-service
pytest

cd ../user-service
pytest

cd ../project-service
pytest
```

### Code Quality
We maintain high code quality standards using:
- Black (code formatting)
- Flake8 (linting)
- isort (import sorting)
- ESLint (JavaScript/TypeScript)
- Pre-commit hooks

Code style is automatically enforced through pre-commit hooks. Maximum line length is set to 88 characters.

## API Documentation
Each service provides its own OpenAPI documentation:

- User Service: http://localhost:8001/docs
- Design Service: http://localhost:8000/docs
- Project Service: http://localhost:8002/docs
- Marketplace Service: http://localhost:8003/docs

## Project Documentation
- [System Design](docs/DESIGN.md)
- [Requirements](docs/REQUIREMENTS.md)
- [Tasks](docs/TASKS.md)
- [API Documentation](docs/api/README.md)

## Architecture

### System Components
- **Frontend**: Next.js application with TypeScript
- **User Service**: Authentication and user management
- **Design Service**: Core AI/ML functionality for design analysis
- **Project Service**: Project and resource management
- **Marketplace Service**: Design template marketplace
- **Analytics Service**: Usage and performance metrics

### Technologies Used
- **Frontend**: Next.js, TypeScript, TailwindCSS
- **Backend**: FastAPI, SQLAlchemy, Pydantic
- **AI/ML**: PyTorch, TensorFlow, Scikit-learn
- **Database**: TiDB (MySQL-compatible)
- **Caching**: Redis
- **Infrastructure**: Docker, Kubernetes (planned)

## Contributing
Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests. We use [conventional commits](https://www.conventionalcommits.org/) for our commit messages.

### Branch Naming Convention
- `feature/*`: New features
- `fix/*`: Bug fixes
- `chore/*`: Maintenance tasks
- `docs/*`: Documentation updates
- `refactor/*`: Code refactoring
- `test/*`: Test additions or modifications

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Authors
- RonoHenry - Initial work - [RonoHenry](https://github.com/RonoHenry)

## Acknowledgments
- Design inspiration from existing DAEC tools
- AI/ML community for model architectures and best practices
- Open source community and contributors
- African construction industry professionals for domain expertise

## Status
🚧 Project is currently in active development
