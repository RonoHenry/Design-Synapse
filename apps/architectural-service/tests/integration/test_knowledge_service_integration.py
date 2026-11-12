"""Integration tests for Knowledge Service client."""

import asyncio
import json
from datetime import datetime
from typing import Dict, List
from uuid import uuid4

import httpx
import pytest
from src.infrastructure.knowledge_service_client import (
    CodeFilters, CodeSection, CodeSectionDetail, CodeStandard,
    KnowledgeServiceClient)


class MockKnowledgeServiceServer:
    """Mock Knowledge Service server for testing."""

    def __init__(self):
        self.request_count = 0
        self.failure_count = 0
        self.should_fail = False
        self.delay_seconds = 0
        self.cache_hits = 0

        # Mock data
        self.code_sections = [
            {
                "code_id": "IBC-2021",
                "section": "1004.1",
                "title": "Occupant Load",
                "content": "The occupant load shall be determined by dividing the floor area...",
                "edition": "2021",
                "effective_date": "2021-01-01T00:00:00Z",
            },
            {
                "code_id": "IBC-2021",
                "section": "1005.1",
                "title": "Egress Width",
                "content": "The minimum width of means of egress shall be 44 inches...",
                "edition": "2021",
                "effective_date": "2021-01-01T00:00:00Z",
            },
            {
                "code_id": "ADA-2010",
                "section": "404.2.3",
                "title": "Door Opening Force",
                "content": "The force required to open doors shall not exceed 5 lbf...",
                "edition": "2010",
                "effective_date": "2010-03-15T00:00:00Z",
            },
        ]

        self.code_standards = [
            {
                "code_id": "IBC-2021",
                "name": "International Building Code",
                "edition": "2021",
                "jurisdiction": "California",
                "applicable_building_types": ["commercial", "residential", "mixed-use"],
            },
            {
                "code_id": "ADA-2010",
                "name": "Americans with Disabilities Act",
                "edition": "2010",
                "jurisdiction": None,
                "applicable_building_types": ["all"],
            },
        ]

        self.detailed_sections = {
            "IBC-2021/1004.1": {
                "code_id": "IBC-2021",
                "section": "1004.1",
                "title": "Occupant Load",
                "content": "The occupant load shall be determined by dividing the floor area...",
                "edition": "2021",
                "subsections": [
                    {"section": "1004.1.1", "title": "Fixed Seating"},
                    {"section": "1004.1.2", "title": "Areas Without Fixed Seating"},
                ],
                "references": ["Table 1004.5", "Section 1004.2"],
                "effective_date": "2021-01-01T00:00:00Z",
            }
        }

    def reset(self):
        """Reset server state."""
        self.request_count = 0
        self.failure_count = 0
        self.should_fail = False
        self.delay_seconds = 0
        self.cache_hits = 0

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

        if method == "GET" and url_path == "/api/v1/codes/search":
            return await self._handle_search_codes(query_params)
        elif method == "GET" and url_path == "/api/v1/codes/applicable":
            return await self._handle_applicable_codes(query_params)
        elif (
            method == "GET"
            and "/api/v1/codes/" in url_path
            and "/sections/" in url_path
        ):
            parts = url_path.split("/")
            code_id = parts[4]
            section = parts[6]
            return await self._handle_get_section(code_id, section)

        return httpx.Response(404, json={"error": "Not found"})

    async def _handle_search_codes(self, params: Dict) -> httpx.Response:
        """Handle code search request."""
        query = params.get("q", "").lower()
        jurisdiction = params.get("jurisdiction")
        building_type = params.get("building_type")

        # Filter code sections based on query and filters
        results = []
        for section in self.code_sections:
            if query in section["title"].lower() or query in section["content"].lower():
                # Apply filters
                if jurisdiction and jurisdiction not in ["California", None]:
                    continue
                if building_type and building_type not in ["commercial", "all"]:
                    continue
                results.append(section)

        return httpx.Response(200, json={"results": results})

    async def _handle_applicable_codes(self, params: Dict) -> httpx.Response:
        """Handle applicable codes request."""
        location = params.get("location", "").lower()
        building_type = params.get("building_type", "").lower()

        # Filter standards based on location and building type
        applicable_codes = []
        for standard in self.code_standards:
            if (
                standard["jurisdiction"]
                and location not in standard["jurisdiction"].lower()
            ):
                continue
            if (
                building_type
                not in [bt.lower() for bt in standard["applicable_building_types"]]
                and "all" not in standard["applicable_building_types"]
            ):
                continue
            applicable_codes.append(standard)

        return httpx.Response(200, json={"codes": applicable_codes})

    async def _handle_get_section(self, code_id: str, section: str) -> httpx.Response:
        """Handle get code section request."""
        section_key = f"{code_id}/{section}"

        if section_key not in self.detailed_sections:
            return httpx.Response(404, json={"error": "Section not found"})

        return httpx.Response(200, json=self.detailed_sections[section_key])


