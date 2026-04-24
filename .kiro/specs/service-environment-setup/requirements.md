# Requirements Document

## Introduction

This feature covers the end-to-end setup of fully operational service environments across the Python microservices monorepo on Windows. "Fully operational" means each in-scope service has an isolated virtual environment, all dependencies installed (including dev deps), a correctly configured `.env` pointing to TiDB Serverless and Redis, all Alembic migrations applied against the real database, the service able to start via `uvicorn`, and integration tests (plus property-based tests where applicable) passing against the real database — not SQLite mocks.

Services in scope: design-service, architectural-service, engineering-service, labor-service, vendor-service, analytics-service.

## Glossary

- **Setup_Orchestrator**: The process (script or manual steps) that drives the full environment setup for a given service.
- **Venv**: A per-service Python virtual environment located at `apps/{service}/.venv`.
- **TiDB**: The TiDB Serverless MySQL-compatible cloud database at `gateway01.eu-central-1.prod.aws.tidbcloud.com:4000`.
- **Root_Env**: The `.env` file at the repository root containing shared TiDB connection details.
- **Service_Env**: The `.env` file inside each service directory (`apps/{service}/.env`) used at runtime and by Alembic.
- **Migration_Runner**: The Alembic CLI invoked inside a service's Venv to apply schema migrations.
- **Health_Endpoint**: The `/health` HTTP endpoint exposed by each FastAPI service.
- **Integration_Test_Suite**: The pytest test suite under `apps/{service}/tests/integration/`.
- **Property_Test_Suite**: The pytest test suite under `apps/{service}/tests/property/` using Hypothesis.
- **Local_Package**: An editable (`-e`) package under `packages/common/` installed into a service's Venv.
- **CPU_Torch**: The CPU-only build of PyTorch installed via the `--index-url https://download.pytorch.org/whl/cpu` flag to avoid the 2 GB GPU download.

---

## Requirements

### Requirement 1: Per-Service Virtual Environment Isolation

**User Story:** As a developer, I want each service to have its own isolated `.venv`, so that dependency conflicts between services are impossible and each service can be set up and torn down independently.

#### Acceptance Criteria

1. THE Setup_Orchestrator SHALL create a Venv at `apps/{service}/.venv` using `python -m venv .venv` when no Venv exists for that service.
2. WHEN a Venv already exists for a service (design-service, analytics-service), THE Setup_Orchestrator SHALL verify the Venv is functional by running `.venv/Scripts/python.exe --version` before proceeding.
3. IF the Venv verification command exits with a non-zero code, THEN THE Setup_Orchestrator SHALL delete the existing Venv and recreate it.
4. THE Setup_Orchestrator SHALL use the Venv's own `pip` executable (`apps/{service}/.venv/Scripts/pip.exe`) for all subsequent package installation steps for that service.
5. THE Venv SHALL be created with `--copies` flag on Windows to avoid symlink permission issues.

---

### Requirement 2: Dependency Installation

**User Story:** As a developer, I want all service dependencies (runtime and dev) installed into the service's Venv, so that the service can start and all tests can run without missing-module errors.

#### Acceptance Criteria

1. WHEN setting up a service, THE Setup_Orchestrator SHALL install packages from `apps/{service}/requirements.txt` into the service's Venv using `pip install -r requirements.txt`.
2. WHEN a root-level `requirements-dev.txt` exists, THE Setup_Orchestrator SHALL also install it into the service's Venv using `pip install -r ../../requirements-dev.txt` (relative to the service directory).
3. WHERE a service's `requirements.txt` contains local editable packages (vendor-service: `packages/common/config`, `auth`, `errors`, `monitoring`, `testing`, `storage`, `http`), THE Setup_Orchestrator SHALL install each local package with `pip install -e <path>` using the absolute path resolved from the repo root.
4. WHERE the service is knowledge-service, THE Setup_Orchestrator SHALL install PyTorch using `pip install torch --index-url https://download.pytorch.org/whl/cpu` instead of the default index to install the CPU-only build.
5. IF any `pip install` command exits with a non-zero code, THEN THE Setup_Orchestrator SHALL report the failing package and the full pip error output, then halt setup for that service.
6. THE Setup_Orchestrator SHALL upgrade `pip` itself (`pip install --upgrade pip`) before installing any other packages.

---

### Requirement 3: Service Environment Configuration (.env)

