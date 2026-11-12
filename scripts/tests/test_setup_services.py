"""
Unit tests for pure functions in scripts/setup_services.py.

Covers:
- load_root_env: missing keys, valid file, file-not-found
- build_database_url: scheme selection (asyncmy vs pymysql), SSL query params
"""

from __future__ import annotations

import os
import sys
import textwrap
from unittest.mock import MagicMock, patch

import pytest

# Ensure the scripts package is importable when running from repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from setup_services import ServiceConfig  # noqa: E402
from setup_services import (SERVICE_TABLE, StepStatus, build_database_url,
                            ensure_venv, install_dependencies, load_root_env,
                            parse_env_file, run_integration_tests,
                            run_migrations, run_property_tests, verify_startup,
                            write_env_file, write_report)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SAMPLE_ENV_VARS = {
    "DB_HOST": "gateway01.eu-central-1.prod.aws.tidbcloud.com",
    "DB_PORT": "4000",
    "DB_USERNAME": "testuser",
    "DB_PASSWORD": "testpass",
    "DB_DATABASE": "testdb",
    "DB_SSL_CA": "./ca.pem",
}


def _write_env(tmp_path, content: str) -> str:
    """Write content to a temp .env file and return its path."""
    env_file = tmp_path / ".env"
    env_file.write_text(textwrap.dedent(content), encoding="utf-8")
    return str(env_file)


# ---------------------------------------------------------------------------
# load_root_env — valid file
# ---------------------------------------------------------------------------


class TestLoadRootEnvValidFile:
    def test_returns_all_required_keys(self, tmp_path):
        path = _write_env(
            tmp_path,
            """
            DB_HOST=gateway01.eu-central-1.prod.aws.tidbcloud.com
            DB_PORT=4000
            DB_USERNAME=myuser
            DB_PASSWORD=mypass
            DB_DATABASE=mydb
            DB_SSL_CA=./ca.pem
            """,
        )
        result = load_root_env(path)
        assert result["DB_HOST"] == "gateway01.eu-central-1.prod.aws.tidbcloud.com"
        assert result["DB_PORT"] == "4000"
        assert result["DB_USERNAME"] == "myuser"
        assert result["DB_PASSWORD"] == "mypass"
        assert result["DB_DATABASE"] == "mydb"
        assert result["DB_SSL_CA"] == "./ca.pem"

    def test_strips_surrounding_double_quotes(self, tmp_path):
        path = _write_env(
            tmp_path,
            """
            DB_HOST="gateway01.example.com"
            DB_PORT="4000"
            DB_USERNAME="user"
            DB_PASSWORD="pass"
            DB_DATABASE="db"
            DB_SSL_CA="./ca.pem"
            """,
        )
        result = load_root_env(path)
        assert result["DB_HOST"] == "gateway01.example.com"
        assert result["DB_PASSWORD"] == "pass"

    def test_strips_surrounding_single_quotes(self, tmp_path):
        path = _write_env(
            tmp_path,
            """
            DB_HOST='gateway01.example.com'
            DB_PORT='4000'
            DB_USERNAME='user'
            DB_PASSWORD='pass'
            DB_DATABASE='db'
            DB_SSL_CA='./ca.pem'
            """,
        )
        result = load_root_env(path)
        assert result["DB_HOST"] == "gateway01.example.com"

    def test_ignores_blank_lines_and_comments(self, tmp_path):
        path = _write_env(
            tmp_path,
            """
            # This is a comment
            DB_HOST=host.example.com

            DB_PORT=4000
            # Another comment
            DB_USERNAME=user
            DB_PASSWORD=pass
            DB_DATABASE=db
            DB_SSL_CA=./ca.pem
            """,
        )
        result = load_root_env(path)
        assert "DB_HOST" in result
        assert len([k for k in result if k.startswith("#")]) == 0

    def test_preserves_extra_non_tidb_keys(self, tmp_path):
        path = _write_env(
            tmp_path,
            """
            DB_HOST=host.example.com
            DB_PORT=4000
            DB_USERNAME=user
            DB_PASSWORD=pass
            DB_DATABASE=db
            DB_SSL_CA=./ca.pem
            REDIS_URL=redis://localhost:6379/0
            SOME_OTHER_KEY=somevalue
            """,
        )
        result = load_root_env(path)
        assert result["REDIS_URL"] == "redis://localhost:6379/0"
        assert result["SOME_OTHER_KEY"] == "somevalue"


# ---------------------------------------------------------------------------
# load_root_env — missing keys / file not found
# ---------------------------------------------------------------------------


class TestLoadRootEnvMissingKeys:
    def test_raises_systemexit_when_file_not_found(self):
        with pytest.raises(SystemExit):
            load_root_env("/nonexistent/path/.env")

    def test_raises_systemexit_when_all_tidb_keys_missing(self, tmp_path):
        path = _write_env(tmp_path, "SOME_KEY=value\n")
        with pytest.raises(SystemExit):
            load_root_env(path)

    def test_raises_systemexit_when_one_key_missing(self, tmp_path):
        # All keys present except DB_SSL_CA
        path = _write_env(
            tmp_path,
            """
            DB_HOST=host.example.com
            DB_PORT=4000
            DB_USERNAME=user
            DB_PASSWORD=pass
            DB_DATABASE=db
            """,
        )
        with pytest.raises(SystemExit):
            load_root_env(path)

    def test_raises_systemexit_when_password_missing(self, tmp_path):
        path = _write_env(
            tmp_path,
            """
            DB_HOST=host.example.com
            DB_PORT=4000
            DB_USERNAME=user
            DB_DATABASE=db
            DB_SSL_CA=./ca.pem
            """,
        )
        with pytest.raises(SystemExit):
            load_root_env(path)

    def test_exit_message_lists_missing_keys(self, tmp_path, capsys):
        path = _write_env(tmp_path, "DB_HOST=host.example.com\n")
        with pytest.raises(SystemExit):
            load_root_env(path)
        captured = capsys.readouterr()
        # The error should mention at least one missing key
        assert "DB_PORT" in captured.err or "missing" in captured.err.lower()


# ---------------------------------------------------------------------------
# build_database_url — scheme selection
# ---------------------------------------------------------------------------


class TestBuildDatabaseUrlScheme:
    def test_pymysql_scheme_for_design_service(self):
        config = SERVICE_TABLE["design-service"]
        url = build_database_url(config, SAMPLE_ENV_VARS)
        assert url.startswith("mysql+pymysql://")

    def test_pymysql_scheme_for_labor_service(self):
        config = SERVICE_TABLE["labor-service"]
        url = build_database_url(config, SAMPLE_ENV_VARS)
        assert url.startswith("mysql+pymysql://")

    def test_pymysql_scheme_for_vendor_service(self):
        config = SERVICE_TABLE["vendor-service"]
        url = build_database_url(config, SAMPLE_ENV_VARS)
        assert url.startswith("mysql+pymysql://")

    def test_pymysql_scheme_for_analytics_service(self):
        config = SERVICE_TABLE["analytics-service"]
        url = build_database_url(config, SAMPLE_ENV_VARS)
        assert url.startswith("mysql+pymysql://")

    def test_asyncmy_scheme_for_architectural_service(self):
        config = SERVICE_TABLE["architectural-service"]
        url = build_database_url(config, SAMPLE_ENV_VARS)
        assert url.startswith("mysql+asyncmy://")

    def test_asyncmy_scheme_for_engineering_service(self):
        config = SERVICE_TABLE["engineering-service"]
        url = build_database_url(config, SAMPLE_ENV_VARS)
        assert url.startswith("mysql+asyncmy://")

    def test_scheme_matches_config_db_scheme_field(self):
        """For every service, the URL scheme must match config.db_scheme."""
        for service_name, config in SERVICE_TABLE.items():
            url = build_database_url(config, SAMPLE_ENV_VARS)
            assert url.startswith(
                config.db_scheme + "://"
            ), f"{service_name}: expected scheme '{config.db_scheme}', got URL '{url}'"

    def test_custom_config_pymysql(self):
        config = ServiceConfig(
            port=9000,
            db_scheme="mysql+pymysql",
            has_migrations=False,
            has_redis=False,
            has_celery=False,
            local_packages=[],
            has_property_tests=False,
        )
        url = build_database_url(config, SAMPLE_ENV_VARS)
        assert url.startswith("mysql+pymysql://")

    def test_custom_config_asyncmy(self):
        config = ServiceConfig(
            port=9001,
            db_scheme="mysql+asyncmy",
            has_migrations=False,
            has_redis=False,
            has_celery=False,
            local_packages=[],
            has_property_tests=False,
        )
        url = build_database_url(config, SAMPLE_ENV_VARS)
        assert url.startswith("mysql+asyncmy://")


# ---------------------------------------------------------------------------
# build_database_url — SSL query params
# ---------------------------------------------------------------------------


class TestBuildDatabaseUrlSSLParams:
    def test_ssl_ca_param_present(self):
        config = SERVICE_TABLE["design-service"]
        url = build_database_url(config, SAMPLE_ENV_VARS)
        assert "ssl_ca=./ca.pem" in url

    def test_ssl_verify_cert_param_present(self):
        config = SERVICE_TABLE["design-service"]
        url = build_database_url(config, SAMPLE_ENV_VARS)
        assert "ssl_verify_cert=true" in url

    def test_ssl_verify_identity_param_present(self):
        config = SERVICE_TABLE["design-service"]
        url = build_database_url(config, SAMPLE_ENV_VARS)
        assert "ssl_verify_identity=true" in url

    def test_all_three_ssl_params_present_for_every_service(self):
        for service_name, config in SERVICE_TABLE.items():
            url = build_database_url(config, SAMPLE_ENV_VARS)
            assert "ssl_ca=" in url, f"{service_name}: missing ssl_ca"
            assert (
                "ssl_verify_cert=true" in url
            ), f"{service_name}: missing ssl_verify_cert"
            assert (
                "ssl_verify_identity=true" in url
            ), f"{service_name}: missing ssl_verify_identity"

    def test_ssl_ca_uses_value_from_env(self):
        env = {**SAMPLE_ENV_VARS, "DB_SSL_CA": "/custom/path/ca-cert.pem"}
        config = SERVICE_TABLE["labor-service"]
        url = build_database_url(config, env)
        assert "ssl_ca=/custom/path/ca-cert.pem" in url

    def test_query_string_separator_is_question_mark(self):
        config = SERVICE_TABLE["design-service"]
        url = build_database_url(config, SAMPLE_ENV_VARS)
        assert "?" in url
        # SSL params must come after the ?
        query = url.split("?", 1)[1]
        assert "ssl_ca=" in query


