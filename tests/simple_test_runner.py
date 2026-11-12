#!/usr/bin/env python3
"""
Simple integration test runner to verify our TDD infrastructure works.

This is a minimal implementation to demonstrate the TDD approach is working.
"""
import subprocess
import sys
from pathlib import Path


def run_basic_tests():
    """Run basic infrastructure tests to verify setup."""
    print("🧪 Running basic integration test infrastructure verification...")

    test_dir = Path(__file__).parent

    try:
        # Run basic infrastructure tests
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                str(test_dir / "integration" / "test_basic_infrastructure.py"),
                "-v",
                "--tb=short",
            ],
            cwd=test_dir.parent,
        )

        if result.returncode == 0:
            print("✅ Basic infrastructure tests passed!")
            return True
        else:
            print("❌ Basic infrastructure tests failed!")
            return False

    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return False


def check_docker_availability():
    """Check if Docker is available and running."""
    try:
        result = subprocess.run(["docker", "version"], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Docker is available and running")
            return True
        else:
            print("❌ Docker is not running properly")
            return False
    except FileNotFoundError:
        print("❌ Docker is not installed")
        return False
    except Exception as e:
        print(f"❌ Error checking Docker: {e}")
        return False


def main():
    """Main entry point for simple test runner."""
    print("🚀 Starting integration test infrastructure verification...")

    # Check prerequisites
    if not check_docker_availability():
        print("Please ensure Docker is installed and running")
        return 1

    # Run basic tests
    if not run_basic_tests():
        return 1

    print("✅ Integration test infrastructure is ready!")
    print("📝 Next steps:")
    print("   1. Install test dependencies: pip install -r tests/requirements.txt")
    print("   2. Run full integration tests: python tests/run_integration_tests.py")
    print("   3. Or use Make commands: cd tests && make test")

    return 0


if __name__ == "__main__":
    sys.exit(main())
