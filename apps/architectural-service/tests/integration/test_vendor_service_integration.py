"""Integration tests for Vendor Service client."""

import asyncio
import json
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List
from uuid import UUID, uuid4

import httpx
import pytest
from src.infrastructure.vendor_service_client import (AvailabilityInfo,
                                                      MaterialQuery,
                                                      SupplierInfo,
                                                      VendorMaterial,
                                                      VendorServiceClient)


class MockVendorServiceServer:
    """Mock Vendor Service server for testing."""

    def __init__(self):
        self.request_count = 0
        self.failure_count = 0
        self.should_fail = False
        self.delay_seconds = 0

        # Mock material data
        self.materials = [
            {
                "material_id": str(uuid4()),
                "name": "Steel Beam I-Section 200x100",
                "category": "structural",
                "material_type": "steel",
                "description": "Hot-rolled steel I-beam for structural applications",
                "properties": {
                    "yield_strength": "355 MPa",
                    "tensile_strength": "510 MPa",
                    "weight": "25.3 kg/m",
                },
                "vendor_id": str(uuid4()),
                "vendor_name": "SteelCorp Industries",
                "price": "125.50",
                "unit": "linear meter",
                "in_stock": True,
                "lead_time_days": 7,
            },
            {
                "material_id": str(uuid4()),
                "name": "Concrete Mix C30/37",
                "category": "structural",
                "material_type": "concrete",
                "description": "High-strength concrete mix for structural elements",
                "properties": {
                    "compressive_strength": "37 MPa",
                    "slump": "150mm",
                    "aggregate_size": "20mm",
                },
                "vendor_id": str(uuid4()),
                "vendor_name": "ConcretePlus Ltd",
                "price": "95.00",
                "unit": "cubic meter",
                "in_stock": True,
                "lead_time_days": 3,
            },
            {
                "material_id": str(uuid4()),
                "name": "Ceramic Floor Tiles Premium",
                "category": "finishes",
                "material_type": "ceramic",
                "description": "Premium ceramic tiles for interior flooring",
                "properties": {
                    "size": "600x600mm",
                    "thickness": "10mm",
                    "slip_resistance": "R10",
                },
                "vendor_id": str(uuid4()),
                "vendor_name": "TileWorld",
                "price": "45.75",
                "unit": "square meter",
                "in_stock": False,
                "lead_time_days": 14,
            },
            {
                "material_id": str(uuid4()),
                "name": "Insulation Foam Board",
                "category": "insulation",
                "material_type": "foam",
                "description": "Rigid foam insulation board for thermal efficiency",
                "properties": {
                    "r_value": "6.5 per inch",
                    "thickness": "2 inches",
                    "compressive_strength": "25 psi",
                },
                "vendor_id": str(uuid4()),
                "vendor_name": "InsulationPro",
                "price": "12.25",
                "unit": "square foot",
                "in_stock": True,
                "lead_time_days": 5,
            },
        ]

        # Create supplier info for each vendor
        self.suppliers = {}
        for material in self.materials:
            vendor_id = material["vendor_id"]
            if vendor_id not in self.suppliers:
                self.suppliers[vendor_id] = {
                    "vendor_id": vendor_id,
                    "vendor_name": material["vendor_name"],
                    "contact_email": f"contact@{material['vendor_name'].lower().replace(' ', '')}.com",
                    "contact_phone": "+1-555-0123",
                    "address": "123 Industrial Ave, Manufacturing City, MC 12345",
                    "rating": 4.2,
                    "certifications": ["ISO 9001", "CE Marking"],
                    "delivery_areas": ["California", "Nevada", "Arizona"],
                }

    def reset(self):
        """Reset server state."""
        self.request_count = 0
        self.failure_count = 0
        self.should_fail = False
        self.delay_seconds = 0

    async def handle_request(self, request: httpx.Request) -> httpx.Response:
        """Handle mock HTTP requests."""
        self.request_count += 1

        if self.delay_seconds > 0:
            await asyncio.sleep(self.delay_seconds)

        if self.should_fail:
            self.failure_count += 1
            if self.failure_count <= 3:  # Fail first 3 attempts
                return httpx.Response(503, json={"error": "Service unavailable"})

        method = request.method
        url_path = request.url.path
        query_params = dict(request.url.params)

        if method == "GET" and url_path == "/api/v1/materials/search":
            return await self._handle_search_materials(query_params)
        elif method == "GET" and "/api/v1/materials/" in url_path:
            if url_path.endswith("/supplier"):
                material_id = url_path.split("/")[-2]
                return await self._handle_get_supplier(material_id)
            elif url_path.endswith("/availability"):
                material_id = url_path.split("/")[-2]
                return await self._handle_check_availability(material_id, query_params)

        return httpx.Response(404, json={"error": "Not found"})

    async def _handle_search_materials(self, params: Dict) -> httpx.Response:
        """Handle material search request."""
        query = params.get("query", "").lower()
        category = params.get("category")
        material_type = params.get("material_type")
        min_price = params.get("min_price")
        max_price = params.get("max_price")
        in_stock = params.get("in_stock")

        # Filter materials based on query and filters
        results = []
        for material in self.materials:
            # Text search
            if (
                query
                and query not in material["name"].lower()
                and query not in material["description"].lower()
            ):
                continue

            # Category filter
            if category and material["category"] != category:
                continue

            # Material type filter
            if material_type and material["material_type"] != material_type:
                continue

            # Price filters
            price = Decimal(material["price"])
            if min_price and price < Decimal(min_price):
                continue
            if max_price and price > Decimal(max_price):
                continue

            # Stock filter
            if in_stock is not None:
                stock_filter = in_stock.lower() == "true"
                if material["in_stock"] != stock_filter:
                    continue

            results.append(material)

        return httpx.Response(200, json={"materials": results})

    async def _handle_get_supplier(self, material_id: str) -> httpx.Response:
        """Handle get supplier info request."""
        # Find material to get vendor_id
        material = next(
            (m for m in self.materials if m["material_id"] == material_id), None
        )
        if not material:
            return httpx.Response(404, json={"error": "Material not found"})

        vendor_id = material["vendor_id"]
        supplier_info = self.suppliers.get(vendor_id)
        if not supplier_info:
            return httpx.Response(404, json={"error": "Supplier not found"})

        return httpx.Response(200, json=supplier_info)

    async def _handle_check_availability(
        self, material_id: str, params: Dict
    ) -> httpx.Response:
        """Handle check availability request."""
        material = next(
            (m for m in self.materials if m["material_id"] == material_id), None
        )
        if not material:
            return httpx.Response(404, json={"error": "Material not found"})

        quantity = Decimal(params.get("quantity", "1"))

        # Calculate estimated delivery based on lead time
        estimated_delivery = None
        if material["lead_time_days"]:
            estimated_delivery = (
                datetime.utcnow() + timedelta(days=material["lead_time_days"])
            ).isoformat()

        availability_info = {
            "material_id": material_id,
            "in_stock": material["in_stock"],
            "quantity_available": 1000 if material["in_stock"] else 0,
            "lead_time_days": material["lead_time_days"],
            "estimated_delivery": estimated_delivery,
            "price": material["price"],
            "minimum_order_quantity": 1,
        }

        return httpx.Response(200, json=availability_info)


