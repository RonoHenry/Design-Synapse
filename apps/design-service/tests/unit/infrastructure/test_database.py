"""
Unit tests for database infrastructure.

Tests database connection, session management, and dependency injection.
"""

from unittest.mock import Mock, patch

import pytest
from sqlalchemy.orm import Session

from src.infrastructure.database import Base, create_db_engine, get_db, get_db_context


class TestDatabaseEngine:
    """Tests for database engine creation."""

    @patch("src.infrastructure.database.get_settings")
    @patch("src.infrastructure.database.create_engine")
    def test_create_db_engine_uses_config(self, mock_create_engine, mock_get_settings):
        """Test that create_db_engine uses configuration from settings."""
        # Arrange
        mock_settings = Mock()
        mock_settings.get_database_url.return_value = (
            "mysql+pymysql://user:pass@host:4000/db"
        )
        mock_settings.get_database_engine_kwargs.return_value = {
            "pool_size": 10,
            "max_overflow": 20,
            "pool_pre_ping": True,
        }
        mock_get_settings.return_value = mock_settings

        # Act
        create_db_engine()

        # Assert
        mock_settings.get_database_url.assert_called_once_with(async_driver=False)
        mock_settings.get_database_engine_kwargs.assert_called_once()
        mock_create_engine.assert_called_once_with(
            "mysql+pymysql://user:pass@host:4000/db",
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
        )

    def test_base_declarative_exists(self):
        """Test that Base declarative is available for models."""
        assert Base is not None
        assert hasattr(Base, "metadata")


class TestGetDbDependency:
    """Tests for get_db FastAPI dependency."""

    @patch("src.infrastructure.database.get_session_local")
    def test_get_db_yields_session(self, mock_get_session_local):
        """Test that get_db yields a database session."""
        # Arrange
        mock_session = Mock(spec=Session)
        mock_session_factory = Mock()
        mock_session_factory.return_value = mock_session
        mock_get_session_local.return_value = mock_session_factory

        # Act
        generator = get_db()
        session = next(generator)

        # Assert
        assert session == mock_session
        mock_session_factory.assert_called_once()

    @patch("src.infrastructure.database.get_session_local")
    def test_get_db_closes_session_on_completion(self, mock_get_session_local):
        """Test that get_db closes session after use."""
        # Arrange
        mock_session = Mock(spec=Session)
        mock_session_factory = Mock()
        mock_session_factory.return_value = mock_session
        mock_get_session_local.return_value = mock_session_factory

        # Act
        generator = get_db()
        next(generator)

        try:
            next(generator)
        except StopIteration:
            pass

        # Assert
        mock_session.close.assert_called_once()

    @patch("src.infrastructure.database.get_session_local")
    def test_get_db_closes_session_on_exception(self, mock_get_session_local):
        """Test that get_db closes session even if exception occurs."""
        # Arrange
        mock_session = Mock(spec=Session)
        mock_session_factory = Mock()
        mock_session_factory.return_value = mock_session
        mock_get_session_local.return_value = mock_session_factory

        # Act
        generator = get_db()
        next(generator)

        try:
            generator.throw(Exception("Test exception"))
        except Exception:
            pass

        # Assert
        mock_session.close.assert_called_once()


class TestGetDbContext:
    """Tests for get_db_context context manager."""

    @patch("src.infrastructure.database.get_session_local")
    def test_get_db_context_yields_session(self, mock_get_session_local):
        """Test that get_db_context yields a database session."""
        # Arrange
        mock_session = Mock(spec=Session)
        mock_session_factory = Mock()
        mock_session_factory.return_value = mock_session
        mock_get_session_local.return_value = mock_session_factory

        # Act
        with get_db_context() as session:
            result_session = session

        # Assert
        assert result_session == mock_session
        mock_session_factory.assert_called_once()

    @patch("src.infrastructure.database.get_session_local")
    def test_get_db_context_closes_session(self, mock_get_session_local):
        """Test that get_db_context closes session after use."""
        # Arrange
        mock_session = Mock(spec=Session)
        mock_session_factory = Mock()
        mock_session_factory.return_value = mock_session
        mock_get_session_local.return_value = mock_session_factory

        # Act
        with get_db_context():
            pass

        # Assert
        mock_session.close.assert_called_once()

    @patch("src.infrastructure.database.get_session_local")
    def test_get_db_context_closes_session_on_exception(self, mock_get_session_local):
        """Test that get_db_context closes session even if exception occurs."""
        # Arrange
        mock_session = Mock(spec=Session)
        mock_session_factory = Mock()
        mock_session_factory.return_value = mock_session
        mock_get_session_local.return_value = mock_session_factory

        # Act & Assert
        with pytest.raises(ValueError):
            with get_db_context():
                raise ValueError("Test exception")

        mock_session.close.assert_called_once()


class TestSessionManagement:
    """Integration tests for session management."""

    @patch("src.infrastructure.database.get_session_local")
    def test_multiple_get_db_calls_create_separate_sessions(
        self, mock_get_session_local
    ):
        """Test that multiple get_db calls create separate sessions."""
        # Arrange
        mock_session_1 = Mock(spec=Session)
        mock_session_2 = Mock(spec=Session)
        mock_session_factory = Mock()
        mock_session_factory.side_effect = [mock_session_1, mock_session_2]
        mock_get_session_local.return_value = mock_session_factory

        # Act
        gen1 = get_db()
        session1 = next(gen1)

        gen2 = get_db()
        session2 = next(gen2)

        # Assert
        assert session1 != session2
        assert mock_session_factory.call_count == 2

    @patch("src.infrastructure.database.get_session_local")
    def test_get_db_context_multiple_calls_create_separate_sessions(
        self, mock_get_session_local
    ):
        """Test that multiple get_db_context calls create separate sessions."""
        # Arrange
        mock_session_1 = Mock(spec=Session)
        mock_session_2 = Mock(spec=Session)
        mock_session_factory = Mock()
        mock_session_factory.side_effect = [mock_session_1, mock_session_2]
        mock_get_session_local.return_value = mock_session_factory

        # Act
        with get_db_context():
            pass

        with get_db_context():
            pass

        # Assert
        assert mock_session_factory.call_count == 2
        mock_session_1.close.assert_called_once()
        mock_session_2.close.assert_called_once()
