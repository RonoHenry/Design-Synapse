#!/usr/bin/env python3
"""
Comprehensive database health check script.
Tests database connectivity, migrations, and basic operations across all services.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add workspace root to Python path
workspace_root = Path(__file__).parent
sys.path.insert(0, str(workspace_root))


async def test_tidb_connection():
    """Test basic TiDB connection."""
    print("🔍 Testing TiDB Connection...")

    try:
        import pymysql

        # Get connection details from environment
        host = os.getenv("TIDB_HOST", "gateway01.us-west-2.prod.aws.tidbcloud.com")
        port = int(os.getenv("TIDB_PORT", "4000"))
        user = os.getenv("TIDB_USER", "2aQp4Ky4TaLLisi.root")
        password = os.getenv("TIDB_PASSWORD", "Kiro2024!")
        database = os.getenv("TIDB_DATABASE", "designsynapse")

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
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()
            print(f"✅ TiDB Connection successful! Version: {version[0]}")

            # Test basic operations
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            print(f"✅ Found {len(tables)} tables in database")

        connection.close()
        return True

    except Exception as e:
        print(f"❌ TiDB Connection failed: {e}")
        return False


async def test_user_service_db():
    """Test user service database operations."""
    print("\n🔍 Testing User Service Database...")

    try:
        # Import user service components
        sys.path.insert(0, str(workspace_root / "apps" / "user-service" / "src"))
        from core.config import UserServiceSettings
        from core.database import get_database_url

        settings = UserServiceSettings()
        db_url = get_database_url(settings)
        print(f"✅ User service database URL configured: {db_url[:50]}...")

        # Test SQLAlchemy connection
        from sqlalchemy import create_engine, text

        engine = create_engine(db_url)

        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("✅ User service SQLAlchemy connection successful")

            # Check if user tables exist
            result = conn.execute(text("SHOW TABLES LIKE 'users'"))
            if result.fetchone():
                print("✅ User tables found")
            else:
                print("⚠️  User tables not found (may need migration)")

        return True

    except Exception as e:
        print(f"❌ User service database test failed: {e}")
        return False


async def test_project_service_db():
    """Test project service database operations."""
    print("\n🔍 Testing Project Service Database...")

    try:
        # Import project service components
        sys.path.insert(0, str(workspace_root / "apps" / "project-service" / "src"))
        from core.config import ProjectServiceSettings

        settings = ProjectServiceSettings()
        print(f"✅ Project service configuration loaded")

        # Test database connection
        from sqlalchemy import create_engine, text

        engine = create_engine(settings.database_url)

        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("✅ Project service SQLAlchemy connection successful")

            # Check if project tables exist
            result = conn.execute(text("SHOW TABLES LIKE 'projects'"))
            if result.fetchone():
                print("✅ Project tables found")
            else:
                print("⚠️  Project tables not found (may need migration)")

        return True

    except Exception as e:
        print(f"❌ Project service database test failed: {e}")
        return False


async def test_knowledge_service_db():
    """Test knowledge service database operations."""
    print("\n🔍 Testing Knowledge Service Database...")

    try:
        # Import knowledge service components
        sys.path.insert(0, str(workspace_root / "apps" / "knowledge-service"))
        from knowledge_service.core.config import KnowledgeServiceSettings

        settings = KnowledgeServiceSettings()
        print(f"✅ Knowledge service configuration loaded")

        # Test database connection
        from sqlalchemy import create_engine, text

        engine = create_engine(settings.database_url)

        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("✅ Knowledge service SQLAlchemy connection successful")

            # Check if knowledge tables exist
            result = conn.execute(text("SHOW TABLES LIKE 'resources'"))
            if result.fetchone():
                print("✅ Knowledge tables found")
            else:
                print("⚠️  Knowledge tables not found (may need migration)")

        return True

    except Exception as e:
        print(f"❌ Knowledge service database test failed: {e}")
        return False


async def test_labor_service_db():
    """Test labor service database operations."""
    print("\n🔍 Testing Labor Service Database...")

    try:
        # Import labor service components
        sys.path.insert(0, str(workspace_root / "apps" / "labor-service" / "src"))
        from core.config import LaborServiceSettings

        settings = LaborServiceSettings()
        print(f"✅ Labor service configuration loaded")

        # Test database connection
        from sqlalchemy import create_engine, text

        engine = create_engine(settings.database_url)

        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("✅ Labor service SQLAlchemy connection successful")

            # Check if labor tables exist
            result = conn.execute(text("SHOW TABLES LIKE 'service_providers'"))
            if result.fetchone():
                print("✅ Labor tables found")
            else:
                print("⚠️  Labor tables not found (may need migration)")

        return True

    except Exception as e:
        print(f"❌ Labor service database test failed: {e}")
        return False


async def test_design_service_db():
    """Test design service database operations."""
    print("\n🔍 Testing Design Service Database...")

    try:
        # Import design service components
        sys.path.insert(0, str(workspace_root / "apps" / "design-service" / "src"))
        from core.config import DesignServiceSettings

        settings = DesignServiceSettings()
        print(f"✅ Design service configuration loaded")

        # Test database connection
        from sqlalchemy import create_engine, text

        engine = create_engine(settings.database_url)

        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("✅ Design service SQLAlchemy connection successful")

            # Check if design tables exist
            result = conn.execute(text("SHOW TABLES LIKE 'designs'"))
            if result.fetchone():
                print("✅ Design tables found")
            else:
                print("⚠️  Design tables not found (may need migration)")

        return True

    except Exception as e:
        print(f"❌ Design service database test failed: {e}")
        return False


async def test_vendor_service_db():
    """Test vendor service database operations."""
    print("\n🔍 Testing Vendor Service Database...")

    try:
        # Import vendor service components
        sys.path.insert(0, str(workspace_root / "apps" / "vendor-service" / "src"))
        from core.config import VendorServiceSettings

        settings = VendorServiceSettings()
        print(f"✅ Vendor service configuration loaded")

        # Test database connection
        from sqlalchemy import create_engine, text

        engine = create_engine(settings.database_url)

        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("✅ Vendor service SQLAlchemy connection successful")

            # Check if vendor tables exist
            result = conn.execute(text("SHOW TABLES LIKE 'vendors'"))
            if result.fetchone():
                print("✅ Vendor tables found")
            else:
                print("⚠️  Vendor tables not found (may need migration)")

        return True

    except Exception as e:
        print(f"❌ Vendor service database test failed: {e}")
        return False


async def test_migration_status():
    """Check migration status across all services."""
    print("\n🔍 Testing Migration Status...")

    try:
        import pymysql

        # Get connection details
        host = os.getenv("TIDB_HOST", "gateway01.us-west-2.prod.aws.tidbcloud.com")
        port = int(os.getenv("TIDB_PORT", "4000"))
        user = os.getenv("TIDB_USER", "2aQp4Ky4TaLLisi.root")
        password = os.getenv("TIDB_PASSWORD", "Kiro2024!")
        database = os.getenv("TIDB_DATABASE", "designsynapse")

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
            # Check alembic version tables
            services = [
                "user_service",
                "project_service",
                "knowledge_service",
                "labor_service",
                "design_service",
            ]

            for service in services:
                table_name = f"alembic_version_{service}"
                cursor.execute(f"SHOW TABLES LIKE '{table_name}'")
                if cursor.fetchone():
                    cursor.execute(f"SELECT version_num FROM {table_name}")
                    version = cursor.fetchone()
                    if version:
                        print(f"✅ {service}: Migration version {version[0]}")
                    else:
                        print(f"⚠️  {service}: No migration version found")
                else:
                    print(f"⚠️  {service}: No alembic version table found")

        connection.close()
        return True

    except Exception as e:
        print(f"❌ Migration status check failed: {e}")
        return False


async def main():
    """Run comprehensive database health check."""
    print("🚀 Starting Comprehensive Database Health Check")
    print("=" * 60)

    results = []

    # Test basic TiDB connection
    results.append(await test_tidb_connection())

    # Test each service database
    results.append(await test_user_service_db())
    results.append(await test_project_service_db())
    results.append(await test_knowledge_service_db())
    results.append(await test_labor_service_db())
    results.append(await test_design_service_db())
    results.append(await test_vendor_service_db())

    # Test migration status
    results.append(await test_migration_status())

    # Summary
    print("\n" + "=" * 60)
    print("📊 Database Health Check Summary")
    print("=" * 60)

    passed = sum(results)
    total = len(results)

    if passed == total:
        print(f"🎉 All tests passed! ({passed}/{total})")
        print("✅ Database is healthy and ready for use")
    else:
        print(f"⚠️  {passed}/{total} tests passed")
        print("❌ Some database issues detected - see details above")

    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
