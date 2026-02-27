"""Generate OpenAPI specification file."""

import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from main import app


def generate_openapi_spec():
    """Generate and save OpenAPI specification."""
    # Get OpenAPI schema
    openapi_schema = app.openapi()

    # Ensure it's OpenAPI 3.0
    openapi_schema["openapi"] = "3.0.2"

    # Save to file
    output_path = Path(__file__).parent / "openapi.json"
    with open(output_path, "w") as f:
        json.dump(openapi_schema, f, indent=2)

    print(f"✓ OpenAPI specification generated: {output_path}")
    print(f"✓ Title: {openapi_schema['info']['title']}")
    print(f"✓ Version: {openapi_schema['info']['version']}")
    print(f"✓ Endpoints: {len(openapi_schema['paths'])}")
    print(f"✓ Schemas: {len(openapi_schema.get('components', {}).get('schemas', {}))}")

    # Validate required fields
    assert "openapi" in openapi_schema, "Missing openapi version"
    assert "info" in openapi_schema, "Missing info section"
    assert "title" in openapi_schema["info"], "Missing title"
    assert "version" in openapi_schema["info"], "Missing version"
    assert "description" in openapi_schema["info"], "Missing description"
    assert "paths" in openapi_schema, "Missing paths"
    assert len(openapi_schema["paths"]) > 0, "No endpoints defined"

    print("\n✓ OpenAPI specification is valid!")

    return openapi_schema


if __name__ == "__main__":
    try:
        generate_openapi_spec()
    except Exception as e:
        print(f"✗ Error generating OpenAPI spec: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
