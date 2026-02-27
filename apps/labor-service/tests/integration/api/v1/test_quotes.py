"""
TDD RED Phase: Failing API tests for quote management endpoints.

These tests define the expected behavior for quote API endpoints
and will fail until the API layer is implemented.
"""
import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient
from src.main import app


class TestQuoteAPI:
    """Test quote management API endpoints."""

    def test_submit_quote_success(self, client, test_data):
        """Test successful quote submission."""
        quote_data = {
            "request_id": test_data["service_request"].id,
            "provider_id": test_data["provider"].id,
            "total_amount": 2000.00,
            "estimated_hours": 40,
            "timeline_days": 10,
            "description": "Complete electrical work for kitchen renovation",
            "cost_breakdown": [
                {
                    "item": "Materials",
                    "amount": 800.00,
                    "description": "Electrical components and wiring",
                },
                {
                    "item": "Labor",
                    "amount": 1200.00,
                    "description": "40 hours at $30/hour",
                },
            ],
            "terms_conditions": "Payment due upon completion. 1-year warranty included.",
            "valid_until": "2024-02-15T23:59:59",
        }

        response = client.post("/api/v1/quotes", json=quote_data)

        assert response.status_code == 201
        data = response.json()
        assert data["request_id"] == 1
        assert data["provider_id"] == 1
        assert data["total_amount"] == 2000.00
        assert data["status"] == "submitted"
        assert data["id"] is not None

    def test_submit_quote_validation_error(self, client):
        """Test quote submission with invalid data."""
        invalid_data = {
            "request_id": "invalid",
            "provider_id": -1,
            "total_amount": -100,  # Negative amount
            "estimated_hours": "invalid",
        }

        response = client.post("/api/v1/quotes", json=invalid_data)

        assert response.status_code == 422
        assert "detail" in response.json()

    def test_get_quote_success(self, client, test_data):
        """Test successful quote retrieval."""
        response = client.get(f"/api/v1/quotes/{test_data['quote'].id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1
        assert "total_amount" in data
        assert "cost_breakdown" in data
        assert "provider" in data
        assert "request" in data

    def test_get_quote_not_found(self, client):
        """Test quote retrieval with non-existent ID."""
        response = client.get("/api/v1/quotes/99999")

        assert response.status_code == 404
        assert response.json()["detail"] == "Quote not found"

    def test_update_quote_success(self, client, test_data):
        """Test successful quote update."""
        update_data = {
            "total_amount": 2200.00,
            "timeline_days": 12,
            "description": "Updated quote with additional work",
        }

        response = client.put("/api/v1/quotes/1", json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert data["total_amount"] == 2200.00
        assert data["timeline_days"] == 12

    def test_accept_quote_success(self, client, test_data):
        """Test successful quote acceptance."""
        response = client.post("/api/v1/quotes/1/accept")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "accepted"
        assert "accepted_at" in data
        assert "booking_id" in data

    def test_reject_quote_success(self, client, test_data):
        """Test successful quote rejection."""
        rejection_data = {"reason": "Budget constraints"}

        response = client.post("/api/v1/quotes/1/reject", json=rejection_data)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "rejected"

    def test_withdraw_quote_success(self, client, test_data):
        """Test successful quote withdrawal by provider."""
        withdrawal_data = {"reason": "No longer available for this timeline"}

        response = client.post("/api/v1/quotes/1/withdraw", json=withdrawal_data)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "withdrawn"

    def test_list_quotes_for_request(self, client):
        """Test listing quotes for a specific request."""
        params = {
            "request_id": 1,
            "status": "submitted",
            "sort_by": "total_amount",
            "order": "asc",
        }

        response = client.get("/api/v1/quotes", params=params)

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)

    def test_list_quotes_for_provider(self, client):
        """Test listing quotes for a specific provider."""
        params = {
            "provider_id": 1,
            "status": "submitted,accepted",
            "page": 1,
            "size": 10,
        }

        response = client.get("/api/v1/quotes", params=params)

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "page" in data
        assert "size" in data

    def test_compare_quotes(self, client):
        """Test quote comparison endpoint."""
        params = {"quote_ids": "1,2,3"}

        response = client.get("/api/v1/quotes/compare", params=params)

        assert response.status_code == 200
        data = response.json()
        assert "quotes" in data
        assert "comparison_metrics" in data
        assert len(data["quotes"]) == 3

    def test_get_quote_analytics(self, client):
        """Test quote analytics endpoint."""
        response = client.get("/api/v1/quotes/1/analytics")

        assert response.status_code == 200
        data = response.json()
        assert "views" in data
        assert "response_time" in data
        assert "competitive_position" in data

    @pytest.mark.asyncio
    async def test_submit_counter_proposal(self, async_client, test_data):
        """Test submitting a counter proposal."""
        counter_data = {
            "original_quote_id": 1,
            "total_amount": 1800.00,
            "timeline_days": 8,
            "message": "Counter proposal with adjusted timeline and pricing",
        }

        response = await async_client.post(
            "/api/v1/quotes/1/counter-proposal", json=counter_data
        )

        assert response.status_code == 201
        data = response.json()
        assert data["total_amount"] == 1800.00
        assert data["timeline_days"] == 8
        assert "original_quote_id" in data
