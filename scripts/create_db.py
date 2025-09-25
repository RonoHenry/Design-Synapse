import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Connect to PostgreSQL server (to create database)
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
    cursor.execute("DROP DATABASE IF EXISTS design_synapse_user_db")
    # Create database
    cursor.execute("CREATE DATABASE design_synapse_user_db")

print("Database created successfully")
