import psycopg2

# Connect to PostgreSQL server
conn = psycopg2.connect(
    dbname='design_synapse_user_db',
    user='postgres',
    password='postgres',
    host='localhost',
    port='5432'
)

# List all tables
with conn.cursor() as cursor:
    cursor.execute("""
    SELECT table_name 
    FROM information_schema.tables 
    WHERE table_schema = 'public' 
    AND table_type = 'BASE TABLE';
    """)
    tables = cursor.fetchall()
    print("Current tables:")
    for table in tables:
        print(f"- {table[0]}")

conn.close()