**User Story:** As a developer, I want each service's `.env` to point to TiDB Serverless and the correct Redis instance, so that the service connects to the real database at runtime and during integration tests.

#### Acceptance Criteria

1. THE Setup_Orchestrator SHALL write or update `apps/{service}/.env` with a `DATABASE_URL` value that uses the TiDB Serverless connection string in the format `mysql+pymysql://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_DATABASE}?ssl_ca={SSL_CA_PATH}&ssl_verify_cert=true&ssl_verify_identity=true`.
2. THE Setup_Orchestrator SHALL read `DB_HOST`, `DB_PORT`, `DB_USERNAME`, `DB_PASSWORD`, `DB_DATABASE`, and `DB_SSL_CA` from the Root_Env when constructing the per-service `DATABASE_URL`.
3. WHEN the service uses an async SQLAlchemy driver (architectural-service uses `asyncmy`, engineering-service uses `asyncmy`), THE Setup_Orchestrator SHALL write the `DATABASE_URL` with the `mysql+asyncmy://` scheme instead of `mysql+pymysql://`.
4. WHEN the service is labor-service, THE Setup_Orchestrator SHALL replace the existing `DATABASE_URL=sqlite:///labor_service.db` value with the TiDB connection string.
5. WHEN the service uses Redis (design-service, labor-service), THE Setup_Orchestrator SHALL ensure `REDIS_URL` is set to `redis://localhost:6379/0` in the Service_Env unless already overridden.
6. WHEN the service uses Celery (design-service), THE Setup_Orchestrator SHALL ensure `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND` are set to the Redis URL in the Service_Env.
7. THE Setup_Orchestrator SHALL preserve all existing non-database keys in the Service_Env when updating the `DATABASE_URL`.
8. IF the Root_Env file does not exist or is missing required TiDB keys, THEN THE Setup_Orchestrator SHALL halt and report which keys are absent.

---

### Requirement 4: Analytics Service Database Assessment

**User Story:** As a developer, I want a clear determination of whether analytics-service should switch from PostgreSQL (psycopg2) to TiDB/MySQL, so that the correct database driver and connection string are used before migrations are run.

#### Acceptance Criteria

1. THE Setup_Orchestrator SHALL detect that analytics-service `requirements.txt` specifies `psycopg2-binary` and report this as a blocking issue requiring resolution before proceeding with analytics-service setup.
2. WHEN analytics-service is configured to use TiDB (i.e., `psycopg2-binary` has been replaced with `pymysql` in `requirements.txt`), THE Setup_Orchestrator SHALL proceed with the standard TiDB `DATABASE_URL` configuration for analytics-service.
3. IF analytics-service retains `psycopg2-binary` and a PostgreSQL `DATABASE_URL` is provided via a separate environment variable `ANALYTICS_DATABASE_URL`, THEN THE Setup_Orchestrator SHALL use that value for analytics-service's `DATABASE_URL` instead of the TiDB string.
4. THE Setup_Orchestrator SHALL document the analytics-service database driver decision in its output log before proceeding.

---

### Requirement 5: Database Migration Execution

**User Story:** As a developer, I want Alembic migrations applied against TiDB for each service that has them, so that the real database schema is up to date before integration tests run.

#### Acceptance Criteria

1. WHEN a service directory contains an `alembic.ini` file (design-service, architectural-service, engineering-service, labor-service, vendor-service), THE Migration_Runner SHALL execute `alembic upgrade head` from within that service directory using the service's Venv Python.
2. THE Migration_Runner SHALL set the `DATABASE_URL` environment variable to the TiDB connection string when invoking `alembic upgrade head`, so that `env.py` picks up the correct URL regardless of what is hardcoded in `alembic.ini`.
3. WHEN the `alembic.ini` for a service has a hardcoded `sqlalchemy.url` pointing to SQLite or a wrong host (labor-service points to SQLite, architectural-service points to `localhost:4000` without SSL), THE Migration_Runner SHALL override it via the `DATABASE_URL` environment variable rather than modifying the file.
4. IF `alembic upgrade head` exits with a non-zero code, THEN THE Migration_Runner SHALL capture and display the full Alembic error output and halt setup for that service.
5. AFTER a successful migration, THE Migration_Runner SHALL run `alembic current` and verify the output contains `(head)` to confirm the migration was applied.

