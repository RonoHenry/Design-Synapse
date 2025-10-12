"""Unit tests for database health check utilities."""

import ssl
from unittest.mock import MagicMock, Mock, patch

import pytest
from sqlalchemy.exc import OperationalError

from packages.common.database.health import (
    DatabaseHealthStatus,
    check_database_health,
)


class TestDatabaseHealthStatus:
    """Tests for DatabaseHealthStatus dataclass."""
    
    def test_healthy_status_creation(self):
        """Test creating a healthy status."""
        status = DatabaseHealthStatus(
            is_healthy=True,
            message="Connection successful",
            response_time_ms=15.5,
            database_version="8.0.11-TiDB-v7.5.0",
            ssl_enabled=True,
        )
        
        assert status.is_healthy is True
        assert status.message == "Connection successful"
        assert status.response_time_ms == 15.5
        assert status.database_version == "8.0.11-TiDB-v7.5.0"
        assert status.ssl_enabled is True
        assert status.error is None
    
    def test_unhealthy_status_creation(self):
        """Test creating an unhealthy status."""
        status = DatabaseHealthStatus(
            is_healthy=False,
            message="Connection failed",
            error="Connection timeout",
        )
        
        assert status.is_healthy is False
        assert status.message == "Connection failed"
        assert status.error == "Connection timeout"
        assert status.response_time_ms is None


