import sys
import time

import psycopg2


def wait_for_postgres(max_attempts=30):
    attempt = 0
    while attempt < max_attempts:
        try:
            conn = psycopg2.connect(
                dbname="postgres",
                user="design_synapse_user",
                password="design_synapse_password",
                host="localhost",
                port="5432",
            )
            conn.close()
            print("Successfully connected to PostgreSQL")
            return True
        except psycopg2.OperationalError:
            attempt += 1
            print(
                f"Waiting for PostgreSQL to start... (attempt {attempt}/{max_attempts})"
            )
            time.sleep(1)

    print("Failed to connect to PostgreSQL after maximum attempts")
    return False


if __name__ == "__main__":
    if not wait_for_postgres():
        sys.exit(1)
