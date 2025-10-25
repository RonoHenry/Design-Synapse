"""Integration tests for optimization endpoints."""

import pytest
from fastapi import status
from unittest.mock import AsyncMock, patch

from src.models.design import Design
from src.models.design_optimization import DesignOptimization
from tests.factories import DesignFactory, DesignOptimizationFactory


class TestOptimizationEndpoints:
    """Test suite for optimization API endpoints."""

    @pytest.fixture
    def sample_design(self, db_session):
        """Create a sample design for testing."""
        design = DesignFactory.create(
            project_id=1,
            name="Test Design",
            building_type="residential",
            specification={
                "building_info": {
                    "type": "residential",
                    "total_area": 250.0,
                },
                "structure": {
                    "foundation_type": "slab",
                    "wall_material": "concrete_block",
                },
            },
            status="draft",
            created_by=1,
        )
        db_session.add(design)
        db_session.commit()
        db_session.refresh(design)
        return design

    @pytest.fixture
    def sample_optimizations(self, db_session, sample_design):
        """Create sample optimizations for testing."""
        optimizations = [
            DesignOptimizationFactory.create(
                design_id=sample_design.id,
                optimization_type="cost",
                title="Use locally sourced materials",
                description="Replace imported materials with local alternatives",
                estimated_cost_impact=-15.0,
                implementation_difficulty="easy",
                priority="high",
                status="suggested",
            ),
            DesignOptimizationFactory.create(
                design_id=sample_design.id,
                optimization_type="structural",
                title="Optimize foundation design",
                description="Use strip foundation instead of slab",
                estimated_cost_impact=-10.0,
                implementation_difficulty="medium",
                priority="medium",
                status="suggested",
            ),
            DesignOptimizationFactory.create(
                design_id=sample_design.id,
                optimization_type="sustainability",
                title="Add rainwater harvesting",
                description="Install rainwater collection system",
                estimated_cost_impact=5.0,
                implementation_difficulty="medium",
                priority="high",
                status="suggested",
            ),
        ]
        
        for opt in optimizations:
            db_session.add(opt)
        
        db_session.commit()
        
        for opt in optimizations:
            db_session.refresh(opt)
        
        return optimizations



    @pytest.fixture
    def mock_llm_optimizations(self):
        """Mock LLM optimization generation."""
        return {
            "optimizations": [
                {
                    "optimization_type": "cost",
                    "title": "Use locally sourced materials",
                    "description": "Replace imported clay tiles with locally manufactured alternatives to reduce material costs by 15%",
                    "estimated_cost_impact": -15.0,
                    "implementation_difficulty": "easy",
                    "priority": "high",
                },
                {
                    "optimization_type": "structural",
                    "title": "Optimize foundation design",
                    "description": "Use strip foundation instead of slab to reduce concrete usage by 20%",
                    "estimated_cost_impact": -10.0,
                    "implementation_difficulty": "medium",
                    "priority": "medium",
                },
                {
                    "optimization_type": "sustainability",
                    "title": "Add rainwater harvesting system",
                    "description": "Install rainwater collection system to reduce water consumption by 30%",
                    "estimated_cost_impact": 5.0,
                    "implementation_difficulty": "medium",
                    "priority": "high",
                },
            ],
            "token_usage": {
                "prompt_tokens": 300,
                "completion_tokens": 500,
                "total_tokens": 800,
            },
        }

    # Test: POST /api/v1/designs/{id}/optimize
    def test_generate_optimizations_success(
        self,
        client,
        db_session,
        sample_design,
        auth_headers,
    ):
        """Test successful optimization generation."""
        # The mock_llm_client from conftest is already configured with generate_optimizations
        
        # Make request
        response = client.post(
            f"/api/v1/designs/{sample_design.id}/optimize",
            json={
                "optimization_types": ["cost", "structural", "sustainability"]
            },
            headers=auth_headers,
        )
        
        # Assert response
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert isinstance(data, list)
        assert len(data) >= 3
        
        # Verify optimization structure
        for opt in data:
            assert "id" in opt
            assert "design_id" in opt
            assert opt["design_id"] == sample_design.id
            assert "optimization_type" in opt
            assert "title" in opt
            assert "description" in opt
            assert "estimated_cost_impact" in opt
            assert "implementation_difficulty" in opt
            assert "priority" in opt
            assert "status" in opt
            assert opt["status"] == "suggested"

    def test_generate_optimizations_design_not_found(
        self,
        client,
        db_session,
        auth_headers,
    ):
        """Test optimization generation with non-existent design."""
        response = client.post(
            "/api/v1/designs/99999/optimize",
            json={
                "optimization_types": ["cost", "structural"]
            },
            headers=auth_headers,
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"].lower()

    def test_generate_optimizations_no_project_access(
        self,
        client,
        db_session,
        sample_design,
        auth_headers,
    ):
        """Test optimization generation without project access."""
        from src.services.project_client import ProjectAccessDeniedError
        from src.api.v1.routes.optimizations import get_project_client
        from src.main import app
        
        # Override the project client to raise access denied
        mock_project_client = app.dependency_overrides[get_project_client]()
        mock_project_client.verify_project_access.side_effect = ProjectAccessDeniedError(
            f"User does not have access to project {sample_design.project_id}"
        )
        
        response = client.post(
            f"/api/v1/designs/{sample_design.id}/optimize",
            json={
                "optimization_types": ["cost"]
            },
            headers=auth_headers,
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "access denied" in response.json()["detail"].lower()

    def test_generate_optimizations_without_auth(
        self,
        client_no_auth,
        db_session,
        sample_design,
    ):
        """Test optimization generation without authentication."""
        response = client_no_auth.post(
            f"/api/v1/designs/{sample_design.id}/optimize",
            json={
                "optimization_types": ["cost"]
            },
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    # Test: GET /api/v1/designs/{id}/optimizations
    def test_get_optimizations_success(
        self,
        client,
        db_session,
        sample_design,
        sample_optimizations,
        auth_headers,
    ):
        """Test successful retrieval of design optimizations."""
        response = client.get(
            f"/api/v1/designs/{sample_design.id}/optimizations",
            headers=auth_headers,
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert isinstance(data, list)
        assert len(data) == 3
        
        # Verify optimization data
        opt_types = [opt["optimization_type"] for opt in data]
        assert "cost" in opt_types
        assert "structural" in opt_types
        assert "sustainability" in opt_types
        
        # Verify all belong to the design
        for opt in data:
            assert opt["design_id"] == sample_design.id

    def test_get_optimizations_empty_list(
        self,
        client,
        db_session,
        sample_design,
        auth_headers,
    ):
        """Test retrieval of optimizations when none exist."""
        response = client.get(
            f"/api/v1/designs/{sample_design.id}/optimizations",
            headers=auth_headers,
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert isinstance(data, list)
        assert len(data) == 0

    def test_get_optimizations_design_not_found(
        self,
        client,
        db_session,
        auth_headers,
    ):
        """Test retrieval of optimizations for non-existent design."""
        response = client.get(
            "/api/v1/designs/99999/optimizations",
            headers=auth_headers,
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_optimizations_no_project_access(
        self,
        client,
        db_session,
        sample_design,
        sample_optimizations,
        auth_headers,
    ):
        """Test retrieval of optimizations without project access."""
        from src.services.project_client import ProjectAccessDeniedError
        from src.api.v1.routes.optimizations import get_project_client
        from src.main import app
        
        # Override the project client to raise access denied
        mock_project_client = app.dependency_overrides[get_project_client]()
        mock_project_client.verify_project_access.side_effect = ProjectAccessDeniedError(
            f"User does not have access to project {sample_design.project_id}"
        )
        
        response = client.get(
            f"/api/v1/designs/{sample_design.id}/optimizations",
            headers=auth_headers,
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN

    # Test: POST /api/v1/optimizations/{id}/apply
    def test_apply_optimization_success(
        self,
        client,
        db_session,
        sample_design,
        sample_optimizations,
        auth_headers,
    ):
        """Test successful application of an optimization."""
        optimization = sample_optimizations[0]
        
        response = client.post(
            f"/api/v1/optimizations/{optimization.id}/apply",
            headers=auth_headers,
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Verify new design version was created
        assert data["id"] != sample_design.id
        assert data["version"] == sample_design.version + 1
        assert data["parent_design_id"] == sample_design.id
        assert data["project_id"] == sample_design.project_id
        
        # Verify optimization was applied
        db_session.refresh(optimization)
        assert optimization.status == "applied"
        assert optimization.applied_by == 1

    def test_apply_optimization_not_found(
        self,
        client,
        db_session,
        auth_headers,
    ):
        """Test applying non-existent optimization."""
        response = client.post(
            "/api/v1/optimizations/99999/apply",
            headers=auth_headers,
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_apply_optimization_already_applied(
        self,
        client,
        db_session,
        sample_design,
        auth_headers,
    ):
        """Test applying an optimization that's already been applied."""
        # Create an already-applied optimization
        optimization = DesignOptimizationFactory.create(
            design_id=sample_design.id,
            optimization_type="cost",
            title="Already applied optimization",
            description="This has already been applied",
            estimated_cost_impact=-5.0,
            implementation_difficulty="easy",
            priority="medium",
            status="applied",  # Already applied
        )
        db_session.add(optimization)
        db_session.commit()
        db_session.refresh(optimization)
        
        response = client.post(
            f"/api/v1/optimizations/{optimization.id}/apply",
            headers=auth_headers,
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        detail = response.json()["detail"].lower()
        assert "already" in detail and "applied" in detail

    def test_apply_optimization_no_project_access(
        self,
        client,
        db_session,
        sample_design,
        sample_optimizations,
        auth_headers,
    ):
        """Test applying optimization without project access."""
        from src.services.project_client import ProjectAccessDeniedError
        from src.api.v1.routes.optimizations import get_project_client
        from src.main import app
        
        optimization = sample_optimizations[0]
        
        # Override the project client to raise access denied
        mock_project_client = app.dependency_overrides[get_project_client]()
        mock_project_client.verify_project_access.side_effect = ProjectAccessDeniedError(
            f"User does not have access to project {sample_design.project_id}"
        )
        
        response = client.post(
            f"/api/v1/optimizations/{optimization.id}/apply",
            headers=auth_headers,
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_apply_optimization_without_auth(
        self,
        client_no_auth,
        db_session,
        sample_optimizations,
    ):
        """Test applying optimization without authentication."""
        optimization = sample_optimizations[0]
        
        response = client_no_auth.post(
            f"/api/v1/optimizations/{optimization.id}/apply",
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_generate_optimizations_with_default_types(
        self,
        client,
        db_session,
        sample_design,
        auth_headers,
    ):
        """Test optimization generation with default optimization types."""
        # Make request without specifying types (should use defaults)
        response = client.post(
            f"/api/v1/designs/{sample_design.id}/optimize",
            json={},
            headers=auth_headers,
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert len(data) >= 3

    def test_generate_optimizations_llm_failure(
        self,
        client,
        db_session,
        sample_design,
        auth_headers,
    ):
        """Test optimization generation when LLM fails."""
        from src.services.llm_client import LLMGenerationError
        from src.api.v1.routes.optimizations import get_llm_client
        from src.main import app
        
        # Override the LLM client to raise an error
        mock_llm_client = app.dependency_overrides[get_llm_client]()
        mock_llm_client.generate_optimizations = AsyncMock(
            side_effect=LLMGenerationError("All LLM providers failed")
        )
        
        response = client.post(
            f"/api/v1/designs/{sample_design.id}/optimize",
            json={
                "optimization_types": ["cost"]
            },
            headers=auth_headers,
        )
        
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "failed" in response.json()["detail"].lower()
