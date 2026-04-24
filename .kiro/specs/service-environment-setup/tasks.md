# Implementation Plan: Service Environment Setup

## Overview

Implement `scripts/setup_services.py` — a single-file Python orchestration script that drives each of the six target services through a sequential pipeline: venv creation → dependency installation → `.env` configuration → Alembic migration → startup health check → integration tests → property tests → consolidated report. Also update three service conftests so integration tests can run against TiDB instead of SQLite.

## Tasks

- [x] 1. Create core script structure: ServiceConfig, ServiceResult, load_root_env, build_database_url
  - Create `scripts/setup_services.py` with the `ServiceConfig` dataclass (port, db_scheme, has_migrations, has_redis, has_celery, local_packages, has_property_tests)
  - Create the `StepStatus` enum (OK, FAILED, SKIPPED) and `ServiceResult` dataclass with `overall` property
  - Populate `SERVICE_TABLE` dict with all six services per the design document
  - Implement `load_root_env(path)`: parse root `.env`, return dict, raise `SystemExit` listing missing TiDB keys if any are absent
  - Implement `build_database_url(config, env_vars)`: construct the full TiDB connection string using the service's `db_scheme` and the six root env keys
  - Add CLI arg parsing (`argparse`) for `--services` (default: all) and `--dry-run`
  - _Requirements: 1.1, 3.1, 3.2, 3.3, 3.8, 9.4, 9.5_

  - [x] 1.1 Write unit tests for load_root_env and build_database_url
    - Test `load_root_env` raises on missing keys, returns correct dict on valid file
    - Test `build_database_url` produces correct scheme for asyncmy vs pymysql services
    - Test `build_database_url` includes all SSL query params
    - _Requirements: 3.1, 3.2, 3.3, 3.8_

  - [x] 1.2 Write property test for build_database_url scheme correctness
    - **Property 3: DATABASE_URL scheme matches driver config**
    - **Validates: Requirements 3.1, 3.3**

- [x] 2. Implement venv setup step
  - Implement `ensure_venv(service_dir)`: create venv with `python -m venv .venv --copies` if absent; verify with `.venv/Scripts/python.exe --version`; delete and recreate if verification fails
  - Wire `ensure_venv` into the main pipeline loop, recording result in `ServiceResult.venv_status`
  - _Requirements: 1.1, 1.2, 1.3, 1.5_

  - [x] 2.1 Write unit tests for ensure_venv logic
    - Test that existing functional venv is not recreated
    - Test that broken venv (non-zero exit from python --version) triggers delete + recreate
    - _Requirements: 1.2, 1.3_

  - [x] 2.2 Write property test for venv pip path isolation
    - **Property 1: Venv pip path isolation**
    - **Validates: Requirements 1.4**

- [x] 3. Implement dependency installation step
  - Implement `install_dependencies(service_dir, config, venv_pip)`:
    - Run `pip install --upgrade pip` first
    - For vendor-service: install each local package in `config.local_packages` with `pip install -e <abs_path>`
    - Run `pip install -r requirements.txt`
    - Run `pip install -r ../../requirements-dev.txt` if the file exists
  - On any non-zero pip exit: log full stderr, set `deps_status=FAILED`, halt that service
  - _Requirements: 2.1, 2.2, 2.3, 2.5, 2.6_

  - [x] 3.1 Write unit tests for install_dependencies ordering
    - Test pip upgrade is called before requirements install
    - Test local packages are installed before requirements.txt for vendor-service
    - Test failure on non-zero pip exit sets correct status
    - _Requirements: 2.5, 2.6_

  - [x] 3.2 Write property test for pip upgrade ordering
    - **Property 2: pip upgrade precedes all installs**
    - **Validates: Requirements 2.6**

- [x] 4. Implement .env configuration step
  - Implement `parse_env_file(path)` and `write_env_file(path, data)`: read/write key=value files preserving order and non-target keys
  - Implement `configure_env(service_dir, config, db_url, root_env)`:
    - Read existing service `.env` (or start empty)
    - Set `DATABASE_URL` to the constructed TiDB URL
    - Set `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` only when applicable and not already set
    - Write back, preserving all other keys
  - Handle analytics-service psycopg2 detection: inspect `requirements.txt`, log blocking warning, check `ANALYTICS_DATABASE_URL` fallback, mark `env_status=FAILED` if unresolved
  - _Requirements: 3.1, 3.4, 3.5, 3.6, 3.7, 3.8, 4.1, 4.2, 4.3, 4.4_

  - [x] 4.1 Write unit tests for parse_env_file / write_env_file round-trip
    - Test that parse → write → parse produces identical dict
    - Test that DATABASE_URL is updated while other keys are preserved
    - _Requirements: 3.7_

  - [x] 4.2 Write property test for non-database key preservation
    - **Property 4: Non-database .env keys are preserved**
    - **Validates: Requirements 3.7**

  - [x] 4.3 Write property test for Redis and Celery vars
    - **Property 5: Redis and Celery vars set for applicable services**
    - **Validates: Requirements 3.5, 3.6**

