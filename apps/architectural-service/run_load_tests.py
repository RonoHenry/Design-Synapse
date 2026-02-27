"""Run load tests and generate performance report."""

import subprocess
import sys
from pathlib import Path


def run_load_tests():
    """Run load tests and capture results."""
    print("=" * 80)
    print("ARCHITECTURAL SERVICE - LOAD TESTING")
    print("=" * 80)
    print()

    print("Running load tests...")
    print("Note: These tests require the service to be running on localhost:8000")
    print()

    # Run pytest with load marker
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/load/test_load_performance.py",
            "-v",
            "-s",
            "-m",
            "load",
            "--tb=short",
            "--color=yes",
        ],
        cwd=Path(__file__).parent,
        capture_output=False,
    )

    print()
    print("=" * 80)

    if result.returncode == 0:
        print("✓ Load tests completed successfully")
        print()
        print("Performance Summary:")
        print("- API performance validated under concurrent load")
        print("- Response times within acceptable thresholds")
        print("- System stability confirmed")
        print("- Concurrent design updates handled correctly")
        print("- Collaboration with multiple users tested")
    elif result.returncode == 5:
        print("⚠ Load tests skipped (service not running)")
        print()
        print("To run load tests:")
        print("1. Start the Architectural Service:")
        print("   uvicorn src.main:app --port 8000")
        print()
        print("2. Run this script again:")
        print("   python run_load_tests.py")
    else:
        print("✗ Load tests failed")
        print()
        print("Check the output above for details")

    print("=" * 80)

    return result.returncode


if __name__ == "__main__":
    sys.exit(run_load_tests())
