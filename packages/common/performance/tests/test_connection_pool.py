"""
Tests for database connection pooling optimization.

Following TDD approach:
1. RED: Write failing tests first
2. GREEN: Implement minimal code to pass tests
3. REFACTOR: Optimize and improve code quality
"""

import asyncio
import time
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ..connection_pool import ConnectionPoolManager, PooledConnection
from ..models import ConnectionStats, PoolConfig


class TestConnectionPoolManager:
    """Test connection pool manager functionality."""

    @pytest.mark.asyncio
    async def test_pool_manager_initialization(self, pool_config):
        """Test connection pool manager initialization."""
        # This test will fail until we implement ConnectionPoolManager
        pool_manager = ConnectionPoolManager(pool_config)
        assert pool_manager.config == pool_config
        assert pool_manager.min_connections == pool_config.min_connections
        assert pool_manager.max_connections == pool_config.max_connections

    @pytest.mark.asyncio
    async def test_pool_connection_acquisition(self, pool_config, mock_db_connection):
        """Test acquiring connection from pool."""
        with patch("sqlalchemy.create_engine") as mock_engine:
            mock_engine.return_value.connect.return_value = mock_db_connection

            pool_manager = ConnectionPoolManager(pool_config)
            await pool_manager.initialize()

            connection = await pool_manager.get_connection()
            assert connection is not None
            assert isinstance(connection, PooledConnection)

    @pytest.mark.asyncio
    async def test_pool_connection_release(self, pool_config, mock_db_connection):
        """Test releasing connection back to pool."""
        with patch("sqlalchemy.create_engine") as mock_engine:
            mock_engine.return_value.connect.return_value = mock_db_connection

            pool_manager = ConnectionPoolManager(pool_config)
            await pool_manager.initialize()

            connection = await pool_manager.get_connection()
            result = await pool_manager.release_connection(connection)
            assert result is True

    @pytest.mark.asyncio
    async def test_pool_max_connections_limit(self, pool_config, mock_db_connection):
        """Test pool respects maximum connection limit."""
        pool_config.max_connections = 2

        with patch("sqlalchemy.create_engine") as mock_engine:
            mock_engine.return_value.connect.return_value = mock_db_connection

            pool_manager = ConnectionPoolManager(pool_config)
            await pool_manager.initialize()

            # Acquire max connections
            connections = []
            for _ in range(pool_config.max_connections):
                conn = await pool_manager.get_connection()
                connections.append(conn)

            # Next acquisition should timeout or wait
            with pytest.raises(
                Exception
            ):  # Should raise timeout or pool exhausted error
                await asyncio.wait_for(pool_manager.get_connection(), timeout=0.1)

    @pytest.mark.asyncio
    async def test_pool_connection_health_check(self, pool_config, mock_db_connection):
        """Test connection health checking."""
        mock_db_connection.is_valid.return_value = True

        with patch("sqlalchemy.create_engine") as mock_engine:
            mock_engine.return_value.connect.return_value = mock_db_connection

            pool_manager = ConnectionPoolManager(pool_config)
            await pool_manager.initialize()

            connection = await pool_manager.get_connection()
            is_healthy = await pool_manager.check_connection_health(connection)
            assert is_healthy is True

    @pytest.mark.asyncio
    async def test_pool_connection_retry_on_failure(self, pool_config):
        """Test connection retry mechanism on failure."""
        with patch("sqlalchemy.create_engine") as mock_engine:
            # First call fails, second succeeds
            mock_engine.return_value.connect.side_effect = [
                Exception("Connection failed"),
                MagicMock(),
            ]

            pool_manager = ConnectionPoolManager(pool_config)

            # Should retry and eventually succeed
            connection = await pool_manager.get_connection()
            assert connection is not None

    @pytest.mark.asyncio
    async def test_pool_statistics_tracking(self, pool_config, mock_db_connection):
        """Test pool statistics collection."""
        with patch("sqlalchemy.create_engine") as mock_engine:
            mock_engine.return_value.connect.return_value = mock_db_connection

            pool_manager = ConnectionPoolManager(pool_config)
            await pool_manager.initialize()

            # Perform some operations
            connection = await pool_manager.get_connection()
            await pool_manager.release_connection(connection)

            stats = await pool_manager.get_statistics()
            assert isinstance(stats, ConnectionStats)
            assert stats.total_connections >= 0
            assert stats.pool_utilization >= 0.0

    @pytest.mark.asyncio
    async def test_pool_connection_timeout(self, pool_config):
        """Test connection timeout handling."""
        pool_config.connection_timeout = 1  # 1 second timeout

        with patch("sqlalchemy.create_engine") as mock_engine:
            # Simulate slow connection
            async def slow_connect():
                await asyncio.sleep(2)  # Longer than timeout
                return MagicMock()

            mock_engine.return_value.connect = slow_connect

            pool_manager = ConnectionPoolManager(pool_config)

            with pytest.raises(asyncio.TimeoutError):
                await pool_manager.get_connection()

    @pytest.mark.asyncio
    async def test_pool_connection_lifecycle(self, pool_config, mock_db_connection):
        """Test complete connection lifecycle management."""
        mock_db_connection.is_valid.return_value = True

        with patch("sqlalchemy.create_engine") as mock_engine:
            mock_engine.return_value.connect.return_value = mock_db_connection

            pool_manager = ConnectionPoolManager(pool_config)
            await pool_manager.initialize()

            # Test full lifecycle
            connection = await pool_manager.get_connection()
            assert connection.is_active()

            # Use connection
            await connection.execute("SELECT 1")

            # Release connection
            await pool_manager.release_connection(connection)

            # Connection should be back in pool
            stats = await pool_manager.get_statistics()
            assert stats.idle_connections > 0

    @pytest.mark.asyncio
    async def test_pool_cleanup_expired_connections(
        self, pool_config, mock_db_connection
    ):
        """Test cleanup of expired connections."""
        pool_config.max_idle_time = 1  # 1 second max idle

        with patch("sqlalchemy.create_engine") as mock_engine:
            mock_engine.return_value.connect.return_value = mock_db_connection

            pool_manager = ConnectionPoolManager(pool_config)
            await pool_manager.initialize()

            # Get and release connection
            connection = await pool_manager.get_connection()
            await pool_manager.release_connection(connection)

            # Wait for expiration
            await asyncio.sleep(1.1)

            # Trigger cleanup
            await pool_manager.cleanup_expired_connections()

            stats = await pool_manager.get_statistics()
            # Expired connections should be cleaned up
            assert stats.idle_connections == 0