- [x] 5. Implement Alembic migration step
  - Implement `run_migrations(service_dir, db_url, venv_python)`:
    - Run `alembic upgrade head` with `DATABASE_URL` injected into subprocess env
    - On non-zero exit: capture full output, set `migration_status=FAILED`, halt service
    - On success: run `alembic current` and verify output contains `(head)`; if not, set `migration_status=FAILED`
  - Skip this step (set `migration_status=SKIPPED`) for services with `has_migrations=False`
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

  - [x] 5.1 Write unit tests for run_migrations
    - Test DATABASE_URL is passed in subprocess env
    - Test non-zero alembic exit sets FAILED status
    - Test missing `(head)` in `alembic current` output sets FAILED
    - _Requirements: 5.2, 5.3, 5.4, 5.5_

  - [x] 5.2 Write property test for migration DATABASE_URL override
    - **Property 6: Migration subprocess always receives DATABASE_URL override**
    - **Validates: Requirements 5.2, 5.3**

- [x] 6. Implement startup health check step
  - Implement `verify_startup(service_dir, config, venv_python, db_url)`:
    - Launch `uvicorn src.main:app --host 127.0.0.1 --port {config.port}` as a subprocess with `DATABASE_URL` in env
    - Poll `http://127.0.0.1:{config.port}/health` every 2 seconds for up to 30 seconds
    - On 200 response: set `startup_status=OK`
    - On non-200 or timeout: log response body / timeout, set `startup_status=FAILED`
    - Always terminate the uvicorn process before returning
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6_

  - [x] 6.1 Write unit tests for verify_startup
    - Test correct port is used per service
    - Test process is terminated after health check regardless of outcome
    - Test timeout path sets FAILED status
    - _Requirements: 6.4, 6.5, 6.6_

  - [ ]* 6.2 Write property test for correct port per service
    - **Property 7: Correct port used for each service startup**
    - **Validates: Requirements 6.6**

  - [ ]* 6.3 Write property test for process termination guarantee
    - **Property 8: Service process is always terminated after health check**
    - **Validates: Requirements 6.5**

- [x] 7. Implement integration test execution step
  - Implement `run_integration_tests(service_dir, db_url, venv_python, config)`:
    - Check if `tests/integration/` exists; if not, set `integration_status=SKIPPED` and return
    - Run `pytest tests/integration/ -v --tb=short` with `DATABASE_URL` (or `TEST_DATABASE_URL` for architectural/engineering) injected into subprocess env
    - Parse pytest output for pass/fail/skip counts; set `integration_status=FAILED` if any failures, else `OK`
    - Log full tracebacks from pytest output on failure
  - _Requirements: 7.1, 7.2, 7.4, 7.5, 7.6_

  - [x] 7.1 Write unit tests for run_integration_tests
    - Test SKIPPED when no tests/integration/ directory
    - Test correct env var name used per service (DATABASE_URL vs TEST_DATABASE_URL)
    - _Requirements: 7.2, 7.6_

  - [x] 7.2 Write property test for integration test DATABASE_URL injection
    - **Property 9: Integration test subprocess always receives DATABASE_URL**
    - **Validates: Requirements 7.2**

- [x] 8. Implement property test execution step
  - Implement `run_property_tests(service_dir, db_url, venv_python)`:
    - Check if `tests/property/` exists; if not, set `property_status=SKIPPED` and return
    - Run `pytest tests/property/ -v --tb=short` with `HYPOTHESIS_MAX_EXAMPLES=50` and `DATABASE_URL` in subprocess env
    - Set `property_status=FAILED` if pytest exits non-zero, else `OK`
    - Capture and display Hypothesis counterexamples from output on failure
  - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

  - [x] 8.1 Write unit tests for run_property_tests
    - Test SKIPPED when no tests/property/ directory
    - Test HYPOTHESIS_MAX_EXAMPLES=50 is set in subprocess env
    - _Requirements: 8.2, 8.5_

  - [x] 8.2 Write property test for HYPOTHESIS_MAX_EXAMPLES setting
    - **Property 10: Property tests receive HYPOTHESIS_MAX_EXAMPLES=50**
    - **Validates: Requirements 8.2**

- [x] 9. Implement report generation
  - Implement `write_report(results, path)`: format a per-service table with all step statuses, overall READY/FAILED, and error messages
  - Write report to `setup-report.txt` in repo root and print to stdout
  - Exit with code 0 if all services READY, non-zero otherwise
  - Wire all steps together in the main pipeline loop
  - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6_

  - [x] 9.1 Write unit tests for ServiceResult.overall
    - Test READY only when all applicable steps are OK or SKIPPED
    - Test FAILED when any step is FAILED
    - Test first error in errors list identifies the first failing step
    - _Requirements: 9.2, 9.3_

  - [x] 9.2 Write property test for READY requires all steps OK
    - **Property 11: READY status requires all applicable steps to pass**
    - **Validates: Requirements 9.2**

  - [x] 9.3 Write property test for FAILED includes first failing step
    - **Property 12: FAILED status includes first failing step**
    - **Validates: Requirements 9.3**