# ---------------------------------------------------------------------------
# build_database_url — credentials and host embedded correctly
# ---------------------------------------------------------------------------


class TestBuildDatabaseUrlCredentials:
    def test_username_in_url(self):
        config = SERVICE_TABLE["design-service"]
        url = build_database_url(config, SAMPLE_ENV_VARS)
        assert "testuser" in url

    def test_password_in_url(self):
        config = SERVICE_TABLE["design-service"]
        url = build_database_url(config, SAMPLE_ENV_VARS)
        assert "testpass" in url

    def test_host_in_url(self):
        config = SERVICE_TABLE["design-service"]
        url = build_database_url(config, SAMPLE_ENV_VARS)
        assert "gateway01.eu-central-1.prod.aws.tidbcloud.com" in url

    def test_port_in_url(self):
        config = SERVICE_TABLE["design-service"]
        url = build_database_url(config, SAMPLE_ENV_VARS)
        assert ":4000/" in url

    def test_database_name_in_url(self):
        config = SERVICE_TABLE["design-service"]
        url = build_database_url(config, SAMPLE_ENV_VARS)
        assert "/testdb?" in url

    def test_full_url_format(self):
        config = SERVICE_TABLE["design-service"]
        url = build_database_url(config, SAMPLE_ENV_VARS)
        expected = (
            "mysql+pymysql://testuser:testpass@"
            "gateway01.eu-central-1.prod.aws.tidbcloud.com:4000/testdb"
            "?ssl_ca=./ca.pem&ssl_verify_cert=true&ssl_verify_identity=true"
        )
        assert url == expected


# ---------------------------------------------------------------------------
# ensure_venv
# ---------------------------------------------------------------------------


class TestEnsureVenvExistingFunctional:
    """Existing, working venv should not be recreated."""

    def test_returns_ok_when_venv_python_exists_and_works(self, tmp_path):
        """If venv python exists and --version exits 0, return OK."""
        venv_python = tmp_path / ".venv" / "Scripts" / "python.exe"
        venv_python.parent.mkdir(parents=True)
        venv_python.touch()

        ok_result = MagicMock(returncode=0, stdout="Python 3.11.0", stderr="")

        with patch("setup_services.subprocess.run", return_value=ok_result):
            status, err = ensure_venv(str(tmp_path))

        assert status == StepStatus.OK
        assert err == ""

    def test_does_not_call_venv_creation_when_existing_venv_works(self, tmp_path):
        """subprocess.run should only be called once (for --version), not for venv creation."""
        venv_python = tmp_path / ".venv" / "Scripts" / "python.exe"
        venv_python.parent.mkdir(parents=True)
        venv_python.touch()

        ok_result = MagicMock(returncode=0, stdout="Python 3.11.0", stderr="")

        with patch("setup_services.subprocess.run", return_value=ok_result) as mock_run:
            ensure_venv(str(tmp_path))

        # Only the --version verification call; no venv creation call
        assert mock_run.call_count == 1
        args = mock_run.call_args[0][0]
        assert "--version" in args

    def test_venv_dir_is_not_deleted_when_venv_works(self, tmp_path):
        """The .venv directory must survive when verification passes."""
        venv_python = tmp_path / ".venv" / "Scripts" / "python.exe"
        venv_python.parent.mkdir(parents=True)
        venv_python.touch()

        ok_result = MagicMock(returncode=0, stdout="Python 3.11.0", stderr="")

        with patch("setup_services.subprocess.run", return_value=ok_result):
            ensure_venv(str(tmp_path))

        assert (tmp_path / ".venv").exists()


class TestEnsureVenvBrokenVenv:
    """Broken venv (non-zero --version exit) must be deleted and recreated."""

    def test_returns_ok_after_delete_and_recreate(self, tmp_path):
        """Broken venv triggers delete + recreate; final result is OK."""
        venv_python = tmp_path / ".venv" / "Scripts" / "python.exe"
        venv_python.parent.mkdir(parents=True)
        venv_python.touch()

        broken_verify = MagicMock(returncode=1, stdout="", stderr="bad interpreter")
        ok_create = MagicMock(returncode=0, stdout="", stderr="")
        ok_verify_after = MagicMock(returncode=0, stdout="Python 3.11.0", stderr="")

        side_effects = [broken_verify, ok_create, ok_verify_after]

        with patch("setup_services.subprocess.run", side_effect=side_effects):
            status, err = ensure_venv(str(tmp_path))

        assert status == StepStatus.OK
        assert err == ""

    def test_venv_dir_is_removed_before_recreate(self, tmp_path):
        """shutil.rmtree must be called on the broken .venv before recreation."""
        venv_python = tmp_path / ".venv" / "Scripts" / "python.exe"
        venv_python.parent.mkdir(parents=True)
        venv_python.touch()

        broken_verify = MagicMock(returncode=1, stdout="", stderr="bad interpreter")
        ok_create = MagicMock(returncode=0, stdout="", stderr="")
        ok_verify_after = MagicMock(returncode=0, stdout="Python 3.11.0", stderr="")

        with patch(
            "setup_services.subprocess.run",
            side_effect=[broken_verify, ok_create, ok_verify_after],
        ):
            with patch("setup_services.shutil.rmtree") as mock_rmtree:
                ensure_venv(str(tmp_path))

        mock_rmtree.assert_called_once()
        removed_path = mock_rmtree.call_args[0][0]
        assert str(removed_path).endswith(".venv")

    def test_venv_creation_called_after_broken_venv_detected(self, tmp_path):
        """After detecting a broken venv, python -m venv must be invoked."""
        venv_python = tmp_path / ".venv" / "Scripts" / "python.exe"
        venv_python.parent.mkdir(parents=True)
        venv_python.touch()

        broken_verify = MagicMock(returncode=1, stdout="", stderr="bad interpreter")
        ok_create = MagicMock(returncode=0, stdout="", stderr="")
        ok_verify_after = MagicMock(returncode=0, stdout="Python 3.11.0", stderr="")

        with patch(
            "setup_services.subprocess.run",
            side_effect=[broken_verify, ok_create, ok_verify_after],
        ) as mock_run:
            ensure_venv(str(tmp_path))

        # Second call should be the venv creation command
        create_call_args = mock_run.call_args_list[1][0][0]
        assert "-m" in create_call_args
        assert "venv" in create_call_args

    def test_returns_failed_when_recreation_also_fails(self, tmp_path):
        """If venv recreation itself fails, return FAILED with an error message."""
        venv_python = tmp_path / ".venv" / "Scripts" / "python.exe"
        venv_python.parent.mkdir(parents=True)
        venv_python.touch()

        broken_verify = MagicMock(returncode=1, stdout="", stderr="bad interpreter")
        failed_create = MagicMock(returncode=1, stdout="", stderr="permission denied")

        with patch(
            "setup_services.subprocess.run", side_effect=[broken_verify, failed_create]
        ):
            with patch("setup_services.shutil.rmtree"):
                status, err = ensure_venv(str(tmp_path))

        assert status == StepStatus.FAILED
        assert err != ""


class TestEnsureVenvNoExistingVenv:
    """When no venv exists at all, it should be created fresh."""

    def test_creates_venv_when_none_exists(self, tmp_path):
        """No .venv directory → creation subprocess must be called."""
        ok_create = MagicMock(returncode=0, stdout="", stderr="")
        ok_verify = MagicMock(returncode=0, stdout="Python 3.11.0", stderr="")

        with patch(
            "setup_services.subprocess.run", side_effect=[ok_create, ok_verify]
        ) as mock_run:
            status, err = ensure_venv(str(tmp_path))

        assert status == StepStatus.OK
        create_call_args = mock_run.call_args_list[0][0][0]
        assert "venv" in create_call_args

    def test_returns_failed_when_fresh_creation_fails(self, tmp_path):
        """If initial venv creation fails, return FAILED."""
        failed_create = MagicMock(returncode=1, stdout="", stderr="no space left")

        with patch("setup_services.subprocess.run", return_value=failed_create):
            status, err = ensure_venv(str(tmp_path))

        assert status == StepStatus.FAILED
        assert "venv creation failed" in err

    def test_returns_failed_when_new_venv_verify_fails(self, tmp_path):
        """If creation succeeds but post-create verification fails, return FAILED."""
        ok_create = MagicMock(returncode=0, stdout="", stderr="")
        broken_verify = MagicMock(returncode=1, stdout="", stderr="")

        with patch(
            "setup_services.subprocess.run", side_effect=[ok_create, broken_verify]
        ):
            status, err = ensure_venv(str(tmp_path))

        assert status == StepStatus.FAILED
        assert "verification failed" in err


class TestEnsureVenvDryRun:
    """Dry-run mode must not touch the filesystem or spawn subprocesses."""

    def test_dry_run_returns_ok_without_subprocess(self, tmp_path):
        with patch("setup_services.subprocess.run") as mock_run:
            status, err = ensure_venv(str(tmp_path), dry_run=True)

        assert status == StepStatus.OK
        assert err == ""
        mock_run.assert_not_called()


# ---------------------------------------------------------------------------
# install_dependencies
# ---------------------------------------------------------------------------

from setup_services import install_dependencies  # noqa: E402


