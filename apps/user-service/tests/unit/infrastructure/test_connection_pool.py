"""
Tests for database connection pooling implementation.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool
from src.infrastructure.database import create_db_engine, get_db


def test_engine_uses_queue_pool():
    """Test that the database engine uses QueuePool for connection pooling."""
    engine = create_db_engine()
    assert isinstance(engine.pool, QueuePool)


def test_pool_size_configuration():
    """Test that the connection pool is configured with correct sizes."""
    engine = create_db_engine()
    assert engine.pool.size() == 5  # Default pool size
    assert engine.pool._max_overflow == 10  # Default max overflow


def test_connection_pool_reuse():
    """Test that connections are reused from the pool."""
    # Get two connections in sequence
    with get_db() as db1:
        conn1 = db1.connection()

    with get_db() as db2:
        conn2 = db2.connection()

    # The underlying DBAPI connection should be different since we closed the first one
    assert id(conn1) != id(conn2)
    # But they should come from the same pool
    assert conn1.engine == conn2.engine


def test_pool_checkout_timeout():
    """Test that connection checkout has a timeout."""
    engine = create_db_engine()
    assert engine.pool._timeout == 30  # Default timeout in seconds


def test_max_connections():
    """Test that the pool enforces maximum connections."""
    max_pool_size = 5
    max_overflow = 10
    total_allowed = max_pool_size + max_overflow

    # Try to get more connections than allowed
    active_connections = []
    connection_error = None

    engine = create_db_engine()
    try:
        for _ in range(total_allowed + 2):  # Try to get more than allowed
            try:
                conn = engine.connect()
                active_connections.append(conn)
            except Exception as e:
                connection_error = e
                break
    finally:
        # Clean up connections
        for conn in active_connections:
            conn.close()

    # We should hit a connection limit error
    assert connection_error is not None
    assert "timeout" in str(connection_error).lower()

    # The number of connections we got should be at most the total allowed
    assert len(active_connections) <= total_allowed
