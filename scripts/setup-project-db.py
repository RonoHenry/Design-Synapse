"""Setup database for project service."""
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Connect to PostgreSQL server with admin role
conn = psycopg2.connect(
    dbname="postgres",
    user="postgres",
    password="postgres",
    host="localhost",
    port="5432",
)
conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)

# Create database
with conn.cursor() as cursor:
    # Drop database if exists
    cursor.execute("DROP DATABASE IF EXISTS design_synapse_project_db")

    # Create database using existing design_synapse_user role
    cursor.execute("CREATE DATABASE design_synapse_project_db OWNER design_synapse_user")

    # Connect to the new database
    conn2 = psycopg2.connect(
        dbname="design_synapse_project_db",
        user="postgres",
        password="postgres",
        host="localhost",
        port="5432",
    )
    conn2.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)

    # Grant all privileges to the role
    with conn2.cursor() as cursor2:
        cursor2.execute(
            "GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO design_synapse_user"
        )
        cursor2.execute(
            "GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO design_synapse_user"
        )
        cursor2.execute(
            "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON TABLES TO design_synapse_user"
        )
        cursor2.execute(
            "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON SEQUENCES TO design_synapse_user"
        )

    conn2.close()

conn.close()

print("Project database setup completed successfully")