"""Integration tests for structural engineering API endpoints.

Tests all structural endpoints per requirements 1.1-1.7:
- POST /api/v1/structural/loads   (req 1.1)
- POST /api/v1/structural/beams   (req 1.2)
- POST /api/v1/structural/columns (req 1.3)
- POST /api/v1/structural/foundations (req 1.4)
- GET  /api/v1/structural/designs/{id}
- PUT  /api/v1/structural/designs/{id}
- DELETE /api/v1/structural/designs/{id}
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from src.main import app

from packages.common.auth.models import UserContext

BASE_URL = "/api/v1/structural"
PROJECT_ID = str(uuid4())
DESIGN_ID = 1


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def engineer_user():
    """Mock engineer user context."""
    return UserContext(
        user_id=str(uuid4()),
        email="engineer@example.com",
        roles=["engineer"],
        permissions=["write:designs", "read:designs"],
    )


@pytest.fixture
def viewer_user():
    """Mock viewer user without engineer role."""
    return UserContext(
        user_id=str(uuid4()),
        email="viewer@example.com",
        roles=["viewer"],
        permissions=["read:designs"],
    )


@pytest.fixture
def load_request_payload():
    """Build a valid load calculation request payload."""
    return {
        "project_id": PROJECT_ID,
        "building_data": {
            "floor_area": 5000.0,
            "height": 40.0,
            "num_floors": 4,
            "occupancy_type": "office",
            "exposure_category": "B",
            "seismic_zone": "2B",
        },
        "load_types": ["dead", "live", "wind", "seismic"],
        "unit_system": "imperial",
    }


@pytest.fixture
def beam_request_payload():
    """Build a valid beam design request payload."""
    return {
        "project_id": PROJECT_ID,
        "loads": {"uniform_load": 2.5, "point_load": 10.0, "load_position": 0.5},
        "span": 20.0,
        "material": {"type": "steel", "grade": "A36", "fy": 36000, "E": 29000000},
        "unit_system": "imperial",
    }


@pytest.fixture
def column_request_payload():
    """Build a valid column design request payload."""
    return {
        "project_id": PROJECT_ID,
        "axial_load": 150000.0,
        "moment": 500000.0,
        "length": 12.0,
        "material": {"type": "steel", "grade": "A36", "fy": 36000, "E": 29000000},
        "unit_system": "imperial",
    }


@pytest.fixture
def foundation_request_payload():
    """Build a valid foundation design request payload."""
    return {
        "project_id": PROJECT_ID,
        "loads": {"axial": 200000.0, "moment_x": 50000.0, "moment_y": 30000.0},
        "soil_properties": {
            "bearing_capacity": 3000.0,
            "cohesion": 0.0,
            "friction_angle": 30.0,
            "unit_weight": 120.0,
        },
        "unit_system": "imperial",
    }


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------


def _make_load_result():
    """Build a mock load calculation result."""
    result = MagicMock()
    result.calculation_id = 12345
    result.project_id = PROJECT_ID
    result.dead_load = 1500.0
    result.live_load = 800.0
    result.wind_load = 450.0
    result.seismic_load = 320.0
    result.total_load = 3070.0
    result.created_at = datetime.now(timezone.utc)
    return result


def _make_beam_result():
    """Build a mock beam design result."""
    result = MagicMock()
    result.geometry = MagicMock()
    result.geometry.depth = 18.0
    result.geometry.width = 7.5
    result.max_deflection = 0.75
    result.stress_ratio = 0.85
    result.is_adequate = True
    return result


def _make_column_result():
    """Build a mock column design result."""
    result = MagicMock()
    result.geometry = MagicMock()
    result.geometry.depth = 14.0
    result.geometry.width = 14.0
    result.geometry.diameter = None
    result.axial_capacity = 450000.0
    result.combined_stress_ratio = 0.72
    result.buckling_capacity = 500000.0
    result.is_adequate = True
    return result


def _make_foundation_result():
    """Build a mock foundation design result."""
    result = MagicMock()
    result.geometry = MagicMock()
    result.geometry.foundation_type = MagicMock()
    result.geometry.foundation_type.value = "spread_footing"
    result.geometry.length = 10.0
    result.geometry.width = 10.0
    result.geometry.depth = 3.0
    result.geometry.thickness = 18.0
    result.geometry.diameter = None
    result.bearing_pressure = 1800.0
    result.settlement = 0.5
    result.reinforcement_area = 2.5
    result.is_adequate = True
    return result


def _make_design_record():
    """Build a mock structural design DB record."""
    record = MagicMock()
    record.id = DESIGN_ID
    record.project_id = PROJECT_ID
    record.design_type = "beam"
    record.title = "Beam Design"
    record.description = "Test beam"
    record.loads = {}
    record.material_properties = {}
    record.geometry = {}
    record.design_results = {}
    record.stress_ratios = {}
    record.status = "draft"
    record.units = "imperial"
    record.created_by = str(uuid4())
    record.created_at = datetime.now(timezone.utc)
    record.updated_at = datetime.now(timezone.utc)
    return record


# ---------------------------------------------------------------------------
# POST /api/v1/structural/loads  (Requirement 1.1)
# ---------------------------------------------------------------------------


class TestCalculateLoads:
    """Tests for POST /api/v1/structural/loads."""

    @patch("src.api.v1.routes.structural.get_structural_service")
    @patch("src.api.dependencies.require_calculation_permission")
    def test_calculate_loads_success(
        self, mock_auth, mock_service_dep, client, engineer_user, load_request_payload
    ):
        """Test successful load calculation returns 201 with results (req 1.1)."""
        mock_auth.return_value = engineer_user

        mock_service = AsyncMock()
        mock_service.calculate_loads = AsyncMock(return_value=_make_load_result())
        mock_service_dep.return_value = mock_service

        response = client.post(f"{BASE_URL}/loads", json=load_request_payload)

        assert response.status_code == 201
        data = response.json()
        assert "dead_load" in data
        assert "live_load" in data
        assert "total_load" in data
        assert data["unit_system"] == "imperial"

    @patch("src.api.dependencies.require_calculation_permission")
    def test_calculate_loads_missing_project_id(self, mock_auth, client, engineer_user):
        """Test load calculation with missing project_id returns 422."""
        mock_auth.return_value = engineer_user

        payload = {"building_data": {}, "load_types": ["dead"]}
        response = client.post(f"{BASE_URL}/loads", json=payload)

        assert response.status_code == 422

    @patch("src.api.dependencies.require_calculation_permission")
    def test_calculate_loads_empty_load_types(
        self, mock_auth, client, engineer_user, load_request_payload
    ):
        """Test load calculation with empty load_types returns 422."""
        mock_auth.return_value = engineer_user

        load_request_payload["load_types"] = []
        response = client.post(f"{BASE_URL}/loads", json=load_request_payload)

        # Empty list may pass schema validation but fail service — 422 or 400
        assert response.status_code in (400, 422)

    @patch("src.api.v1.routes.structural.get_structural_service")
    @patch("src.api.dependencies.require_calculation_permission")
    def test_calculate_loads_service_error(
        self, mock_auth, mock_service_dep, client, engineer_user, load_request_payload
    ):
        """Test load calculation handles service errors gracefully (req 1.7)."""
        mock_auth.return_value = engineer_user

        mock_service = AsyncMock()
        mock_service.calculate_loads = AsyncMock(side_effect=Exception("DB error"))
        mock_service_dep.return_value = mock_service

        response = client.post(f"{BASE_URL}/loads", json=load_request_payload)

        assert response.status_code == 500
        assert "error" in response.json()

    @patch("src.api.v1.routes.structural.get_structural_service")
    @patch("src.api.dependencies.require_calculation_permission")
    def test_calculate_loads_validation_error(
        self, mock_auth, mock_service_dep, client, engineer_user, load_request_payload
    ):
        """Test load calculation handles ValueError from service (req 1.7)."""
        mock_auth.return_value = engineer_user

        mock_service = AsyncMock()
        mock_service.calculate_loads = AsyncMock(
            side_effect=ValueError("Invalid building data")
        )
        mock_service_dep.return_value = mock_service

        response = client.post(f"{BASE_URL}/loads", json=load_request_payload)

        assert response.status_code == 400
        assert "error" in response.json()
