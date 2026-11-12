# User Service

User authentication, authorization, and profile management service for DesignSynapse.

## Overview

The User Service provides comprehensive user management functionality including:
- User registration and authentication
- JWT token-based authentication
- Role-based access control (RBAC)
- User profile management
- Password management and security

## Features

- **Authentication**: Secure user login/logout with JWT tokens
- **Authorization**: Role-based permissions system
- **User Management**: Create, read, update user profiles
- **Security**: Password hashing, token refresh, secure sessions
- **Roles**: Admin, user, moderator role management

## Setup

### Prerequisites

- Python 3.11+
- PostgreSQL or TiDB database
- Redis (for session management)

### Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. Set up the database:
```bash
# Run database migrations
alembic upgrade head

# Create default roles (optional)
python src/scripts/create_default_roles.py
```

4. Run the service:
```bash
uvicorn src.main:app --reload --port 8001
```

## Configuration

### Required Environment Variables

```bash
# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_USERNAME=your_username
DB_PASSWORD=your_password
DB_DATABASE=user_service

# JWT Configuration
JWT_SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# Email Configuration (if email verification enabled)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
REQUIRE_EMAIL_VERIFICATION=false
```

### Optional Environment Variables

```bash
# Service URLs
FRONTEND_URL=http://localhost:3000

# Security Settings
PASSWORD_MIN_LENGTH=8
MAX_LOGIN_ATTEMPTS=5
LOCKOUT_DURATION_MINUTES=15
```

## API Documentation

Once running, visit:
- **Swagger UI**: http://localhost:8001/docs
- **ReDoc**: http://localhost:8001/redoc

### Key Endpoints

#### Authentication
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - User login
- `POST /api/v1/auth/refresh` - Refresh access token
- `POST /api/v1/auth/logout` - User logout

#### User Management
- `GET /api/v1/users/me` - Get current user profile
- `PUT /api/v1/users/me` - Update current user profile
- `POST /api/v1/users/change-password` - Change password

#### Role Management (Admin only)
- `GET /api/v1/roles` - List all roles
- `POST /api/v1/roles` - Create new role
- `POST /api/v1/users/{user_id}/roles/{role_name}` - Assign role to user

### Example API Usage

#### Register a new user
```bash
curl -X POST "http://localhost:8001/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john.doe@example.com",
    "username": "john_doe",
    "password": "SecurePass123!",
    "first_name": "John",
    "last_name": "Doe"
  }'
```

#### Login
```bash
curl -X POST "http://localhost:8001/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john_doe",
    "password": "SecurePass123!"
  }'
```

#### Get user profile (requires authentication)
```bash
curl -X GET "http://localhost:8001/api/v1/users/me" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## Project Structure

```
apps/user-service/
├── src/
│   ├── api/
│   │   └── v1/
│   │       ├── schemas/      # Pydantic request/response models
│   │       ├── auth.py       # Authentication endpoints
│   │       ├── roles.py      # Role management endpoints
│   │       └── users.py      # User management endpoints
│   ├── core/
│   │   ├── config.py         # Configuration settings
│   │   ├── security.py       # Security utilities
│   │   └── exceptions.py     # Custom exceptions
│   ├── models/
│   │   ├── user.py          # User SQLAlchemy model
│   │   └── role.py          # Role SQLAlchemy model
│   ├── scripts/
│   │   └── create_default_roles.py  # Setup script
│   └── main.py              # FastAPI application
├── tests/
│   ├── unit/                # Unit tests
│   ├── integration/         # Integration tests
│   ├── factories.py         # Test data factories
│   └── conftest.py         # Test configuration
├── migrations/              # Alembic database migrations
├── requirements.txt         # Python dependencies
└── alembic.ini             # Alembic configuration
```

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test categories
pytest tests/unit/          # Unit tests only
pytest tests/integration/   # Integration tests only
```

### Database Migrations

```bash
# Create a new migration
alembic revision --autogenerate -m "Description of changes"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

### Code Quality

```bash
# Format code
black src/ tests/

# Lint code
flake8 src/ tests/

# Type checking
mypy src/
```

## Security Features

- **Password Hashing**: Uses bcrypt for secure password storage
- **JWT Tokens**: Stateless authentication with configurable expiration
- **Rate Limiting**: Protection against brute force attacks
- **Input Validation**: Comprehensive request validation
- **CORS**: Configurable cross-origin resource sharing
- **SQL Injection Protection**: SQLAlchemy ORM prevents SQL injection

## Monitoring and Health

- **Health Check**: `GET /health` - Service health status
- **Ready Check**: `GET /ready` - Service readiness (includes database connectivity)
- **Metrics**: Built-in request metrics and performance monitoring

## Troubleshooting

### Common Issues

1. **Database Connection Errors**
   - Verify database credentials in `.env`
   - Ensure database server is running
   - Check network connectivity

2. **JWT Token Issues**
   - Verify `JWT_SECRET_KEY` is set and consistent
   - Check token expiration settings
   - Ensure system clock is synchronized

3. **Email Verification Issues**
   - Verify SMTP configuration
   - Check email provider settings
   - Ensure firewall allows SMTP traffic

### Logs

Service logs include:
- Authentication attempts
- Authorization failures
- Database operations
- Error details with request IDs

## Contributing

1. Follow the existing code style
2. Add tests for new functionality
3. Update documentation as needed
4. Ensure all tests pass before submitting
