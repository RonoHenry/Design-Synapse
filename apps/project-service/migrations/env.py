import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Add the project root directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Add packages directory to path for common config
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
)

# Import the SQLAlchemy Base and models
from src.infrastructure.database import Base
from src.models.comment import Comment
from src.models.project import Project

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set the target metadata to our Base.metadata
target_metadata = Base.metadata

# Override the sqlalchemy.url from environment variables if available
# This allows using the DatabaseConfig for TiDB connection
try:
    # Change to project root to find .env file
    project_root = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..")
    )
    os.chdir(project_root)

    from packages.common.config.database import DatabaseConfig

    db_config = DatabaseConfig()
    connection_url = db_config.get_connection_url(async_driver=False)
    config.set_main_option("sqlalchemy.url", connection_url)
    print(
        f"Using database connection: {db_config.host}:{db_config.port}/{db_config.database}"
    )
except Exception as e:
    # Fall back to the URL in alembic.ini if config fails
    print(f"Warning: Could not load DatabaseConfig: {e}")
    print("Falling back to alembic.ini URL")
    pass

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
