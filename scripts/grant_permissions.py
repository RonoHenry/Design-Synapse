import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Connect to PostgreSQL as postgres user
conn = psycopg2.connect(
    dbname="design_synapse_user_db",
    user="postgres",
    password="postgres",
    host="localhost",
    port="5432"
)

# Set isolation level to AUTOCOMMIT
conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)

# Create a cursor
cur = conn.cursor()

try:
    # Grant all privileges on user_roles table to design_synapse_user
    cur.execute('GRANT ALL PRIVILEGES ON TABLE user_roles TO design_synapse_user')
    print("Successfully granted permissions on user_roles table")

except Exception as e:
    print(f"Error granting permissions: {e}")

finally:
    # Close cursor and connection
    cur.close()
    conn.close()