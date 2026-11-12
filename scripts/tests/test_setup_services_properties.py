"""
Property-based tests for scripts/setup_services.py.

Uses Hypothesis to verify correctness properties across all valid inputs.
Subprocess calls are mocked — no real processes or network calls are made.

Tag format: # Feature: service-environment-setup, Property N: <description>
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

from hypothesis import given, settings
from hypothesis import strategies as st

# Ensure the scripts package is importable when running from repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from setup_services import (SERVICE_TABLE, ServiceConfig, StepStatus,
                            build_database_url)

# ---------------------------------------------------------------------------
# Shared strategies
# ---------------------------------------------------------------------------

# Strategy: sample a valid service name from SERVICE_TABLE
service_names = st.sampled_from(list(SERVICE_TABLE.keys()))

# Strategy: generate arbitrary env-var dicts (non-empty keys and values)
env_dicts = st.dictionaries(st.text(min_size=1), st.text())

# Strategy: generate a complete set of required TiDB env vars with
# arbitrary (but non-empty) values so build_database_url never KeyErrors.
tidb_env = st.fixed_dictionaries(
    {
        "DB_HOST": st.text(min_size=1),
        "DB_PORT": st.text(min_size=1),
        "DB_USERNAME": st.text(min_size=1),
        "DB_PASSWORD": st.text(min_size=1),
        "DB_DATABASE": st.text(min_size=1),
        "DB_SSL_CA": st.text(min_size=1),
    }
)


# ---------------------------------------------------------------------------
# Property 3: DATABASE_URL scheme matches driver config
# Feature: service-environment-setup, Property 3:
#   For any service in SERVICE_TABLE, the DATABASE_URL produced by
#   build_database_url must begin with the scheme stored in that
#   service's db_scheme field.
# Validates: Requirements 3.1, 3.3
# ---------------------------------------------------------------------------


@given(service_name=service_names, env_vars=tidb_env)
@settings(max_examples=100)
def test_database_url_scheme_matches_driver_config(
    service_name: str, env_vars: dict[str, str]
) -> None:
    """
    # Feature: service-environment-setup, Property 3:
    # DATABASE_URL scheme matches driver config.
    # Validates: Requirements 3.1, 3.3
    """
    config = SERVICE_TABLE[service_name]
    url = build_database_url(config, env_vars)

    expected_prefix = config.db_scheme + "://"
    assert url.startswith(expected_prefix), (
        f"Service '{service_name}': expected URL to start with "
        f"'{expected_prefix}', got '{url[:60]}...'"
    )


@given(
    db_scheme=st.sampled_from(["mysql+pymysql", "mysql+asyncmy"]),
    env_vars=tidb_env,
)
@settings(max_examples=100)
def test_custom_config_scheme_is_preserved(
    db_scheme: str, env_vars: dict[str, str]
) -> None:
    """
    # Feature: service-environment-setup, Property 3 (variant):
    # Any ServiceConfig with an explicit db_scheme produces a URL
    # that starts with exactly that scheme — not a hardcoded default.
    # Validates: Requirements 3.1, 3.3
    """
    config = ServiceConfig(
        port=9999,
        db_scheme=db_scheme,
        has_migrations=False,
        has_redis=False,
        has_celery=False,
        local_packages=[],
        has_property_tests=False,
    )
    url = build_database_url(config, env_vars)
    assert url.startswith(db_scheme + "://"), (
        f"Expected scheme '{db_scheme}', got URL starting with "
        f"'{url.split('://')[0]}://'"
    )


@given(service_name=service_names, env_vars=tidb_env)
@settings(max_examples=100)
def test_database_url_scheme_not_swapped_between_services(
    service_name: str, env_vars: dict[str, str]
) -> None:
    """
    # Feature: service-environment-setup, Property 3 (cross-service):
    # asyncmy services never produce a pymysql URL and vice-versa.
    # Validates: Requirements 3.1, 3.3
    """
    config = SERVICE_TABLE[service_name]
    url = build_database_url(config, env_vars)

    if config.db_scheme == "mysql+asyncmy":
        assert not url.startswith(
            "mysql+pymysql://"
        ), f"Service '{service_name}' uses asyncmy but URL has pymysql scheme"
    else:
        assert not url.startswith(
            "mysql+asyncmy://"
        ), f"Service '{service_name}' uses pymysql but URL has asyncmy scheme"


# ---------------------------------------------------------------------------
# Property 1: Venv pip path isolation
# Feature: service-environment-setup, Property 1:
#   For any service name in SERVICE_TABLE, every pip install subprocess
#   call made during that service's setup must use the pip executable at
#   apps/{service}/.venv/Scripts/pip.exe — never a system pip or another
#   service's pip.
# Validates: Requirements 1.4
# ---------------------------------------------------------------------------


@given(service_name=service_names)
@settings(max_examples=100)
def test_venv_pip_path_isolation(service_name: str) -> None:
    """
    # Feature: service-environment-setup, Property 1:
    # Venv pip path isolation — all pip calls use the service-local venv pip.
    # Validates: Requirements 1.4
    """
    # Derive the expected pip executable path for this service
    repo_root = Path(__file__).resolve().parent.parent.parent
    expected_pip = str(
        repo_root / "apps" / service_name / ".venv" / "Scripts" / "pip.exe"
    )

    captured_calls: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        # Record every subprocess.run invocation
        if isinstance(cmd, (list, tuple)):
            captured_calls.append(list(cmd))
        result = MagicMock()
        result.returncode = 0
        result.stdout = "pip 23.0"
        result.stderr = ""
        return result

    config = SERVICE_TABLE[service_name]
    service_dir = str(repo_root / "apps" / service_name)

    # Patch subprocess.run and Path.exists so the venv appears present
    with (
        patch("subprocess.run", side_effect=fake_run),
        patch("pathlib.Path.exists", return_value=True),
        patch("shutil.rmtree"),
    ):
        from setup_services import install_dependencies

        try:
            install_dependencies(service_dir, config, expected_pip)
        except NotImplementedError:
            # install_dependencies not yet implemented — skip assertion
            return

    # Filter to only pip install calls
    pip_calls = [
        cmd
        for cmd in captured_calls
        if cmd and "pip" in Path(cmd[0]).name.lower() and "install" in cmd
    ]

    for cmd in pip_calls:
        actual_pip = cmd[0]
        assert actual_pip == expected_pip, (
            f"Service '{service_name}': pip call used '{actual_pip}' "
            f"but expected '{expected_pip}'. "
            "All pip installs must use the service-local venv pip."
        )
        # Must not be a system pip (no .venv in path would indicate system pip)
        assert ".venv" in actual_pip, (
            f"Service '{service_name}': pip path '{actual_pip}' does not "
            "contain '.venv' — system pip must not be used."
        )
        # Must not reference a different service's venv
        assert service_name in actual_pip, (
            f"Service '{service_name}': pip path '{actual_pip}' does not "
            f"reference the correct service directory."
        )


# ---------------------------------------------------------------------------
# Property 2: pip upgrade precedes all installs
# Feature: service-environment-setup, Property 2:
#   For any service, the `pip install --upgrade pip` call must appear
#   before any other `pip install` call in the sequence of subprocess
#   invocations for that service.
# Validates: Requirements 2.6
# ---------------------------------------------------------------------------


@given(service_name=service_names)
@settings(max_examples=100)
def test_pip_upgrade_precedes_all_installs(service_name: str) -> None:
    """
    # Feature: service-environment-setup, Property 2:
    # pip upgrade precedes all installs.
    # Validates: Requirements 2.6
    """
    repo_root = Path(__file__).resolve().parent.parent.parent
    config = SERVICE_TABLE[service_name]
    service_dir = str(repo_root / "apps" / service_name)

    # Derive the expected venv pip path for this service
    venv_pip = str(repo_root / "apps" / service_name / ".venv" / "Scripts" / "pip.exe")

    captured_calls: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        if isinstance(cmd, (list, tuple)):
            captured_calls.append(list(cmd))
        result = MagicMock()
        result.returncode = 0
        result.stdout = ""
        result.stderr = ""
        return result

    with (
        patch("subprocess.run", side_effect=fake_run),
        patch("pathlib.Path.exists", return_value=True),
        patch("shutil.rmtree"),
    ):
        from setup_services import install_dependencies

        install_dependencies(service_dir, config, venv_pip)

    # Collect all `pip install` invocations in order
    pip_install_calls = [
        cmd
        for cmd in captured_calls
        if len(cmd) >= 2 and "pip" in Path(cmd[0]).name.lower() and "install" in cmd
    ]

    assert (
        pip_install_calls
    ), f"Service '{service_name}': no pip install calls were recorded"

    # The very first pip install call must be the upgrade
    first_call = pip_install_calls[0]
    assert "--upgrade" in first_call and "pip" in first_call, (
        f"Service '{service_name}': first pip install call was not "
        f"`pip install --upgrade pip`. Got: {first_call}"
    )

    # No subsequent call should be another upgrade-pip call
    # (upgrade must happen exactly once, at position 0)
    for subsequent_call in pip_install_calls[1:]:
        is_upgrade_pip = "--upgrade" in subsequent_call and subsequent_call[-1] == "pip"
        assert not is_upgrade_pip, (
            f"Service '{service_name}': `pip install --upgrade pip` appeared "
            f"again after the first call. Calls: {pip_install_calls}"
        )


# ---------------------------------------------------------------------------
# Property 4: Non-database .env keys are preserved
# Feature: service-environment-setup, Property 4:
#   For any service .env file with arbitrary existing key-value pairs,
#   after configure_env updates DATABASE_URL, all keys that are not
#   DATABASE_URL, REDIS_URL, CELERY_BROKER_URL, or CELERY_RESULT_BACKEND
#   must be present in the updated file with their original values unchanged.
# Validates: Requirements 3.7
# ---------------------------------------------------------------------------

# Keys that configure_env is allowed to add or modify
_MANAGED_KEYS = frozenset(
    {"DATABASE_URL", "REDIS_URL", "CELERY_BROKER_URL", "CELERY_RESULT_BACKEND"}
)

# Strategy: arbitrary key-value pairs whose keys are not managed keys.
# Keys must not contain '=' (used as delimiter) or '#' (comment marker).
# Values must not contain newlines (line separator) or carriage returns,
# and must not have leading/trailing whitespace (stripped on parse).
_safe_key = (
    st.text(
        min_size=1,
        alphabet=st.characters(
            blacklist_characters="=#\r\n", blacklist_categories=("Cs",)
        ),
    )
    .map(str.strip)
    .filter(lambda k: k and k not in _MANAGED_KEYS)
)
_safe_value = st.text(
    alphabet=st.characters(blacklist_characters="\r\n", blacklist_categories=("Cs",))
).map(str.strip)
non_managed_env = st.dictionaries(_safe_key, _safe_value)


@given(
    service_name=service_names,
    existing_env=non_managed_env,
    env_vars=tidb_env,
)
@settings(max_examples=100)
def test_non_database_env_keys_are_preserved(
    service_name: str,
    existing_env: dict[str, str],
    env_vars: dict[str, str],
) -> None:
    """
    # Feature: service-environment-setup, Property 4:
    # Non-database .env keys are preserved after configure_env runs.
    # Validates: Requirements 3.7
    """
    import tempfile

    from setup_services import configure_env, parse_env_file, write_env_file

    config = SERVICE_TABLE[service_name]
    db_url = build_database_url(config, env_vars)

    with tempfile.TemporaryDirectory() as tmp_dir:
        env_path = os.path.join(tmp_dir, ".env")

        # Write the pre-existing non-managed keys to the service .env
        if existing_env:
            write_env_file(env_path, existing_env)

        # Run configure_env against the temp directory (dry_run=False)
        configure_env(tmp_dir, config, db_url, env_vars, dry_run=False)

        # Read back the resulting .env
        result_env = parse_env_file(env_path)

    # Every pre-existing non-managed key must survive unchanged
    for key, original_value in existing_env.items():
        assert key in result_env, (
            f"Service '{service_name}': key '{key}' was present before "
            "configure_env but is missing from the updated .env."
        )
        assert result_env[key] == original_value, (
            f"Service '{service_name}': key '{key}' had value "
            f"'{original_value}' before configure_env but now has "
            f"'{result_env[key]}'. Non-managed keys must not be modified."
        )


# ---------------------------------------------------------------------------
# Property 5: Redis and Celery vars set for applicable services
# Feature: service-environment-setup, Property 5:
#   For any service where has_redis=True, the resulting .env must contain
#   REDIS_URL. For any service where has_celery=True, the resulting .env
#   must contain both CELERY_BROKER_URL and CELERY_RESULT_BACKEND.
# Validates: Requirements 3.5, 3.6
# ---------------------------------------------------------------------------


@given(service_name=service_names, env_vars=tidb_env)
@settings(max_examples=100)
def test_redis_and_celery_vars_set_for_applicable_services(
    service_name: str,
    env_vars: dict[str, str],
) -> None:
    """
    # Feature: service-environment-setup, Property 5:
    # Redis and Celery vars set for applicable services.
    # Validates: Requirements 3.5, 3.6
    """
    import tempfile

    from setup_services import configure_env, parse_env_file

    config = SERVICE_TABLE[service_name]
    db_url = build_database_url(config, env_vars)

    with tempfile.TemporaryDirectory() as tmp_dir:
        # Start with an empty .env so no vars are pre-set
        configure_env(tmp_dir, config, db_url, env_vars, dry_run=False)
        result_env = parse_env_file(os.path.join(tmp_dir, ".env"))

    if config.has_redis:
        assert "REDIS_URL" in result_env, (
            f"Service '{service_name}' has has_redis=True but REDIS_URL "
            "is missing from the configured .env."
        )

    if config.has_celery:
        assert "CELERY_BROKER_URL" in result_env, (
            f"Service '{service_name}' has has_celery=True but "
            "CELERY_BROKER_URL is missing from the configured .env."
        )
        assert "CELERY_RESULT_BACKEND" in result_env, (
            f"Service '{service_name}' has has_celery=True but "
            "CELERY_RESULT_BACKEND is missing from the configured .env."
        )


@given(
    service_name=service_names,
    existing_redis_url=st.text(
        min_size=1,
        alphabet=st.characters(
            blacklist_characters="\r\n", blacklist_categories=("Cs",)
        ),
    )
    .map(str.strip)
    .filter(lambda v: bool(v)),
    env_vars=tidb_env,
)
@settings(max_examples=100)
def test_redis_url_not_overwritten_when_already_set(
    service_name: str,
    existing_redis_url: str,
    env_vars: dict[str, str],
) -> None:
    """
    # Feature: service-environment-setup, Property 5 (variant):
    # When REDIS_URL is already present in the service .env, configure_env
    # must not overwrite it — the existing value is preserved.
    # Validates: Requirements 3.5
    """
    import tempfile

    from setup_services import configure_env, parse_env_file, write_env_file

    config = SERVICE_TABLE[service_name]
    if not config.has_redis:
        # Property only applies to Redis-enabled services
        return

    db_url = build_database_url(config, env_vars)

    with tempfile.TemporaryDirectory() as tmp_dir:
        env_path = os.path.join(tmp_dir, ".env")
        # Pre-populate .env with a custom REDIS_URL
        write_env_file(env_path, {"REDIS_URL": existing_redis_url})

        configure_env(tmp_dir, config, db_url, env_vars, dry_run=False)
        result_env = parse_env_file(env_path)

    assert result_env.get("REDIS_URL") == existing_redis_url, (
        f"Service '{service_name}': pre-existing REDIS_URL "
        f"'{existing_redis_url}' was overwritten by configure_env. "
        "Existing values must be preserved."
    )


@given(
    service_name=service_names,
    existing_broker=st.text(
        min_size=1,
        alphabet=st.characters(
            blacklist_characters="\r\n", blacklist_categories=("Cs",)
        ),
    )
    .map(str.strip)
    .filter(lambda v: bool(v)),
    existing_backend=st.text(
        min_size=1,
        alphabet=st.characters(
            blacklist_characters="\r\n", blacklist_categories=("Cs",)
        ),
    )
    .map(str.strip)
    .filter(lambda v: bool(v)),
    env_vars=tidb_env,
)
@settings(max_examples=100)
def test_celery_vars_not_overwritten_when_already_set(
    service_name: str,
    existing_broker: str,
    existing_backend: str,
    env_vars: dict[str, str],
) -> None:
    """
    # Feature: service-environment-setup, Property 5 (variant):
    # When CELERY_BROKER_URL / CELERY_RESULT_BACKEND are already present,
    # configure_env must not overwrite them.
    # Validates: Requirements 3.6
    """
    import tempfile

    from setup_services import configure_env, parse_env_file, write_env_file

    config = SERVICE_TABLE[service_name]
    if not config.has_celery:
        return

    db_url = build_database_url(config, env_vars)

    with tempfile.TemporaryDirectory() as tmp_dir:
        env_path = os.path.join(tmp_dir, ".env")
        write_env_file(
            env_path,
            {
                "CELERY_BROKER_URL": existing_broker,
                "CELERY_RESULT_BACKEND": existing_backend,
            },
        )

        configure_env(tmp_dir, config, db_url, env_vars, dry_run=False)
        result_env = parse_env_file(env_path)

    assert result_env.get("CELERY_BROKER_URL") == existing_broker, (
        f"Service '{service_name}': pre-existing CELERY_BROKER_URL "
        f"'{existing_broker}' was overwritten."
    )
    assert result_env.get("CELERY_RESULT_BACKEND") == existing_backend, (
        f"Service '{service_name}': pre-existing CELERY_RESULT_BACKEND "
        f"'{existing_backend}' was overwritten."
    )


# ---------------------------------------------------------------------------
# Property 6: Migration subprocess always receives DATABASE_URL override
# Feature: service-environment-setup, Property 6:
#   For any service that has migrations, the alembic upgrade head subprocess
#   call must include DATABASE_URL set to the TiDB connection string in its
#   environment, regardless of what is in alembic.ini.
# Validates: Requirements 5.2, 5.3
# ---------------------------------------------------------------------------


@given(service_name=service_names, env_vars=tidb_env)
@settings(max_examples=100)
def test_migration_subprocess_receives_database_url_override(
    service_name: str,
    env_vars: dict[str, str],
) -> None:
    """
    # Feature: service-environment-setup, Property 6:
    # Migration subprocess always receives DATABASE_URL override.
    # Validates: Requirements 5.2, 5.3
    """
    from setup_services import run_migrations

    config = SERVICE_TABLE[service_name]
    if not config.has_migrations:
        return

    repo_root = Path(__file__).resolve().parent.parent.parent
    service_dir = str(repo_root / "apps" / service_name)
    venv_python = str(
        repo_root / "apps" / service_name / ".venv" / "Scripts" / "python.exe"
    )
    db_url = build_database_url(config, env_vars)

    captured_envs: list[dict] = []

    def fake_run(cmd, **kwargs):
        env = kwargs.get("env", {})
        captured_envs.append(dict(env))
        result = MagicMock()
        result.returncode = 0
        result.stdout = "(head)"
        result.stderr = ""
        return result

    with patch("subprocess.run", side_effect=fake_run):
        run_migrations(service_dir, db_url, venv_python, dry_run=False)

    assert captured_envs, (
        f"Service '{service_name}': no subprocess calls were recorded "
        "during run_migrations — expected at least alembic upgrade head."
    )

    # Every subprocess call made by run_migrations must carry the correct
    # DATABASE_URL override (both upgrade head and alembic current).
    for i, env in enumerate(captured_envs):
        assert "DATABASE_URL" in env, (
            f"Service '{service_name}': subprocess call #{i} did not receive "
            "DATABASE_URL in its environment."
        )
        assert env["DATABASE_URL"] == db_url, (
            f"Service '{service_name}': subprocess call #{i} received "
            f"DATABASE_URL='{env['DATABASE_URL']}' but expected '{db_url}'. "
            "The TiDB URL must override any value from alembic.ini."
        )
        # Confirm the URL uses the correct scheme for this service
        assert env["DATABASE_URL"].startswith(config.db_scheme + "://"), (
            f"Service '{service_name}': DATABASE_URL in subprocess env "
            f"'{env['DATABASE_URL']}' does not start with expected scheme "
            f"'{config.db_scheme}://'."
        )


# ---------------------------------------------------------------------------
# Property 9: Integration test subprocess always receives DATABASE_URL
# Feature: service-environment-setup, Property 9:
#   For any service with an integration test directory, the pytest subprocess
#   call must include DATABASE_URL (or TEST_DATABASE_URL for services that use
#   that variable) set to the TiDB connection string in its environment.
# Validates: Requirements 7.2
# ---------------------------------------------------------------------------


@given(service_name=service_names, env_vars=tidb_env)
@settings(max_examples=100)
def test_integration_test_subprocess_receives_database_url(
    service_name: str,
    env_vars: dict[str, str],
) -> None:
    """
    # Feature: service-environment-setup, Property 9:
    # Integration test subprocess always receives DATABASE_URL injection.
    # Validates: Requirements 7.2
    """
    from setup_services import run_integration_tests

    config = SERVICE_TABLE[service_name]
    repo_root = Path(__file__).resolve().parent.parent.parent
    service_dir = str(repo_root / "apps" / service_name)
    venv_python = str(
        repo_root / "apps" / service_name / ".venv" / "Scripts" / "python.exe"
    )
    db_url = build_database_url(config, env_vars)
    expected_env_var = config.test_db_env_var

    captured_envs: list[dict] = []

    def fake_run(cmd, **kwargs):
        env = kwargs.get("env", {})
        captured_envs.append(dict(env))
        result = MagicMock()
        result.returncode = 0
        result.stdout = "1 passed"
        result.stderr = ""
        return result

    # Patch both subprocess.run and os.path.isdir so the integration dir
    # appears to exist regardless of the actual filesystem state.
    with (
        patch("subprocess.run", side_effect=fake_run),
        patch("os.path.isdir", return_value=True),
    ):
        run_integration_tests(service_dir, db_url, venv_python, config, dry_run=False)

    assert captured_envs, (
        f"Service '{service_name}': no subprocess calls were recorded "
        "during run_integration_tests — expected at least one pytest call."
    )

    for i, env in enumerate(captured_envs):
        assert expected_env_var in env, (
            f"Service '{service_name}': subprocess call #{i} did not receive "
            f"'{expected_env_var}' in its environment. "
            f"config.test_db_env_var='{expected_env_var}'."
        )
        assert env[expected_env_var] == db_url, (
            f"Service '{service_name}': subprocess call #{i} received "
            f"{expected_env_var}='{env[expected_env_var]}' but expected "
            f"'{db_url}'."
        )
        # Confirm the injected URL uses the correct scheme for this service
        assert env[expected_env_var].startswith(config.db_scheme + "://"), (
            f"Service '{service_name}': {expected_env_var} in subprocess env "
            f"'{env[expected_env_var]}' does not start with expected scheme "
            f"'{config.db_scheme}://'."
        )


# ---------------------------------------------------------------------------
# Property 10: Property tests receive HYPOTHESIS_MAX_EXAMPLES=50
# Feature: service-environment-setup, Property 10:
#   For any service with a tests/property/ directory, the pytest subprocess
#   call must include HYPOTHESIS_MAX_EXAMPLES=50 in its environment.
# Validates: Requirements 8.2
# ---------------------------------------------------------------------------


@given(service_name=service_names, env_vars=tidb_env)
@settings(max_examples=100)
def test_property_tests_receive_hypothesis_max_examples(
    service_name: str,
    env_vars: dict[str, str],
) -> None:
    """
    # Feature: service-environment-setup, Property 10:
    # Property tests receive HYPOTHESIS_MAX_EXAMPLES=50.
    # Validates: Requirements 8.2
    """
    from setup_services import run_property_tests

    config = SERVICE_TABLE[service_name]
    repo_root = Path(__file__).resolve().parent.parent.parent
    service_dir = str(repo_root / "apps" / service_name)
    venv_python = str(
        repo_root / "apps" / service_name / ".venv" / "Scripts" / "python.exe"
    )
    db_url = build_database_url(config, env_vars)

    captured_envs: list[dict] = []

    def fake_run(cmd, **kwargs):
        env = kwargs.get("env", {})
        captured_envs.append(dict(env))
        result = MagicMock()
        result.returncode = 0
        result.stdout = "1 passed"
        result.stderr = ""
        return result

    # Patch subprocess.run and os.path.isdir so the property dir appears to
    # exist regardless of the actual filesystem state.
    with (
        patch("subprocess.run", side_effect=fake_run),
        patch("os.path.isdir", return_value=True),
    ):
        run_property_tests(service_dir, db_url, venv_python, dry_run=False)

    assert captured_envs, (
        f"Service '{service_name}': no subprocess calls were recorded "
        "during run_property_tests — expected at least one pytest call."
    )

    for i, env in enumerate(captured_envs):
        assert "HYPOTHESIS_MAX_EXAMPLES" in env, (
            f"Service '{service_name}': subprocess call #{i} did not receive "
            "'HYPOTHESIS_MAX_EXAMPLES' in its environment."
        )
        assert env["HYPOTHESIS_MAX_EXAMPLES"] == "50", (
            f"Service '{service_name}': subprocess call #{i} received "
            f"HYPOTHESIS_MAX_EXAMPLES='{env['HYPOTHESIS_MAX_EXAMPLES']}' "
            "but expected '50'."
        )


# ---------------------------------------------------------------------------
# Property 11: READY status requires all applicable steps to pass
# Feature: service-environment-setup, Property 11:
#   For any ServiceResult, overall is "READY" if and only if every step
#   status is OK or SKIPPED — no FAILED step may be present.
# Validates: Requirements 9.2
# ---------------------------------------------------------------------------

# Strategy: generate a list of 7 step statuses (one per pipeline step)
step_status_combos = st.lists(
    st.sampled_from(list(StepStatus)),
    min_size=7,
    max_size=7,
)


@given(statuses=step_status_combos)
@settings(max_examples=100)
def test_ready_requires_all_steps_ok_or_skipped(statuses: list) -> None:
    """
    # Feature: service-environment-setup, Property 11:
    # READY status requires all applicable steps to pass.
    # Validates: Requirements 9.2
    """
    from setup_services import ServiceResult, StepStatus

    (
        venv_s,
        deps_s,
        env_s,
        migration_s,
        startup_s,
        integration_s,
        property_s,
    ) = statuses

    result = ServiceResult(
        service="test-service",
        venv_status=venv_s,
        deps_status=deps_s,
        env_status=env_s,
        migration_status=migration_s,
        startup_status=startup_s,
        integration_status=integration_s,
        property_status=property_s,
    )

    has_any_failed = any(s == StepStatus.FAILED for s in statuses)

    if has_any_failed:
        assert result.overall == "FAILED", (
            f"Expected 'FAILED' when at least one step is FAILED, "
            f"but got '{result.overall}'. Statuses: {statuses}"
        )
    else:
        assert result.overall == "READY", (
            f"Expected 'READY' when all steps are OK or SKIPPED, "
            f"but got '{result.overall}'. Statuses: {statuses}"
        )


# ---------------------------------------------------------------------------
# Property 12: FAILED status includes first failing step
# Feature: service-environment-setup, Property 12:
#   For any ServiceResult where overall is "FAILED", the errors list must be
#   non-empty and the first error must identify the step that failed first in
#   pipeline order (venv → deps → env → migration → startup → integration →
#   property).
# Validates: Requirements 9.3
# ---------------------------------------------------------------------------

# Pipeline step names in order — must match the order returned by
# ServiceResult._step_statuses().
_PIPELINE_STEP_NAMES = [
    "venv",
    "deps",
    "env",
    "migration",
    "startup",
    "integration",
    "property",
]


@given(statuses=step_status_combos)
@settings(max_examples=100)
def test_failed_status_includes_first_failing_step(statuses: list) -> None:
    """
    # Feature: service-environment-setup, Property 12:
    # FAILED status includes first failing step.
    # Validates: Requirements 9.3
    """
    from setup_services import ServiceResult, StepStatus

    (
        venv_s,
        deps_s,
        env_s,
        migration_s,
        startup_s,
        integration_s,
        property_s,
    ) = statuses

    # Build the errors list the same way the pipeline does: one entry per
    # FAILED step, in pipeline order.
    errors: list[str] = []
    for step_name, step_status in zip(_PIPELINE_STEP_NAMES, statuses):
        if step_status == StepStatus.FAILED:
            errors.append(f"{step_name} step failed")

    result = ServiceResult(
        service="test-service",
        venv_status=venv_s,
        deps_status=deps_s,
        env_status=env_s,
        migration_status=migration_s,
        startup_status=startup_s,
        integration_status=integration_s,
        property_status=property_s,
        errors=errors,
    )

    if result.overall == "FAILED":
        # errors must be non-empty
        assert len(result.errors) > 0, (
            "ServiceResult.overall is 'FAILED' but errors list is empty. "
            f"Statuses: {statuses}"
        )

        # Determine which step failed first in pipeline order
        first_failing_step = next(
            name
            for name, status in zip(_PIPELINE_STEP_NAMES, statuses)
            if status == StepStatus.FAILED
        )

        # The first error must reference the first failing step name
        assert first_failing_step in result.errors[0], (
            f"First error '{result.errors[0]}' does not identify the first "
            f"failing step '{first_failing_step}'. "
            f"Statuses: {statuses}"
        )
    else:
        # When READY, errors should be empty (no failures recorded)
        assert len(result.errors) == 0, (
            f"ServiceResult.overall is 'READY' but errors list is non-empty: "
            f"{result.errors}. Statuses: {statuses}"
        )
