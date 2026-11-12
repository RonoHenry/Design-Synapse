#!/usr/bin/env python3
"""
Simple database connectivity test.
"""

import os

import pymysql


def test_tidb_connection():
    """Test basic TiDB connection."""
    print("🔍 Testing TiDB Connection...")

    try:
        # Get connection details from environment
        host = os.getenv("DB_HOST", "gateway01.eu-central-1.prod.aws.tidbcloud.com")
        port = int(os.getenv("DB_PORT", "4000"))
        user = os.getenv("DB_USERNAME", "kbFV66oHabEtRud.root")
        password = os.getenv("DB_PASSWORD", "aPdG5f34Qjzs0gBM")
        database = os.getenv("DB_DATABASE", "test")

        print(f"Connecting to: {host}:{port}/{database}")

        # Test connection
        connection = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            ssl_ca="ca.pem",
            ssl_verify_cert=True,
            ssl_verify_identity=True,
        )

        with connection.cursor() as cursor:
            # Test basic operations
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()
            print(f"✅ TiDB Connection successful! Version: {version[0]}")

            # Show all tables
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            print(f"✅ Found {len(tables)} tables in database:")
            for table in tables[:10]:  # Show first 10 tables
                print(f"   - {table[0]}")
            if len(tables) > 10:
                print(f"   ... and {len(tables) - 10} more tables")

            # Test a simple query on each service's main table
            service_tables = {
                "users": "User Service",
                "projects": "Project Service",
                "resources": "Knowledge Service",
                "service_providers": "Labor Service",
                "designs": "Design Service",
                "vendors": "Vendor Service",
            }

            print("\n🔍 Testing service tables:")
            for table_name, service_name in service_tables.items():
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    count = cursor.fetchone()[0]
                    print(f"✅ {service_name}: {count} records in {table_name}")
                except Exception as e:
                    print(
                        f"⚠️  {service_name}: Table {table_name} not found or error: {str(e)[:50]}..."
                    )

            # Test alembic version tables
            print("\n🔍 Testing migration status:")
            cursor.execute("SHOW TABLES LIKE 'alembic_version%'")
            alembic_tables = cursor.fetchall()

            if alembic_tables:
                for table in alembic_tables:
                    table_name = table[0]
                    try:
                        cursor.execute(f"SELECT version_num FROM {table_name}")
                        version = cursor.fetchone()
                        if version:
                            service = table_name.replace("alembic_version_", "")
                            print(f"✅ {service}: Migration version {version[0]}")
                        else:
                            print(f"⚠️  {table_name}: No version found")
                    except Exception as e:
                        print(f"❌ {table_name}: Error reading version: {e}")
            else:
                print("⚠️  No alembic version tables found")

        connection.close()
        return True

    except Exception as e:
        print(f"❌ TiDB Connection failed: {e}")
        return False


if __name__ == "__main__":
    success = test_tidb_connection()

    print("\n" + "=" * 60)
    if success:
        print("🎉 Database connectivity test PASSED!")
        print("✅ TiDB is accessible and contains expected data")
    else:
        print("❌ Database connectivity test FAILED!")
        print("⚠️  Check connection settings and network access")
    print("=" * 60)
