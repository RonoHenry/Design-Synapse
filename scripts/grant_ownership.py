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
    # First, grant all privileges on all tables
    cur.execute('GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO design_synapse_user')
    
    # Then, alter the ownership of all tables
    cur.execute("""
        DO $$
        DECLARE
            t text;
        BEGIN
            FOR t IN 
                SELECT tablename FROM pg_tables WHERE schemaname = 'public'
            LOOP
                EXECUTE format('ALTER TABLE %I OWNER TO design_synapse_user', t);
            END LOOP;
        END
        $$;
    """)
    
    # Also grant privileges on all sequences
    cur.execute('GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO design_synapse_user')
    
    # And update ownership of sequences
    cur.execute("""
        DO $$
        DECLARE
            s text;
        BEGIN
            FOR s IN 
                SELECT sequencename FROM pg_sequences WHERE schemaname = 'public'
            LOOP
                EXECUTE format('ALTER SEQUENCE %I OWNER TO design_synapse_user', s);
            END LOOP;
        END
        $$;
    """)
    
    print("Successfully granted permissions and ownership")

except Exception as e:
    print(f"Error granting permissions: {e}")

finally:
    # Close cursor and connection
    cur.close()
    conn.close()