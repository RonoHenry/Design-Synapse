"""Database health check utilities for TiDB connectivity verification."""

import ssl
import time
from dataclasses import dataclass
from typing import Optional

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError


@dataclass
class DatabaseHealthStatus:
    """Database health check status."""
    
    is_healthy: bool
    message: str
    response_time_ms: Optional[float] = None
    database_version: Optional[str] = None
    ssl_enabled: Optional[bool] = None
    error: Optional[str] = None


def check_database_health(
    connection_url: str,
    ssl_ca: Optional[str] = None,
    ssl_verify_cert: bool = True,
    ssl_verify_identity: bool = True,
    timeout: int = 5,
    max_retries: int = 3,
) -> DatabaseHealthStatus:
    """
    Check database connectivity and health with retry logic.
    
    Args:
        connection_url: SQLAlchemy database connection URL
        ssl_ca: Path to SSL CA certificate
        ssl_verify_cert: Whether to verify SSL certificate
        ssl_verify_identity: Whether to verify SSL identity
        timeout: Connection timeout in seconds
        max_retries: Maximum number of retry attempts
    
    Returns:
        DatabaseHealthStatus with connection details
    """
    last_error = None
    retry_delay = 1  # Initial retry delay in seconds
    
    for attempt in range(max_retries):
        try:
            # Build connect_args for SSL if needed
            connect_args = {}
            ssl_enabled = False
            
            if ssl_ca:
                ssl_enabled = True
                connect_args["ssl"] = {
                    "ca": ssl_ca,
                    "check_hostname": ssl_verify_identity,
                    "verify_mode": ssl.CERT_REQUIRED if ssl_verify_cert else ssl.CERT_NONE,
                }
            
            # Create engine with minimal pool for health check
            engine = create_engine(
                connection_url,
                pool_size=1,
                max_overflow=0,
                pool_pre_ping=True,
                connect_args=connect_args if connect_args else None,
            )
            
            # Measure response time
            start_time = time.time()
            
            with engine.connect() as conn:
                # Execute simple query to verify connectivity
                result = conn.execute(text("SELECT 1 as health_check"))
                result.fetchone()
                
                # Get database version
                version_result = conn.execute(text("SELECT VERSION() as version"))
                version_row = version_result.fetchone()
                db_version = version_row[0] if version_row else None
            
            response_time = (time.time() - start_time) * 1000  # Convert to ms
            
            # Clean up engine
            engine.dispose()
            
            return DatabaseHealthStatus(
                is_healthy=True,
                message="Database connection successful",
                response_time_ms=round(response_time, 2),
                database_version=db_version,
                ssl_enabled=ssl_enabled,
            )
        
        except SQLAlchemyError as e:
            last_error = str(e)
            
            # If this isn't the last attempt, wait before retrying
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            
        except Exception as e:
            last_error = str(e)
            
            # For non-SQLAlchemy errors, don't retry
            break
    
    # All retries failed
    return DatabaseHealthStatus(
        is_healthy=False,
        message=f"Database connection failed after {max_retries} attempts",
        error=last_error,
    )
