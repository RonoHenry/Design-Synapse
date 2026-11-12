"""Apply project-service migration."""
import os
import sys

sys.path.insert(0, os.path.abspath("."))

from sqlalchemy import create_engine, text

from packages.common.config.database import DatabaseConfig

config = DatabaseConfig()
engine = create_engine(
    config.get_connection_url(async_driver=False), **config.get_engine_kwargs()
)

# SQL from the migration file
migration_sql = """
CREATE TABLE projects (
    id INTEGER NOT NULL AUTO_INCREMENT,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    owner_id INTEGER NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'draft',
    is_public BOOLEAN DEFAULT 0,
    is_archived BOOLEAN DEFAULT 0,
    version INTEGER DEFAULT 1,
    project_metadata JSON,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id)
);

CREATE TABLE project_collaborators (
    project_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    PRIMARY KEY (project_id, user_id),
    FOREIGN KEY(project_id) REFERENCES projects (id) ON DELETE CASCADE
);

CREATE TABLE comments (
    id INTEGER NOT NULL AUTO_INCREMENT,
    content TEXT NOT NULL,
    author_id INTEGER NOT NULL,
    project_id INTEGER NOT NULL,
    parent_id INTEGER,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    FOREIGN KEY(parent_id) REFERENCES comments (id) ON DELETE CASCADE,
    FOREIGN KEY(project_id) REFERENCES projects (id) ON DELETE CASCADE
);

INSERT INTO alembic_version (version_num) VALUES ('b2c3d4e5f6a7');
"""

with engine.connect() as conn:
    for statement in migration_sql.strip().split(";"):
        statement = statement.strip()
        if statement:
            try:
                conn.execute(text(statement))
                print(f"✅ Executed: {statement[:50]}...")
            except Exception as e:
                print(f"❌ Error: {e}")
                print(f"   Statement: {statement[:100]}")

    conn.commit()
    print("\n✅ Project-service migration applied successfully!")