---

### Requirement 6: Service Startup Verification

**User Story:** As a developer, I want to verify each service can actually start and respond to HTTP requests, so that I know the environment is fully operational and not just "installed".

#### Acceptance Criteria

1. THE Setup_Orchestrator SHALL start each service using `uvicorn src.main:app --host 127.0.0.1 --port {service_port}` with the service's Venv Python, with a startup timeout of 30 seconds.
2. WHEN the service has started, THE Setup_Orchestrator SHALL send an HTTP GET request to `http://127.0.0.1:{service_port}/health` and verify the response status code is 200.
3. IF the health check returns a non-200 status code, THEN THE Setup_Orchestrator SHALL capture the response body and report it as a startup failure for that service.
4. IF the service process does not start within 30 seconds, THEN THE Setup_Orchestrator SHALL terminate the process and report a startup timeout failure.
5. AFTER the health check completes (pass or fail), THE Setup_Orchestrator SHALL terminate the service process before proceeding to the next step.
6. THE Setup_Orchestrator SHALL use the following port assignments: design-service=8004, architectural-service=8007, engineering-service=8008, labor-service=8006, vendor-service=8005, analytics-service=8009.

---

### Requirement 7: Integration Test Execution

**User Story:** As a developer, I want integration tests to run against the real TiDB database for each service, so that I can confirm the service logic works end-to-end and not just against SQLite mocks.

#### Acceptance Criteria

1. THE Setup_Orchestrator SHALL run integration tests for each service by executing `pytest tests/integration/ -v --tb=short` from within the service directory using the service's Venv Python.
2. THE Setup_Orchestrator SHALL set the `DATABASE_URL` environment variable to the TiDB connection string when invoking pytest, so that test conftest files pick up the real database.
3. WHEN a service's test conftest creates a test database schema (e.g., `CREATE DATABASE IF NOT EXISTS`), THE Setup_Orchestrator SHALL ensure the TiDB credentials have sufficient privileges to create schemas.
4. IF any integration test fails, THE Setup_Orchestrator SHALL report the test name, failure reason, and full traceback, then continue running remaining tests for that service.
5. THE Setup_Orchestrator SHALL report a per-service summary of passed, failed, and skipped integration tests.
6. WHEN a service has no `tests/integration/` directory, THE Setup_Orchestrator SHALL skip the integration test step and log that no integration tests were found.

---

### Requirement 8: Property-Based Test Execution

**User Story:** As a developer, I want property-based tests (Hypothesis) to run for services that have them, so that invariants and edge cases are verified as part of the environment validation.

#### Acceptance Criteria

1. WHEN a service directory contains a `tests/property/` subdirectory (architectural-service, engineering-service, labor-service), THE Setup_Orchestrator SHALL run `pytest tests/property/ -v --tb=short` using the service's Venv Python.
2. THE Setup_Orchestrator SHALL set `HYPOTHESIS_MAX_EXAMPLES=50` in the environment when running property tests to keep runtime reasonable during setup validation.
3. IF a property test fails and Hypothesis provides a shrunk counterexample, THE Setup_Orchestrator SHALL capture and display the full counterexample in the failure report.
4. THE Setup_Orchestrator SHALL run property tests after integration tests for the same service.
5. WHEN a service has no `tests/property/` directory, THE Setup_Orchestrator SHALL skip the property test step and log that no property tests were found.

---

### Requirement 9: Setup Verification Report

**User Story:** As a developer, I want a consolidated report of the setup outcome for all services, so that I can see at a glance which services are fully operational and which have failures.

#### Acceptance Criteria

1. THE Setup_Orchestrator SHALL produce a per-service status summary with the following fields: Venv status, dependency install status, .env configuration status, migration status, startup health check status, integration test result (pass/fail/skip), property test result (pass/fail/skip).
2. THE Setup_Orchestrator SHALL mark a service as "READY" only when all applicable steps have passed.
3. THE Setup_Orchestrator SHALL mark a service as "FAILED" and include the first failing step when any step fails.
4. WHEN all services are marked "READY", THE Setup_Orchestrator SHALL exit with code 0.
5. WHEN one or more services are marked "FAILED", THE Setup_Orchestrator SHALL exit with a non-zero code.
6. THE Setup_Orchestrator SHALL write the report to `setup-report.txt` in the repository root in addition to printing it to stdout.