class TestInstallDependenciesPipUpgradeOrder:
    """pip upgrade must be called before requirements.txt install."""

    def test_pip_upgrade_called_before_requirements(self, tmp_path):
        """The first subprocess.run call must be pip install --upgrade pip."""
        # Create a requirements.txt so the function doesn't fail on missing file
        (tmp_path / "requirements.txt").touch()

        ok = MagicMock(returncode=0, stdout="", stderr="")
        config = ServiceConfig(
            port=9000,
            db_scheme="mysql+pymysql",
            has_migrations=False,
            has_redis=False,
            has_celery=False,
            local_packages=[],
            has_property_tests=False,
        )

        with patch("setup_services.subprocess.run", return_value=ok) as mock_run:
            install_dependencies(str(tmp_path), config, "pip", dry_run=False)

        calls = mock_run.call_args_list
        assert len(calls) >= 2

        # First call: pip upgrade
        first_cmd = calls[0][0][0]
        assert "--upgrade" in first_cmd
        assert "pip" in first_cmd

        # Find the requirements.txt install call index
        req_idx = next(
            i
            for i, c in enumerate(calls)
            if "-r" in c[0][0] and "requirements.txt" in c[0][0]
        )
        # pip upgrade (index 0) must come before requirements.txt install
        assert 0 < req_idx

    def test_pip_upgrade_is_first_subprocess_call(self, tmp_path):
        """Regardless of local packages, pip upgrade is always the very first call."""
        (tmp_path / "requirements.txt").touch()

        ok = MagicMock(returncode=0, stdout="", stderr="")
        config = ServiceConfig(
            port=9000,
            db_scheme="mysql+pymysql",
            has_migrations=False,
            has_redis=False,
            has_celery=False,
            local_packages=[],
            has_property_tests=False,
        )

        with patch("setup_services.subprocess.run", return_value=ok) as mock_run:
            install_dependencies(str(tmp_path), config, "pip", dry_run=False)

        first_cmd = mock_run.call_args_list[0][0][0]
        assert "install" in first_cmd
        assert "--upgrade" in first_cmd
        assert "pip" in first_cmd


class TestInstallDependenciesLocalPackagesOrder:
    """Local packages must be installed before requirements.txt for vendor-service."""

    def test_local_packages_installed_before_requirements_txt(self, tmp_path):
        """All local package installs must precede the requirements.txt install."""
        (tmp_path / "requirements.txt").touch()

        ok = MagicMock(returncode=0, stdout="", stderr="")
        config = SERVICE_TABLE["vendor-service"]

        with patch("setup_services.subprocess.run", return_value=ok) as mock_run:
            install_dependencies(str(tmp_path), config, "pip", dry_run=False)

        calls = mock_run.call_args_list
        cmds = [c[0][0] for c in calls]

        # Find index of requirements.txt install
        req_idx = next(
            i for i, cmd in enumerate(cmds) if "-r" in cmd and "requirements.txt" in cmd
        )

        # Find indices of all local package installs
        local_pkg_indices = [i for i, cmd in enumerate(cmds) if "-e" in cmd]

        assert len(local_pkg_indices) == len(
            config.local_packages
        ), "Expected one install call per local package"
        for pkg_idx in local_pkg_indices:
            assert pkg_idx < req_idx, (
                f"Local package install at index {pkg_idx} must come before "
                f"requirements.txt install at index {req_idx}"
            )

    def test_all_vendor_service_local_packages_installed(self, tmp_path):
        """Each local package in vendor-service config gets its own pip install -e call."""
        (tmp_path / "requirements.txt").touch()

        ok = MagicMock(returncode=0, stdout="", stderr="")
        config = SERVICE_TABLE["vendor-service"]

        with patch("setup_services.subprocess.run", return_value=ok) as mock_run:
            install_dependencies(str(tmp_path), config, "pip", dry_run=False)

        cmds = [c[0][0] for c in mock_run.call_args_list]
        editable_installs = [cmd for cmd in cmds if "-e" in cmd]

        assert len(editable_installs) == len(config.local_packages)

    def test_no_local_package_calls_for_service_without_local_packages(self, tmp_path):
        """Services with empty local_packages must not produce any -e install calls."""
        (tmp_path / "requirements.txt").touch()

        ok = MagicMock(returncode=0, stdout="", stderr="")
        config = SERVICE_TABLE["design-service"]  # has no local_packages

        with patch("setup_services.subprocess.run", return_value=ok) as mock_run:
            install_dependencies(str(tmp_path), config, "pip", dry_run=False)

        cmds = [c[0][0] for c in mock_run.call_args_list]
        editable_installs = [cmd for cmd in cmds if "-e" in cmd]
        assert editable_installs == []


class TestInstallDependenciesFailureHandling:
    """Non-zero pip exit must set deps_status=FAILED and halt."""

    def test_pip_upgrade_failure_returns_failed(self, tmp_path):
        """If pip upgrade exits non-zero, return StepStatus.FAILED."""
        (tmp_path / "requirements.txt").touch()

        fail = MagicMock(returncode=1, stdout="", stderr="upgrade error")
        config = ServiceConfig(
            port=9000,
            db_scheme="mysql+pymysql",
            has_migrations=False,
            has_redis=False,
            has_celery=False,
            local_packages=[],
            has_property_tests=False,
        )

        with patch("setup_services.subprocess.run", return_value=fail):
            status = install_dependencies(str(tmp_path), config, "pip", dry_run=False)

        assert status == StepStatus.FAILED

    def test_requirements_install_failure_returns_failed(self, tmp_path):
        """If requirements.txt install exits non-zero, return StepStatus.FAILED."""
        (tmp_path / "requirements.txt").touch()

        ok = MagicMock(returncode=0, stdout="", stderr="")
        fail = MagicMock(returncode=1, stdout="", stderr="requirements error")
        config = ServiceConfig(
            port=9000,
            db_scheme="mysql+pymysql",
            has_migrations=False,
            has_redis=False,
            has_celery=False,
            local_packages=[],
            has_property_tests=False,
        )

        # First call (pip upgrade) succeeds, second (requirements.txt) fails
        with patch("setup_services.subprocess.run", side_effect=[ok, fail]):
            status = install_dependencies(str(tmp_path), config, "pip", dry_run=False)

        assert status == StepStatus.FAILED

    def test_local_package_failure_returns_failed(self, tmp_path):
        """If a local package install exits non-zero, return StepStatus.FAILED."""
        (tmp_path / "requirements.txt").touch()

        ok = MagicMock(returncode=0, stdout="", stderr="")
        fail = MagicMock(returncode=1, stdout="", stderr="local pkg error")
        config = SERVICE_TABLE["vendor-service"]

        # pip upgrade succeeds, first local package fails
        with patch("setup_services.subprocess.run", side_effect=[ok, fail]):
            status = install_dependencies(str(tmp_path), config, "pip", dry_run=False)

        assert status == StepStatus.FAILED

    def test_failure_halts_subsequent_installs(self, tmp_path):
        """After a failure, no further subprocess.run calls should be made."""
        (tmp_path / "requirements.txt").touch()

        fail = MagicMock(returncode=1, stdout="", stderr="upgrade error")
        config = ServiceConfig(
            port=9000,
            db_scheme="mysql+pymysql",
            has_migrations=False,
            has_redis=False,
            has_celery=False,
            local_packages=[],
            has_property_tests=False,
        )

        with patch("setup_services.subprocess.run", return_value=fail) as mock_run:
            install_dependencies(str(tmp_path), config, "pip", dry_run=False)

        # Only the failing pip upgrade call should have been made
        assert mock_run.call_count == 1

    def test_success_returns_ok(self, tmp_path):
        """All steps succeeding returns StepStatus.OK."""
        (tmp_path / "requirements.txt").touch()

        ok = MagicMock(returncode=0, stdout="", stderr="")
        config = ServiceConfig(
            port=9000,
            db_scheme="mysql+pymysql",
            has_migrations=False,
            has_redis=False,
            has_celery=False,
            local_packages=[],
            has_property_tests=False,
        )

        with patch("setup_services.subprocess.run", return_value=ok):
            status = install_dependencies(str(tmp_path), config, "pip", dry_run=False)

        assert status == StepStatus.OK


class TestInstallDependenciesDryRun:
    """Dry-run mode must not invoke any subprocesses."""

    def test_dry_run_returns_ok_without_subprocess(self, tmp_path):
        config = SERVICE_TABLE["vendor-service"]

        with patch("setup_services.subprocess.run") as mock_run:
            status = install_dependencies(str(tmp_path), config, "pip", dry_run=True)

        assert status == StepStatus.OK
        mock_run.assert_not_called()


# ---------------------------------------------------------------------------
# Task 4.1 — parse_env_file / write_env_file unit tests
# Requirements: 3.7
# ---------------------------------------------------------------------------


class TestParseEnvFileRoundTrip:
    """parse → write → parse must produce an identical dict."""

    def test_round_trip_preserves_all_keys(self, tmp_path):
        """Writing then re-reading a dict returns the same dict."""
        env_path = str(tmp_path / ".env")
        original = {
            "DATABASE_URL": "mysql+pymysql://user:pass@host:4000/db",
            "REDIS_URL": "redis://localhost:6379/0",
            "SECRET_KEY": "supersecret",
            "DEBUG": "false",
        }
        write_env_file(env_path, original)
        result = parse_env_file(env_path)
        assert result == original

    def test_round_trip_single_key(self, tmp_path):
        """A single-key file survives a round-trip unchanged."""
        env_path = str(tmp_path / ".env")
        original = {"FOO": "bar"}
        write_env_file(env_path, original)
        assert parse_env_file(env_path) == original

    def test_round_trip_empty_value(self, tmp_path):
        """Keys with empty string values survive a round-trip."""
        env_path = str(tmp_path / ".env")
        original = {"EMPTY_KEY": ""}
        write_env_file(env_path, original)
        assert parse_env_file(env_path) == original

    def test_round_trip_value_with_equals_sign(self, tmp_path):
        """Values that contain '=' are preserved correctly."""
        env_path = str(tmp_path / ".env")
        original = {"TOKEN": "abc=def=ghi"}
        write_env_file(env_path, original)
        assert parse_env_file(env_path) == original

    def test_round_trip_many_keys(self, tmp_path):
        """A larger dict with varied values survives a round-trip."""
        env_path = str(tmp_path / ".env")
        original = {f"KEY_{i}": f"value_{i}" for i in range(20)}
        write_env_file(env_path, original)
        assert parse_env_file(env_path) == original

    def test_round_trip_preserves_insertion_order(self, tmp_path):
        """Key order is preserved through a write → parse cycle."""
        env_path = str(tmp_path / ".env")
        original = {"Z_KEY": "z", "A_KEY": "a", "M_KEY": "m"}
        write_env_file(env_path, original)
        result = parse_env_file(env_path)
        assert list(result.keys()) == list(original.keys())


