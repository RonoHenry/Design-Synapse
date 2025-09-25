# DesignSynapse

## Overview
AI-driven platform for the DAEC (Design, Architecture, Engineering, Construction) industry, streamlining the built environment workflow in Africa.

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
- Python 3.13+
- Node.js 18+
- Docker & Docker Compose
- PostgreSQL 14+
- Redis

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

# Start backend services
cd ../design-service
uvicorn main:app --reload
```

## Testing
```bash
# Run all tests
npm test

# Run specific service tests
cd apps/design-service
pytest
```

## Documentation
- [System Design](docs/DESIGN.md)
- [Requirements](docs/REQUIREMENTS.md)
- [Tasks](docs/TASKS.md)
- [API Documentation](docs/api/README.md)

## Contributing
Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Authors
- RonoHenry - Initial work - [RonoHenry](https://github.com/RonoHenry)

## Acknowledgments
- Design inspiration from existing DAEC tools
- AI/ML community for model architectures
- Open source community