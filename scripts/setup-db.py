import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Connect to PostgreSQL server with admin role
conn = psycopg2.connect(
    dbname='postgres',
    user='postgres',
    password='postgres',
    host='localhost',
    port='5432'
)
conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)

# Create role and database
with conn.cursor() as cursor:
    # Drop role if exists
    cursor.execute("DROP ROLE IF EXISTS design_synapse_user")
    
    # Create role
    cursor.execute("""
        CREATE ROLE design_synapse_user WITH
        LOGIN
        NOSUPERUSER
        NOCREATEDB
        NOCREATEROLE
        INHERIT
        NOREPLICATION
        CONNECTION LIMIT -1
        PASSWORD 'design_synapse_password'
    """)
    
    # Drop database if exists
    cursor.execute("DROP DATABASE IF EXISTS design_synapse_user_db")
    
    # Create database owned by the new role
    cursor.execute("CREATE DATABASE design_synapse_user_db OWNER design_synapse_user")
    
    # Connect to the new database
    conn2 = psycopg2.connect(
        dbname='design_synapse_user_db',
        user='postgres',
        password='postgres',
        host='localhost',
        port='5432'
    )
    conn2.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    
    # Grant all privileges to the new role
    with conn2.cursor() as cursor2:
        cursor2.execute("GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO design_synapse_user")
        cursor2.execute("GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO design_synapse_user")
        cursor2.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON TABLES TO design_synapse_user")
        cursor2.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON SEQUENCES TO design_synapse_user")
    
    conn2.close()

conn.close()

print("Database and role setup completed successfully")