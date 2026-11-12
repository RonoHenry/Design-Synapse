#!/usr/bin/env python3
"""
Test runner for monitoring package.
"""

import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

if __name__ == "__main__":
    import pytest

    # Run tests in the current directory
    test_dir = Path(__file__).parent / "tests"
    exit_code = pytest.main([str(test_dir), "-v"])
    sys.exit(exit_code)
