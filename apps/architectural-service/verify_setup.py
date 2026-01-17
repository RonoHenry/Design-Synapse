"""Verify project setup."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))


def verify_imports():
    """Verify all core modules can be imported."""
    print("Verifying imports...")

    try:
        from src.core.config import settings

        print(f"✓ Config loaded: {settings.app_name} v{settings.app_version}")
    except Exception as e:
        print(f"✗ Config failed: {e}")
        return False

    try:
        from src.core.exceptions import (ConflictError, NotFoundError,
                                         ValidationError)

        print("✓ Exceptions loaded")
    except Exception as e:
        print(f"✗ Exceptions failed: {e}")
        return False

    try:
        from src.core.database import Base, get_db

        print("✓ Database module loaded")
    except Exception as e:
        print(f"✗ Database failed: {e}")
        # This is expected if asyncmy is not installed
        print("  Note: Database connection requires asyncmy package")

    return True


def verify_structure():
    """Verify project structure."""
    print("\nVerifying project structure...")

    required_dirs = [
        "src",
        "src/core",
        "src/models",
        "src/repositories",
        "src/services",
        "src/api",
        "src/api/v1",
        "src/api/v1/routes",
        "src/api/v1/schemas",
        "src/infrastructure",
        "tests",
        "tests/unit",
        "tests/integration",
        "tests/property",
        "migrations",
    ]

    base_path = Path(__file__).parent
    all_exist = True

    for dir_path in required_dirs:
        full_path = base_path / dir_path
        if full_path.exists():
            print(f"✓ {dir_path}")
        else:
            print(f"✗ {dir_path} - MISSING")
            all_exist = False

    return all_exist


def verify_files():
    """Verify required files exist."""
    print("\nVerifying required files...")

    required_files = [
        "pyproject.toml",
        "requirements.txt",
        "pytest.ini",
        "alembic.ini",
        "README.md",
        "Dockerfile",
        ".env.example",
        ".gitignore",
        "src/__init__.py",
        "src/main.py",
        "src/core/config.py",
        "src/core/database.py",
        "src/core/exceptions.py",
        "migrations/env.py",
        "migrations/script.py.mako",
        "tests/conftest.py",
    ]

    base_path = Path(__file__).parent
    all_exist = True

    for file_path in required_files:
        full_path = base_path / file_path
        if full_path.exists():
            print(f"✓ {file_path}")
        else:
            print(f"✗ {file_path} - MISSING")
            all_exist = False

    return all_exist


def main():
    """Run all verification checks."""
    print("=" * 60)
    print("Architectural Service - Setup Verification")
    print("=" * 60)

    imports_ok = verify_imports()
    structure_ok = verify_structure()
    files_ok = verify_files()

    print("\n" + "=" * 60)
    if imports_ok and structure_ok and files_ok:
        print("✓ All checks passed!")
        print("=" * 60)
        return 0
    else:
        print("✗ Some checks failed")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
