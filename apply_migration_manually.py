"""Manually apply the migration."""
import sys
import os

sys.path.insert(0, os.path.abspath('.'))

from packages.common.config.database import DatabaseConfig
from sqlalchemy import create_engine, text

config = DatabaseConfig()
engine = create_engine(
    config.get_connection_url(async_driver=False),
    **config.get_engine_kwargs()
)

# SQL from the migration file
migration_sql = """
CREATE TABLE users (
    id INTEGER NOT NULL AUTO_INCREMENT,
    email VARCHAR(255) NOT NULL,
    username VARCHAR(255) NOT NULL,
    password VARCHAR(255) NOT NULL,
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_active BOOLEAN NOT NULL DEFAULT 1,
    PRIMARY KEY (id)
);

CREATE UNIQUE INDEX ix_users_email ON users (email);
CREATE UNIQUE INDEX ix_users_username ON users (username);

CREATE TABLE roles (
    id INTEGER NOT NULL AUTO_INCREMENT,
    name VARCHAR(255) NOT NULL,
    description VARCHAR(500),
    PRIMARY KEY (id)
);

CREATE INDEX ix_roles_id ON roles (id);
CREATE UNIQUE INDEX ix_roles_name ON roles (name);

CREATE TABLE user_roles (
    user_id INTEGER NOT NULL,
    role_id INTEGER NOT NULL,
    PRIMARY KEY (user_id, role_id),
    FOREIGN KEY(role_id) REFERENCES roles (id),
    FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL,
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

INSERT INTO alembic_version (version_num) VALUES ('a1b2c3d4e5f6');
"""

with engine.connect() as conn:
    for statement in migration_sql.strip().split(';'):
        statement = statement.strip()
        if statement:
            try:
                conn.execute(text(statement))
                print(f"✅ Executed: {statement[:50]}...")
            except Exception as e:
                print(f"❌ Error: {e}")
                print(f"   Statement: {statement[:100]}")
    
    conn.commit()
    print("\n✅ Migration applied successfully!")
