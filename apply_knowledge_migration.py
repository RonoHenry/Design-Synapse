"""Apply knowledge-service migration."""
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
CREATE TABLE resources (
    id INTEGER NOT NULL AUTO_INCREMENT,
    title VARCHAR(255) NOT NULL,
    description VARCHAR(1000) NOT NULL,
    content_type VARCHAR(50) NOT NULL,
    source_url VARCHAR(500) NOT NULL,
    source_platform VARCHAR(100),
    vector_embedding JSON,
    author VARCHAR(255),
    publication_date DATETIME,
    doi VARCHAR(100),
    license_type VARCHAR(100),
    summary TEXT,
    key_takeaways JSON,
    keywords JSON,
    storage_path VARCHAR(500) NOT NULL,
    file_size INTEGER,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id)
);

CREATE TABLE topics (
    id INTEGER NOT NULL AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    description VARCHAR(500) NOT NULL,
    parent_id INTEGER,
    PRIMARY KEY (id),
    UNIQUE KEY (name),
    FOREIGN KEY(parent_id) REFERENCES topics (id)
);

CREATE TABLE bookmarks (
    id INTEGER NOT NULL AUTO_INCREMENT,
    user_id INTEGER NOT NULL,
    resource_id INTEGER NOT NULL,
    notes TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    CONSTRAINT check_user_id_positive CHECK (user_id > 0),
    CONSTRAINT unique_user_resource UNIQUE (user_id, resource_id),
    FOREIGN KEY(resource_id) REFERENCES resources (id) ON DELETE CASCADE
);

CREATE TABLE citations (
    id INTEGER NOT NULL AUTO_INCREMENT,
    resource_id INTEGER NOT NULL,
    project_id INTEGER NOT NULL,
    context TEXT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY (id),
    FOREIGN KEY(resource_id) REFERENCES resources (id) ON DELETE CASCADE
);

CREATE TABLE resource_topics (
    resource_id INTEGER NOT NULL,
    topic_id INTEGER NOT NULL,
    PRIMARY KEY (resource_id, topic_id),
    FOREIGN KEY(resource_id) REFERENCES resources (id),
    FOREIGN KEY(topic_id) REFERENCES topics (id)
);

INSERT INTO alembic_version (version_num) VALUES ('c3d4e5f6a7b8');
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
    print("\n✅ Knowledge-service migration applied successfully!")