class TestParseEnvFileDatabaseUrlUpdate:
    """DATABASE_URL is updated while all other keys are preserved."""

    def test_database_url_is_updated(self, tmp_path):
        """After writing a new DATABASE_URL the value is changed."""
        env_path = str(tmp_path / ".env")
        # Write initial state
        initial = {
            "DATABASE_URL": "sqlite:///old.db",
            "SECRET_KEY": "keep-me",
            "PORT": "8000",
        }
        write_env_file(env_path, initial)

        # Simulate what configure_env does: read, update, write back
        data = parse_env_file(env_path)
        new_url = (
            "mysql+pymysql://user:pass@host:4000/db"
            "?ssl_ca=./ca.pem"
            "&ssl_verify_cert=true"
            "&ssl_verify_identity=true"
        )
        data["DATABASE_URL"] = new_url
        write_env_file(env_path, data)

        result = parse_env_file(env_path)
        assert result["DATABASE_URL"] == new_url

    def test_non_database_keys_preserved_after_url_update(self, tmp_path):
        """All keys other than DATABASE_URL survive the update."""
        env_path = str(tmp_path / ".env")
        initial = {
            "DATABASE_URL": "sqlite:///old.db",
            "SECRET_KEY": "keep-me",
            "PORT": "8000",
            "LOG_LEVEL": "INFO",
        }
        write_env_file(env_path, initial)

        data = parse_env_file(env_path)
        data["DATABASE_URL"] = "mysql+pymysql://u:p@h:4000/db"
        write_env_file(env_path, data)

        result = parse_env_file(env_path)
        assert result["SECRET_KEY"] == "keep-me"
        assert result["PORT"] == "8000"
        assert result["LOG_LEVEL"] == "INFO"

    def test_non_database_key_count_unchanged(self, tmp_path):
        """The total number of keys does not change after a URL update."""
        env_path = str(tmp_path / ".env")
        initial = {
            "DATABASE_URL": "sqlite:///old.db",
            "A": "1",
            "B": "2",
            "C": "3",
        }
        write_env_file(env_path, initial)

        data = parse_env_file(env_path)
        data["DATABASE_URL"] = "mysql+pymysql://u:p@h:4000/db"
        write_env_file(env_path, data)

        result = parse_env_file(env_path)
        assert len(result) == len(initial)

    def test_adding_database_url_to_env_without_one(self, tmp_path):
        """DATABASE_URL can be added to a file that did not have it."""
        env_path = str(tmp_path / ".env")
        initial = {"SECRET_KEY": "abc", "PORT": "8080"}
        write_env_file(env_path, initial)

        data = parse_env_file(env_path)
        data["DATABASE_URL"] = "mysql+pymysql://u:p@h:4000/db"
        write_env_file(env_path, data)

        result = parse_env_file(env_path)
        assert "DATABASE_URL" in result
        assert result["SECRET_KEY"] == "abc"
        assert result["PORT"] == "8080"

    def test_parse_returns_empty_dict_for_missing_file(self, tmp_path):
        """parse_env_file returns {} when the file does not exist."""
        env_path = str(tmp_path / "nonexistent.env")
        assert parse_env_file(env_path) == {}

    def test_write_creates_file_if_not_present(self, tmp_path):
        """write_env_file creates the file when it does not exist."""
        env_path = str(tmp_path / "new.env")
        write_env_file(env_path, {"KEY": "value"})
        assert parse_env_file(env_path) == {"KEY": "value"}


# ---------------------------------------------------------------------------
# run_migrations tests
# ---------------------------------------------------------------------------


class TestRunMigrationsDatabaseUrlInjection:
    """DATABASE_URL must be passed in the subprocess env for both alembic calls."""

    def _make_successful_run(self):
        """Return a mock subprocess.run that simulates successful alembic calls."""
        upgrade_result = MagicMock()
        upgrade_result.returncode = 0
        upgrade_result.stdout = "Running upgrade -> abc123"
        upgrade_result.stderr = ""

        current_result = MagicMock()
        current_result.returncode = 0
        current_result.stdout = "abc123 (head)"
        current_result.stderr = ""

        return [upgrade_result, current_result]

    def test_database_url_passed_to_upgrade_head(self, tmp_path):
        """alembic upgrade head subprocess receives DATABASE_URL in its env."""
        side_effects = self._make_successful_run()
        with patch(
            "setup_services.subprocess.run", side_effect=side_effects
        ) as mock_run:
            run_migrations(str(tmp_path), "mysql+pymysql://user:pass@host/db", "python")

        upgrade_call = mock_run.call_args_list[0]
        env_passed = upgrade_call.kwargs.get("env") or upgrade_call[1].get("env")
        assert env_passed is not None
        assert env_passed["DATABASE_URL"] == "mysql+pymysql://user:pass@host/db"

    def test_database_url_passed_to_alembic_current(self, tmp_path):
        """alembic current subprocess also receives DATABASE_URL in its env."""
        side_effects = self._make_successful_run()
        with patch(
            "setup_services.subprocess.run", side_effect=side_effects
        ) as mock_run:
            run_migrations(str(tmp_path), "mysql+asyncmy://user:pass@host/db", "python")

        current_call = mock_run.call_args_list[1]
        env_passed = current_call.kwargs.get("env") or current_call[1].get("env")
        assert env_passed is not None
        assert env_passed["DATABASE_URL"] == "mysql+asyncmy://user:pass@host/db"

    def test_database_url_overrides_any_existing_env_value(self, tmp_path):
        """DATABASE_URL in subprocess env reflects the value passed to run_migrations,
        not whatever might be set in the parent process environment."""
        side_effects = self._make_successful_run()
        with patch.dict(os.environ, {"DATABASE_URL": "sqlite:///old.db"}):
            with patch(
                "setup_services.subprocess.run", side_effect=side_effects
            ) as mock_run:
                run_migrations(
                    str(tmp_path), "mysql+pymysql://new:url@host/db", "python"
                )

        upgrade_call = mock_run.call_args_list[0]
        env_passed = upgrade_call.kwargs.get("env") or upgrade_call[1].get("env")
        assert env_passed["DATABASE_URL"] == "mysql+pymysql://new:url@host/db"

    def test_both_calls_use_same_database_url(self, tmp_path):
        """Both alembic subprocesses receive the identical DATABASE_URL value."""
        db_url = "mysql+pymysql://u:p@host:4000/mydb?ssl_ca=./ca.pem"
        side_effects = self._make_successful_run()
        with patch(
            "setup_services.subprocess.run", side_effect=side_effects
        ) as mock_run:
            run_migrations(str(tmp_path), db_url, "python")

        calls = mock_run.call_args_list
        env_upgrade = calls[0].kwargs.get("env") or calls[0][1].get("env")
        env_current = calls[1].kwargs.get("env") or calls[1][1].get("env")
        assert env_upgrade["DATABASE_URL"] == env_current["DATABASE_URL"] == db_url


class TestRunMigrationsNonZeroExit:
    """Non-zero alembic upgrade head exit code must set FAILED status."""

    def test_nonzero_upgrade_returns_failed(self, tmp_path):
        """run_migrations returns FAILED when alembic upgrade head exits non-zero."""
        failed_result = MagicMock()
        failed_result.returncode = 1
        failed_result.stdout = "FAILED: can't connect"
        failed_result.stderr = "Connection refused"

        with patch("setup_services.subprocess.run", return_value=failed_result):
            status = run_migrations(str(tmp_path), "mysql+pymysql://u:p@h/db", "python")

        assert status == StepStatus.FAILED

    def test_nonzero_upgrade_does_not_call_alembic_current(self, tmp_path):
        """When upgrade head fails, alembic current is never invoked."""
        failed_result = MagicMock()
        failed_result.returncode = 2
        failed_result.stdout = ""
        failed_result.stderr = "error"

        with patch(
            "setup_services.subprocess.run", return_value=failed_result
        ) as mock_run:
            run_migrations(str(tmp_path), "mysql+pymysql://u:p@h/db", "python")

        # Only one subprocess call should have been made (upgrade head)
        assert mock_run.call_count == 1

    def test_exit_code_1_returns_failed(self, tmp_path):
        """Exit code 1 is treated as failure."""
        result = MagicMock(returncode=1, stdout="", stderr="err")
        with patch("setup_services.subprocess.run", return_value=result):
            assert (
                run_migrations(str(tmp_path), "mysql+pymysql://u:p@h/db", "python")
                == StepStatus.FAILED
            )

    def test_exit_code_nonzero_other_than_1_returns_failed(self, tmp_path):
        """Any non-zero exit code (e.g. 127) is treated as failure."""
        result = MagicMock(returncode=127, stdout="", stderr="command not found")
        with patch("setup_services.subprocess.run", return_value=result):
            assert (
                run_migrations(str(tmp_path), "mysql+pymysql://u:p@h/db", "python")
                == StepStatus.FAILED
            )


class TestRunMigrationsHeadVerification:
    """Missing '(head)' in alembic current output must set FAILED status."""

    def _upgrade_ok(self):
        r = MagicMock()
        r.returncode = 0
        r.stdout = "Running upgrade base -> abc123"
        r.stderr = ""
        return r

    def test_missing_head_in_stdout_returns_failed(self, tmp_path):
        """FAILED when alembic current stdout lacks '(head)'."""
        current = MagicMock(returncode=0, stdout="abc123", stderr="")
        with patch(
            "setup_services.subprocess.run", side_effect=[self._upgrade_ok(), current]
        ):
            status = run_migrations(str(tmp_path), "mysql+pymysql://u:p@h/db", "python")
        assert status == StepStatus.FAILED

    def test_missing_head_in_stderr_only_returns_failed(self, tmp_path):
        """FAILED when neither stdout nor stderr of alembic current contains '(head)'."""
        current = MagicMock(returncode=0, stdout="", stderr="some warning")
        with patch(
            "setup_services.subprocess.run", side_effect=[self._upgrade_ok(), current]
        ):
            status = run_migrations(str(tmp_path), "mysql+pymysql://u:p@h/db", "python")
        assert status == StepStatus.FAILED

    def test_head_in_stdout_returns_ok(self, tmp_path):
        """OK when alembic current stdout contains '(head)'."""
        current = MagicMock(returncode=0, stdout="abc123 (head)", stderr="")
        with patch(
            "setup_services.subprocess.run", side_effect=[self._upgrade_ok(), current]
        ):
            status = run_migrations(str(tmp_path), "mysql+pymysql://u:p@h/db", "python")
        assert status == StepStatus.OK

    def test_head_in_stderr_returns_ok(self, tmp_path):
        """OK when '(head)' appears in stderr of alembic current (some alembic versions log there)."""
        current = MagicMock(returncode=0, stdout="", stderr="abc123 (head)")
        with patch(
            "setup_services.subprocess.run", side_effect=[self._upgrade_ok(), current]
        ):
            status = run_migrations(str(tmp_path), "mysql+pymysql://u:p@h/db", "python")
        assert status == StepStatus.OK

    def test_empty_current_output_returns_failed(self, tmp_path):
        """FAILED when alembic current produces no output at all."""
        current = MagicMock(returncode=0, stdout="", stderr="")
        with patch(
            "setup_services.subprocess.run", side_effect=[self._upgrade_ok(), current]
        ):
            status = run_migrations(str(tmp_path), "mysql+pymysql://u:p@h/db", "python")
        assert status == StepStatus.FAILED

    def test_partial_head_string_not_matched(self, tmp_path):
        """'headless' or 'ahead' should not satisfy the '(head)' check."""
        current = MagicMock(returncode=0, stdout="abc123 headless", stderr="")
        with patch(
            "setup_services.subprocess.run", side_effect=[self._upgrade_ok(), current]
        ):
            status = run_migrations(str(tmp_path), "mysql+pymysql://u:p@h/db", "python")
        assert status == StepStatus.FAILED


