"""Run tests with correct Python path."""
import os
import sys
import pytest

# Add the necessary paths
app_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(app_dir))
apps_dir = os.path.dirname(app_dir)

# Add paths to Python path
sys.path.extend([
    os.path.join(project_root, "apps", "knowledge-service"),
    project_root,
    os.path.dirname(project_root)  # Parent of project root
])

if __name__ == "__main__":
    # Run pytest
    sys.exit(pytest.main(["-v", "tests/"]))