"""Run comprehensive test validation for the Architectural Service."""

import subprocess
import sys
from pathlib import Path


def run_command(cmd, description):
    """Run a command and return the result."""
    print(f"\n{'='*80}")
    print(f"{description}")
    print(f"{'='*80}")

    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minutes timeout
        )

        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)

        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print(f"✗ Command timed out after 5 minutes")
        return False
    except Exception as e:
        print(f"✗ Error running command: {e}")
        return False


def main():
    """Run all test validations."""
    results = {}

    # 1. Run unit tests
    results["unit"] = run_command(
        "pytest tests/unit -v --tb=short -x", "1. Running Unit Tests"
    )

    # 2. Run property-based tests
    results["property"] = run_command(
        "pytest tests/property -v --tb=short -x --hypothesis-profile=default",
        "2. Running Property-Based Tests",
    )

    # 3. Run integration tests
    results["integration"] = run_command(
        "pytest tests/integration -v --tb=short -x", "3. Running Integration Tests"
    )

    # 4. Run coverage report
    results["coverage"] = run_command(
        "pytest --cov=src --cov-report=term --cov-report=html --tb=short",
        "4. Running Coverage Analysis",
    )

    # Print summary
    print(f"\n{'='*80}")
    print("TEST VALIDATION SUMMARY")
    print(f"{'='*80}")

    for test_type, passed in results.items():
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{test_type.upper():20} {status}")

    all_passed = all(results.values())

    if all_passed:
        print(f"\n✓ All test validations passed!")
        return 0
    else:
        print(f"\n✗ Some test validations failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
