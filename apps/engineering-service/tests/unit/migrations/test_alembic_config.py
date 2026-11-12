"""Tests for Alembic migration configuration."""

from pathlib import Path

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory

# Get the engineering service root directory
SERVICE_ROOT = Path(__file__).parent.parent.parent.parent


@pytest.mark.unit
class TestAlembicConfiguration:
    """Test Alembic migration configuration."""

    def test_alembic_ini_exists(self):
        """Test that alembic.ini file exists."""
        alembic_ini = SERVICE_ROOT / "alembic.ini"
        assert alembic_ini.exists(), "alembic.ini file not found"

    def test_migrations_directory_exists(self):
        """Test that migrations directory exists."""
        migrations_dir = SERVICE_ROOT / "migrations"
        assert migrations_dir.exists(), "migrations directory not found"
        assert migrations_dir.is_dir(), "migrations is not a directory"

    def test_migrations_env_exists(self):
        """Test that migrations/env.py exists."""
        env_file = SERVICE_ROOT / "migrations" / "env.py"
        assert env_file.exists(), "migrations/env.py not found"

    def test_migrations_versions_directory_exists(self):
        """Test that migrations/versions directory exists."""
        versions_dir = SERVICE_ROOT / "migrations" / "versions"
        assert versions_dir.exists(), "migrations/versions directory not found"
        assert versions_dir.is_dir(), "versions is not a directory"

    def test_alembic_config_loads(self):
        """Test that Alembic config can be loaded."""
        config_path = str(SERVICE_ROOT / "alembic.ini")
        config = Config(config_path)
        assert config is not None
        assert config.get_main_option("script_location") is not None

    def test_script_directory_loads(self):
        """Test that ScriptDirectory can be loaded."""
        config_path = str(SERVICE_ROOT / "alembic.ini")
        config = Config(config_path)
        script = ScriptDirectory.from_config(config)
        assert script is not None

    def test_target_metadata_configured(self):
        """Test that target_metadata is configured in env.py."""
        env_file = SERVICE_ROOT / "migrations" / "env.py"
        with open(env_file, "r") as f:
            content = f.read()
            assert "target_metadata" in content
            assert "Base.metadata" in content

    def test_async_migrations_configured(self):
        """Test that async migrations are configured."""
        env_file = SERVICE_ROOT / "migrations" / "env.py"
        with open(env_file, "r") as f:
            content = f.read()
            assert "async_engine_from_config" in content
            assert "run_async_migrations" in content
            assert "asyncio.run" in content
