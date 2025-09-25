W# DesignSynapse Branching Strategy

## Core Branches

### `main` (Production)
- Always reflects production-ready state
- Protected branch - no direct commits
- Requires pull request with approvals
- Tagged with version numbers for releases
- Auto-deploys to production environment

### `develop` (Integration)
- Main development branch
- Contains latest delivered development changes
- Protected branch - no direct commits
- Source for feature branches
- Auto-deploys to staging environment

## Supporting Branches

### Feature Branches
- Branch naming: `feature/service-name/feature-description`
- Examples:
  - `feature/design-service/ai-model-integration`
  - `feature/user-service/oauth-implementation`
  - `feature/frontend/3d-viewer`
- Branch from: `develop`
- Merge back into: `develop`
- Naming convention:
  ```
  feature/[service-name]/[feature-description]
  feature/[issue-number]-[short-description]
  ```

### Release Branches
- Branch naming: `release/v[major].[minor].[patch]`
- Example: `release/v1.2.0`
- Branch from: `develop`
- Merge back into: `main` and `develop`
- Used for release preparation
- Only bug fixes, documentation, and release-oriented tasks

### Hotfix Branches
- Branch naming: `hotfix/v[major].[minor].[patch+1]`
- Example: `hotfix/v1.2.1`
- Branch from: `main`
- Merge back into: `main` and `develop`
- Used for urgent production fixes

### Service-Specific Development
For each microservice:
```
apps/[service-name]
├── main (production)
├── develop
├── feature/[feature-name]
└── hotfix/[fix-name]
```

## Workflow Rules

### 1. Creating New Features
```bash
# Start a new feature
git checkout develop
git pull origin develop
git checkout -b feature/service-name/feature-description
```

### 2. Pull Request Requirements
- Must pass CI/CD pipeline
- Requires at least one code review
- Must pass automated tests
- No merge conflicts
- Up-to-date with target branch

### 3. Commit Guidelines
- Use conventional commits:
  ```
  feat: add new AI model integration
  fix: resolve authentication bug
  docs: update API documentation
  test: add unit tests for user service
  chore: update dependencies
  ```

### 4. Release Process
```bash
# Create release branch
git checkout develop
git pull origin develop
git checkout -b release/v1.2.0

# After testing and fixes
git checkout main
git merge release/v1.2.0
git tag -a v1.2.0 -m "Release version 1.2.0"
git push origin main --tags

git checkout develop
git merge release/v1.2.0
git push origin develop
```

### 5. Hotfix Process
```bash
# Create hotfix branch
git checkout main
git checkout -b hotfix/v1.2.1

# After fixing
git checkout main
git merge hotfix/v1.2.1
git tag -a v1.2.1 -m "Hotfix version 1.2.1"
git push origin main --tags

git checkout develop
git merge hotfix/v1.2.1
git push origin develop
```

## CI/CD Integration

### Branch Protection Rules
1. `main` branch:
   - Require pull request approvals
   - Require CI/CD checks to pass
   - No direct pushes
   - Required status checks

2. `develop` branch:
   - Require pull request approvals
   - Require CI/CD checks to pass
   - No direct pushes
   - Required status checks

### Automated Processes
- Feature branches: Deploy to development environment
- Develop: Deploy to staging environment
- Main: Deploy to production environment
- Release branches: Deploy to pre-production environment

## Version Control Best Practices

### 1. Commit Messages
```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

Types:
- feat: New feature
- fix: Bug fix
- docs: Documentation changes
- style: Formatting changes
- refactor: Code restructuring
- test: Test addition/modification
- chore: Maintenance tasks

### 2. Pull Request Template
```markdown
## Description
[Feature/Fix description]

## Type of change
- [ ] New feature
- [ ] Bug fix
- [ ] Documentation update
- [ ] Refactoring

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing completed

## Checklist
- [ ] My code follows the style guidelines
- [ ] I have performed a self-review
- [ ] I have commented my code
- [ ] I have updated the documentation
```

### 3. Code Review Guidelines
- Review for:
  - Code quality
  - Test coverage
  - Documentation
  - Security concerns
  - Performance impacts
  - Architecture alignment

## Microservices Considerations

### Service-Specific Branches
Each service in the `apps` directory can have its own development cycle:
```
apps/
├── design-service/
│   ├── main
│   ├── develop
│   └── feature/new-ai-model
├── user-service/
│   ├── main
│   ├── develop
│   └── feature/oauth2
└── frontend/
    ├── main
    ├── develop
    └── feature/3d-viewer
```

### Cross-Service Changes
For features requiring changes across multiple services:
- Create related feature branches with same prefix
- Use pull request linking
- Coordinate deployments through release branches