class TestPooledConnection:
    """Test pooled connection wrapper."""

    def test_pooled_connection_creation(self, mock_db_connection):
        """Test pooled connection wrapper creation."""
        pooled_conn = PooledConnection(mock_db_connection, pool_id="test_pool")

        assert pooled_conn.connection == mock_db_connection
        assert pooled_conn.pool_id == "test_pool"
        assert pooled_conn.is_active()

    @pytest.mark.asyncio
    async def test_pooled_connection_execute(self, mock_db_connection):
        """Test executing queries through pooled connection."""
        mock_db_connection.execute.return_value = MagicMock()

        pooled_conn = PooledConnection(mock_db_connection, pool_id="test_pool")

        result = await pooled_conn.execute("SELECT * FROM users")
        assert result is not None
        mock_db_connection.execute.assert_called_once_with("SELECT * FROM users")

    def test_pooled_connection_close(self, mock_db_connection):
        """Test closing pooled connection."""
        pooled_conn = PooledConnection(mock_db_connection, pool_id="test_pool")

        pooled_conn.close()
        assert not pooled_conn.is_active()
        mock_db_connection.close.assert_called_once()

    def test_pooled_connection_health_check(self, mock_db_connection):
        """Test pooled connection health checking."""
        mock_db_connection.is_valid.return_value = True

        pooled_conn = PooledConnection(mock_db_connection, pool_id="test_pool")

        is_healthy = pooled_conn.is_healthy()
        assert is_healthy is True


class TestConnectionPoolPerformance:
    """Test connection pool performance characteristics."""

    @pytest.mark.asyncio
    async def test_pool_concurrent_access(self, pool_config, mock_db_connection):
        """Test pool performance under concurrent access."""
        with patch("sqlalchemy.create_engine") as mock_engine:
            mock_engine.return_value.connect.return_value = mock_db_connection

            pool_manager = ConnectionPoolManager(pool_config)
            await pool_manager.initialize()

            async def get_and_release_connection():
                conn = await pool_manager.get_connection()
                await asyncio.sleep(0.01)  # Simulate work
                await pool_manager.release_connection(conn)

            # Run concurrent operations
            start_time = time.time()
            tasks = [get_and_release_connection() for _ in range(20)]
            await asyncio.gather(*tasks)
            end_time = time.time()

            # Should complete within reasonable time
            assert end_time - start_time < 2.0

    @pytest.mark.asyncio
    async def test_pool_utilization_metrics(self, pool_config, mock_db_connection):
        """Test pool utilization measurement."""
        with patch("sqlalchemy.create_engine") as mock_engine:
            mock_engine.return_value.connect.return_value = mock_db_connection

            pool_manager = ConnectionPoolManager(pool_config)
            await pool_manager.initialize()

            # Acquire half of max connections
            connections = []
            for _ in range(pool_config.max_connections // 2):
                conn = await pool_manager.get_connection()
                connections.append(conn)

            stats = await pool_manager.get_statistics()
            expected_utilization = 0.5  # 50% utilization
            assert abs(stats.pool_utilization - expected_utilization) < 0.1

    @pytest.mark.asyncio
    async def test_pool_connection_time_tracking(self, pool_config, mock_db_connection):
        """Test connection acquisition time tracking."""
        with patch("sqlalchemy.create_engine") as mock_engine:
            mock_engine.return_value.connect.return_value = mock_db_connection

            pool_manager = ConnectionPoolManager(pool_config)
            await pool_manager.initialize()

            start_time = time.time()
            connection = await pool_manager.get_connection()
            end_time = time.time()

            connection_time = (end_time - start_time) * 1000  # Convert to ms

            stats = await pool_manager.get_statistics()
            assert stats.avg_connection_time_ms >= 0