- [x] 10. Checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 11. Update conftest.py for architectural-service to read TEST_DATABASE_URL
  - In `apps/architectural-service/tests/conftest.py`, update `test_engine` fixture:
    - Read `TEST_DATABASE_URL` from `os.environ`
    - If set, use it as the engine URL (with `NullPool`)
    - If not set, fall back to `sqlite+aiosqlite:///test_architectural.db` (existing behavior)
  - _Requirements: 7.2 (architectural-service uses TEST_DATABASE_URL per design)_

- [x] 12. Update conftest.py for engineering-service to read TEST_DATABASE_URL
  - In `apps/engineering-service/tests/conftest.py`, update `test_db_engine` fixture:
    - Read `TEST_DATABASE_URL` from `os.environ`
    - If set, use it as the engine URL
    - If not set, fall back to `sqlite+aiosqlite:///:memory:` (existing behavior)
  - _Requirements: 7.2 (engineering-service uses TEST_DATABASE_URL per design)_

- [x] 13. Update conftest.py for labor-service to not override DATABASE_URL if already set
  - In `apps/labor-service/tests/conftest.py`, change the module-level `os.environ["DATABASE_URL"] = "sqlite:///./test_labor_service.db"` line to only set the SQLite default when `DATABASE_URL` is not already present in the environment
  - Update `TEST_DATABASE_URL` and `test_engine` creation to use `os.environ.get("DATABASE_URL", "sqlite:///./test_labor_service.db")` so the script-injected TiDB URL takes effect
  - _Requirements: 7.2 (labor-service reads DATABASE_URL directly per design)_

- [x] 14. Write unit tests for pure functions in scripts/setup_services.py
  - Create `scripts/tests/test_setup_services.py`
  - Cover: `load_root_env` (missing keys, valid file), `build_database_url` (scheme selection, SSL params), `parse_env_file`/`write_env_file` round-trip, `ServiceResult.overall` (all combinations), port lookup per service, psycopg2 detection logic
  - _Requirements: 3.1, 3.2, 3.3, 3.7, 3.8, 4.1, 9.2, 9.3_

- [x] 15. Write property-based tests for the 12 correctness properties
  - Create `scripts/tests/test_setup_services_properties.py` using Hypothesis
  - Mock `subprocess.run` so no real processes are spawned
  - Implement one test per property, each tagged with `# Feature: service-environment-setup, Property N: ...`
  - Use `@settings(max_examples=100)` for all property tests
  - Generators: `st.sampled_from(list(SERVICE_TABLE.keys()))`, `st.dictionaries(st.text(min_size=1), st.text())`, `st.lists(st.sampled_from(StepStatus), min_size=7, max_size=7)`
  - _Requirements: 1.4, 2.6, 3.1, 3.3, 3.5, 3.6, 3.7, 5.2, 5.3, 6.5, 6.6, 7.2, 8.2, 9.2, 9.3_

- [x] 16. Execute the script for design-service and fix any issues found
  - Run `python scripts/setup_services.py --services design-service` from the repo root
  - Review output and `setup-report.txt`; fix any failures in the script or service config
  - _Requirements: 1–9 (all, for design-service)_

- [x] 17. Execute the script for architectural-service and fix any issues found
  - Run `python scripts/setup_services.py --services architectural-service`
  - Fix any issues; verify integration and property tests pass against TiDB
  - _Requirements: 1–9 (all, for architectural-service)_

- [x] 18. Execute the script for engineering-service and fix any issues found
  - Run `python scripts/setup_services.py --services engineering-service`
  - Fix any issues; verify integration and property tests pass against TiDB
  - _Requirements: 1–9 (all, for engineering-service)_

- [x] 19. Execute the script for labor-service and fix any issues found
  - Run `python scripts/setup_services.py --services labor-service`
  - Fix any issues; verify integration and property tests pass against TiDB
  - _Requirements: 1–9 (all, for labor-service)_

- [x] 20. Execute the script for vendor-service and fix any issues found
  - Run `python scripts/setup_services.py --services vendor-service`
  - Fix any issues; verify local package installs succeed and integration tests pass
  - _Requirements: 1–9 (all, for vendor-service)_

- [ ] 21. Execute the script for analytics-service and fix any issues found
  - Run `python scripts/setup_services.py --services analytics-service`
  - Resolve psycopg2 vs pymysql decision per Requirement 4; fix any issues
  - _Requirements: 1–9 (all, for analytics-service), 4.1–4.4_

- [ ] 22. Final checkpoint — Ensure all tests pass
  - Run `python scripts/setup_services.py` (all services) and confirm `setup-report.txt` shows all services READY
  - Ensure all unit and property tests in `scripts/tests/` pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Conftest updates (tasks 11–13) are prerequisites for integration test execution (tasks 16–21)
- Property tests mock subprocess.run — no real processes or network calls needed
- The script is idempotent: re-running on an already-set-up service detects the existing venv and proceeds