class TestCheckDatabaseHealth:
    """Tests for check_database_health function."""
    
    @patch("packages.common.database.health.create_engine")
    @patch("packages.common.database.health.time.time")
    def test_successful_connection_without_ssl(self, mock_time, mock_create_engine):
        """Test successful database connection without SSL."""
        # Mock time for response time calculation
        mock_time.side_effect = [0.0, 0.015]  # 15ms response time
        
        # Mock database connection and results
        mock_result = MagicMock()
        mock_result.fetchone.return_value = (1,)
        
        mock_version_result = MagicMock()
        mock_version_result.fetchone.return_value = ("8.0.11-TiDB-v7.5.0",)
        
        mock_conn = MagicMock()
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=False)
        mock_conn.execute.side_effect = [mock_result, mock_version_result]
        
        mock_engine = MagicMock()
        mock_engine.connect.return_value = mock_conn
        mock_create_engine.return_value = mock_engine
        
        # Execute health check
        status = check_database_health("mysql+pymysql://user:pass@localhost/test")
        
        # Verify results
        assert status.is_healthy is True
        assert status.message == "Database connection successful"
        assert status.response_time_ms == 15.0
        assert status.database_version == "8.0.11-TiDB-v7.5.0"
        assert status.ssl_enabled is False
        assert status.error is None
        
        # Verify engine was created correctly
        mock_create_engine.assert_called_once()
        call_args = mock_create_engine.call_args
        assert call_args[0][0] == "mysql+pymysql://user:pass@localhost/test"
        assert call_args[1]["pool_size"] == 1
        assert call_args[1]["max_overflow"] == 0
        assert call_args[1]["pool_pre_ping"] is True
        
        # Verify engine was disposed
        mock_engine.dispose.assert_called_once()
    
    @patch("packages.common.database.health.create_engine")
    @patch("packages.common.database.health.time.time")
    def test_successful_connection_with_ssl(self, mock_time, mock_create_engine):
        """Test successful database connection with SSL."""
        mock_time.side_effect = [0.0, 0.020]  # 20ms response time
        
        # Mock database connection and results
        mock_result = MagicMock()
        mock_result.fetchone.return_value = (1,)
        
        mock_version_result = MagicMock()
        mock_version_result.fetchone.return_value = ("8.0.11-TiDB-v7.5.0",)
        
        mock_conn = MagicMock()
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=False)
        mock_conn.execute.side_effect = [mock_result, mock_version_result]
        
        mock_engine = MagicMock()
        mock_engine.connect.return_value = mock_conn
        mock_create_engine.return_value = mock_engine
        
        # Execute health check with SSL
        status = check_database_health(
            "mysql+pymysql://user:pass@localhost/test",
            ssl_ca="/path/to/ca.pem",
            ssl_verify_cert=True,
            ssl_verify_identity=True,
        )
        
        # Verify results
        assert status.is_healthy is True
        assert status.ssl_enabled is True
        
        # Verify SSL configuration was passed
        call_args = mock_create_engine.call_args
        connect_args = call_args[1]["connect_args"]
        assert "ssl" in connect_args
        assert connect_args["ssl"]["ca"] == "/path/to/ca.pem"
        assert connect_args["ssl"]["check_hostname"] is True
        assert connect_args["ssl"]["verify_mode"] == ssl.CERT_REQUIRED
    
    @patch("packages.common.database.health.create_engine")
    @patch("packages.common.database.health.time.time")
    def test_ssl_without_verification(self, mock_time, mock_create_engine):
        """Test SSL configuration without certificate verification."""
        mock_time.side_effect = [0.0, 0.010]
        
        mock_result = MagicMock()
        mock_result.fetchone.return_value = (1,)
        
        mock_version_result = MagicMock()
        mock_version_result.fetchone.return_value = ("8.0.11-TiDB-v7.5.0",)
        
        mock_conn = MagicMock()
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=False)
        mock_conn.execute.side_effect = [mock_result, mock_version_result]
        
        mock_engine = MagicMock()
        mock_engine.connect.return_value = mock_conn
        mock_create_engine.return_value = mock_engine
        
        # Execute health check with SSL but no verification
        status = check_database_health(
            "mysql+pymysql://user:pass@localhost/test",
            ssl_ca="/path/to/ca.pem",
            ssl_verify_cert=False,
            ssl_verify_identity=False,
        )
        
        # Verify SSL configuration
        call_args = mock_create_engine.call_args
        connect_args = call_args[1]["connect_args"]
        assert connect_args["ssl"]["check_hostname"] is False
        assert connect_args["ssl"]["verify_mode"] == ssl.CERT_NONE
    
    @patch("packages.common.database.health.create_engine")
    @patch("packages.common.database.health.time.sleep")
    def test_connection_failure_with_retries(self, mock_sleep, mock_create_engine):
        """Test connection failure with retry logic."""
        # Mock engine that always fails
        mock_engine = MagicMock()
        mock_engine.connect.side_effect = OperationalError(
            "Connection failed", None, None
        )
        mock_create_engine.return_value = mock_engine
        
        # Execute health check
        status = check_database_health(
            "mysql+pymysql://user:pass@localhost/test",
            max_retries=3,
        )
        
        # Verify failure status
        assert status.is_healthy is False
        assert "failed after 3 attempts" in status.message
        assert status.error is not None
        assert "Connection failed" in status.error
        
        # Verify retries occurred (3 attempts = 2 sleeps)
        assert mock_sleep.call_count == 2
        # Verify exponential backoff (1s, 2s)
        mock_sleep.assert_any_call(1)
        mock_sleep.assert_any_call(2)
    
    @patch("packages.common.database.health.create_engine")
    def test_connection_success_after_retry(self, mock_create_engine):
        """Test successful connection after initial failures."""
        # Mock engine that fails twice then succeeds
        mock_result = MagicMock()
        mock_result.fetchone.return_value = (1,)
        
        mock_version_result = MagicMock()
        mock_version_result.fetchone.return_value = ("8.0.11-TiDB-v7.5.0",)
        
        mock_conn = MagicMock()
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=False)
        mock_conn.execute.side_effect = [mock_result, mock_version_result]
        
        mock_engine = MagicMock()
        # Fail twice, then succeed
        mock_engine.connect.side_effect = [
            OperationalError("Connection failed", None, None),
            OperationalError("Connection failed", None, None),
            mock_conn,
        ]
        mock_create_engine.return_value = mock_engine
        
        # Execute health check
        status = check_database_health(
            "mysql+pymysql://user:pass@localhost/test",
            max_retries=3,
        )
        
        # Verify success after retries
        assert status.is_healthy is True
        assert status.message == "Database connection successful"
        assert mock_engine.connect.call_count == 3
    
    @patch("packages.common.database.health.create_engine")
    def test_non_sqlalchemy_error_no_retry(self, mock_create_engine):
        """Test that non-SQLAlchemy errors don't trigger retries."""
        # Mock engine that raises a generic exception
        mock_engine = MagicMock()
        mock_engine.connect.side_effect = ValueError("Invalid configuration")
        mock_create_engine.return_value = mock_engine
        
        # Execute health check
        status = check_database_health(
            "mysql+pymysql://user:pass@localhost/test",
            max_retries=3,
        )
        
        # Verify failure without retries
        assert status.is_healthy is False
        assert "Invalid configuration" in status.error
        # Should only attempt once for non-SQLAlchemy errors
        assert mock_engine.connect.call_count == 1
    
    @patch("packages.common.database.health.create_engine")
    @patch("packages.common.database.health.time.time")
    def test_response_time_calculation(self, mock_time, mock_create_engine):
        """Test accurate response time calculation."""
        # Mock time with 50ms response
        mock_time.side_effect = [0.0, 0.050]
        
        mock_result = MagicMock()
        mock_result.fetchone.return_value = (1,)
        
        mock_version_result = MagicMock()
        mock_version_result.fetchone.return_value = ("8.0.11-TiDB-v7.5.0",)
        
        mock_conn = MagicMock()
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=False)
        mock_conn.execute.side_effect = [mock_result, mock_version_result]
        
        mock_engine = MagicMock()
        mock_engine.connect.return_value = mock_conn
        mock_create_engine.return_value = mock_engine
        
        # Execute health check
        status = check_database_health("mysql+pymysql://user:pass@localhost/test")
        
        # Verify response time is 50ms
        assert status.response_time_ms == 50.0
