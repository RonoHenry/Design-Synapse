"""
Database Configuration and Connection Management

Handles SQLAlchemy setup, session management, and database connections
for the Labor Services Marketplace with TiDB compatibility.
"""

from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from sqlalchemy.pool import QueuePool
from typing import Generator
import logging

from .config import get_settings

logger = logging.getLogger(__name__)

# SQLAlchemy setup
settings = get_settings()

# Create engine with database-specific settings
connect_args = {}
if settings.database_url.startswith("mysql"):
    # TiDB/MySQL-specific settings
    connect_args = {
        "charset": "utf8mb4",
        "autocommit": False,
    }
elif settings.database_url.startswith("sqlite"):
    # SQLite-specific settings
    connect_args = {
        "check_same_thread": False,
    }

# Create engine with appropriate settings based on database type
if settings.database_url.startswith("sqlite"):
    # SQLite configuration
    engine = create_engine(
        settings.database_url,
        echo=settings.debug,
        connect_args=connect_args
    )
else:
    # MySQL/TiDB configuration
    engine = create_engine(
        settings.database_url,
        poolclass=QueuePool,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        pool_pre_ping=True,
        pool_recycle=3600,
        echo=settings.debug,
        connect_args=connect_args
    )

# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Base class for models
Base = declarative_base()

# Metadata for migrations
metadata = MetaData()


def get_db() -> Generator[Session, None, None]:
    """
    Database session dependency for FastAPI
    
    Yields:
        Session: SQLAlchemy database session
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def get_db_session():
    """
    Context manager for database sessions
    
    Returns:
        Session: SQLAlchemy database session
    """
    return SessionLocal()


def create_tables():
    """Create all database tables"""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        raise


def drop_tables():
    """Drop all database tables (use with caution)"""
    try:
        Base.metadata.drop_all(bind=engine)
        logger.info("Database tables dropped successfully")
    except Exception as e:
        logger.error(f"Error dropping database tables: {e}")
        raise


def check_database_connection() -> bool:
    """
    Check if database connection is working
    
    Returns:
        bool: True if connection is successful, False otherwise
    """
    try:
        with engine.connect() as connection:
            connection.execute("SELECT 1")
        logger.info("Database connection successful")
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False


class DatabaseManager:
    """Database management utilities"""
    
    @staticmethod
    def get_session() -> Session:
        """Get a new database session"""
        return SessionLocal()
    
    @staticmethod
    def close_session(session: Session):
        """Close a database session"""
        try:
            session.close()
        except Exception as e:
            logger.error(f"Error closing database session: {e}")
    
    @staticmethod
    def commit_session(session: Session):
        """Commit a database session"""
        try:
            session.commit()
        except Exception as e:
            logger.error(f"Error committing database session: {e}")
            session.rollback()
            raise
    
    @staticmethod
    def rollback_session(session: Session):
        """Rollback a database session"""
        try:
            session.rollback()
        except Exception as e:
            logger.error(f"Error rolling back database session: {e}")


# Health check function
async def health_check() -> dict:
    """
    Perform database health check
    
    Returns:
        dict: Health check results
    """
    try:
        is_connected = check_database_connection()
        return {
            "database": "healthy" if is_connected else "unhealthy",
            "connection": "active" if is_connected else "failed"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "database": "unhealthy",
            "connection": "failed",
            "error": str(e)
        }