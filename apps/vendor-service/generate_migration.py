"""Generate initial Alembic migration for vendor service."""
import subprocess
import sys


def main():
    """Generate the initial migration."""
    print("Generating initial migration for vendor service...")

    try:
        result = subprocess.run(
            [
                "alembic",
                "revision",
                "--autogenerate",
                "-m",
                "initial_vendor_service_schema",
            ],
            cwd="apps/vendor-service",
            capture_output=True,
            text=True,
        )

        print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)

        if result.returncode == 0:
            print("\n✓ Migration generated successfully!")
            print(
                "Review the migration file in apps/vendor-service/migrations/versions/"
            )
        else:
            print("\n✗ Migration generation failed!")
            sys.exit(1)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