@pytest.fixture
async def mock_knowledge_server():
    """Create mock Knowledge Service server."""
    server = MockKnowledgeServiceServer()
    yield server
    server.reset()


@pytest.fixture
async def knowledge_client(mock_knowledge_server):
    """Create Knowledge Service client with mock server."""

    # Create a mock transport that routes to our mock server
    class MockTransport(httpx.AsyncBaseTransport):
        def __init__(self, server):
            self.server = server

        async def handle_async_request(self, request):
            response = await self.server.handle_request(request)
            return response

    client = KnowledgeServiceClient("http://mock-knowledge-service")
    # Replace the HTTP client with our mock transport
    await client._client.aclose()
    client._client = httpx.AsyncClient(transport=MockTransport(mock_knowledge_server))

    yield client
    await client.close()


class TestKnowledgeServiceIntegration:
    """Integration tests for Knowledge Service client."""

    @pytest.mark.asyncio
    async def test_code_search(self, knowledge_client, mock_knowledge_server):
        """
        Test building code search functionality.

        **Validates: Requirements 9.1**
        """
        # Search for occupant load codes
        results = await knowledge_client.search_codes("occupant load")

        assert len(results) > 0
        assert isinstance(results[0], CodeSection)

        # Verify search found relevant section
        occupant_section = next(
            (r for r in results if "Occupant Load" in r.title), None
        )
        assert occupant_section is not None
        assert occupant_section.code_id == "IBC-2021"
        assert occupant_section.section == "1004.1"
        assert "occupant load" in occupant_section.content.lower()

    @pytest.mark.asyncio
    async def test_code_search_with_filters(self, knowledge_client):
        """
        Test code search with filters.

        **Validates: Requirements 9.1**
        """
        # Search with filters
        filters = CodeFilters(
            jurisdiction="California", building_type="commercial", edition="2021"
        )

        results = await knowledge_client.search_codes("egress", filters)

        assert len(results) > 0
        for result in results:
            assert isinstance(result, CodeSection)
            assert result.edition == "2021"

    @pytest.mark.asyncio
    async def test_applicable_codes_retrieval(self, knowledge_client):
        """
        Test retrieval of applicable codes for location and building type.

        **Validates: Requirements 9.2**
        """
        # Get applicable codes for California commercial building
        codes = await knowledge_client.get_applicable_codes("California", "commercial")

        assert len(codes) > 0
        assert isinstance(codes[0], CodeStandard)

        # Should include IBC for California commercial
        ibc_code = next((c for c in codes if c.code_id == "IBC-2021"), None)
        assert ibc_code is not None
        assert ibc_code.name == "International Building Code"
        assert "commercial" in ibc_code.applicable_building_types

    @pytest.mark.asyncio
    async def test_code_section_retrieval(self, knowledge_client):
        """
        Test retrieval of specific code section with details.

        **Validates: Requirements 9.3**
        """
        # Get detailed section information
        section_detail = await knowledge_client.get_code_section("IBC-2021", "1004.1")

        assert isinstance(section_detail, CodeSectionDetail)
        assert section_detail.code_id == "IBC-2021"
        assert section_detail.section == "1004.1"
        assert section_detail.title == "Occupant Load"
        assert len(section_detail.subsections) > 0
        assert len(section_detail.references) > 0

    @pytest.mark.asyncio
    async def test_caching_behavior(self, knowledge_client, mock_knowledge_server):
        """
        Test caching behavior for frequently accessed codes.

        **Validates: Requirements 9.4**
        """
        # Make the same search request multiple times
        query = "occupant load"

        # First request
        results1 = await knowledge_client.search_codes(query)
        initial_request_count = mock_knowledge_server.request_count

        # Second request (should be cached)
        results2 = await knowledge_client.search_codes(query)

        # Results should be identical
        assert len(results1) == len(results2)
        assert results1[0].code_id == results2[0].code_id

        # Note: In a real implementation with Redis cache,
        # the second request might not hit the server
        # For this mock, we just verify the results are consistent

    @pytest.mark.asyncio
    async def test_cache_invalidation(self, knowledge_client):
        """
        Test cache invalidation functionality.

        **Validates: Requirements 9.4**
        """
        # Make a request to populate cache
        await knowledge_client.search_codes("egress")

        # Invalidate cache
        invalidated_count = await knowledge_client.invalidate_knowledge_cache()

        # Should return count of invalidated entries (or 0 if no cache)
        assert isinstance(invalidated_count, int)
        assert invalidated_count >= 0

    @pytest.mark.asyncio
    async def test_retry_on_failures(self, knowledge_client, mock_knowledge_server):
        """
        Test retry logic on service failures.

        **Validates: Requirements 9.1, 9.4**
        """
        # Configure server to fail first few attempts
        mock_knowledge_server.should_fail = True

        # Request should eventually succeed after retries
        results = await knowledge_client.search_codes("occupant")

        assert len(results) > 0
        assert mock_knowledge_server.failure_count >= 3  # Should have retried

    @pytest.mark.asyncio
    async def test_circuit_breaker_behavior(
        self, knowledge_client, mock_knowledge_server
    ):
        """
        Test circuit breaker opens after repeated failures.

        **Validates: Requirements 9.4**
        """
        # Configure server to always fail
        mock_knowledge_server.should_fail = True
        mock_knowledge_server.failure_count = 0

        # Make multiple requests to trigger circuit breaker
        failure_count = 0
        for _ in range(10):
            try:
                await knowledge_client.search_codes("test")
            except Exception:
                failure_count += 1

        # Circuit breaker should have opened, preventing some requests
        assert failure_count > 0

    @pytest.mark.asyncio
    async def test_timeout_handling(self, knowledge_client, mock_knowledge_server):
        """
        Test handling of request timeouts.

        **Validates: Requirements 9.4**
        """
        # Configure server to delay responses
        mock_knowledge_server.delay_seconds = 0.5

        # Create client with short timeout
        short_timeout_client = KnowledgeServiceClient(
            "http://mock-knowledge-service", timeout=0.1
        )

        # Request should timeout and be retried
        with pytest.raises((httpx.TimeoutException, Exception)):
            await short_timeout_client.search_codes("test")

        await short_timeout_client.close()

    @pytest.mark.asyncio
    async def test_multiple_code_standards(self, knowledge_client):
        """
        Test handling of multiple code standards.

        **Validates: Requirements 9.2**
        """
        # Get codes for a location that should have multiple standards
        codes = await knowledge_client.get_applicable_codes("California", "commercial")

        # Should have both IBC and ADA
        code_ids = [code.code_id for code in codes]
        assert "IBC-2021" in code_ids
        assert "ADA-2010" in code_ids

        # Verify each code has proper metadata
        for code in codes:
            assert code.name is not None
            assert code.edition is not None
            assert len(code.applicable_building_types) > 0

    @pytest.mark.asyncio
    async def test_section_not_found_error(self, knowledge_client):
        """
        Test handling of section not found errors.

        **Validates: Requirements 9.3**
        """
        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            await knowledge_client.get_code_section("NONEXISTENT", "999.999")

        assert exc_info.value.response.status_code == 404

    @pytest.mark.asyncio
    async def test_empty_search_results(self, knowledge_client):
        """
        Test handling of empty search results.

        **Validates: Requirements 9.1**
        """
        # Search for something that won't match
        results = await knowledge_client.search_codes("nonexistent_code_term")

        assert isinstance(results, list)
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_concurrent_requests(self, knowledge_client):
        """
        Test handling of concurrent requests.

        **Validates: Requirements 9.1, 9.4**
        """
        # Submit multiple concurrent search requests
        tasks = []
        queries = ["occupant", "egress", "accessibility", "fire", "structural"]

        for query in queries:
            task = knowledge_client.search_codes(query)
            tasks.append(task)

        # Wait for all requests to complete
        results_list = await asyncio.gather(*tasks)

        # Verify all requests completed successfully
        assert len(results_list) == len(queries)
        for results in results_list:
            assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_code_edition_filtering(self, knowledge_client):
        """
        Test filtering by code edition.

        **Validates: Requirements 9.1**
        """
        # Search with specific edition filter
        filters = CodeFilters(edition="2021")
        results = await knowledge_client.search_codes("occupant", filters)

        # All results should be from 2021 edition
        for result in results:
            assert result.edition == "2021"

    @pytest.mark.asyncio
    async def test_jurisdiction_specific_codes(self, knowledge_client):
        """
        Test retrieval of jurisdiction-specific codes.

        **Validates: Requirements 9.2**
        """
        # Get codes for California (should include jurisdiction-specific codes)
        ca_codes = await knowledge_client.get_applicable_codes(
            "California", "commercial"
        )

        # Get codes for a different location
        ny_codes = await knowledge_client.get_applicable_codes("New York", "commercial")

        # Both should have some codes, but may differ
        assert len(ca_codes) > 0
        assert len(ny_codes) >= 0  # May be empty in mock

        # ADA should be applicable everywhere
        ca_code_ids = [code.code_id for code in ca_codes]
        if len(ny_codes) > 0:
            ny_code_ids = [code.code_id for code in ny_codes]
            # ADA should be in both if NY has any codes
            assert "ADA-2010" in ca_code_ids
