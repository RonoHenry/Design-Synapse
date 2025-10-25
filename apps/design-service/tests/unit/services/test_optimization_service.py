"""Tests for OptimizationService."""

import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime, timezone
import time

from src.services.optimization_service import OptimizationService
from src.services.llm_client import LLMGenerationError, LLMTimeoutError
from src.models.design import Design
from src.models.design_optimization import DesignOptimization


class TestOptimizationService:
    """Test suite for OptimizationService."""

    @pytest.fixture
    def mock_llm_client(self):
        """Create a mock LLM client."""
        client = Mock()
        client.generate_optimizations = AsyncMock()
        return client

    @pytest.fixture
    def mock_optimization_repository(self):
        """Create a mock optimization repository."""
        repo = Mock()
        repo.create_optimization = Mock()
        repo.get_optimizations_by_design_id = Mock()
        repo.update_optimization_status = Mock()
        return repo

    @pytest.fixture
    def mock_design_repository(self):
        """Create a mock design repository."""
        repo = Mock()
        repo.get_design_by_id = Mock()
        repo.create_design = Mock()
        return repo

    @pytest.fixture
    def optimization_service(
        self, mock_llm_client, mock_optimization_repository, mock_design_repository
    ):
        """Create an OptimizationService instance with mocked dependencies."""
        return OptimizationService(
            llm_client=mock_llm_client,
            optimization_repository=mock_optimization_repository,
            design_repository=mock_design_repository,
        )

    @pytest.fixture
    def sample_design(self):
        """Create a sample design for testing."""
        design = Design(
            project_id=1,
            name="Modern Family Home",
            description="A 3-bedroom single-family home",
            specification={
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
            building_type="residential",
            version=1,
            status="draft",
            created_by=123,
        )
        design.id = 1
        return design

    @pytest.fixture
    def mock_llm_optimizations(self):
        """Create mock LLM optimization response."""
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

    # Test: generate_optimizations - returns at least 3 suggestions
    @pytest.mark.asyncio
    async def test_generate_optimizations_returns_at_least_three_suggestions(
        self,
        optimization_service,
        mock_llm_client,
        mock_optimization_repository,
        sample_design,
        mock_llm_optimizations,
    ):
        """Test that generate_optimizations returns at least 3 suggestions."""
        # Arrange
        optimization_types = ["cost", "structural", "sustainability"]
        
        # Mock LLM response
        mock_llm_client.generate_optimizations.return_value = mock_llm_optimizations
        
        # Mock optimization creation
        created_optimizations = []
        for i, opt_data in enumerate(mock_llm_optimizations["optimizations"]):
            opt = DesignOptimization(
                design_id=sample_design.id,
                optimization_type=opt_data["optimization_type"],
                title=opt_data["title"],
                description=opt_data["description"],
                estimated_cost_impact=opt_data["estimated_cost_impact"],
                implementation_difficulty=opt_data["implementation_difficulty"],
                priority=opt_data["priority"],
                status="suggested",
            )
            opt.id = i + 1
            created_optimizations.append(opt)
        
        mock_optimization_repository.create_optimization.side_effect = created_optimizations
        
        # Act
        result = await optimization_service.generate_optimizations(
            design=sample_design,
            optimization_types=optimization_types,
        )
        
        # Assert
        assert result is not None
        assert len(result) >= 3
        assert len(result) == 3
        
        # Verify all optimization types are present
        opt_types = [opt.optimization_type for opt in result]
        assert "cost" in opt_types
        assert "structural" in opt_types
        assert "sustainability" in opt_types
        
        # Verify LLM was called
        mock_llm_client.generate_optimizations.assert_called_once_with(
            design_specification=sample_design.specification,
            optimization_types=optimization_types,
        )
        
        # Verify optimizations were created
        assert mock_optimization_repository.create_optimization.call_count == 3

    # Test: generate_optimizations - with no optimizations found
    @pytest.mark.asyncio
    async def test_generate_optimizations_no_optimizations_found(
        self,
        optimization_service,
        mock_llm_client,
        mock_optimization_repository,
        sample_design,
    ):
        """Test generate_optimizations when no optimizations are found."""
        # Arrange
        optimization_types = ["cost", "structural", "sustainability"]
        
        # Mock LLM response with empty optimizations
        mock_llm_client.generate_optimizations.return_value = {
            "optimizations": [],
            "token_usage": {
                "prompt_tokens": 300,
                "completion_tokens": 50,
                "total_tokens": 350,
            },
        }
        
        # Act
        result = await optimization_service.generate_optimizations(
            design=sample_design,
            optimization_types=optimization_types,
        )
        
        # Assert
        assert result is not None
        assert len(result) == 0
        
        # Verify LLM was called
        mock_llm_client.generate_optimizations.assert_called_once()
        
        # Verify no optimizations were created
        mock_optimization_repository.create_optimization.assert_not_called()

    # Test: apply_optimization - creates new design version
    @pytest.mark.asyncio
    async def test_apply_optimization_creates_new_design_version(
        self,
        optimization_service,
        mock_optimization_repository,
        mock_design_repository,
        sample_design,
    ):
        """Test that apply_optimization creates a new design version."""
        # Arrange
        user_id = 123
        optimization_id = 1
        
        # Mock optimization
        optimization = DesignOptimization(
            design_id=sample_design.id,
            optimization_type="cost",
            title="Use locally sourced materials",
            description="Replace imported clay tiles with locally manufactured alternatives",
            estimated_cost_impact=-15.0,
            implementation_difficulty="easy",
            priority="high",
            status="suggested",
        )
        optimization.id = optimization_id
        optimization.design = sample_design
        
        # Mock repository responses
        mock_optimization_repository.update_optimization_status.return_value = optimization
        mock_design_repository.get_design_by_id.return_value = sample_design
        
        # Mock new design version creation
        new_design = Design(
            project_id=sample_design.project_id,
            name=sample_design.name,
            description=sample_design.description,
            specification=sample_design.specification.copy(),
            building_type=sample_design.building_type,
            version=2,
            parent_design_id=sample_design.id,
            status="draft",
            created_by=user_id,
        )
        new_design.id = 2
        mock_design_repository.create_design.return_value = new_design
        
        # Act
        result = await optimization_service.apply_optimization(
            optimization_id=optimization_id,
            user_id=user_id,
        )
        
        # Assert
        assert result is not None
        assert result.id == 2
        assert result.version == 2
        assert result.parent_design_id == sample_design.id
        assert result.created_by == user_id
        
        # Verify optimization status was updated to 'applied'
        mock_optimization_repository.update_optimization_status.assert_called_once_with(
            optimization_id=optimization_id,
            status="applied",
            user_id=user_id,
        )
        
        # Verify new design version was created
        mock_design_repository.create_design.assert_called_once()
        call_kwargs = mock_design_repository.create_design.call_args[1]
        assert call_kwargs["version"] == 2
        assert call_kwargs["parent_design_id"] == sample_design.id
        assert call_kwargs["created_by"] == user_id

    # Test: optimization completion within 20 seconds
    @pytest.mark.asyncio
    async def test_generate_optimizations_completes_within_20_seconds(
        self,
        optimization_service,
        mock_llm_client,
        mock_optimization_repository,
        sample_design,
        mock_llm_optimizations,
    ):
        """Test that optimization generation completes within 20 seconds."""
        # Arrange
        optimization_types = ["cost", "structural", "sustainability"]
        
        # Mock LLM response
        mock_llm_client.generate_optimizations.return_value = mock_llm_optimizations
        
        # Mock optimization creation
        created_optimizations = []
        for i, opt_data in enumerate(mock_llm_optimizations["optimizations"]):
            opt = DesignOptimization(
                design_id=sample_design.id,
                optimization_type=opt_data["optimization_type"],
                title=opt_data["title"],
                description=opt_data["description"],
                estimated_cost_impact=opt_data["estimated_cost_impact"],
                implementation_difficulty=opt_data["implementation_difficulty"],
                priority=opt_data["priority"],
                status="suggested",
            )
            opt.id = i + 1
            created_optimizations.append(opt)
        
        mock_optimization_repository.create_optimization.side_effect = created_optimizations
        
        # Act
        start_time = time.time()
        result = await optimization_service.generate_optimizations(
            design=sample_design,
            optimization_types=optimization_types,
        )
        end_time = time.time()
        
        # Assert
        elapsed_time = end_time - start_time
        assert elapsed_time < 20.0, f"Optimization took {elapsed_time:.2f} seconds, should be < 20 seconds"
        assert result is not None
        assert len(result) >= 3

    # Test: generate_optimizations - LLM failure
    @pytest.mark.asyncio
    async def test_generate_optimizations_llm_failure(
        self,
        optimization_service,
        mock_llm_client,
        mock_optimization_repository,
        sample_design,
    ):
        """Test generate_optimizations fails when LLM generation fails."""
        # Arrange
        optimization_types = ["cost", "structural", "sustainability"]
        
        # Mock LLM failure
        mock_llm_client.generate_optimizations.side_effect = LLMGenerationError(
            "All LLM providers failed"
        )
        
        # Act & Assert
        with pytest.raises(LLMGenerationError) as exc_info:
            await optimization_service.generate_optimizations(
                design=sample_design,
                optimization_types=optimization_types,
            )
        
        assert "All LLM providers failed" in str(exc_info.value)
        
        # Verify LLM was called
        mock_llm_client.generate_optimizations.assert_called_once()
        
        # Verify no optimizations were created
        mock_optimization_repository.create_optimization.assert_not_called()

    # Test: generate_optimizations - LLM timeout
    @pytest.mark.asyncio
    async def test_generate_optimizations_llm_timeout(
        self,
        optimization_service,
        mock_llm_client,
        mock_optimization_repository,
        sample_design,
    ):
        """Test generate_optimizations fails when LLM request times out."""
        # Arrange
        optimization_types = ["cost", "structural", "sustainability"]
        
        # Mock LLM timeout
        mock_llm_client.generate_optimizations.side_effect = LLMTimeoutError(
            "Request timed out after 60 seconds"
        )
        
        # Act & Assert
        with pytest.raises(LLMTimeoutError) as exc_info:
            await optimization_service.generate_optimizations(
                design=sample_design,
                optimization_types=optimization_types,
            )
        
        assert "timed out" in str(exc_info.value)
        
        # Verify LLM was called
        mock_llm_client.generate_optimizations.assert_called_once()
        
        # Verify no optimizations were created
        mock_optimization_repository.create_optimization.assert_not_called()

    # Test: apply_optimization - optimization not found
    @pytest.mark.asyncio
    async def test_apply_optimization_not_found(
        self,
        optimization_service,
        mock_optimization_repository,
    ):
        """Test apply_optimization fails when optimization doesn't exist."""
        # Arrange
        user_id = 123
        optimization_id = 999
        
        # Mock optimization not found
        mock_optimization_repository.update_optimization_status.return_value = None
        
        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            await optimization_service.apply_optimization(
                optimization_id=optimization_id,
                user_id=user_id,
            )
        
        assert "not found" in str(exc_info.value).lower()
        
        # Verify optimization status update was attempted
        mock_optimization_repository.update_optimization_status.assert_called_once()

    # Test: apply_optimization - design not found
    @pytest.mark.asyncio
    async def test_apply_optimization_design_not_found(
        self,
        optimization_service,
        mock_optimization_repository,
        mock_design_repository,
    ):
        """Test apply_optimization fails when associated design doesn't exist."""
        # Arrange
        user_id = 123
        optimization_id = 1
        
        # Mock optimization
        optimization = DesignOptimization(
            design_id=999,  # Non-existent design
            optimization_type="cost",
            title="Test optimization",
            description="Test description",
            estimated_cost_impact=-10.0,
            implementation_difficulty="easy",
            priority="high",
            status="suggested",
        )
        optimization.id = optimization_id
        
        mock_optimization_repository.update_optimization_status.return_value = optimization
        
        # Mock design not found
        mock_design_repository.get_design_by_id.return_value = None
        
        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            await optimization_service.apply_optimization(
                optimization_id=optimization_id,
                user_id=user_id,
            )
        
        assert "design" in str(exc_info.value).lower()
        assert "not found" in str(exc_info.value).lower()

    # Test: generate_optimizations with specific optimization types
    @pytest.mark.asyncio
    async def test_generate_optimizations_with_specific_types(
        self,
        optimization_service,
        mock_llm_client,
        mock_optimization_repository,
        sample_design,
    ):
        """Test generate_optimizations with specific optimization types."""
        # Arrange
        optimization_types = ["cost"]  # Only cost optimizations
        
        # Mock LLM response with only cost optimizations
        mock_llm_client.generate_optimizations.return_value = {
            "optimizations": [
                {
                    "optimization_type": "cost",
                    "title": "Cost optimization 1",
                    "description": "Description 1",
                    "estimated_cost_impact": -10.0,
                    "implementation_difficulty": "easy",
                    "priority": "high",
                },
                {
                    "optimization_type": "cost",
                    "title": "Cost optimization 2",
                    "description": "Description 2",
                    "estimated_cost_impact": -5.0,
                    "implementation_difficulty": "medium",
                    "priority": "medium",
                },
            ],
            "token_usage": {
                "prompt_tokens": 200,
                "completion_tokens": 300,
                "total_tokens": 500,
            },
        }
        
        # Mock optimization creation
        created_optimizations = []
        for i, opt_data in enumerate(mock_llm_client.generate_optimizations.return_value["optimizations"]):
            opt = DesignOptimization(
                design_id=sample_design.id,
                optimization_type=opt_data["optimization_type"],
                title=opt_data["title"],
                description=opt_data["description"],
                estimated_cost_impact=opt_data["estimated_cost_impact"],
                implementation_difficulty=opt_data["implementation_difficulty"],
                priority=opt_data["priority"],
                status="suggested",
            )
            opt.id = i + 1
            created_optimizations.append(opt)
        
        mock_optimization_repository.create_optimization.side_effect = created_optimizations
        
        # Act
        result = await optimization_service.generate_optimizations(
            design=sample_design,
            optimization_types=optimization_types,
        )
        
        # Assert
        assert result is not None
        assert len(result) == 2
        
        # Verify all are cost optimizations
        for opt in result:
            assert opt.optimization_type == "cost"
        
        # Verify LLM was called with correct types
        mock_llm_client.generate_optimizations.assert_called_once_with(
            design_specification=sample_design.specification,
            optimization_types=optimization_types,
        )
