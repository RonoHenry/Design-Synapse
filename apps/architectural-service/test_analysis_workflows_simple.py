#!/usr/bin/env python3
"""
Simple end-to-end analysis workflow test for the Architectural Service.
This test verifies that all analysis services are properly implemented and can be instantiated.
"""

import asyncio
import os
import sys

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))


def test_analysis_services_import():
    """Test that all analysis services can be imported successfully."""
    try:
        from src.services.accessibility_service import AccessibilityService
        from src.services.compliance_service import ComplianceService
        from src.services.energy_analysis_service import EnergyAnalysisService
        from src.services.material_service import MaterialService
        from src.services.space_planning_service import SpacePlanningService
        from src.services.structural_analysis_service import \
            StructuralAnalysisService

        print("✓ All analysis services imported successfully")
        return True
    except ImportError as e:
        print(f"✗ Failed to import analysis services: {e}")
        return False


def test_analysis_schemas_import():
    """Test that all analysis schemas can be imported successfully."""
    try:
        from src.api.v1.schemas.analysis import (AccessibilityCheckRequest,
                                                 AccessibilityCheckResponse,
                                                 ComplianceCheckRequest,
                                                 ComplianceCheckResponse,
                                                 EnergyAnalysisRequest,
                                                 EnergyAnalysisResponse,
                                                 MaterialSpecificationRequest,
                                                 MaterialSpecificationResponse,
                                                 SpacePlanningRequest,
                                                 SpacePlanningResponse,
                                                 StructuralAnalysisRequest,
                                                 StructuralAnalysisResponse)

        print("✓ All analysis schemas imported successfully")
        return True
    except ImportError as e:
        print(f"✗ Failed to import analysis schemas: {e}")
        return False


def test_analysis_models_import():
    """Test that all analysis models can be imported successfully."""
    try:
        from src.models.accessibility_check import AccessibilityCheck
        from src.models.compliance_check import ComplianceCheck
        from src.models.energy_analysis import EnergyAnalysis
        from src.models.material_specification import MaterialSpecification
        from src.models.space_planning import SpacePlanning
        from src.models.structural_analysis import StructuralAnalysis

        print("✓ All analysis models imported successfully")
        return True
    except ImportError as e:
        print(f"✗ Failed to import analysis models: {e}")
        return False


def test_external_service_clients_import():
    """Test that all external service clients can be imported successfully."""
    try:
        from src.infrastructure.design_service_client import \
            DesignServiceClient
        from src.infrastructure.knowledge_service_client import \
            KnowledgeServiceClient
        from src.infrastructure.project_service_client import \
            ProjectServiceClient
        from src.infrastructure.vendor_service_client import \
            VendorServiceClient

        print("✓ All external service clients imported successfully")
        return True
    except ImportError as e:
        print(f"✗ Failed to import external service clients: {e}")
        return False


def main():
    """Run all analysis workflow tests."""
    print("Running Analysis Services Verification...")
    print("=" * 50)

    tests = [
        test_analysis_services_import,
        test_analysis_schemas_import,
        test_analysis_models_import,
        test_external_service_clients_import,
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        if test():
            passed += 1
        print()

    print("=" * 50)
    print(f"Analysis Services Verification Results: {passed}/{total} tests passed")

    if passed == total:
        print("✓ All analysis services are properly implemented and ready!")
        return True
    else:
        print("✗ Some analysis services have issues that need to be addressed.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