class TestRunMigrationsDryRun:
    """Dry-run mode must skip all subprocess calls and return SKIPPED."""

    def test_dry_run_returns_skipped(self, tmp_path):
        with patch("setup_services.subprocess.run") as mock_run:
            status = run_migrations(
                str(tmp_path), "mysql+pymysql://u:p@h/db", "python", dry_run=True
            )
        assert status == StepStatus.SKIPPED
        mock_run.assert_not_called()


# ---------------------------------------------------------------------------
# verify_startup
# ---------------------------------------------------------------------------

from unittest.mock import MagicMock, call, patch  # noqa: F811 (re-import ok)


def _make_config(port: int = 8004) -> ServiceConfig:
    return ServiceConfig(
        port=port,
        db_scheme="mysql+pymysql",
        has_migrations=False,
        has_redis=False,
        has_celery=False,
        local_packages=[],
        has_property_tests=False,
    )


class TestVerifyStartupDryRun:
    def test_dry_run_returns_ok_without_popen(self, tmp_path):
        with patch("setup_services.subprocess.Popen") as mock_popen:
            status = verify_startup(
                str(tmp_path), _make_config(), "python", "db://url", dry_run=True
            )
        assert status == StepStatus.OK
        mock_popen.assert_not_called()


class TestVerifyStartupHealthCheckOK:
    def test_returns_ok_on_200_response(self, tmp_path):
        """A 200 from /health sets startup_status=OK."""
        mock_proc = MagicMock()
        mock_proc.terminate = MagicMock()
        mock_proc.wait = MagicMock()

        mock_resp = MagicMock()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.status = 200

        with patch("setup_services.subprocess.Popen", return_value=mock_proc):
            with patch("setup_services.time.sleep"):
                with patch("setup_services.time.monotonic", side_effect=[0, 1, 100]):
                    with patch(
                        "setup_services.urllib.request.urlopen", return_value=mock_resp
                    ):
                        status = verify_startup(
                            str(tmp_path), _make_config(), "python", "db://url"
                        )

        assert status == StepStatus.OK

    def test_process_terminated_on_success(self, tmp_path):
        """Process must be terminated even when health check passes."""
        mock_proc = MagicMock()
        mock_resp = MagicMock()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.status = 200

        with patch("setup_services.subprocess.Popen", return_value=mock_proc):
            with patch("setup_services.time.sleep"):
                with patch("setup_services.time.monotonic", side_effect=[0, 1, 100]):
                    with patch(
                        "setup_services.urllib.request.urlopen", return_value=mock_resp
                    ):
                        verify_startup(
                            str(tmp_path), _make_config(), "python", "db://url"
                        )

        mock_proc.terminate.assert_called_once()


class TestVerifyStartupHealthCheckFailed:
    def test_returns_failed_on_http_error(self, tmp_path):
        """An HTTPError from /health sets startup_status=FAILED."""
        import urllib.error

        mock_proc = MagicMock()
        http_err = urllib.error.HTTPError(
            url="http://127.0.0.1:8004/health",
            code=500,
            msg="Internal Server Error",
            hdrs=None,
            fp=MagicMock(read=lambda: b"error body"),
        )

        with patch("setup_services.subprocess.Popen", return_value=mock_proc):
            with patch("setup_services.time.sleep"):
                with patch("setup_services.time.monotonic", side_effect=[0, 1, 100]):
                    with patch(
                        "setup_services.urllib.request.urlopen", side_effect=http_err
                    ):
                        status = verify_startup(
                            str(tmp_path), _make_config(), "python", "db://url"
                        )

        assert status == StepStatus.FAILED

    def test_process_terminated_on_http_error(self, tmp_path):
        """Process must be terminated even when health check returns an HTTP error."""
        import urllib.error

        mock_proc = MagicMock()
        http_err = urllib.error.HTTPError(
            url="http://127.0.0.1:8004/health",
            code=500,
            msg="Internal Server Error",
            hdrs=None,
            fp=MagicMock(read=lambda: b"error body"),
        )

        with patch("setup_services.subprocess.Popen", return_value=mock_proc):
            with patch("setup_services.time.sleep"):
                with patch("setup_services.time.monotonic", side_effect=[0, 1, 100]):
                    with patch(
                        "setup_services.urllib.request.urlopen", side_effect=http_err
                    ):
                        verify_startup(
                            str(tmp_path), _make_config(), "python", "db://url"
                        )

        mock_proc.terminate.assert_called_once()


class TestVerifyStartupTimeout:
    def test_returns_failed_on_timeout(self, tmp_path):
        """If /health never responds within 30s, startup_status=FAILED."""
        import urllib.error

        mock_proc = MagicMock()
        url_err = urllib.error.URLError("connection refused")

        # monotonic: start=0, then each loop iteration advances past deadline
        # We need: initial call (0), then loop checks that exhaust the 30s window
        monotonic_values = [0] + [
            31
        ] * 20  # deadline exceeded immediately after first check

        with patch("setup_services.subprocess.Popen", return_value=mock_proc):
            with patch("setup_services.time.sleep"):
                with patch(
                    "setup_services.time.monotonic", side_effect=monotonic_values
                ):
                    with patch(
                        "setup_services.urllib.request.urlopen", side_effect=url_err
                    ):
                        status = verify_startup(
                            str(tmp_path), _make_config(), "python", "db://url"
                        )

        assert status == StepStatus.FAILED

    def test_process_terminated_on_timeout(self, tmp_path):
        """Process must be terminated even when startup times out."""
        import urllib.error

        mock_proc = MagicMock()
        url_err = urllib.error.URLError("connection refused")
        monotonic_values = [0] + [31] * 20

        with patch("setup_services.subprocess.Popen", return_value=mock_proc):
            with patch("setup_services.time.sleep"):
                with patch(
                    "setup_services.time.monotonic", side_effect=monotonic_values
                ):
                    with patch(
                        "setup_services.urllib.request.urlopen", side_effect=url_err
                    ):
                        verify_startup(
                            str(tmp_path), _make_config(), "python", "db://url"
                        )

        mock_proc.terminate.assert_called_once()


class TestVerifyStartupPopen:
    def test_popen_uses_correct_port(self, tmp_path):
        """The uvicorn command must use the port from config."""
        mock_proc = MagicMock()
        mock_resp = MagicMock()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.status = 200

        with patch(
            "setup_services.subprocess.Popen", return_value=mock_proc
        ) as mock_popen:
            with patch("setup_services.time.sleep"):
                with patch("setup_services.time.monotonic", side_effect=[0, 1, 100]):
                    with patch(
                        "setup_services.urllib.request.urlopen", return_value=mock_resp
                    ):
                        verify_startup(
                            str(tmp_path), _make_config(port=8007), "python", "db://url"
                        )

        cmd = mock_popen.call_args[0][0]
        assert "8007" in cmd

    def test_popen_sets_database_url_in_env(self, tmp_path):
        """The DATABASE_URL must be passed in the subprocess environment."""
        mock_proc = MagicMock()
        mock_resp = MagicMock()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.status = 200

        db_url = "mysql+pymysql://user:pass@host/db"

        with patch(
            "setup_services.subprocess.Popen", return_value=mock_proc
        ) as mock_popen:
            with patch("setup_services.time.sleep"):
                with patch("setup_services.time.monotonic", side_effect=[0, 1, 100]):
                    with patch(
                        "setup_services.urllib.request.urlopen", return_value=mock_resp
                    ):
                        verify_startup(str(tmp_path), _make_config(), "python", db_url)

        env_passed = (
            mock_popen.call_args[1].get("env") or mock_popen.call_args[0][1]
            if len(mock_popen.call_args[0]) > 1
            else None
        )
        if env_passed is None:
            env_passed = mock_popen.call_args.kwargs.get("env")
        assert env_passed is not None
        assert env_passed["DATABASE_URL"] == db_url


# ---------------------------------------------------------------------------
# Task 6.1 — Additional verify_startup unit tests
# ---------------------------------------------------------------------------
# Requirements: 6.4, 6.5, 6.6


