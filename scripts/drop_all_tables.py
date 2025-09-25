import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Connect to PostgreSQL server
conn = psycopg2.connect(
    dbname="design_synapse_user_db",
    user="postgres",
    password="postgres",
    host="localhost",
    port="5432",
)

# Drop all tables
with conn.cursor() as cursor:
    cursor.execute(
        """
    DO $$ DECLARE
        r RECORD;
    BEGIN
        FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') LOOP
            EXECUTE 'DROP TABLE IF EXISTS ' || quote_ident(r.tablename) || ' CASCADE';
        END LOOP;
    END $$;
    """
    )

conn.commit()
conn.close()

print("All tables dropped successfully")
