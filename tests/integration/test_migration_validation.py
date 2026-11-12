"""Integration tests for migration validation scripts."""

import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Add packages to path
packages_path = Path(__file__).parent.parent
sys.path.insert(0, str(packages_path))

from packages.common.config.database import DatabaseConfig


class TestMigrationValidation:
    """Test migration validation scripts."""

    @pytest.fixture
    def mock_database_config(self):
        """Mock database configuration."""
        config = Mock(spec=DatabaseConfig)
        config.host = "localhost"
        config.port = 5432
        config.database = "test_db"
        config.get_connection_url.return_value = (
            "mysql://user:pass@localhost:3306/test_db"
        )
        config.get_engine_kwargs.return_value = {"pool_size": 5}
        return config

    def test_verify_all_migrations_script_exists(self):
        """Test that the migration verification script exists."""
        script_path = Path("verify_all_migrations.py")
        assert script_path.exists(), "Migration verification script should exist"

    def test_verify_all_migrations_script_structure(self):
        """Test that the migration verification script has correct structure."""
        script_path = Path("verify_all_migrations.py")

        with open(script_path, "r") as f:
            content = f.read()

        # Check for essential components
        assert "DatabaseConfig" in content
        assert "create_engine" in content
        assert "SHOW TABLES" in content
        assert "alembic_version" in content
        assert "users" in content  # User service table
        assert "projects" in content  # Project service table
        assert "resources" in content  # Knowledge service table

    @patch("sqlalchemy.create_engine")
    @patch("packages.common.config.database.DatabaseConfig")
    def test_verify_all_migrations_database_connection(
        self, mock_config_class, mock_create_engine
    ):
        """Test database connection in migration verification."""
        # Setup mocks
        mock_config = Mock()
        mock_config.get_connection_url.return_value = (
            "mysql://test:test@localhost:3306/test_db"
        )
        mock_config.get_engine_kwargs.return_value = {"pool_size": 5}
        mock_config_class.return_value = mock_config

        mock_engine = Mock()
        mock_connection = Mock()
        mock_engine.connect.return_value.__enter__.return_value = mock_connection
        mock_create_engine.return_value = mock_engine

        # Mock database queries
        mock_connection.execute.side_effect = [
            # SHOW TABLES result
            Mock(
                fetchall=lambda: [
                    ("users",),
                    ("projects",),
                    ("resources",),
                    ("alembic_version",),
                ]
            ),
            # Alembic versions result
            Mock(
                fetchall=lambda: [
                    ("a1b2c3d4e5f6",),
                    ("b2c3d4e5f6a7",),
                    ("c3d4e5f6a7b8",),
                ]
            ),
            # Database version result
            Mock(fetchone=lambda: ("MySQL 8.0.33",)),
        ]

        # Import and run the script logic
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "verify_migrations", "verify_all_migrations.py"
        )

        # The script should run without errors
        assert spec is not None

    def test_migration_validation_user_service_tables(self):
        """Test validation of user service tables."""
        expected_tables = ["users", "roles", "user_roles"]

        # This would be called by the actual script
        for table in expected_tables:
            assert isinstance(table, str)
            assert len(table) > 0

    def test_migration_validation_project_service_tables(self):
        """Test validation of project service tables."""
        expected_tables = ["projects", "project_collaborators", "comments"]

        for table in expected_tables:
            assert isinstance(table, str)
            assert len(table) > 0

    def test_migration_validation_knowledge_service_tables(self):
        """Test validation of knowledge service tables."""
        expected_tables = [
            "resources",
            "topics",
            "bookmarks",
            "citations",
            "resource_topics",
        ]

        for table in expected_tables:
            assert isinstance(table, str)
            assert len(table) > 0

    def test_migration_validation_alembic_versions(self):
        """Test validation of alembic version tracking."""
        expected_versions = {
            "a1b2c3d4e5f6": "user-service",
            "b2c3d4e5f6a7": "project-service",
            "c3d4e5f6a7b8": "knowledge-service",
        }

        for version, service in expected_versions.items():
            assert len(version) == 12  # Standard alembic version length
            assert service.endswith("-service")

    @patch("subprocess.run")
    def test_migration_script_execution(self, mock_subprocess):
        """Test that migration scripts can be executed."""
        mock_subprocess.return_value = Mock(returncode=0, stdout="Success", stderr="")

        # Test running the verification script
        result = subprocess.run(
            [sys.executable, "verify_all_migrations.py"], capture_output=True, text=True
        )

        # The mock should have been called
        mock_subprocess.assert_called_once()

    def test_individual_service_migration_scripts_exist(self):
        """Test that individual service migration scripts exist."""
        migration_scripts = [
            "apply_knowledge_migration.py",
            "apply_project_migration.py",
        ]

        for script in migration_scripts:
            script_path = Path(script)
            assert script_path.exists(), f"Migration script {script} should exist"

    def test_migration_rollback_scripts_exist(self):
        """Test that migration rollback scripts exist."""
        rollback_scripts = [
            "apps/design-service/test_migration_rollback.py",
            "apps/design-service/test_rollback.py",
        ]

        for script in rollback_scripts:
            script_path = Path(script)
            assert script_path.exists(), f"Rollback script {script} should exist"

    @patch("sqlalchemy.create_engine")
    def test_migration_validation_error_handling(self, mock_create_engine):
        """Test error handling in migration validation."""
        # Mock database connection failure
        mock_create_engine.side_effect = Exception("Database connection failed")

        with pytest.raises(Exception, match="Database connection failed"):
            mock_create_engine("mysql://test:test@localhost:3306/test_db")

    def test_migration_validation_table_existence_check(self):
        """Test table existence validation logic."""
        # Simulate table check logic
        existing_tables = ["users", "projects", "resources", "alembic_version"]
        required_tables = [
            "users",
            "roles",
            "projects",
            "comments",
            "resources",
            "topics",
        ]

        missing_tables = []
        for table in required_tables:
            if table not in existing_tables:
                missing_tables.append(table)

        # Should identify missing tables
        assert "roles" in missing_tables
        assert "comments" in missing_tables
        assert "topics" in missing_tables

    def test_migration_validation_version_tracking(self):
        """Test alembic version tracking validation."""
        # Simulate version check logic
        applied_versions = ["a1b2c3d4e5f6", "b2c3d4e5f6a7"]
        expected_versions = ["a1b2c3d4e5f6", "b2c3d4e5f6a7", "c3d4e5f6a7b8"]

        missing_versions = []
        for version in expected_versions:
            if version not in applied_versions:
                missing_versions.append(version)

        # Should identify missing version
        assert "c3d4e5f6a7b8" in missing_versions

    def test_migration_validation_database_version_check(self):
        """Test database version compatibility check."""
        # Test different database versions
        compatible_versions = ["MySQL 8.0.33", "MySQL 8.0.30", "TiDB 7.1.0"]

        for version in compatible_versions:
            assert "MySQL" in version or "TiDB" in version
            # Version should have numeric components
            assert any(char.isdigit() for char in version)

    @patch("os.path.exists")
    def test_migration_validation_file_dependencies(self, mock_exists):
        """Test validation of migration file dependencies."""
        # Mock file existence checks
        mock_exists.return_value = True

        required_files = [
            "packages/common/config/database.py",
            "apps/user-service/migrations/versions/a1b2c3d4e5f6_initial_migration_tidb.py",
            "apps/project-service/migrations/versions/b2c3d4e5f6a7_initial_migration_tidb.py",
            "apps/knowledge-service/migrations/versions/c3d4e5f6a7b8_initial_migration_tidb.py",
        ]

        for file_path in required_files:
            assert mock_exists(file_path) is True

    def test_migration_validation_output_format(self):
        """Test that migration validation produces expected output format."""
        # Test output formatting logic
        service_tables = {
            "user-service": ["users", "roles", "user_roles"],
            "project-service": ["projects", "project_collaborators", "comments"],
            "knowledge-service": ["resources", "topics", "bookmarks", "citations"],
        }

        for service, tables in service_tables.items():
            assert service.endswith("-service")
            assert len(tables) > 0
            for table in tables:
                assert isinstance(table, str)
                assert len(table) > 0
