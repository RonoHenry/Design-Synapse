"""Grant necessary database permissions to service users."""

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Connect to PostgreSQL as postgres user
conn = psycopg2.connect(
    dbname="design_synapse_user_db",
    user="postgres",
    password="postgres",
    host="localhost",
    port="5432",
)

# Set isolation level to AUTOCOMMIT
conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)

# Create a cursor
cur = conn.cursor()

try:
    # Grant all privileges and ownership on tables and sequences to design_synapse_user
    tables = ["roles", "users", "user_profiles", "user_roles"]
    for table in tables:
        # Grant ownership of tables
        cur.execute(f"ALTER TABLE {table} OWNER TO design_synapse_user")
        print(f"Successfully transferred ownership of {table} table")

        # For tables with id sequences
        if table != "user_roles":  # user_roles table might not have an id sequence
            cur.execute(f"ALTER SEQUENCE {table}_id_seq OWNER TO design_synapse_user")
            print(f"Successfully transferred ownership of {table}_id_seq sequence")

except Exception as e:
    print(f"Error granting permissions: {e}")

finally:
    # Close cursor and connection
    cur.close()
    conn.close()
