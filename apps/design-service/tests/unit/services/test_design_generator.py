"""Tests for DesignGeneratorService."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone

from src.services.design_generator import DesignGeneratorService
from src.services.llm_client import LLMGenerationError, LLMTimeoutError
from src.services.project_client import ProjectAccessDeniedError
from src.api.v1.schemas.requests import DesignGenerationRequest
from src.models.design import Design


class TestDesignGeneratorService:
    """Test suite for DesignGeneratorService."""

    @pytest.fixture
    def mock_llm_client(self):
        """Create a mock LLM client."""
        client = Mock()
        client.generate_design_specification = AsyncMock()
        return client

    @pytest.fixture
    def mock_project_client(self):
        """Create a mock project client."""
        client = Mock()
        client.verify_project_access = AsyncMock()
        client.get_project_details = AsyncMock()
        return client

    @pytest.fixture
    def mock_design_repository(self):
        """Create a mock design repository."""
        repo = Mock()
        repo.create_design = Mock()
        repo.get_design_by_id = Mock()
        return repo

    @pytest.fixture
    def design_generator_service(
        self, mock_llm_client, mock_project_client, mock_design_repository
    ):
        """Create a DesignGeneratorService instance with mocked dependencies."""
        return DesignGeneratorService(
            llm_client=mock_llm_client,
            project_client=mock_project_client,
            design_repository=mock_design_repository,
        )

    @pytest.fixture
    def valid_generation_request(self):
        """Create a valid design generation request."""
        return DesignGenerationRequest(
            project_id=1,
            name="Modern Family Home",
            description="A 3-bedroom single-family home with open floor plan",
            building_type="residential",
            requirements={
                "num_floors": 2,
                "total_area": 250.0,
                "bedrooms": 3,
                "bathrooms": 2,
            },
        )

    @pytest.fixture
    def mock_llm_response(self):
        """Create a mock LLM response."""
        return {
            "specification": {
                "building_info": {
                    "type": "residential",
                    "subtype": "single_family",
                    "total_area": 250.0,
                    "num_floors": 2,
                    "height": 7.5,
                },
                "structure": {
                    "foundation_type": "slab",
                    "wall_material": "concrete_block",
                    "roof_type": "pitched",
                    "roof_material": "clay_tiles",
                },
                "spaces": [
                    {
                        "name": "Living Room",
                        "area": 35.0,
                        "floor": 1,
                        "dimensions": {"length": 7.0, "width": 5.0, "height": 3.0},
                    }
                ],
                "materials": [
                    {
                        "name": "Concrete Blocks",
                        "quantity": 5000,
                        "unit": "pieces",
                        "estimated_cost": 150000,
                    }
                ],
                "compliance": {
                    "building_code": "Kenya_Building_Code_2020",
                    "zoning": "residential_low_density",
                    "setbacks": {"front": 5.0, "rear": 3.0, "side": 2.0},
                },
            },
            "confidence_score": 85.0,
            "model_version": "gpt-4",
            "token_usage": {
                "prompt_tokens": 500,
                "completion_tokens": 1000,
                "total_tokens": 1500,
            },
        }

    # Test: generate_design - happy path
    @pytest.mark.asyncio
    async def test_generate_design_success(
        self,
        design_generator_service,
        mock_llm_client,
        mock_project_client,
        mock_design_repository,
        valid_generation_request,
        mock_llm_response,
    ):
        """Test successful design generation with valid request."""
        # Arrange
        user_id = 123
        
        # Mock project access verification
        mock_project_client.verify_project_access.return_value = True
        
        # Mock LLM response
        mock_llm_client.generate_design_specification.return_value = mock_llm_response
        
        # Mock design creation
        created_design = Design(
            project_id=valid_generation_request.project_id,
            name=valid_generation_request.name,
            description=valid_generation_request.description,
            specification=mock_llm_response["specification"],
            building_type=valid_generation_request.building_type,
            total_area=250.0,
            num_floors=2,
            generation_prompt=valid_generation_request.description,
            confidence_score=mock_llm_response["confidence_score"],
            ai_model_version=mock_llm_response["model_version"],
            version=1,
            status="draft",
            created_by=user_id,
        )
        created_design.id = 1  # Set id after creation (simulates DB auto-increment)
        mock_design_repository.create_design.return_value = created_design
        
        # Act
        result = await design_generator_service.generate_design(
            request=valid_generation_request,
            user_id=user_id,
        )
        
        # Assert
        assert result is not None
        assert result.id == 1
        assert result.name == valid_generation_request.name
        assert result.project_id == valid_generation_request.project_id
        assert result.building_type == valid_generation_request.building_type
        assert result.confidence_score == 85.0
        assert result.ai_model_version == "gpt-4"
        assert result.version == 1
        assert result.status == "draft"
        assert result.created_by == user_id
        
        # Verify project access was checked
        mock_project_client.verify_project_access.assert_called_once_with(
            project_id=valid_generation_request.project_id,
            user_id=user_id,
        )
        
        # Verify LLM was called
        mock_llm_client.generate_design_specification.assert_called_once_with(
            description=valid_generation_request.description,
            building_type=valid_generation_request.building_type,
            requirements=valid_generation_request.requirements,
        )
        
        # Verify design was created
        mock_design_repository.create_design.assert_called_once()
        call_kwargs = mock_design_repository.create_design.call_args[1]
        assert call_kwargs["project_id"] == valid_generation_request.project_id
        assert call_kwargs["name"] == valid_generation_request.name
        assert call_kwargs["building_type"] == valid_generation_request.building_type
        assert call_kwargs["created_by"] == user_id

    # Test: generate_design - project access denied
    @pytest.mark.asyncio
    async def test_generate_design_project_access_denied(
        self,
        design_generator_service,
        mock_project_client,
        mock_llm_client,
        mock_design_repository,
        valid_generation_request,
    ):
        """Test design generation fails when user doesn't have project access."""
        # Arrange
        user_id = 123
        
        # Mock project access denial
        mock_project_client.verify_project_access.side_effect = ProjectAccessDeniedError(
            f"User {user_id} is not a member of project {valid_generation_request.project_id}"
        )
        
        # Act & Assert
        with pytest.raises(ProjectAccessDeniedError) as exc_info:
            await design_generator_service.generate_design(
                request=valid_generation_request,
                user_id=user_id,
            )
        
        assert f"User {user_id} is not a member" in str(exc_info.value)
        
        # Verify project access was checked
        mock_project_client.verify_project_access.assert_called_once_with(
            project_id=valid_generation_request.project_id,
            user_id=user_id,
        )
        
        # Verify LLM was NOT called
        mock_llm_client.generate_design_specification.assert_not_called()
        
        # Verify design was NOT created
        mock_design_repository.create_design.assert_not_called()

    # Test: generate_design - LLM failure
    @pytest.mark.asyncio
    async def test_generate_design_llm_failure(
        self,
        design_generator_service,
        mock_llm_client,
        mock_project_client,
        mock_design_repository,
        valid_generation_request,
    ):
        """Test design generation fails when LLM generation fails."""
        # Arrange
        user_id = 123
        
        # Mock project access verification
        mock_project_client.verify_project_access.return_value = True
        
        # Mock LLM failure
        mock_llm_client.generate_design_specification.side_effect = LLMGenerationError(
            "All LLM providers failed"
        )
        
        # Act & Assert
        with pytest.raises(LLMGenerationError) as exc_info:
            await design_generator_service.generate_design(
                request=valid_generation_request,
                user_id=user_id,
            )
        
        assert "All LLM providers failed" in str(exc_info.value)
        
        # Verify project access was checked
        mock_project_client.verify_project_access.assert_called_once()
        
        # Verify LLM was called
        mock_llm_client.generate_design_specification.assert_called_once()
        
        # Verify design was NOT created
        mock_design_repository.create_design.assert_not_called()

    # Test: generate_design - LLM timeout
    @pytest.mark.asyncio
    async def test_generate_design_llm_timeout(
        self,
        design_generator_service,
        mock_llm_client,
        mock_project_client,
        mock_design_repository,
        valid_generation_request,
    ):
        """Test design generation fails when LLM request times out."""
        # Arrange
        user_id = 123
        
        # Mock project access verification
        mock_project_client.verify_project_access.return_value = True
        
        # Mock LLM timeout
        mock_llm_client.generate_design_specification.side_effect = LLMTimeoutError(
            "Request timed out after 60 seconds"
        )
        
        # Act & Assert
        with pytest.raises(LLMTimeoutError) as exc_info:
            await design_generator_service.generate_design(
                request=valid_generation_request,
                user_id=user_id,
            )
        
        assert "timed out" in str(exc_info.value)
        
        # Verify project access was checked
        mock_project_client.verify_project_access.assert_called_once()
        
        # Verify LLM was called
        mock_llm_client.generate_design_specification.assert_called_once()
        
        # Verify design was NOT created
        mock_design_repository.create_design.assert_not_called()

    # Test: create_design_version - creates new version with parent_design_id
    @pytest.mark.asyncio
    async def test_create_design_version_success(
        self,
        design_generator_service,
        mock_design_repository,
    ):
        """Test creating a new design version with parent_design_id."""
        # Arrange
        user_id = 123
        parent_design_id = 1
        
        # Mock parent design
        parent_design = Design(
            project_id=1,
            name="Original Design",
            description="Original description",
            specification={"building_info": {"type": "residential"}},
            building_type="residential",
            version=1,
            status="draft",
            created_by=user_id,
        )
        parent_design.id = parent_design_id  # Set id after creation
        mock_design_repository.get_design_by_id.return_value = parent_design
        
        # Mock new version creation
        new_version = Design(
            project_id=parent_design.project_id,
            name="Updated Design",
            description="Updated description",
            specification={"building_info": {"type": "residential", "updated": True}},
            building_type=parent_design.building_type,
            version=2,
            parent_design_id=parent_design_id,
            status="draft",
            created_by=user_id,
        )
        new_version.id = 2  # Set id after creation
        mock_design_repository.create_design.return_value = new_version
        
        # Updates to apply
        updates = {
            "name": "Updated Design",
            "description": "Updated description",
            "specification": {"building_info": {"type": "residential", "updated": True}},
        }
        
        # Act
        result = await design_generator_service.create_design_version(
            design_id=parent_design_id,
            updates=updates,
            user_id=user_id,
        )
        
        # Assert
        assert result is not None
        assert result.id == 2
        assert result.version == 2
        assert result.parent_design_id == parent_design_id
        assert result.name == "Updated Design"
        assert result.description == "Updated description"
        assert result.created_by == user_id
        
        # Verify parent design was retrieved
        mock_design_repository.get_design_by_id.assert_called_once_with(
            parent_design_id, include_archived=False
        )
        
        # Verify new version was created
        mock_design_repository.create_design.assert_called_once()
        call_kwargs = mock_design_repository.create_design.call_args[1]
        assert call_kwargs["version"] == 2
        assert call_kwargs["parent_design_id"] == parent_design_id
        assert call_kwargs["project_id"] == parent_design.project_id
        assert call_kwargs["building_type"] == parent_design.building_type

    # Test: create_design_version - parent design not found
    @pytest.mark.asyncio
    async def test_create_design_version_parent_not_found(
        self,
        design_generator_service,
        mock_design_repository,
    ):
        """Test creating design version fails when parent design doesn't exist."""
        # Arrange
        user_id = 123
        parent_design_id = 999
        
        # Mock parent design not found
        mock_design_repository.get_design_by_id.return_value = None
        
        updates = {"name": "Updated Design"}
        
        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            await design_generator_service.create_design_version(
                design_id=parent_design_id,
                updates=updates,
                user_id=user_id,
            )
        
        assert "not found" in str(exc_info.value).lower()
        
        # Verify parent design lookup was attempted
        mock_design_repository.get_design_by_id.assert_called_once_with(
            parent_design_id, include_archived=False
        )
        
        # Verify new version was NOT created
        mock_design_repository.create_design.assert_not_called()

    # Test: confidence score calculation
    def test_calculate_confidence_score_complete_specification(
        self, design_generator_service
    ):
        """Test confidence score calculation for complete specification."""
        # Arrange
        specification = {
            "building_info": {"type": "residential", "total_area": 250.0, "num_floors": 2},
            "structure": {"foundation_type": "slab"},
            "spaces": [{"name": "Living Room", "area": 35.0}],
            "materials": [{"name": "Concrete Blocks", "quantity": 5000}],
            "compliance": {"building_code": "Kenya_Building_Code_2020"},
        }
        requirements = {"total_area": 250.0, "num_floors": 2}
        
        # Act
        score = design_generator_service._calculate_confidence_score(
            specification, requirements
        )
        
        # Assert
        assert score >= 70.0  # Base score
        assert score <= 100.0  # Max score
        # Should have bonuses for all sections + matching requirements
        assert score >= 90.0

    def test_calculate_confidence_score_incomplete_specification(
        self, design_generator_service
    ):
        """Test confidence score calculation for incomplete specification."""
        # Arrange
        specification = {
            "building_info": {"type": "residential"},
            # Missing structure, spaces, materials, compliance
        }
        requirements = {}
        
        # Act
        score = design_generator_service._calculate_confidence_score(
            specification, requirements
        )
        
        # Assert
        assert score >= 70.0  # Base score
        assert score < 90.0  # Should be lower due to missing sections

    def test_calculate_confidence_score_mismatched_requirements(
        self, design_generator_service
    ):
        """Test confidence score when requirements don't match."""
        # Arrange
        specification = {
            "building_info": {"type": "residential", "total_area": 200.0, "num_floors": 1},
            "structure": {},
            "spaces": [],
            "materials": [],
            "compliance": {},
        }
        requirements = {"total_area": 250.0, "num_floors": 2}  # Different from spec
        
        # Act
        score = design_generator_service._calculate_confidence_score(
            specification, requirements
        )
        
        # Assert
        assert score >= 70.0  # Base score
        # Should not get requirement matching bonuses
        assert score < 100.0
