"""Integration tests for analysis endpoints."""

from datetime import datetime
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.design import Design


class TestAnalysisEndpoints:
    """Test analysis endpoints integration."""

    @pytest.fixture
    def sample_design(self):
        """Sample design for testing."""
        return Design(
            id=str(uuid4()),
            project_id=str(uuid4()),
            name="Test Building",
            description="Test building for analysis",
            building_type="commercial",
            location_data={
                "address": "123 Test Street",
                "city": "Test City",
                "state": "Test State",
                "country": "Test Country",
                "postal_code": "12345",
                "latitude": 37.7749,
                "longitude": -122.4194,
                "jurisdiction": "Test Jurisdiction",
            },
            current_version="1.0",
            version_number=1,
            status="draft",
            is_deleted=False,
            metadata={
                "floors": 3,
                "total_area_sqft": 30000,
                "occupancy_type": "office",
            },
            created_by=str(uuid4()),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

    @pytest.fixture
    def auth_headers(self):
        """Authentication headers for testing."""
        return {"Authorization": "Bearer test-token"}

    # ============================================================================
    # Compliance Check Tests
    # ============================================================================

    async def test_compliance_check_workflow(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        sample_design: Design,
        auth_headers: dict,
    ):
        """Test complete compliance check workflow."""
        # Create design in database
        db_session.add(sample_design)
        await db_session.commit()

        # Request compliance check
        compliance_request = {
            "code_standards": ["IBC-2021", "ADA"],
            "jurisdiction": "Test Jurisdiction",
            "check_types": ["building_code", "accessibility"],
        }

        response = await client.post(
            f"/api/v1/designs/{sample_design.id}/compliance-checks",
            json=compliance_request,
            headers=auth_headers,
        )

        assert response.status_code == 201
        compliance_data = response.json()
        assert "id" in compliance_data
        assert compliance_data["design_id"] == sample_design.id
        assert compliance_data["status"] in ["pending", "in_progress", "completed"]

        # Get compliance check results
        check_id = compliance_data["id"]
        response = await client.get(
            f"/api/v1/compliance-checks/{check_id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        results = response.json()
        assert results["id"] == check_id
        assert "violations" in results
        assert "passed" in results

    async def test_compliance_check_invalid_design(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test compliance check with invalid design ID."""
        invalid_design_id = str(uuid4())
        compliance_request = {
            "code_standards": ["IBC-2021"],
            "jurisdiction": "Test Jurisdiction",
            "check_types": ["egress"],
        }

        response = await client.post(
            f"/api/v1/designs/{invalid_design_id}/compliance-checks",
            json=compliance_request,
            headers=auth_headers,
        )

        assert response.status_code == 404
        error_data = response.json()
        assert "error" in error_data

    # ============================================================================
    # Structural Analysis Tests
    # ============================================================================

    async def test_structural_analysis_workflow(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        sample_design: Design,
        auth_headers: dict,
    ):
        """Test complete structural analysis workflow."""
        # Create design in database
        db_session.add(sample_design)
        await db_session.commit()

        # Request structural analysis
        structural_request = {
            "structural_system": "steel_frame",
            "analysis_type": "static",
            "load_parameters": {
                "dead_load_psf": 15.0,
                "live_load_psf": 50.0,
                "wind_speed_mph": 90.0,
                "seismic_zone": "2",
                "snow_load_psf": 20.0,
            },
        }

        response = await client.post(
            f"/api/v1/designs/{sample_design.id}/structural-analysis",
            json=structural_request,
            headers=auth_headers,
        )

        assert response.status_code == 201
        analysis_data = response.json()
        assert "id" in analysis_data
        assert analysis_data["design_id"] == sample_design.id
        assert analysis_data["status"] in ["pending", "in_progress", "completed"]

        # Get structural analysis results
        analysis_id = analysis_data["id"]
        response = await client.get(
            f"/api/v1/structural-analysis/{analysis_id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        results = response.json()
        assert results["id"] == analysis_id
        assert "load_calculations" in results
        assert "issues" in results

    # ============================================================================
    # Material Specification Tests
    # ============================================================================

    async def test_material_specification_workflow(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        sample_design: Design,
        auth_headers: dict,
    ):
        """Test complete material specification workflow."""
        # Create design in database
        db_session.add(sample_design)
        await db_session.commit()

        # Add material specification
        material_request = {
            "category": "structural",
            "properties": {
                "type": "steel",
                "grade": "A992",
                "yield_strength": 50000,
                "finish": "painted",
            },
            "design_elements": [str(uuid4())],
        }

        response = await client.post(
            f"/api/v1/designs/{sample_design.id}/materials",
            json=material_request,
            headers=auth_headers,
        )

        assert response.status_code == 201
        material_data = response.json()
        assert "id" in material_data
        assert material_data["design_id"] == sample_design.id
        assert material_data["category"] == "structural"

        # List materials for design
        response = await client.get(
            f"/api/v1/designs/{sample_design.id}/materials",
            headers=auth_headers,
        )

        assert response.status_code == 200
        materials = response.json()
        assert len(materials) >= 1
        assert any(m["id"] == material_data["id"] for m in materials)

        # Search materials
        response = await client.get(
            "/api/v1/materials/search?query=steel&category=structural",
            headers=auth_headers,
        )

        assert response.status_code == 200
        search_results = response.json()
        assert isinstance(search_results, list)

    # ============================================================================
    # Space Planning Tests
    # ============================================================================

    async def test_space_planning_workflow(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        sample_design: Design,
        auth_headers: dict,
    ):
        """Test complete space planning workflow."""
        # Create design in database
        db_session.add(sample_design)
        await db_session.commit()

        # Request space planning
        space_planning_request = {
            "requirements": [
                {
                    "space_type": "office",
                    "min_area": 150.0,
                    "max_area": 200.0,
                    "adjacencies": ["corridor", "reception"],
                    "requirements": ["natural_light", "privacy"],
                },
                {
                    "space_type": "conference_room",
                    "min_area": 300.0,
                    "max_area": 400.0,
                    "adjacencies": ["office", "corridor"],
                    "requirements": ["av_equipment", "natural_light"],
                },
            ],
            "constraints": {
                "total_area": 30000.0,
                "max_floors": 3,
                "site_constraints": ["parking", "setbacks"],
            },
            "optimization_goals": ["maximize_efficiency", "improve_circulation"],
        }

        response = await client.post(
            f"/api/v1/designs/{sample_design.id}/space-planning",
            json=space_planning_request,
            headers=auth_headers,
        )

        assert response.status_code == 201
        planning_data = response.json()
        assert "id" in planning_data
        assert planning_data["design_id"] == sample_design.id
        assert planning_data["status"] in ["pending", "in_progress", "completed"]

        # Get space planning results
        planning_id = planning_data["id"]
        response = await client.get(
            f"/api/v1/space-planning/{planning_id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        results = response.json()
        assert results["id"] == planning_id
        assert "recommendations" in results
        assert "metrics" in results

    # ============================================================================
    # Accessibility Check Tests
    # ============================================================================

    async def test_accessibility_check_workflow(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        sample_design: Design,
        auth_headers: dict,
    ):
        """Test complete accessibility check workflow."""
        # Create design in database
        db_session.add(sample_design)
        await db_session.commit()

        # Request accessibility check
        accessibility_request = {
            "standards": ["ADA", "ANSI-A117.1"],
            "check_areas": ["entrances", "restrooms", "corridors", "parking"],
        }

        response = await client.post(
            f"/api/v1/designs/{sample_design.id}/accessibility-checks",
            json=accessibility_request,
            headers=auth_headers,
        )

        assert response.status_code == 201
        check_data = response.json()
        assert "id" in check_data
        assert check_data["design_id"] == sample_design.id
        assert check_data["status"] in ["pending", "in_progress", "completed"]

        # Get accessibility check results
        check_id = check_data["id"]
        response = await client.get(
            f"/api/v1/accessibility-checks/{check_id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        results = response.json()
        assert results["id"] == check_id
        assert "violations" in results
        assert "accessible_routes" in results
        assert "passed" in results

    # ============================================================================
    # Energy Analysis Tests
    # ============================================================================

    async def test_energy_analysis_workflow(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        sample_design: Design,
        auth_headers: dict,
    ):
        """Test complete energy analysis workflow."""
        # Create design in database
        db_session.add(sample_design)
        await db_session.commit()

        # Request energy analysis
        energy_request = {
            "standards": ["ASHRAE-90.1", "LEED"],
            "climate_zone": "4A",
            "building_parameters": {
                "total_area": 30000.0,
                "number_of_floors": 3,
                "occupancy_type": "office",
                "hvac_system": "VAV",
                "window_to_wall_ratio": 0.4,
                "insulation_r_value": 19.0,
            },
        }

        response = await client.post(
            f"/api/v1/designs/{sample_design.id}/energy-analysis",
            json=energy_request,
            headers=auth_headers,
        )

        assert response.status_code == 201
        analysis_data = response.json()
        assert "id" in analysis_data
        assert analysis_data["design_id"] == sample_design.id
        assert analysis_data["status"] in ["pending", "in_progress", "completed"]

        # Get energy analysis results
        analysis_id = analysis_data["id"]
        response = await client.get(
            f"/api/v1/energy-analysis/{analysis_id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        results = response.json()
        assert results["id"] == analysis_id
        assert "envelope_performance" in results
        assert "energy_consumption" in results
        assert "recommendations" in results

    # ============================================================================
    # Error Handling Tests
    # ============================================================================

    async def test_analysis_endpoints_authentication_required(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        sample_design: Design,
    ):
        """Test that all analysis endpoints require authentication."""
        # Create design in database
        db_session.add(sample_design)
        await db_session.commit()

        endpoints_and_data = [
            (
                f"/api/v1/designs/{sample_design.id}/compliance-checks",
                {"code_standards": ["IBC-2021"]},
            ),
            (
                f"/api/v1/designs/{sample_design.id}/structural-analysis",
                {"structural_system": "steel_frame", "analysis_type": "static"},
            ),
            (
                f"/api/v1/designs/{sample_design.id}/materials",
                {"category": "structural", "properties": {"type": "steel"}},
            ),
            (
                f"/api/v1/designs/{sample_design.id}/space-planning",
                {
                    "requirements": [{"space_type": "office", "min_area": 150}],
                    "constraints": {"total_area": 1000},
                },
            ),
            (
                f"/api/v1/designs/{sample_design.id}/accessibility-checks",
                {"standards": ["ADA"]},
            ),
            (
                f"/api/v1/designs/{sample_design.id}/energy-analysis",
                {
                    "standards": ["ASHRAE-90.1"],
                    "climate_zone": "4A",
                    "building_parameters": {"total_area": 1000},
                },
            ),
        ]

        for endpoint, data in endpoints_and_data:
            response = await client.post(endpoint, json=data)
            assert response.status_code == 401

    async def test_analysis_endpoints_validation_errors(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        sample_design: Design,
        auth_headers: dict,
    ):
        """Test validation errors for analysis endpoints."""
        # Create design in database
        db_session.add(sample_design)
        await db_session.commit()

        # Test compliance check with empty standards
        response = await client.post(
            f"/api/v1/designs/{sample_design.id}/compliance-checks",
            json={"code_standards": []},
            headers=auth_headers,
        )
        assert response.status_code == 400

        # Test material specification with missing properties
        response = await client.post(
            f"/api/v1/designs/{sample_design.id}/materials",
            json={"category": "structural"},
            headers=auth_headers,
        )
        assert response.status_code == 400

        # Test space planning with empty requirements
        response = await client.post(
            f"/api/v1/designs/{sample_design.id}/space-planning",
            json={"requirements": [], "constraints": {"total_area": 1000}},
            headers=auth_headers,
        )
        assert response.status_code == 400

    async def test_get_nonexistent_analysis_results(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test getting results for non-existent analyses."""
        nonexistent_id = str(uuid4())

        endpoints = [
            f"/api/v1/compliance-checks/{nonexistent_id}",
            f"/api/v1/structural-analysis/{nonexistent_id}",
            f"/api/v1/space-planning/{nonexistent_id}",
            f"/api/v1/accessibility-checks/{nonexistent_id}",
            f"/api/v1/energy-analysis/{nonexistent_id}",
        ]

        for endpoint in endpoints:
            response = await client.get(endpoint, headers=auth_headers)
            assert response.status_code == 404
