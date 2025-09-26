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
- PostgreSQL 14+
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

4. Start development servers
```bash
# Start all services
docker-compose up -d

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
```bash
# Setup database users and permissions
cd scripts
./init-databases.sh  # or init-databases.bat on Windows

# Run migrations
cd ../apps/user-service
alembic upgrade head
```

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
- **Database**: PostgreSQL
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
