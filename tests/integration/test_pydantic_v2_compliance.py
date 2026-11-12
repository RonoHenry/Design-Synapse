"""
Property-based tests for Pydantic v2 compliance across the system.

Feature: system-wide-fixes
Property 2: Pydantic schemas use modern patterns
Validates: Requirements 2.1, 2.2
"""

import ast
import importlib
import inspect
import sys
from pathlib import Path
from typing import List, Tuple

import pytest


class TestPydanticV2Compliance:
    """Property-based tests for Pydantic v2 compliance."""

    def test_pydantic_schemas_use_modern_patterns(self):
        """
        Property 2: Pydantic schemas use modern patterns
        For any Pydantic schema in the system, it should use ConfigDict
        instead of class-based config and BaseModel instead of GenericModel

        **Feature: system-wide-fixes, Property 2: Pydantic schemas use modern patterns**
        **Validates: Requirements 2.1, 2.2**
        """
        workspace_root = Path(__file__).parent.parent.parent

        # Find all Python files that might contain Pydantic schemas
        schema_files = []

        # Check labor service schemas (primary target)
        labor_schemas_dir = workspace_root / "apps/labor-service/src/api/v1/schemas"
        if labor_schemas_dir.exists():
            schema_files.extend(labor_schemas_dir.glob("*.py"))

        # Check other service schemas
        for service_dir in [
            "apps/user-service",
            "apps/design-service",
            "apps/knowledge-service",
        ]:
            schemas_path = workspace_root / service_dir / "src/api/v1/schemas"
            if schemas_path.exists():
                schema_files.extend(schemas_path.glob("*.py"))

        # Check common packages
        common_packages = workspace_root / "packages/common"
        if common_packages.exists():
            for py_file in common_packages.rglob("*.py"):
                if "models.py" in py_file.name or "schema" in py_file.name.lower():
                    schema_files.append(py_file)

        violations = []

        for schema_file in schema_files:
            if schema_file.name == "__init__.py":
                continue

            try:
                # Read and parse the file
                content = schema_file.read_text(encoding="utf-8")

                # Check for Pydantic v1 patterns
                file_violations = self._check_pydantic_v1_patterns(schema_file, content)
                violations.extend(file_violations)

            except Exception as e:
                # Skip files that can't be read or parsed
                continue

        # Assert no violations found
        if violations:
            violation_messages = [
                f"{file}:{line}: {message}" for file, line, message in violations
            ]
            pytest.fail(
                f"Found {len(violations)} Pydantic v1 pattern violations:\n"
                + "\n".join(violation_messages[:10])  # Show first 10 violations
            )

    def _check_pydantic_v1_patterns(
        self, file_path: Path, content: str
    ) -> List[Tuple[str, int, str]]:
        """Check for Pydantic v1 patterns in file content."""
        violations = []
        lines = content.split("\n")

        for line_num, line in enumerate(lines, 1):
            line_stripped = line.strip()

            # Check for GenericModel import
            if "from pydantic.generics import GenericModel" in line:
                violations.append(
                    (
                        str(file_path),
                        line_num,
                        "Uses deprecated 'from pydantic.generics import GenericModel' - should use BaseModel",
                    )
                )

            # Check for GenericModel usage in class definitions
            if "GenericModel" in line and "class " in line:
                violations.append(
                    (
                        str(file_path),
                        line_num,
                        "Uses deprecated GenericModel in class definition - should use BaseModel",
                    )
                )

            # Check for class-based Config
            if line_stripped == "class Config:":
                violations.append(
                    (
                        str(file_path),
                        line_num,
                        "Uses deprecated class-based Config - should use model_config = ConfigDict(...)",
                    )
                )

            # Check for json_encoders in Config
            if (
                "json_encoders" in line
                and "class Config"
                not in content[max(0, content.find(line) - 200) : content.find(line)]
            ):
                # This is a heuristic to avoid false positives
                if (
                    "model_config"
                    not in content[
                        max(0, content.find(line) - 100) : content.find(line) + 100
                    ]
                ):
                    violations.append(
                        (
                            str(file_path),
                            line_num,
                            "Uses deprecated json_encoders - should use custom serializers or ConfigDict",
                        )
                    )

        return violations

    def test_no_pydantic_deprecation_warnings_in_imports(self):
        """
        Test that importing Pydantic schemas doesn't produce deprecation warnings.
        This validates that the migration is working correctly.
        """
        workspace_root = Path(__file__).parent.parent.parent

        # Test importing the labor service base schemas (main target)
        labor_base_schema_path = (
            workspace_root / "apps/labor-service/src/api/v1/schemas/base.py"
        )

        if not labor_base_schema_path.exists():
            pytest.skip("Labor service base schemas not found")

        # Add the labor service src to Python path temporarily
        labor_src_path = str(workspace_root / "apps/labor-service/src")
        if labor_src_path not in sys.path:
            sys.path.insert(0, labor_src_path)

        try:
            # Import the module and check for warnings
            import warnings

            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")

                # Import the base schemas module
                from api.v1.schemas import base

                # Check for Pydantic deprecation warnings
                pydantic_warnings = [
                    warning
                    for warning in w
                    if "pydantic" in str(warning.message).lower()
                    and (
                        "deprecated" in str(warning.message).lower()
                        or "config" in str(warning.message).lower()
                    )
                ]

                if pydantic_warnings:
                    warning_messages = [
                        str(warning.message) for warning in pydantic_warnings
                    ]
                    pytest.fail(
                        f"Found {len(pydantic_warnings)} Pydantic deprecation warnings:\n"
                        + "\n".join(warning_messages)
                    )

        except ImportError as e:
            pytest.skip(f"Could not import labor service schemas: {e}")
        finally:
            # Clean up sys.path
            if labor_src_path in sys.path:
                sys.path.remove(labor_src_path)

    def test_pydantic_v2_features_work(self):
        """
        Test that Pydantic v2 features are working correctly.
        This validates that the migration preserves functionality.
        """
        workspace_root = Path(__file__).parent.parent.parent
        labor_src_path = str(workspace_root / "apps/labor-service/src")

        if labor_src_path not in sys.path:
            sys.path.insert(0, labor_src_path)

        try:
            from datetime import datetime

            from api.v1.schemas.base import BaseResponse, SuccessResponse

            # Test BaseResponse with ConfigDict
            response = BaseResponse(message="Test message")
            assert response.success is True
            assert response.message == "Test message"
            assert isinstance(response.timestamp, datetime)

            # Test serialization works with new ConfigDict
            response_dict = response.model_dump()
            assert "success" in response_dict
            assert "message" in response_dict
            assert "timestamp" in response_dict

            # Test Generic response works with BaseModel instead of GenericModel
            data_response = SuccessResponse[dict](data={"key": "value"})
            assert data_response.success is True
            assert data_response.data == {"key": "value"}

            # Test serialization of generic response
            data_dict = data_response.model_dump()
            assert "data" in data_dict
            assert data_dict["data"] == {"key": "value"}

        except ImportError as e:
            pytest.skip(f"Could not import labor service schemas: {e}")
        except Exception as e:
            pytest.fail(f"Pydantic v2 functionality test failed: {e}")
        finally:
            # Clean up sys.path
            if labor_src_path in sys.path:
                sys.path.remove(labor_src_path)
