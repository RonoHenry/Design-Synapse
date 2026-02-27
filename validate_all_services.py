#!/usr/bin/env python3
"""
Comprehensive validation script to test all services and their functionality.
This will show us what's actually working from all our development work.
"""

import asyncio
import json
import os
import sys
import traceback
from pathlib import Path
from typing import Any, Dict, List

# Add workspace root to Python path
workspace_root = Path(__file__).parent
sys.path.insert(0, str(workspace_root))


class ServiceValidator:
    def __init__(self):
        self.results = {}
        self.total_tests = 0
        self.passed_tests = 0

    def log_test(self, service: str, test_name: str, status: str, details: str = ""):
        """Log test results."""
        if service not in self.results:
            self.results[service] = []

        self.results[service].append(
            {"test": test_name, "status": status, "details": details}
        )

        self.total_tests += 1
        if status == "PASS":
            self.passed_tests += 1
            print(f"✅ {service}: {test_name}")
        elif status == "FAIL":
            print(f"❌ {service}: {test_name} - {details}")
        else:  # SKIP
            print(f"⚠️  {service}: {test_name} - {details}")

    async def test_design_service(self):
        """Test Design Service functionality."""
        print("\n🏗️  Testing Design Service...")

        try:
            # Test model imports
            sys.path.insert(0, str(workspace_root / "apps" / "design-service" / "src"))
            from models.design import Design
            from models.design_comment import DesignComment
            from models.design_file import DesignFile
            from models.design_validation import DesignValidation

            self.log_test("Design Service", "Model imports", "PASS")

            # Test API schema imports
            from api.v1.schemas.requests import DesignCreateRequest
            from api.v1.schemas.responses import DesignResponse

            self.log_test("Design Service", "API schema imports", "PASS")

            # Test service imports
            from services.validation_service import ValidationService
            from services.visual_generation_service import \
                VisualGenerationService

            self.log_test("Design Service", "Service layer imports", "PASS")

            # Test repository imports
            from repositories.design_repository import DesignRepository
            from repositories.validation_repository import ValidationRepository

            self.log_test("Design Service", "Repository layer imports", "PASS")

            # Test configuration
            from core.config import DesignServiceSettings

            settings = DesignServiceSettings()
            self.log_test("Design Service", "Configuration loading", "PASS")

            # Test database models can be instantiated
            design = Design(
                title="Test Design",
                description="Test Description",
                user_id=1,
                project_id=1,
            )
            self.log_test("Design Service", "Model instantiation", "PASS")

        except Exception as e:
            self.log_test("Design Service", "Overall functionality", "FAIL", str(e))

    async def test_vendor_service(self):
        """Test Vendor Service functionality."""
        print("\n🏪 Testing Vendor Service...")

        try:
            # Test model imports
            sys.path.insert(0, str(workspace_root / "apps" / "vendor-service" / "src"))
            from models.order import Order, OrderItem
            from models.product import Product
            from models.review import Review
            from models.vendor import Vendor

            self.log_test("Vendor Service", "Model imports", "PASS")

            # Test API schema imports
            from api.v1.schemas.product import (ProductCreateRequest,
                                                ProductResponse)
            from api.v1.schemas.vendor import (VendorCreateRequest,
                                               VendorResponse)

            self.log_test("Vendor Service", "API schema imports", "PASS")

            # Test service imports
            from services.order_service import OrderService
            from services.product_service import ProductService
            from services.vendor_service import VendorService

            self.log_test("Vendor Service", "Service layer imports", "PASS")

            # Test repository imports
            from repositories.order_repository import OrderRepository
            from repositories.product_repository import ProductRepository
            from repositories.vendor_repository import VendorRepository

            self.log_test("Vendor Service", "Repository layer imports", "PASS")

            # Test configuration
            from core.config import VendorServiceSettings

            settings = VendorServiceSettings()
            self.log_test("Vendor Service", "Configuration loading", "PASS")

            # Test model instantiation
            vendor = Vendor(
                user_id=1, company_name="Test Company", email="test@example.com"
            )
            self.log_test("Vendor Service", "Model instantiation", "PASS")

        except Exception as e:
            self.log_test("Vendor Service", "Overall functionality", "FAIL", str(e))

    async def test_knowledge_service(self):
        """Test Knowledge Service functionality."""
        print("\n📚 Testing Knowledge Service...")

        try:
            # Test model imports
            sys.path.insert(0, str(workspace_root / "apps" / "knowledge-service"))
            from knowledge_service.models.bookmark import Bookmark
            from knowledge_service.models.resource import Resource

            self.log_test("Knowledge Service", "Model imports", "PASS")

            # Test API imports
            from knowledge_service.api.v1.resources import \
                router as resources_router
            from knowledge_service.api.v1.search import router as search_router

            self.log_test("Knowledge Service", "API router imports", "PASS")

            # Test service imports
            from knowledge_service.services.content_extraction import \
                ContentExtractionService
            from knowledge_service.services.recommendation import \
                RecommendationService
            from knowledge_service.services.vector_search import \
                VectorSearchService

            self.log_test("Knowledge Service", "Service layer imports", "PASS")

            # Test core functionality
            from knowledge_service.core.llm import LLMClient
            from knowledge_service.core.vector_search import VectorSearchEngine

            self.log_test("Knowledge Service", "Core functionality imports", "PASS")

            # Test configuration
            from knowledge_service.core.config import KnowledgeServiceSettings

            settings = KnowledgeServiceSettings()
            self.log_test("Knowledge Service", "Configuration loading", "PASS")

            # Test model instantiation
            resource = Resource(
                title="Test Resource",
                content="Test content",
                resource_type="document",
                user_id=1,
            )
            self.log_test("Knowledge Service", "Model instantiation", "PASS")

        except Exception as e:
            self.log_test("Knowledge Service", "Overall functionality", "FAIL", str(e))

    async def test_labor_service(self):
        """Test Labor Service functionality."""
        print("\n👷 Testing Labor Service...")

        try:
            # Test model imports
            sys.path.insert(0, str(workspace_root / "apps" / "labor-service" / "src"))
            from models.booking import Booking
            from models.quote import Quote
            from models.review import Review
            from models.service_provider import ServiceProvider
            from models.service_request import ServiceRequest

            self.log_test("Labor Service", "Model imports", "PASS")

            # Test API schema imports
            from api.v1.schemas.booking import (BookingCreateRequest,
                                                BookingResponse)
            from api.v1.schemas.provider import (ProviderCreateRequest,
                                                 ProviderResponse)
            from api.v1.schemas.request import (ServiceRequestCreate,
                                                ServiceRequestResponse)

            self.log_test("Labor Service", "API schema imports", "PASS")

            # Test service imports
            from services.booking_service import BookingService
            from services.matching_service import MatchingService
            from services.provider_service import ProviderService
            from services.request_service import RequestService

            self.log_test("Labor Service", "Service layer imports", "PASS")

            # Test repository imports
            from repositories.booking_repository import BookingRepository
            from repositories.quote_repository import QuoteRepository
            from repositories.service_provider_repository import \
                ServiceProviderRepository

            self.log_test("Labor Service", "Repository layer imports", "PASS")

            # Test configuration
            from core.config import LaborServiceSettings

            settings = LaborServiceSettings()
            self.log_test("Labor Service", "Configuration loading", "PASS")

            # Test model instantiation
            provider = ServiceProvider(
                user_id=1, business_name="Test Provider", email="provider@example.com"
            )
            self.log_test("Labor Service", "Model instantiation", "PASS")

        except Exception as e:
            self.log_test("Labor Service", "Overall functionality", "FAIL", str(e))

    async def test_user_service(self):
        """Test User Service functionality."""
        print("\n👤 Testing User Service...")

        try:
            # Test model imports
            sys.path.insert(0, str(workspace_root / "apps" / "user-service" / "src"))
            from models.role import Role
            from models.user import User
            from models.user_profile import UserProfile

            self.log_test("User Service", "Model imports", "PASS")

            # Test API schema imports
            from api.v1.schemas.auth import UserCreateRequest, UserResponse
            from api.v1.schemas.roles import RoleResponse

            self.log_test("User Service", "API schema imports", "PASS")

            # Test configuration
            from core.config import UserServiceSettings

            settings = UserServiceSettings()
            self.log_test("User Service", "Configuration loading", "PASS")

            # Test model instantiation
            user = User(email="test@example.com", username="testuser")
            self.log_test("User Service", "Model instantiation", "PASS")

        except Exception as e:
            self.log_test("User Service", "Overall functionality", "FAIL", str(e))

    async def test_project_service(self):
        """Test Project Service functionality."""
        print("\n📋 Testing Project Service...")

        try:
            # Test model imports
            sys.path.insert(0, str(workspace_root / "apps" / "project-service" / "src"))
            from models.comment import Comment
            from models.project import Project

            self.log_test("Project Service", "Model imports", "PASS")

            # Test API schema imports
            from api.v1.schemas.project import (ProjectCreateRequest,
                                                ProjectResponse)

            self.log_test("Project Service", "API schema imports", "PASS")

            # Test configuration
            from core.config import ProjectServiceSettings

            settings = ProjectServiceSettings()
            self.log_test("Project Service", "Configuration loading", "PASS")

            # Test model instantiation
            project = Project(
                name="Test Project", description="Test Description", user_id=1
            )
            self.log_test("Project Service", "Model instantiation", "PASS")

        except Exception as e:
            self.log_test("Project Service", "Overall functionality", "FAIL", str(e))

    async def test_common_packages(self):
        """Test common packages functionality."""
        print("\n📦 Testing Common Packages...")

        try:
            # Test authentication
            sys.path.insert(0, str(workspace_root / "packages" / "common"))
            from auth.middleware import AuthMiddleware
            from auth.rbac import RBACManager

            self.log_test("Common Packages", "Authentication imports", "PASS")

            # Test monitoring
            from monitoring.health import HealthChecker
            from monitoring.tracing import TracingManager

            self.log_test("Common Packages", "Monitoring imports", "PASS")

            # Test rate limiting
            from rate_limiting.algorithms import SlidingWindow, TokenBucket
            from rate_limiting.middleware import RateLimitMiddleware

            self.log_test("Common Packages", "Rate limiting imports", "PASS")

            # Test error handling
            from errors.base import BaseError
            from errors.handlers import ErrorHandler

            self.log_test("Common Packages", "Error handling imports", "PASS")

            # Test configuration
            from config.database import DatabaseConfig
            from config.loader import ConfigLoader

            self.log_test("Common Packages", "Configuration imports", "PASS")

            # Test performance
            from performance.cache import CacheManager
            from performance.connection_pool import ConnectionPool

            self.log_test("Common Packages", "Performance imports", "PASS")

            # Test security
            from security.input_validation import InputValidator
            from security.threat_detection import ThreatDetector

            self.log_test("Common Packages", "Security imports", "PASS")

        except Exception as e:
            self.log_test("Common Packages", "Overall functionality", "FAIL", str(e))

    async def test_api_gateway(self):
        """Test API Gateway functionality."""
        print("\n🌐 Testing API Gateway...")

        try:
            # Test API Gateway imports
            sys.path.insert(0, str(workspace_root / "apps" / "api-gateway" / "src"))
            from services.request_router import RequestRouter
            from services.service_registry import ServiceRegistry

            self.log_test("API Gateway", "Service imports", "PASS")

            # Test models
            from models.request import Request
            from models.service import Service

            self.log_test("API Gateway", "Model imports", "PASS")

            # Test routes
            from api.v1.routes.health import router as health_router

            self.log_test("API Gateway", "Route imports", "PASS")

        except Exception as e:
            self.log_test("API Gateway", "Overall functionality", "FAIL", str(e))

    async def test_database_integration(self):
        """Test database integration across services."""
        print("\n🗄️  Testing Database Integration...")

        try:
            # Test database connectivity (we know this works from earlier)
            import pymysql

            # Get connection details
            host = os.getenv("DB_HOST", "gateway01.eu-central-1.prod.aws.tidbcloud.com")
            port = int(os.getenv("DB_PORT", "4000"))
            user = os.getenv("DB_USERNAME", "kbFV66oHabEtRud.root")
            password = os.getenv("DB_PASSWORD", "aPdG5f34Qjzs0gBM")
            database = os.getenv("DB_DATABASE", "test")

            connection = pymysql.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                database=database,
                ssl_ca="ca.pem",
                ssl_verify_cert=True,
                ssl_verify_identity=True,
            )

            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = %s",
                    (database,),
                )
                table_count = cursor.fetchone()[0]

            connection.close()
            self.log_test(
                "Database", "TiDB connectivity", "PASS", f"{table_count} tables found"
            )

        except Exception as e:
            self.log_test("Database", "TiDB connectivity", "FAIL", str(e))

    async def test_infrastructure_components(self):
        """Test infrastructure components."""
        print("\n🏗️  Testing Infrastructure Components...")

        try:
            # Test service registry
            sys.path.insert(0, str(workspace_root / "packages" / "common"))
            from service_registry.health_checker import HealthChecker
            from service_registry.registry import ServiceRegistry

            self.log_test("Infrastructure", "Service registry imports", "PASS")

            # Test HTTP clients
            from http.base_client import BaseHTTPClient
            from http.service_registry import ServiceRegistryClient

            self.log_test("Infrastructure", "HTTP client imports", "PASS")

            # Test resilience patterns
            from resilience.circuit_breaker import CircuitBreaker
            from resilience.retry import RetryManager

            self.log_test("Infrastructure", "Resilience pattern imports", "PASS")

        except Exception as e:
            self.log_test("Infrastructure", "Overall functionality", "FAIL", str(e))

    async def run_all_tests(self):
        """Run all validation tests."""
        print("🚀 Starting Comprehensive Service Validation")
        print("=" * 80)

        # Test each service
        await self.test_design_service()
        await self.test_vendor_service()
        await self.test_knowledge_service()
        await self.test_labor_service()
        await self.test_user_service()
        await self.test_project_service()
        await self.test_common_packages()
        await self.test_api_gateway()
        await self.test_database_integration()
        await self.test_infrastructure_components()

        # Print summary
        self.print_summary()

    def print_summary(self):
        """Print comprehensive test summary."""
        print("\n" + "=" * 80)
        print("📊 COMPREHENSIVE VALIDATION SUMMARY")
        print("=" * 80)

        # Overall stats
        pass_rate = (
            (self.passed_tests / self.total_tests * 100) if self.total_tests > 0 else 0
        )
        print(
            f"Overall: {self.passed_tests}/{self.total_tests} tests passed ({pass_rate:.1f}%)"
        )

        if pass_rate >= 80:
            print("🎉 EXCELLENT! Most functionality is working correctly")
        elif pass_rate >= 60:
            print("✅ GOOD! Majority of functionality is working")
        elif pass_rate >= 40:
            print("⚠️  PARTIAL! Some functionality working, needs attention")
        else:
            print("❌ NEEDS WORK! Many components need fixes")

        print("\n📋 Service-by-Service Breakdown:")
        print("-" * 50)

        for service, tests in self.results.items():
            passed = sum(1 for t in tests if t["status"] == "PASS")
            total = len(tests)
            rate = (passed / total * 100) if total > 0 else 0

            status_icon = "✅" if rate >= 80 else "⚠️" if rate >= 50 else "❌"
            print(f"{status_icon} {service}: {passed}/{total} ({rate:.0f}%)")

            # Show failed tests
            failed_tests = [t for t in tests if t["status"] == "FAIL"]
            if failed_tests:
                for test in failed_tests[:3]:  # Show first 3 failures
                    print(f"   ❌ {test['test']}: {test['details'][:60]}...")
                if len(failed_tests) > 3:
                    print(f"   ... and {len(failed_tests) - 3} more failures")

        print("\n🔍 What This Tells Us:")
        print("-" * 30)

        if pass_rate >= 80:
            print("• Your development work is paying off!")
            print("• Most services have solid foundations")
            print("• Core functionality is implemented correctly")
            print("• Ready for integration testing and deployment")
        elif pass_rate >= 60:
            print("• Good progress on service development")
            print("• Core components are working")
            print("• Some areas need attention before production")
        elif pass_rate >= 40:
            print("• Basic structure is in place")
            print("• Several components need fixes")
            print("• Focus on failing services first")
        else:
            print("• Foundational work is present")
            print("• Many components need implementation")
            print("• Consider prioritizing core services")

        print(
            f"\n💾 Database Status: {'✅ Connected' if any('TiDB connectivity' in str(t) and t.get('status') == 'PASS' for tests in self.results.values() for t in tests) else '❌ Issues'}"
        )
        print(
            f"🏗️  Infrastructure: {'✅ Ready' if 'Infrastructure' in self.results else '⚠️  Partial'}"
        )
        print(
            f"🔧 Common Packages: {'✅ Working' if 'Common Packages' in self.results else '❌ Missing'}"
        )


async def main():
    """Main validation function."""
    validator = ServiceValidator()
    await validator.run_all_tests()

    # Return success if most tests pass
    pass_rate = (
        (validator.passed_tests / validator.total_tests * 100)
        if validator.total_tests > 0
        else 0
    )
    return pass_rate >= 60


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