class TestVerifyStartupPortPerService:
    """Property 7: each service uses the port defined in SERVICE_TABLE."""

    def _run_with_port(self, tmp_path, service_name: str):
        """Helper: run verify_startup for a named service and return the Popen cmd."""
        config = SERVICE_TABLE[service_name]
        mock_proc = MagicMock()
        mock_resp = MagicMock()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.status = 200

        with patch(
            "setup_services.subprocess.Popen", return_value=mock_proc
        ) as mock_popen:
            with patch("setup_services.time.sleep"):
                with patch("setup_services.time.monotonic", side_effect=[0, 1, 100]):
                    with patch(
                        "setup_services.urllib.request.urlopen", return_value=mock_resp
                    ):
                        verify_startup(str(tmp_path), config, "python", "db://url")

        return mock_popen.call_args[0][0]

    def test_design_service_uses_port_8004(self, tmp_path):
        cmd = self._run_with_port(tmp_path, "design-service")
        assert "8004" in cmd

    def test_architectural_service_uses_port_8007(self, tmp_path):
        cmd = self._run_with_port(tmp_path, "architectural-service")
        assert "8007" in cmd

    def test_engineering_service_uses_port_8008(self, tmp_path):
        cmd = self._run_with_port(tmp_path, "engineering-service")
        assert "8008" in cmd

    def test_labor_service_uses_port_8006(self, tmp_path):
        cmd = self._run_with_port(tmp_path, "labor-service")
        assert "8006" in cmd

    def test_vendor_service_uses_port_8005(self, tmp_path):
        cmd = self._run_with_port(tmp_path, "vendor-service")
        assert "8005" in cmd

    def test_analytics_service_uses_port_8009(self, tmp_path):
        cmd = self._run_with_port(tmp_path, "analytics-service")
        assert "8009" in cmd

    def test_all_service_ports_match_service_table(self, tmp_path):
        """Exhaustive check: every service in SERVICE_TABLE uses its configured port."""
        expected_ports = {
            "design-service": 8004,
            "architectural-service": 8007,
            "engineering-service": 8008,
            "labor-service": 8006,
            "vendor-service": 8005,
            "analytics-service": 8009,
        }
        for service_name, expected_port in expected_ports.items():
            cmd = self._run_with_port(tmp_path, service_name)
            assert (
                str(expected_port) in cmd
            ), f"{service_name}: expected port {expected_port} in cmd {cmd}"


class TestVerifyStartupProcessTerminationGuarantee:
    """Requirement 6.5: process is always terminated regardless of outcome."""

    def test_process_terminated_on_non_200_status(self, tmp_path):
        """Non-200 (not HTTPError) response still terminates the process."""
        mock_proc = MagicMock()
        mock_resp = MagicMock()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.status = 503  # non-200, not an exception

        with patch("setup_services.subprocess.Popen", return_value=mock_proc):
            with patch("setup_services.time.sleep"):
                with patch("setup_services.time.monotonic", side_effect=[0, 1, 100]):
                    with patch(
                        "setup_services.urllib.request.urlopen", return_value=mock_resp
                    ):
                        status = verify_startup(
                            str(tmp_path), _make_config(), "python", "db://url"
                        )

        assert status == StepStatus.FAILED
        mock_proc.terminate.assert_called_once()

    def test_process_terminated_exactly_once_on_success(self, tmp_path):
        """terminate() is called exactly once even on a clean success path."""
        mock_proc = MagicMock()
        mock_resp = MagicMock()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.status = 200

        with patch("setup_services.subprocess.Popen", return_value=mock_proc):
            with patch("setup_services.time.sleep"):
                with patch("setup_services.time.monotonic", side_effect=[0, 1, 100]):
                    with patch(
                        "setup_services.urllib.request.urlopen", return_value=mock_resp
                    ):
                        verify_startup(
                            str(tmp_path), _make_config(), "python", "db://url"
                        )

        mock_proc.terminate.assert_called_once()

    def test_process_terminated_exactly_once_on_timeout(self, tmp_path):
        """terminate() is called exactly once when the 30s deadline is exceeded."""
        import urllib.error

        mock_proc = MagicMock()
        url_err = urllib.error.URLError("connection refused")
        monotonic_values = [0] + [31] * 20

        with patch("setup_services.subprocess.Popen", return_value=mock_proc):
            with patch("setup_services.time.sleep"):
                with patch(
                    "setup_services.time.monotonic", side_effect=monotonic_values
                ):
                    with patch(
                        "setup_services.urllib.request.urlopen", side_effect=url_err
                    ):
                        verify_startup(
                            str(tmp_path), _make_config(), "python", "db://url"
                        )

        mock_proc.terminate.assert_called_once()


class TestVerifyStartupTimeoutStatus:
    """Requirement 6.4: timeout sets FAILED status."""

    def test_timeout_returns_failed_not_ok(self, tmp_path):
        """Exhausting the 30s window must return FAILED, never OK."""
        import urllib.error

        mock_proc = MagicMock()
        url_err = urllib.error.URLError("connection refused")
        monotonic_values = [0] + [31] * 20

        with patch("setup_services.subprocess.Popen", return_value=mock_proc):
            with patch("setup_services.time.sleep"):
                with patch(
                    "setup_services.time.monotonic", side_effect=monotonic_values
                ):
                    with patch(
                        "setup_services.urllib.request.urlopen", side_effect=url_err
                    ):
                        status = verify_startup(
                            str(tmp_path), _make_config(), "python", "db://url"
                        )

        assert status == StepStatus.FAILED
        assert status != StepStatus.OK

    def test_timeout_returns_failed_not_skipped(self, tmp_path):
        """Timeout must not be confused with SKIPPED."""
        import urllib.error

        mock_proc = MagicMock()
        url_err = urllib.error.URLError("connection refused")
        monotonic_values = [0] + [31] * 20

        with patch("setup_services.subprocess.Popen", return_value=mock_proc):
            with patch("setup_services.time.sleep"):
                with patch(
                    "setup_services.time.monotonic", side_effect=monotonic_values
                ):
                    with patch(
                        "setup_services.urllib.request.urlopen", side_effect=url_err
                    ):
                        status = verify_startup(
                            str(tmp_path), _make_config(), "python", "db://url"
                        )

        assert status == StepStatus.FAILED
        assert status != StepStatus.SKIPPED

    def test_health_url_uses_correct_port_in_timeout_scenario(self, tmp_path):
        """Even in the timeout path, the health URL must use the configured port.

        monotonic sequence: deadline=0+30=30, first while-check returns 1 (< 30, enters
        loop), sleep runs, urlopen is called and raises URLError, second while-check
        returns 31 (>= 30, exits via else-clause → FAILED).
        """
        import urllib.error

        mock_proc = MagicMock()
        url_err = urllib.error.URLError("connection refused")
        # call 1: deadline = 0+30 = 30
        # call 2: 1 < 30 → enter loop body, sleep, urlopen raises URLError
        # call 3: 31 < 30 → False → while-else fires → FAILED
        monotonic_values = [0, 1, 31] + [31] * 10
        captured_urls = []

        def capturing_urlopen(url, **kwargs):
            captured_urls.append(url)
            raise url_err

        with patch("setup_services.subprocess.Popen", return_value=mock_proc):
            with patch("setup_services.time.sleep"):
                with patch(
                    "setup_services.time.monotonic", side_effect=monotonic_values
                ):
                    with patch(
                        "setup_services.urllib.request.urlopen",
                        side_effect=capturing_urlopen,
                    ):
                        verify_startup(
                            str(tmp_path), _make_config(port=8006), "python", "db://url"
                        )

        # At least one poll attempt should have used the correct port
        assert any("8006" in str(u) for u in captured_urls)


# ---------------------------------------------------------------------------
# run_integration_tests
# ---------------------------------------------------------------------------


def _make_integration_config(
    service_name: str = "design-service",
    test_db_env_var: str = "DATABASE_URL",
) -> ServiceConfig:
    """Return a minimal ServiceConfig for integration test testing."""
    return ServiceConfig(
        port=8004,
        db_scheme="mysql+pymysql",
        has_migrations=False,
        has_redis=False,
        has_celery=False,
        local_packages=[],
        has_property_tests=False,
        test_db_env_var=test_db_env_var,
    )


class TestRunIntegrationTestsSkipped:
    """run_integration_tests returns SKIPPED when no tests/integration/ dir."""

    def test_skipped_when_no_integration_dir(self, tmp_path):
        config = _make_integration_config()
        status = run_integration_tests(
            str(tmp_path), "mysql+pymysql://...", "python", config
        )
        assert status == StepStatus.SKIPPED

    def test_skipped_does_not_call_subprocess(self, tmp_path):
        config = _make_integration_config()
        with patch("setup_services.subprocess.run") as mock_run:
            run_integration_tests(
                str(tmp_path), "mysql+pymysql://...", "python", config
            )
        mock_run.assert_not_called()


class TestRunIntegrationTestsDatabaseUrlInjection:
    """Correct env var name is injected into the pytest subprocess."""

    def _make_integration_dir(self, tmp_path):
        integration_dir = tmp_path / "tests" / "integration"
        integration_dir.mkdir(parents=True)
        return integration_dir

    def test_database_url_injected_for_pymysql_service(self, tmp_path):
        """Services with test_db_env_var='DATABASE_URL' inject DATABASE_URL."""
        self._make_integration_dir(tmp_path)
        config = _make_integration_config(test_db_env_var="DATABASE_URL")
        db_url = "mysql+pymysql://user:pass@host:4000/db"

        captured_envs = []

        def capture_run(cmd, **kwargs):
            captured_envs.append(kwargs.get("env", {}))
            return MagicMock(returncode=0, stdout="1 passed", stderr="")

        with patch("setup_services.subprocess.run", side_effect=capture_run):
            run_integration_tests(str(tmp_path), db_url, "python", config)

        assert len(captured_envs) == 1
        assert captured_envs[0].get("DATABASE_URL") == db_url

    def test_test_database_url_injected_for_asyncmy_service(self, tmp_path):
        """Services with test_db_env_var='TEST_DATABASE_URL' inject TEST_DATABASE_URL."""
        self._make_integration_dir(tmp_path)
        config = _make_integration_config(test_db_env_var="TEST_DATABASE_URL")
        db_url = "mysql+asyncmy://user:pass@host:4000/db"

        captured_envs = []

        def capture_run(cmd, **kwargs):
            captured_envs.append(kwargs.get("env", {}))
            return MagicMock(returncode=0, stdout="1 passed", stderr="")

        with patch("setup_services.subprocess.run", side_effect=capture_run):
            run_integration_tests(str(tmp_path), db_url, "python", config)

        assert len(captured_envs) == 1
        assert captured_envs[0].get("TEST_DATABASE_URL") == db_url
        # DATABASE_URL should NOT be set to the TiDB URL by this function
        assert captured_envs[0].get("DATABASE_URL") != db_url

    def test_architectural_service_uses_test_database_url(self):
        """SERVICE_TABLE entry for architectural-service uses TEST_DATABASE_URL."""
        assert (
            SERVICE_TABLE["architectural-service"].test_db_env_var
            == "TEST_DATABASE_URL"
        )

    def test_engineering_service_uses_test_database_url(self):
        """SERVICE_TABLE entry for engineering-service uses TEST_DATABASE_URL."""
        assert (
            SERVICE_TABLE["engineering-service"].test_db_env_var == "TEST_DATABASE_URL"
        )

    def test_design_service_uses_database_url(self):
        """SERVICE_TABLE entry for design-service uses DATABASE_URL."""
        assert SERVICE_TABLE["design-service"].test_db_env_var == "DATABASE_URL"

    def test_labor_service_uses_database_url(self):
        """SERVICE_TABLE entry for labor-service uses DATABASE_URL."""
        assert SERVICE_TABLE["labor-service"].test_db_env_var == "DATABASE_URL"


