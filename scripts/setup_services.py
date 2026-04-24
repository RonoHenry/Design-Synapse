"""
scripts/setup_services.py

Orchestration script for setting up fully operational service environments
across the Python microservices monorepo on Windows.

Usage:
    python scripts/setup_services.py [--services svc1 svc2 ...] [--dry-run]
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Literal

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class ServiceConfig:
    """Per-service configuration used throughout the setup pipeline."""

    port: int
    db_scheme: str
    has_migrations: bool
    has_redis: bool
    has_celery: bool
    local_packages: list[str]
    has_property_tests: bool
    # Env var name used to inject the DB URL into pytest subprocess.
    # architectural-service and engineering-service read TEST_DATABASE_URL;
    # all others read DATABASE_URL directly.
    test_db_env_var: str = "DATABASE_URL"
    # Health check path (default /health, some services use /api/v1/health)
    health_path: str = "/health"


class StepStatus(Enum):
    OK = "OK"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


@dataclass
class ServiceResult:
    """Tracks the outcome of each pipeline step for a single service."""

    service: str
    venv_status: StepStatus = StepStatus.SKIPPED
    deps_status: StepStatus = StepStatus.SKIPPED
    env_status: StepStatus = StepStatus.SKIPPED
    migration_status: StepStatus = StepStatus.SKIPPED
    startup_status: StepStatus = StepStatus.SKIPPED
    integration_status: StepStatus = StepStatus.SKIPPED
    property_status: StepStatus = StepStatus.SKIPPED
    errors: list[str] = field(default_factory=list)

    def _step_statuses(self) -> list[StepStatus]:
        return [
            self.venv_status,
            self.deps_status,
            self.env_status,
            self.migration_status,
            self.startup_status,
            self.integration_status,
            self.property_status,
        ]

    @property
    def overall(self) -> Literal["READY", "FAILED"]:
        failed = [s for s in self._step_statuses() if s == StepStatus.FAILED]
        return "FAILED" if failed else "READY"


# ---------------------------------------------------------------------------
# SERVICE_TABLE
# ---------------------------------------------------------------------------

SERVICE_TABLE: dict[str, ServiceConfig] = {
    "design-service": ServiceConfig(
        port=8004,
        db_scheme="mysql+pymysql",
        has_migrations=True,
        has_redis=True,
        has_celery=True,
        local_packages=[],
        has_property_tests=False,
    ),
    "architectural-service": ServiceConfig(
        port=8007,
        db_scheme="mysql+asyncmy",
        has_migrations=True,
        has_redis=False,
        has_celery=False,
        local_packages=[],
        has_property_tests=True,
        test_db_env_var="TEST_DATABASE_URL",
        health_path="/api/v1/health/live",
    ),
    "engineering-service": ServiceConfig(
        port=8008,
        db_scheme="mysql+asyncmy",
        has_migrations=True,
        has_redis=False,
        has_celery=False,
        local_packages=[],
        has_property_tests=True,
        test_db_env_var="TEST_DATABASE_URL",
    ),
    "labor-service": ServiceConfig(
        port=8006,
        db_scheme="mysql+pymysql",
        has_migrations=True,
        has_redis=True,
        has_celery=False,
        local_packages=[],
        has_property_tests=True,
    ),
    "vendor-service": ServiceConfig(
        port=8005,
        db_scheme="mysql+pymysql",
        has_migrations=True,
        has_redis=False,
        has_celery=False,
        local_packages=[],  # Handled by requirements.txt with -e entries
        has_property_tests=False,
    ),
    "analytics-service": ServiceConfig(
        port=8009,
        db_scheme="mysql+pymysql",
        has_migrations=False,
        has_redis=False,
        has_celery=False,
        local_packages=[],
        has_property_tests=False,
    ),
}

# Required TiDB keys that must be present in the root .env
REQUIRED_TIDB_KEYS = [
    "DB_HOST",
    "DB_PORT",
    "DB_USERNAME",
    "DB_PASSWORD",
    "DB_DATABASE",
    "DB_SSL_CA",
]


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------


def load_root_env(path: str) -> dict[str, str]:
    """Parse the root .env file and return a dict of key-value pairs.

    Raises SystemExit listing any missing TiDB keys if they are absent.
    """
    env_vars: dict[str, str] = {}

    try:
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                # Skip blank lines and comments
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, _, value = line.partition("=")
                    key = key.strip()
                    value = value.strip()
                    # Strip surrounding quotes if present
                    if (
                        len(value) >= 2
                        and value[0] in ('"', "'")
                        and value[-1] == value[0]
                    ):
                        value = value[1:-1]
                    env_vars[key] = value
    except FileNotFoundError:
        print(f"ERROR: Root .env file not found at '{path}'", file=sys.stderr)
        sys.exit(1)

    missing = [k for k in REQUIRED_TIDB_KEYS if k not in env_vars]
    if missing:
        print(
            f"ERROR: Root .env is missing required TiDB keys: {', '.join(missing)}",
            file=sys.stderr,
        )
        sys.exit(1)

    return env_vars


def build_database_url(config: ServiceConfig, env_vars: dict[str, str]) -> str:
    """Construct the full TiDB connection string for a service.

    For mysql+pymysql services:
        {scheme}://{user}:{pass}@{host}:{port}/{db}
            ?ssl_ca={abs_ssl_ca}&ssl_verify_cert=true&ssl_verify_identity=true

    For mysql+asyncmy services:
        {scheme}://{user}:{pass}@{host}:{port}/{db}?ssl_ca={abs_ssl_ca}
        (ssl_verify_cert / ssl_verify_identity are pymysql-specific and not
        accepted by asyncmy; SSL context is built from ssl_ca in the service)
    """
    scheme = config.db_scheme
    username = env_vars["DB_USERNAME"]
    password = env_vars["DB_PASSWORD"]
    host = env_vars["DB_HOST"]
    port = env_vars["DB_PORT"]
    database = env_vars["DB_DATABASE"]
    ssl_ca = env_vars["DB_SSL_CA"]

    # Resolve ssl_ca to an absolute path so it works regardless of cwd
    repo_root = Path(os.path.dirname(os.path.dirname(__file__)))
    ssl_ca_path = Path(ssl_ca)
    if not ssl_ca_path.is_absolute():
        ssl_ca_path = (repo_root / ssl_ca_path).resolve()
    ssl_ca_abs = str(ssl_ca_path)

    if scheme == "mysql+asyncmy":
        # asyncmy only accepts ssl_ca (not ssl_verify_cert/ssl_verify_identity)
        return (
            f"{scheme}://{username}:{password}@{host}:{port}/{database}"
            f"?ssl_ca={ssl_ca_abs}"
        )
    else:
        return (
            f"{scheme}://{username}:{password}@{host}:{port}/{database}"
            f"?ssl_ca={ssl_ca_abs}&ssl_verify_cert=true&ssl_verify_identity=true"
        )


# ---------------------------------------------------------------------------
# Pipeline step stubs (implemented in subsequent tasks)
# ---------------------------------------------------------------------------


def ensure_venv(service_dir: str, dry_run: bool = False) -> tuple[StepStatus, str]:
    """Create or verify the service venv. Recreate if broken.

    Returns (StepStatus.OK, "") on success, or
    (StepStatus.FAILED, error_message) on failure.
    """
    svc_path = Path(service_dir)
    venv_python = svc_path / ".venv" / "Scripts" / "python.exe"

    def _create_venv() -> tuple[bool, str]:
        """Run python -m venv .venv --copies in service_dir."""
        result = subprocess.run(
            [sys.executable, "-m", "venv", ".venv", "--copies"],
            cwd=service_dir,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            msg = result.stderr.strip() or result.stdout.strip()
            return False, f"venv creation failed: {msg}"
        return True, ""

    def _verify_venv() -> bool:
        """Return True if the venv python responds with exit code 0."""
        result = subprocess.run(
            [str(venv_python), "--version"],
            cwd=service_dir,
            capture_output=True,
            text=True,
        )
        return result.returncode == 0

    if dry_run:
        print(f"  [DRY RUN] Would ensure venv in {service_dir}")
        return StepStatus.OK, ""

    if venv_python.exists():
        # Venv already present — verify it works
        if _verify_venv():
            print(f"  [venv] Existing venv OK for {svc_path.name}")
            return StepStatus.OK, ""

        # Broken venv — delete and recreate
        print(
            f"  [venv] Broken venv detected for {svc_path.name},"
            " deleting and recreating..."
        )
        shutil.rmtree(svc_path / ".venv", ignore_errors=True)

    # Create fresh venv
    print(f"  [venv] Creating venv for {svc_path.name}...")
    ok, err = _create_venv()
    if not ok:
        return StepStatus.FAILED, err

    # Verify the newly created venv
    if not _verify_venv():
        return (
            StepStatus.FAILED,
            "venv created but python --version verification failed",
        )

    print(f"  [venv] Venv created successfully for {svc_path.name}")
    return StepStatus.OK, ""


def install_dependencies(
    service_dir: str,
    config: ServiceConfig,
    venv_pip: str,
    dry_run: bool = False,
) -> StepStatus:
    """pip upgrade, install local packages, requirements.txt, dev requirements.

    Steps (in order):
    1. pip install --upgrade pip
    2. For vendor-service: pip install -e <abs_path> for each local package
    3. pip install -r requirements.txt
    4. pip install -r ../../requirements-dev.txt  (if the file exists)

    Returns StepStatus.OK on success, StepStatus.FAILED on any non-zero exit.
    """
    if dry_run:
        print(f"  [DRY RUN] Would install dependencies in {service_dir}")
        return StepStatus.OK

    svc_path = Path(service_dir)
    repo_root = svc_path.parent.parent
    merged_env = os.environ.copy()

    def _run_pip(cmd: list[str], label: str) -> tuple[bool, str]:
        """Run a pip command; return (success, stderr_on_failure)."""
        result = subprocess.run(
            cmd,
            cwd=service_dir,
            env=merged_env,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            stderr = result.stderr.strip() or result.stdout.strip()
            print(
                f"  [deps] FAILED ({label}):\n{stderr}",
                file=sys.stderr,
            )
            return False, stderr
        return True, ""

    # Step 1: upgrade pip itself
    # On Windows, pip.exe cannot upgrade itself; use python -m pip instead
    venv_python_for_pip = str(Path(venv_pip).parent / "python.exe")
    ok, _ = _run_pip(
        [venv_python_for_pip, "-m", "pip", "install", "--upgrade", "pip"],
        "pip upgrade",
    )
    if not ok:
        return StepStatus.FAILED

    # Step 2: local editable packages (vendor-service only)
    for rel_pkg in config.local_packages:
        abs_pkg = str(repo_root / rel_pkg)
        ok, _ = _run_pip(
            [venv_pip, "install", "-e", abs_pkg],
            f"local package {rel_pkg}",
        )
        if not ok:
            return StepStatus.FAILED

    # Step 3: service requirements.txt
    ok, _ = _run_pip(
        [venv_pip, "install", "-r", "requirements.txt"],
        "requirements.txt",
    )
    if not ok:
        return StepStatus.FAILED

    # Step 4: root dev requirements (optional — only if file exists)
    dev_req = repo_root / "requirements-dev.txt"
    if dev_req.exists():
        ok, _ = _run_pip(
            [venv_pip, "install", "-r", "../../requirements-dev.txt"],
            "requirements-dev.txt",
        )
        if not ok:
            return StepStatus.FAILED

    print(f"  [deps] Dependencies installed for {svc_path.name}")
    return StepStatus.OK


def parse_env_file(path: str) -> dict[str, str]:
    """Read a key=value .env file and return an ordered dict.

    Skips blank lines and comments (#). Strips surrounding single or
    double quotes from values. Returns an empty dict if the file does
    not exist.
    """
    result: dict[str, str] = {}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, _, value = line.partition("=")
                    key = key.strip()
                    value = value.strip()
                    if (
                        len(value) >= 2
                        and value[0] in ('"', "'")
                        and value[-1] == value[0]
                    ):
                        value = value[1:-1]
                    result[key] = value
    except FileNotFoundError:
        pass
    return result


def write_env_file(path: str, data: dict[str, str]) -> None:
    """Write key=value pairs to *path*, one per line."""
    with open(path, "w", encoding="utf-8") as fh:
        for key, value in data.items():
            fh.write(f"{key}={value}\n")


def configure_env(
    service_dir: str,
    config: ServiceConfig,
    db_url: str,
    root_env: dict[str, str],
    dry_run: bool = False,
) -> StepStatus:
    """Write or update the service .env with DATABASE_URL and optional vars."""
    svc_name = os.path.basename(service_dir)

    # --- analytics-service: psycopg2-binary detection ---
    if svc_name == "analytics-service":
        req_path = os.path.join(service_dir, "requirements.txt")
        has_psycopg2 = False
        try:
            with open(req_path, "r", encoding="utf-8") as fh:
                for line in fh:
                    if line.strip().startswith("psycopg2-binary"):
                        has_psycopg2 = True
                        break
        except FileNotFoundError:
            pass

        if has_psycopg2:
            print(
                "analytics-service: psycopg2-binary detected"
                " \u2014 resolve before proceeding"
                " (replace with pymysql or provide"
                " ANALYTICS_DATABASE_URL)"
            )
            fallback = os.environ.get("ANALYTICS_DATABASE_URL")
            if fallback:
                print(
                    "  [env] analytics-service: using"
                    " ANALYTICS_DATABASE_URL as fallback"
                )
                db_url = fallback
            else:
                print(
                    "  [env] analytics-service: no fallback"
                    " available \u2014 skipping",
                    file=sys.stderr,
                )
                return StepStatus.FAILED

    # --- Read existing .env (empty dict if absent) ---
    env_path = os.path.join(service_dir, ".env")
    env_data = parse_env_file(env_path)

    # --- Always set DATABASE_URL ---
    env_data["DATABASE_URL"] = db_url

    # --- Conditionally set Redis / Celery vars ---
    if config.has_redis and "REDIS_URL" not in env_data:
        env_data["REDIS_URL"] = "redis://localhost:6379/0"

    if config.has_celery:
        if "CELERY_BROKER_URL" not in env_data:
            env_data["CELERY_BROKER_URL"] = "redis://localhost:6379/0"
        if "CELERY_RESULT_BACKEND" not in env_data:
            env_data["CELERY_RESULT_BACKEND"] = "redis://localhost:6379/0"

    # --- Dry-run: print and return without touching disk ---
    if dry_run:
        print(f"  [DRY RUN] Would write {env_path}:")
        for k, v in env_data.items():
            print(f"    {k}={v}")
        return StepStatus.OK

    # --- Write back ---
    write_env_file(env_path, env_data)
    print(f"  [env] Written {env_path}")
    return StepStatus.OK


def run_migrations(
    service_dir: str,
    db_url: str,
    venv_python: str,
    dry_run: bool = False,
) -> StepStatus:
    """Run alembic upgrade head and verify with alembic current.

    Injects DATABASE_URL into the subprocess environment so alembic env.py
    picks up the TiDB URL regardless of what is hardcoded in alembic.ini.

    If upgrade head fails because tables already exist (e.g. the schema was
    applied outside of alembic), stamps the revision to head so subsequent
    runs are idempotent.

    Returns SKIPPED when dry_run is True.
    """
    if dry_run:
        print("  [DRY RUN] Would run: alembic upgrade head")
        return StepStatus.SKIPPED

    merged_env = os.environ.copy()
    merged_env["DATABASE_URL"] = db_url

    def _alembic_current_is_head() -> bool:
        """Return True if alembic current reports (head)."""
        result = subprocess.run(
            [venv_python, "-m", "alembic", "current"],
            cwd=service_dir,
            env=merged_env,
            capture_output=True,
            text=True,
        )
        combined = result.stdout + result.stderr
        return "(head)" in combined

    # --- alembic upgrade head ---
    print("  [migration] Running alembic upgrade head ...")
    upgrade_result = subprocess.run(
        [venv_python, "-m", "alembic", "upgrade", "head"],
        cwd=service_dir,
        env=merged_env,
        capture_output=True,
        text=True,
    )
    if upgrade_result.returncode != 0:
        combined_err = upgrade_result.stdout + upgrade_result.stderr
        # Check if the failure is because tables already exist — if so, stamp head
        # Also handle stale/unknown revision in alembic_version table
        tables_exist = "already exists" in combined_err or (
            "Table" in combined_err and "exists" in combined_err
        )
        unknown_revision = "Can't locate revision identified by" in combined_err
        if tables_exist or unknown_revision:
            reason = (
                "Tables already exist in database"
                if tables_exist
                else "Unknown revision in alembic_version table"
            )
            print(
                f"  [migration] {reason};"
                " stamping alembic revision to head (--purge) ..."
            )
            stamp_result = subprocess.run(
                [venv_python, "-m", "alembic", "stamp", "--purge", "head"],
                cwd=service_dir,
                env=merged_env,
                capture_output=True,
                text=True,
            )
            if stamp_result.returncode != 0:
                print("  [migration] FAILED — alembic stamp --purge head failed")
                print("  [migration] stderr:", stamp_result.stderr)
                return StepStatus.FAILED
            print("  [migration] Stamped to head successfully")
        else:
            print(
                "  [migration] FAILED — alembic upgrade head returned non-zero exit code"
            )
            print("  [migration] stdout:", upgrade_result.stdout)
            print("  [migration] stderr:", upgrade_result.stderr)
            return StepStatus.FAILED
    else:
        print("  [migration] alembic upgrade head succeeded")

    # --- alembic current — verify (head) ---
    if not _alembic_current_is_head():
        current_result = subprocess.run(
            [venv_python, "-m", "alembic", "current"],
            cwd=service_dir,
            env=merged_env,
            capture_output=True,
            text=True,
        )
        print(
            "  [migration] FAILED — 'alembic current' output does not contain '(head)'"
        )
        print("  [migration] output:", current_result.stdout + current_result.stderr)
        return StepStatus.FAILED

    print("  [migration] Verified at head")
    return StepStatus.OK


def verify_startup(
    service_dir: str,
    config: ServiceConfig,
    venv_python: str,
    db_url: str,
    dry_run: bool = False,
) -> StepStatus:
    """Start uvicorn, poll /health, then always terminate the process.

    Launches uvicorn as a background subprocess with DATABASE_URL set,
    polls http://127.0.0.1:{port}/health every 2 seconds for up to 30
    seconds, then terminates the process regardless of outcome.
    """
    if dry_run:
        print(
            f"  [DRY RUN] Would start uvicorn on port {config.port}" " and poll /health"
        )
        return StepStatus.OK

    port = config.port
    health_url = f"http://127.0.0.1:{port}{config.health_path}"
    cmd = [
        venv_python,
        "-m",
        "uvicorn",
        "src.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
    ]

    # On Windows, asyncmy requires SelectorEventLoop for SSL.
    # Pass --loop asyncio so uvicorn uses asyncio.SelectorEventLoop
    # instead of the default ProactorEventLoop.
    if config.db_scheme == "mysql+asyncmy" and sys.platform == "win32":
        cmd += ["--loop", "asyncio"]

    merged_env = os.environ.copy()
    merged_env["DATABASE_URL"] = db_url

    print(f"  [startup] Launching uvicorn on port {port} ...")
    proc = subprocess.Popen(
        cmd,
        cwd=service_dir,
        env=merged_env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    status = StepStatus.FAILED
    try:
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            time.sleep(2)
            try:
                with urllib.request.urlopen(health_url, timeout=5) as resp:
                    if resp.status == 200:
                        print(f"  [startup] Health check OK" f" (HTTP {resp.status})")
                        status = StepStatus.OK
                        break
                    else:
                        body = resp.read().decode("utf-8", errors="replace")
                        print(
                            f"  [startup] Non-200 response" f" ({resp.status}): {body}"
                        )
                        status = StepStatus.FAILED
                        break
            except urllib.error.HTTPError as exc:
                body = exc.read().decode("utf-8", errors="replace")
                print(f"  [startup] HTTP error {exc.code}: {body}")
                status = StepStatus.FAILED
                break
            except (urllib.error.URLError, OSError):
                # Service not yet accepting connections — keep polling
                pass
        else:
            print(f"  [startup] Timed out waiting for {health_url}" " after 30 seconds")
            status = StepStatus.FAILED
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
        print(f"  [startup] uvicorn process terminated")

    return status


def run_integration_tests(
    service_dir: str,
    db_url: str,
    venv_python: str,
    config: ServiceConfig,
    dry_run: bool = False,
) -> StepStatus:
    """Run pytest tests/integration/ with the TiDB DATABASE_URL injected.

    Uses TEST_DATABASE_URL for services whose conftest reads that variable
    (architectural-service, engineering-service), and DATABASE_URL for all
    others (design-service uses TEST_DATABASE_URL too — handled via config).

    Returns:
        OK      – all tests passed (or no failures)
        FAILED  – one or more tests failed
        SKIPPED – tests/integration/ directory does not exist
    """
    integration_dir = os.path.join(service_dir, "tests", "integration")
    if not os.path.isdir(integration_dir):
        print("  [SKIP] No tests/integration/ directory found")
        return StepStatus.SKIPPED

    env_var_name = config.test_db_env_var
    print(
        f"  [INTEGRATION] Running pytest tests/integration/ "
        f"(injecting {env_var_name})"
    )

    if dry_run:
        print(
            f"  [DRY RUN] Would run: pytest tests/integration/ -v --tb=short "
            f"with {env_var_name}=<tidb_url>"
        )
        return StepStatus.OK

    merged_env = os.environ.copy()
    merged_env[env_var_name] = db_url

    result = subprocess.run(
        # --no-cov disables coverage collection so that --cov-fail-under
        # thresholds in pytest.ini don't cause false failures when the
        # setup script is only checking whether tests pass.
        [
            venv_python,
            "-m",
            "pytest",
            "tests/integration/",
            "-v",
            "--tb=short",
            "--no-cov",
        ],
        cwd=service_dir,
        env=merged_env,
        capture_output=True,
        text=True,
    )

    # Print output so the user can see progress
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)

    # Parse pass/fail/skip counts from pytest summary line
    # e.g. "5 passed, 2 failed, 1 skipped"
    output = result.stdout + result.stderr
    failed_count = _parse_pytest_count(output, "failed")
    error_count = _parse_pytest_count(output, "error")
    passed_count = _parse_pytest_count(output, "passed")
    skipped_count = _parse_pytest_count(output, "skipped")

    print(
        f"  [INTEGRATION] Results — passed: {passed_count}, "
        f"failed: {failed_count}, errors: {error_count}, "
        f"skipped: {skipped_count}"
    )

    if failed_count > 0 or error_count > 0:
        # Log tracebacks: pytest --tb=short already includes them in stdout
        print(f"  [INTEGRATION] FAILED — see output above for tracebacks")
        return StepStatus.FAILED

    return StepStatus.OK


def _parse_pytest_count(output: str, label: str) -> int:
    """Extract a count like '3 failed' or '5 passed' from pytest summary output."""
    import re

    match = re.search(rf"(\d+)\s+{re.escape(label)}", output)
    return int(match.group(1)) if match else 0


def run_property_tests(
    service_dir: str,
    db_url: str,
    venv_python: str,
    dry_run: bool = False,
) -> StepStatus:
    """Run pytest tests/property/ with HYPOTHESIS_MAX_EXAMPLES=50 and DATABASE_URL injected.

    Returns:
        OK      – all property tests passed
        FAILED  – one or more property tests failed
        SKIPPED – tests/property/ directory does not exist
    """
    property_dir = os.path.join(service_dir, "tests", "property")
    if not os.path.isdir(property_dir):
        print("  [SKIP] No tests/property/ directory found")
        return StepStatus.SKIPPED

    print("  [PROPERTY] Running pytest tests/property/ " "(HYPOTHESIS_MAX_EXAMPLES=50)")

    if dry_run:
        print(
            "  [DRY RUN] Would run: pytest tests/property/ -v --tb=short "
            "with HYPOTHESIS_MAX_EXAMPLES=50 and DATABASE_URL=<tidb_url>"
        )
        return StepStatus.OK

    merged_env = os.environ.copy()
    merged_env["DATABASE_URL"] = db_url
    merged_env["HYPOTHESIS_MAX_EXAMPLES"] = "50"

    result = subprocess.run(
        # --no-cov disables coverage collection so that --cov-fail-under
        # thresholds in pytest.ini don't cause false failures when the
        # setup script is only checking whether tests pass.
        [
            venv_python,
            "-m",
            "pytest",
            "tests/property/",
            "-v",
            "--tb=short",
            "--no-cov",
        ],
        cwd=service_dir,
        env=merged_env,
        capture_output=True,
        text=True,
    )

    output = result.stdout + result.stderr

    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)

    failed_count = _parse_pytest_count(output, "failed")
    error_count = _parse_pytest_count(output, "error")

    if failed_count > 0 or error_count > 0:
        # Extract and display Hypothesis counterexamples from output
        _print_hypothesis_counterexamples(output)
        print(
            f"  [PROPERTY] FAILED — " f"failed: {failed_count}, errors: {error_count}"
        )
        return StepStatus.FAILED

    passed_count = _parse_pytest_count(output, "passed")
    skipped_count = _parse_pytest_count(output, "skipped")
    print(f"  [PROPERTY] OK — passed: {passed_count}, skipped: {skipped_count}")
    return StepStatus.OK


def _print_hypothesis_counterexamples(output: str) -> None:
    """Extract and print Hypothesis shrunk counterexamples from pytest output."""
    import re

    # Hypothesis prints counterexamples in blocks starting with
    # "Falsifying example:" or "Falsifying explicit example:"
    blocks = re.findall(
        r"(Falsifying (?:explicit )?example:.*?)(?=\nFalsifying |\Z)",
        output,
        re.DOTALL,
    )
    if blocks:
        print("  [PROPERTY] Hypothesis counterexamples found:")
        for block in blocks:
            for line in block.strip().splitlines():
                print(f"    {line}")
    else:
        # Also surface any FAILED lines with Hypothesis shrink info
        for line in output.splitlines():
            if "Falsifying" in line or "Shrunk example" in line:
                print(f"  [PROPERTY] {line}")


def write_report(results: list[ServiceResult], path: str) -> None:
    """Format a per-service table, write to *path*, and print to stdout.

    Table columns: Service | Venv | Deps | Env | Migration | Startup |
                   Integration | Property | Overall

    StepStatus display: OK → ✓, FAILED → ✗, SKIPPED → -

    Error messages for FAILED services are printed below the table.
    """
    _STATUS_SYMBOL = {
        StepStatus.OK: "OK",
        StepStatus.FAILED: "FAIL",
        StepStatus.SKIPPED: "SKIP",
    }

    headers = [
        "Service",
        "Venv",
        "Deps",
        "Env",
        "Migration",
        "Startup",
        "Integration",
        "Property",
        "Overall",
    ]

    # Build rows
    rows: list[list[str]] = []
    for r in results:
        rows.append(
            [
                r.service,
                _STATUS_SYMBOL[r.venv_status],
                _STATUS_SYMBOL[r.deps_status],
                _STATUS_SYMBOL[r.env_status],
                _STATUS_SYMBOL[r.migration_status],
                _STATUS_SYMBOL[r.startup_status],
                _STATUS_SYMBOL[r.integration_status],
                _STATUS_SYMBOL[r.property_status],
                r.overall,
            ]
        )

    # Compute column widths
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(cell))

    def _fmt_row(cells: list[str]) -> str:
        return (
            "| "
            + " | ".join(cell.ljust(col_widths[i]) for i, cell in enumerate(cells))
            + " |"
        )

    separator = "+-" + "-+-".join("-" * w for w in col_widths) + "-+"

    lines: list[str] = []
    lines.append("SERVICE ENVIRONMENT SETUP REPORT")
    lines.append("=" * len(separator))
    lines.append(separator)
    lines.append(_fmt_row(headers))
    lines.append(separator)
    for row in rows:
        lines.append(_fmt_row(row))
    lines.append(separator)

    # Error details for failed services
    failed_results = [r for r in results if r.overall == "FAILED"]
    if failed_results:
        lines.append("")
        lines.append("ERRORS:")
        for r in failed_results:
            lines.append(f"  {r.service}:")
            for err in r.errors:
                lines.append(f"    - {err}")

    # Overall summary line
    lines.append("")
    ready_count = sum(1 for r in results if r.overall == "READY")
    failed_count = len(failed_results)
    lines.append(
        f"Summary: {ready_count}/{len(results)} services READY,"
        f" {failed_count} FAILED"
    )

    report_text = "\n".join(lines) + "\n"

    # Print to stdout
    print(report_text)

    # Write to file
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(report_text)

    print(f"[report] Written to {path}")


# ---------------------------------------------------------------------------
# CLI argument parsing
# ---------------------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Set up fully operational service environments for the monorepo.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--services",
        nargs="+",
        metavar="SERVICE",
        default=list(SERVICE_TABLE.keys()),
        help=(
            "Space-separated list of service names to set up. "
            f"Defaults to all: {', '.join(SERVICE_TABLE.keys())}"
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Print what would be done without executing any commands.",
    )
    return parser.parse_args(argv)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)

    # Validate requested service names
    unknown = [s for s in args.services if s not in SERVICE_TABLE]
    if unknown:
        print(f"ERROR: Unknown service(s): {', '.join(unknown)}", file=sys.stderr)
        print(f"Valid services: {', '.join(SERVICE_TABLE.keys())}", file=sys.stderr)
        sys.exit(1)

    # Load root .env — halts with SystemExit if missing or incomplete
    root_env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    root_env = load_root_env(root_env_path)

    if args.dry_run:
        print("[DRY RUN] No commands will be executed.\n")

    results: list[ServiceResult] = []

    for service_name in args.services:
        config = SERVICE_TABLE[service_name]
        service_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "apps", service_name
        )
        venv_python = os.path.join(service_dir, ".venv", "Scripts", "python.exe")

        print(f"\n{'='*60}")
        print(f"  Setting up: {service_name}")
        print(f"{'='*60}")

        result = ServiceResult(service=service_name)
        db_url = build_database_url(config, root_env)

        # Step 1: Venv
        try:
            venv_status, venv_err = ensure_venv(service_dir, dry_run=args.dry_run)
            result.venv_status = venv_status
            if venv_err:
                result.errors.append(f"venv: {venv_err}")
        except NotImplementedError:
            result.venv_status = StepStatus.SKIPPED

        if result.venv_status == StepStatus.FAILED:
            if not any(e.startswith("venv:") for e in result.errors):
                result.errors.append("venv: setup failed")
            results.append(result)
            continue

        # Step 2: Dependencies
        venv_pip = os.path.join(service_dir, ".venv", "Scripts", "pip.exe")
        try:
            result.deps_status = install_dependencies(
                service_dir, config, venv_pip, dry_run=args.dry_run
            )
        except NotImplementedError:
            result.deps_status = StepStatus.SKIPPED

        if result.deps_status == StepStatus.FAILED:
            result.errors.append("deps: installation failed")
            results.append(result)
            continue

        # Step 3: .env configuration
        try:
            result.env_status = configure_env(
                service_dir, config, db_url, root_env, dry_run=args.dry_run
            )
        except NotImplementedError:
            result.env_status = StepStatus.SKIPPED

        if result.env_status == StepStatus.FAILED:
            result.errors.append("env: configuration failed")
            results.append(result)
            continue

        # Step 4: Migrations (if applicable)
        if config.has_migrations:
            try:
                result.migration_status = run_migrations(
                    service_dir, db_url, venv_python, dry_run=args.dry_run
                )
            except NotImplementedError:
                result.migration_status = StepStatus.SKIPPED
        else:
            result.migration_status = StepStatus.SKIPPED

        if result.migration_status == StepStatus.FAILED:
            result.errors.append("migration: alembic upgrade failed")
            results.append(result)
            continue

        # Step 5: Startup health check
        try:
            result.startup_status = verify_startup(
                service_dir,
                config,
                venv_python,
                db_url,
                dry_run=args.dry_run,
            )
        except NotImplementedError:
            result.startup_status = StepStatus.SKIPPED

        if result.startup_status == StepStatus.FAILED:
            result.errors.append("startup: health check failed")
            results.append(result)
            continue

        # Step 6: Integration tests
        integration_dir = os.path.join(service_dir, "tests", "integration")
        if os.path.isdir(integration_dir):
            try:
                result.integration_status = run_integration_tests(
                    service_dir, db_url, venv_python, config, dry_run=args.dry_run
                )
            except NotImplementedError:
                result.integration_status = StepStatus.SKIPPED
        else:
            print(f"  [SKIP] No tests/integration/ directory found for {service_name}")
            result.integration_status = StepStatus.SKIPPED

        # Step 7: Property tests (if applicable)
        property_dir = os.path.join(service_dir, "tests", "property")
        if config.has_property_tests and os.path.isdir(property_dir):
            try:
                result.property_status = run_property_tests(
                    service_dir, db_url, venv_python, dry_run=args.dry_run
                )
            except NotImplementedError:
                result.property_status = StepStatus.SKIPPED
        else:
            if not config.has_property_tests:
                print(f"  [SKIP] Property tests not configured for {service_name}")
            else:
                print(f"  [SKIP] No tests/property/ directory found for {service_name}")
            result.property_status = StepStatus.SKIPPED

        results.append(result)

    # Final report
    print(f"\n{'='*60}")
    print("  SETUP SUMMARY")
    print(f"{'='*60}")
    for r in results:
        print(f"  {r.service:30s}  {r.overall}")
        if r.errors:
            for err in r.errors:
                print(f"    - {err}")

    report_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "setup-report.txt"
    )
    write_report(results, report_path)

    any_failed = any(r.overall == "FAILED" for r in results)
    sys.exit(1 if any_failed else 0)


if __name__ == "__main__":
    main()