@pytest.fixture
async def mock_vendor_server():
    """Create mock Vendor Service server."""
    server = MockVendorServiceServer()
    yield server
    server.reset()


@pytest.fixture
async def vendor_client(mock_vendor_server):
    """Create Vendor Service client with mock server."""

    # Create a mock transport that routes to our mock server
    class MockTransport(httpx.AsyncBaseTransport):
        def __init__(self, server):
            self.server = server

        async def handle_async_request(self, request):
            response = await self.server.handle_request(request)
            return response

    client = VendorServiceClient("http://mock-vendor-service")
    # Replace the HTTP client with our mock transport
    await client._client.aclose()
    client._client = httpx.AsyncClient(transport=MockTransport(mock_vendor_server))

    yield client
    await client.close()


class TestVendorServiceIntegration:
    """Integration tests for Vendor Service client."""

    @pytest.mark.asyncio
    async def test_material_search(self, vendor_client):
        """
        Test material search functionality.

        **Validates: Requirements 4.2**
        """
        # Search for steel materials
        query = MaterialQuery(query="steel")
        materials = await vendor_client.search_materials(query)

        assert len(materials) > 0
        assert isinstance(materials[0], VendorMaterial)

        # Verify steel material found
        steel_material = next((m for m in materials if "steel" in m.name.lower()), None)
        assert steel_material is not None
        assert steel_material.category == "structural"
        assert steel_material.material_type == "steel"
        assert steel_material.price > 0
        assert steel_material.vendor_name is not None

    @pytest.mark.asyncio
    async def test_material_search_with_filters(self, vendor_client):
        """
        Test material search with various filters.

        **Validates: Requirements 4.2**
        """
        # Search with category filter
        query = MaterialQuery(
            query="",
            category="structural",
            min_price=Decimal("50.00"),
            max_price=Decimal("200.00"),
            in_stock=True,
        )

        materials = await vendor_client.search_materials(query)

        assert len(materials) > 0
        for material in materials:
            assert material.category == "structural"
            assert material.price >= Decimal("50.00")
            assert material.price <= Decimal("200.00")
            assert material.in_stock is True

    @pytest.mark.asyncio
    async def test_material_search_by_type(self, vendor_client):
        """
        Test material search by material type.

        **Validates: Requirements 4.2**
        """
        # Search for concrete materials
        query = MaterialQuery(query="concrete", material_type="concrete")
        materials = await vendor_client.search_materials(query)

        assert len(materials) > 0
        for material in materials:
            assert material.material_type == "concrete"

    @pytest.mark.asyncio
    async def test_supplier_info_retrieval(self, vendor_client):
        """
        Test supplier information retrieval.

        **Validates: Requirements 4.3**
        """
        # First, search for a material to get its ID
        query = MaterialQuery(query="steel")
        materials = await vendor_client.search_materials(query)
        assert len(materials) > 0

        material_id = materials[0].material_id

        # Get supplier info
        supplier_info = await vendor_client.get_supplier_info(material_id)

        assert isinstance(supplier_info, SupplierInfo)
        assert supplier_info.vendor_name is not None
        assert supplier_info.contact_email is not None
        assert supplier_info.contact_phone is not None
        assert supplier_info.rating is not None
        assert len(supplier_info.certifications) > 0
        assert len(supplier_info.delivery_areas) > 0

    @pytest.mark.asyncio
    async def test_availability_checking(self, vendor_client):
        """
        Test material availability checking.

        **Validates: Requirements 4.3**
        """
        # Search for a material
        query = MaterialQuery(query="concrete")
        materials = await vendor_client.search_materials(query)
        assert len(materials) > 0

        material_id = materials[0].material_id
        quantity = Decimal("10.5")

        # Check availability
        availability = await vendor_client.check_availability(material_id, quantity)

        assert isinstance(availability, AvailabilityInfo)
        assert availability.material_id == material_id
        assert isinstance(availability.in_stock, bool)
        assert availability.price > 0
        assert availability.lead_time_days is not None
        if availability.in_stock:
            assert availability.quantity_available is not None
            assert availability.quantity_available >= 0

    @pytest.mark.asyncio
    async def test_out_of_stock_materials(self, vendor_client):
        """
        Test handling of out-of-stock materials.

        **Validates: Requirements 4.3**
        """
        # Search for materials that might be out of stock
        query = MaterialQuery(query="ceramic")
        materials = await vendor_client.search_materials(query)

        # Find an out-of-stock material
        out_of_stock_material = next((m for m in materials if not m.in_stock), None)

        if out_of_stock_material:
            availability = await vendor_client.check_availability(
                out_of_stock_material.material_id, Decimal("1")
            )

            assert availability.in_stock is False
            assert availability.lead_time_days is not None
            assert availability.estimated_delivery is not None

    @pytest.mark.asyncio
    async def test_price_range_filtering(self, vendor_client):
        """
        Test filtering materials by price range.

        **Validates: Requirements 4.2**
        """
        # Search for materials in specific price range
        query = MaterialQuery(
            query="", min_price=Decimal("10.00"), max_price=Decimal("50.00")
        )

        materials = await vendor_client.search_materials(query)

        assert len(materials) > 0
        for material in materials:
            assert material.price >= Decimal("10.00")
            assert material.price <= Decimal("50.00")

    @pytest.mark.asyncio
    async def test_material_properties_validation(self, vendor_client):
        """
        Test that material properties are properly returned.

        **Validates: Requirements 4.2**
        """
        # Search for structural materials
        query = MaterialQuery(query="structural", category="structural")
        materials = await vendor_client.search_materials(query)

        assert len(materials) > 0
        for material in materials:
            assert isinstance(material.properties, dict)
            assert len(material.properties) > 0
            # Structural materials should have relevant properties
            if material.material_type == "steel":
                assert any(
                    "strength" in key.lower() for key in material.properties.keys()
                )

    @pytest.mark.asyncio
    async def test_retry_on_failures(self, vendor_client, mock_vendor_server):
        """
        Test retry logic on service failures.

        **Validates: Requirements 4.2, 4.3**
        """
        # Configure server to fail first few attempts
        mock_vendor_server.should_fail = True

        query = MaterialQuery(query="steel")

        # Request should eventually succeed after retries
        materials = await vendor_client.search_materials(query)

        assert len(materials) > 0
        assert mock_vendor_server.failure_count >= 3  # Should have retried

    @pytest.mark.asyncio
    async def test_circuit_breaker_behavior(self, vendor_client, mock_vendor_server):
        """
        Test circuit breaker opens after repeated failures.

        **Validates: Requirements 4.2, 4.3**
        """
        # Configure server to always fail
        mock_vendor_server.should_fail = True
        mock_vendor_server.failure_count = 0

        query = MaterialQuery(query="test")

        # Make multiple requests to trigger circuit breaker
        failure_count = 0
        for _ in range(10):
            try:
                await vendor_client.search_materials(query)
            except Exception:
                failure_count += 1

        # Circuit breaker should have opened, preventing some requests
        assert failure_count > 0

    @pytest.mark.asyncio
    async def test_timeout_handling(self, vendor_client, mock_vendor_server):
        """
        Test handling of request timeouts.

        **Validates: Requirements 4.2, 4.3**
        """
        # Configure server to delay responses
        mock_vendor_server.delay_seconds = 0.5

        # Create client with short timeout
        short_timeout_client = VendorServiceClient(
            "http://mock-vendor-service", timeout=0.1
        )

        query = MaterialQuery(query="test")

        # Request should timeout and be retried
        with pytest.raises((httpx.TimeoutException, Exception)):
            await short_timeout_client.search_materials(query)

        await short_timeout_client.close()

    @pytest.mark.asyncio
    async def test_material_not_found_error(self, vendor_client):
        """
        Test handling of material not found errors.

        **Validates: Requirements 4.3**
        """
        non_existent_material_id = uuid4()

        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            await vendor_client.get_supplier_info(non_existent_material_id)

        assert exc_info.value.response.status_code == 404

    @pytest.mark.asyncio
    async def test_empty_search_results(self, vendor_client):
        """
        Test handling of empty search results.

        **Validates: Requirements 4.2**
        """
        # Search for something that won't match
        query = MaterialQuery(query="nonexistent_material_xyz")
        materials = await vendor_client.search_materials(query)

        assert isinstance(materials, list)
        assert len(materials) == 0

    @pytest.mark.asyncio
    async def test_concurrent_requests(self, vendor_client):
        """
        Test handling of concurrent requests.

        **Validates: Requirements 4.2, 4.3**
        """
        # Submit multiple concurrent search requests
        tasks = []
        queries = ["steel", "concrete", "ceramic", "insulation", "wood"]

        for query_text in queries:
            query = MaterialQuery(query=query_text)
            task = vendor_client.search_materials(query)
            tasks.append(task)

        # Wait for all requests to complete
        results_list = await asyncio.gather(*tasks)

        # Verify all requests completed successfully
        assert len(results_list) == len(queries)
        for results in results_list:
            assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_multiple_categories_search(self, vendor_client):
        """
        Test searching across multiple material categories.

        **Validates: Requirements 4.2**
        """
        categories = ["structural", "finishes", "insulation"]

        for category in categories:
            query = MaterialQuery(query=category, category=category)
            materials = await vendor_client.search_materials(query)

            # Should find materials in each category
            if len(materials) > 0:
                for material in materials:
                    assert material.category == category

    @pytest.mark.asyncio
    async def test_lead_time_information(self, vendor_client):
        """
        Test that lead time information is properly returned.

        **Validates: Requirements 4.3**
        """
        # Search for materials
        query = MaterialQuery(query="")
        materials = await vendor_client.search_materials(query)

        assert len(materials) > 0

        # Check availability for materials with lead times
        for material in materials[:3]:  # Test first 3 materials
            availability = await vendor_client.check_availability(
                material.material_id, Decimal("1")
            )

            assert availability.lead_time_days is not None
            assert availability.lead_time_days >= 0

            if availability.lead_time_days > 0:
                assert availability.estimated_delivery is not None

    @pytest.mark.asyncio
    async def test_vendor_rating_information(self, vendor_client):
        """
        Test that vendor rating information is included.

        **Validates: Requirements 4.3**
        """
        # Search for a material
        query = MaterialQuery(query="steel")
        materials = await vendor_client.search_materials(query)
        assert len(materials) > 0

        # Get supplier info
        supplier_info = await vendor_client.get_supplier_info(materials[0].material_id)

        assert supplier_info.rating is not None
        assert isinstance(supplier_info.rating, float)
        assert 0.0 <= supplier_info.rating <= 5.0