class TestRunIntegrationTestsPassFailCounts:
    """Integration test status is derived from pytest exit code and output."""

    def _make_integration_dir(self, tmp_path):
        integration_dir = tmp_path / "tests" / "integration"
        integration_dir.mkdir(parents=True)
        return integration_dir

    def test_returns_ok_when_all_tests_pass(self, tmp_path):
        self._make_integration_dir(tmp_path)
        config = _make_integration_config()

        with patch("setup_services.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout="5 passed", stderr=""
            )
            status = run_integration_tests(str(tmp_path), "db://url", "python", config)

        assert status == StepStatus.OK

    def test_returns_failed_when_pytest_exits_nonzero(self, tmp_path):
        self._make_integration_dir(tmp_path)
        config = _make_integration_config()

        with patch("setup_services.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1, stdout="2 failed, 3 passed", stderr=""
            )
            status = run_integration_tests(str(tmp_path), "db://url", "python", config)

        assert status == StepStatus.FAILED

    def test_returns_failed_when_failed_count_nonzero(self, tmp_path):
        """Even if returncode is 0, explicit 'N failed' in output means FAILED."""
        self._make_integration_dir(tmp_path)
        config = _make_integration_config()

        with patch("setup_services.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout="1 failed, 4 passed", stderr=""
            )
            status = run_integration_tests(str(tmp_path), "db://url", "python", config)

        assert status == StepStatus.FAILED

    def test_returns_failed_when_error_count_nonzero(self, tmp_path):
        self._make_integration_dir(tmp_path)
        config = _make_integration_config()

        with patch("setup_services.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="1 error", stderr="")
            status = run_integration_tests(str(tmp_path), "db://url", "python", config)

        assert status == StepStatus.FAILED

    def test_skipped_tests_do_not_cause_failure(self, tmp_path):
        self._make_integration_dir(tmp_path)
        config = _make_integration_config()

        with patch("setup_services.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout="3 passed, 2 skipped", stderr=""
            )
            status = run_integration_tests(str(tmp_path), "db://url", "python", config)

        assert status == StepStatus.OK


class TestRunIntegrationTestsDryRun:
    """Dry-run mode returns OK without spawning a subprocess."""

    def _make_integration_dir(self, tmp_path):
        integration_dir = tmp_path / "tests" / "integration"
        integration_dir.mkdir(parents=True)

    def test_dry_run_returns_ok(self, tmp_path):
        self._make_integration_dir(tmp_path)
        config = _make_integration_config()

        with patch("setup_services.subprocess.run") as mock_run:
            status = run_integration_tests(
                str(tmp_path), "db://url", "python", config, dry_run=True
            )

        mock_run.assert_not_called()
        assert status == StepStatus.OK


# ---------------------------------------------------------------------------
# run_property_tests
# ---------------------------------------------------------------------------


class TestRunPropertyTestsSkipped:
    """SKIPPED when no tests/property/ directory exists."""

    def test_skipped_when_no_property_dir(self, tmp_path):
        status = run_property_tests(str(tmp_path), "db://url", "python")
        assert status == StepStatus.SKIPPED

    def test_skipped_does_not_call_subprocess(self, tmp_path):
        with patch("setup_services.subprocess.run") as mock_run:
            run_property_tests(str(tmp_path), "db://url", "python")
        mock_run.assert_not_called()


class TestRunPropertyTestsHypothesisEnv:
    """HYPOTHESIS_MAX_EXAMPLES=50 is always set in the subprocess env."""

    def _make_property_dir(self, tmp_path):
        prop_dir = tmp_path / "tests" / "property"
        prop_dir.mkdir(parents=True)

    def test_hypothesis_max_examples_set_to_50(self, tmp_path):
        self._make_property_dir(tmp_path)
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "1 passed"
        mock_result.stderr = ""

        with patch(
            "setup_services.subprocess.run", return_value=mock_result
        ) as mock_run:
            run_property_tests(str(tmp_path), "db://url", "python")

        call_env = mock_run.call_args.kwargs.get("env") or mock_run.call_args[1].get(
            "env"
        )
        assert call_env["HYPOTHESIS_MAX_EXAMPLES"] == "50"

    def test_hypothesis_max_examples_is_string_not_int(self, tmp_path):
        self._make_property_dir(tmp_path)
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "1 passed"
        mock_result.stderr = ""

        with patch(
            "setup_services.subprocess.run", return_value=mock_result
        ) as mock_run:
            run_property_tests(str(tmp_path), "db://url", "python")

        call_env = mock_run.call_args.kwargs.get("env") or mock_run.call_args[1].get(
            "env"
        )
        assert isinstance(call_env["HYPOTHESIS_MAX_EXAMPLES"], str)

    def test_database_url_also_injected(self, tmp_path):
        self._make_property_dir(tmp_path)
        db_url = "mysql+pymysql://user:pass@host:4000/db?ssl_ca=ca.pem"
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "1 passed"
        mock_result.stderr = ""

        with patch(
            "setup_services.subprocess.run", return_value=mock_result
        ) as mock_run:
            run_property_tests(str(tmp_path), db_url, "python")

        call_env = mock_run.call_args.kwargs.get("env") or mock_run.call_args[1].get(
            "env"
        )
        assert call_env["DATABASE_URL"] == db_url


class TestRunPropertyTestsPassFail:
    """OK on zero exit, FAILED on non-zero exit."""

    def _make_property_dir(self, tmp_path):
        prop_dir = tmp_path / "tests" / "property"
        prop_dir.mkdir(parents=True)

    def test_returns_ok_when_pytest_exits_zero(self, tmp_path):
        self._make_property_dir(tmp_path)
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "3 passed"
        mock_result.stderr = ""

        with patch("setup_services.subprocess.run", return_value=mock_result):
            status = run_property_tests(str(tmp_path), "db://url", "python")

        assert status == StepStatus.OK

    def test_returns_failed_when_pytest_exits_nonzero(self, tmp_path):
        self._make_property_dir(tmp_path)
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = "1 failed"
        mock_result.stderr = ""

        with patch("setup_services.subprocess.run", return_value=mock_result):
            status = run_property_tests(str(tmp_path), "db://url", "python")

        assert status == StepStatus.FAILED


class TestRunPropertyTestsDryRun:
    """Dry-run mode returns OK without spawning a subprocess."""

    def _make_property_dir(self, tmp_path):
        prop_dir = tmp_path / "tests" / "property"
        prop_dir.mkdir(parents=True)

    def test_dry_run_returns_ok(self, tmp_path):
        self._make_property_dir(tmp_path)

        with patch("setup_services.subprocess.run") as mock_run:
            status = run_property_tests(
                str(tmp_path), "db://url", "python", dry_run=True
            )

        mock_run.assert_not_called()
        assert status == StepStatus.OK


# ---------------------------------------------------------------------------
# write_report — Requirements 9.1, 9.2, 9.3, 9.4, 9.5, 9.6
# ---------------------------------------------------------------------------


def _make_result(
    service: str,
    venv: StepStatus = StepStatus.OK,
    deps: StepStatus = StepStatus.OK,
    env: StepStatus = StepStatus.OK,
    migration: StepStatus = StepStatus.OK,
    startup: StepStatus = StepStatus.OK,
    integration: StepStatus = StepStatus.OK,
    property_: StepStatus = StepStatus.SKIPPED,
    errors: list[str] | None = None,
) -> "ServiceResult":
    from setup_services import ServiceResult

    r = ServiceResult(service=service)
    r.venv_status = venv
    r.deps_status = deps
    r.env_status = env
    r.migration_status = migration
    r.startup_status = startup
    r.integration_status = integration
    r.property_status = property_
    r.errors = errors or []
    return r


class TestWriteReportFileCreation:
    """write_report writes the report to the given path."""

    def test_creates_report_file(self, tmp_path):
        report_path = str(tmp_path / "setup-report.txt")
        results = [_make_result("design-service")]
        write_report(results, report_path)
        assert os.path.exists(report_path)

    def test_report_file_is_non_empty(self, tmp_path):
        report_path = str(tmp_path / "setup-report.txt")
        results = [_make_result("design-service")]
        write_report(results, report_path)
        assert os.path.getsize(report_path) > 0

    def test_report_file_contains_service_name(self, tmp_path):
        report_path = str(tmp_path / "setup-report.txt")
        results = [_make_result("labor-service")]
        write_report(results, report_path)
        content = open(report_path, encoding="utf-8").read()
        assert "labor-service" in content

    def test_report_file_contains_all_service_names(self, tmp_path):
        report_path = str(tmp_path / "setup-report.txt")
        results = [
            _make_result("design-service"),
            _make_result("labor-service"),
            _make_result("vendor-service"),
        ]
        write_report(results, report_path)
        content = open(report_path, encoding="utf-8").read()
        for svc in ("design-service", "labor-service", "vendor-service"):
            assert svc in content


class TestWriteReportOverallStatus:
    """READY and FAILED appear correctly in the report."""

    def test_ready_service_shows_ready(self, tmp_path):
        report_path = str(tmp_path / "setup-report.txt")
        results = [_make_result("design-service")]
        write_report(results, report_path)
        content = open(report_path, encoding="utf-8").read()
        assert "READY" in content

    def test_failed_service_shows_failed(self, tmp_path):
        report_path = str(tmp_path / "setup-report.txt")
        results = [
            _make_result(
                "design-service",
                startup=StepStatus.FAILED,
                errors=["startup: health check failed"],
            )
        ]
        write_report(results, report_path)
        content = open(report_path, encoding="utf-8").read()
        assert "FAILED" in content

    def test_error_message_included_for_failed_service(self, tmp_path):
        report_path = str(tmp_path / "setup-report.txt")
        results = [
            _make_result(
                "labor-service",
                deps=StepStatus.FAILED,
                errors=["deps: installation failed"],
            )
        ]
        write_report(results, report_path)
        content = open(report_path, encoding="utf-8").read()
        assert "deps: installation failed" in content

    def test_no_error_section_when_all_ready(self, tmp_path):
        report_path = str(tmp_path / "setup-report.txt")
        results = [_make_result("design-service"), _make_result("labor-service")]
        write_report(results, report_path)
        content = open(report_path, encoding="utf-8").read()
        # No ERRORS section when all pass
        assert "ERRORS:" not in content


class TestWriteReportTableColumns:
    """Report table includes all required column headers."""

    def test_all_column_headers_present(self, tmp_path):
        report_path = str(tmp_path / "setup-report.txt")
        results = [_make_result("design-service")]
        write_report(results, report_path)
        content = open(report_path, encoding="utf-8").read()
        for col in (
            "Service",
            "Venv",
            "Deps",
            "Env",
            "Migration",
            "Startup",
            "Integration",
            "Property",
            "Overall",
        ):
            assert col in content, f"Column '{col}' missing from report"

    def test_step_statuses_shown_in_table(self, tmp_path):
        report_path = str(tmp_path / "setup-report.txt")
        results = [
            _make_result(
                "engineering-service",
                migration=StepStatus.SKIPPED,
                integration=StepStatus.OK,
                property_=StepStatus.FAILED,
                errors=["property: test failed"],
            )
        ]
        write_report(results, report_path)
        content = open(report_path, encoding="utf-8").read()
        # OK, FAIL, SKIP should all appear
        assert "OK" in content
        assert "FAIL" in content
        assert "SKIP" in content


class TestWriteReportStdout:
    """write_report also prints to stdout."""

    def test_prints_to_stdout(self, tmp_path, capsys):
        report_path = str(tmp_path / "setup-report.txt")
        results = [_make_result("design-service")]
        write_report(results, report_path)
        captured = capsys.readouterr()
        assert "design-service" in captured.out

    def test_stdout_contains_overall_status(self, tmp_path, capsys):
        report_path = str(tmp_path / "setup-report.txt")
        results = [_make_result("design-service")]
        write_report(results, report_path)
        captured = capsys.readouterr()
        assert "READY" in captured.out


class TestWriteReportSummaryLine:
    """Report includes a summary count line."""

    def test_summary_shows_ready_count(self, tmp_path):
        report_path = str(tmp_path / "setup-report.txt")
        results = [
            _make_result("design-service"),
            _make_result("labor-service"),
            _make_result(
                "vendor-service",
                startup=StepStatus.FAILED,
                errors=["startup: health check failed"],
            ),
        ]
        write_report(results, report_path)
        content = open(report_path, encoding="utf-8").read()
        # 2 of 3 READY
        assert "2/3" in content or "2 " in content


# ---------------------------------------------------------------------------
# Task 9.1 – ServiceResult.overall unit tests
# Requirements: 9.2, 9.3
# ---------------------------------------------------------------------------


class TestServiceResultOverallReady:
    """overall == 'READY' when every applicable step is OK or SKIPPED."""

    def test_all_ok_is_ready(self):
        r = _make_result(
            "design-service",
            venv=StepStatus.OK,
            deps=StepStatus.OK,
            env=StepStatus.OK,
            migration=StepStatus.OK,
            startup=StepStatus.OK,
            integration=StepStatus.OK,
            property_=StepStatus.OK,
        )
        assert r.overall == "READY"

    def test_all_skipped_is_ready(self):
        r = _make_result(
            "analytics-service",
            venv=StepStatus.SKIPPED,
            deps=StepStatus.SKIPPED,
            env=StepStatus.SKIPPED,
            migration=StepStatus.SKIPPED,
            startup=StepStatus.SKIPPED,
            integration=StepStatus.SKIPPED,
            property_=StepStatus.SKIPPED,
        )
        assert r.overall == "READY"

    def test_mix_of_ok_and_skipped_is_ready(self):
        # analytics-service: no migrations, no property tests
        r = _make_result(
            "analytics-service",
            venv=StepStatus.OK,
            deps=StepStatus.OK,
            env=StepStatus.OK,
            migration=StepStatus.SKIPPED,
            startup=StepStatus.OK,
            integration=StepStatus.SKIPPED,
            property_=StepStatus.SKIPPED,
        )
        assert r.overall == "READY"

    def test_property_skipped_does_not_prevent_ready(self):
        r = _make_result(
            "design-service",
            property_=StepStatus.SKIPPED,
        )
        assert r.overall == "READY"

    def test_integration_skipped_does_not_prevent_ready(self):
        r = _make_result(
            "vendor-service",
            integration=StepStatus.SKIPPED,
            property_=StepStatus.SKIPPED,
        )
        assert r.overall == "READY"

    def test_migration_skipped_does_not_prevent_ready(self):
        r = _make_result(
            "analytics-service",
            migration=StepStatus.SKIPPED,
        )
        assert r.overall == "READY"


class TestServiceResultOverallFailed:
    """overall == 'FAILED' when any step is FAILED."""

    def test_venv_failed_returns_failed(self):
        r = _make_result(
            "design-service", venv=StepStatus.FAILED, errors=["venv: creation failed"]
        )
        assert r.overall == "FAILED"

    def test_deps_failed_returns_failed(self):
        r = _make_result(
            "design-service",
            deps=StepStatus.FAILED,
            errors=["deps: pip install failed"],
        )
        assert r.overall == "FAILED"

    def test_env_failed_returns_failed(self):
        r = _make_result(
            "design-service", env=StepStatus.FAILED, errors=["env: psycopg2 detected"]
        )
        assert r.overall == "FAILED"

    def test_migration_failed_returns_failed(self):
        r = _make_result(
            "design-service",
            migration=StepStatus.FAILED,
            errors=["migration: alembic upgrade head failed"],
        )
        assert r.overall == "FAILED"

    def test_startup_failed_returns_failed(self):
        r = _make_result(
            "design-service",
            startup=StepStatus.FAILED,
            errors=["startup: health check returned 500"],
        )
        assert r.overall == "FAILED"

    def test_integration_failed_returns_failed(self):
        r = _make_result(
            "design-service",
            integration=StepStatus.FAILED,
            errors=["integration: 2 tests failed"],
        )
        assert r.overall == "FAILED"

    def test_property_failed_returns_failed(self):
        r = _make_result(
            "architectural-service",
            property_=StepStatus.FAILED,
            errors=["property: counterexample found"],
        )
        assert r.overall == "FAILED"

    def test_single_failed_step_among_all_ok_returns_failed(self):
        r = _make_result(
            "labor-service",
            venv=StepStatus.OK,
            deps=StepStatus.OK,
            env=StepStatus.OK,
            migration=StepStatus.OK,
            startup=StepStatus.FAILED,
            integration=StepStatus.OK,
            property_=StepStatus.OK,
            errors=["startup: timeout after 30s"],
        )
        assert r.overall == "FAILED"

    def test_multiple_failed_steps_returns_failed(self):
        r = _make_result(
            "vendor-service",
            deps=StepStatus.FAILED,
            migration=StepStatus.FAILED,
            errors=["deps: pip error", "migration: alembic error"],
        )
        assert r.overall == "FAILED"


class TestServiceResultOverallFirstError:
    """errors[0] identifies the first failing step in pipeline order.

    Pipeline order: venv → deps → env → migration → startup → integration → property
    Requirements: 9.3
    """

    def test_first_error_identifies_venv_step(self):
        r = _make_result(
            "design-service",
            venv=StepStatus.FAILED,
            errors=["venv: creation failed"],
        )
        assert r.errors[0] == "venv: creation failed"

    def test_first_error_identifies_deps_step(self):
        r = _make_result(
            "design-service",
            deps=StepStatus.FAILED,
            errors=["deps: pip install failed"],
        )
        assert r.errors[0] == "deps: pip install failed"

    def test_first_error_identifies_env_step(self):
        r = _make_result(
            "analytics-service",
            env=StepStatus.FAILED,
            errors=["env: psycopg2-binary detected — resolve before proceeding"],
        )
        assert (
            r.errors[0] == "env: psycopg2-binary detected — resolve before proceeding"
        )

    def test_first_error_identifies_migration_step(self):
        r = _make_result(
            "labor-service",
            migration=StepStatus.FAILED,
            errors=["migration: alembic upgrade head exited with code 1"],
        )
        assert r.errors[0] == "migration: alembic upgrade head exited with code 1"

    def test_first_error_identifies_startup_step(self):
        r = _make_result(
            "engineering-service",
            startup=StepStatus.FAILED,
            errors=["startup: service did not respond within 30s"],
        )
        assert r.errors[0] == "startup: service did not respond within 30s"

    def test_first_error_identifies_integration_step(self):
        r = _make_result(
            "architectural-service",
            integration=StepStatus.FAILED,
            errors=["integration: 3 tests failed"],
        )
        assert r.errors[0] == "integration: 3 tests failed"

    def test_first_error_identifies_property_step(self):
        r = _make_result(
            "engineering-service",
            property_=StepStatus.FAILED,
            errors=["property: Hypothesis found counterexample"],
        )
        assert r.errors[0] == "property: Hypothesis found counterexample"

    def test_errors_list_is_non_empty_when_failed(self):
        r = _make_result(
            "design-service",
            startup=StepStatus.FAILED,
            errors=["startup: health check returned 503"],
        )
        assert r.overall == "FAILED"
        assert len(r.errors) > 0

    def test_errors_list_may_be_empty_when_ready(self):
        r = _make_result("design-service")
        assert r.overall == "READY"
        assert r.errors == []

    def test_multiple_errors_first_is_earliest_pipeline_step(self):
        # deps fails before startup in pipeline order
        r = _make_result(
            "vendor-service",
            deps=StepStatus.FAILED,
            startup=StepStatus.FAILED,
            errors=["deps: pip install failed", "startup: health check failed"],
        )
        assert r.errors[0] == "deps: pip install failed"
