"""
Unit tests for MEPCalculationService.design_fire_protection method.

Tests the fire protection system design functionality per NFPA 13.
"""

import pytest
from src.services.mep_calculation_service import MEPCalculationService


@pytest.mark.asyncio
async def test_design_fire_protection_basic(test_db_session):
    """Test basic fire protection system design."""
    # Arrange
    service = MEPCalculationService(test_db_session)
    project_id = "test-project-123"
    user_id = "test-user-456"

    building_data = {
        "floor_area": 5000.0,  # sq ft
        "ceiling_height": 12.0,  # ft
        "occupancy_hazard": "ordinary_hazard_1",
        "construction_type": "Type II",
        "supply_pressure": 80.0,  # psi
        "system_type": "wet_pipe",
    }

    # Act
    result = await service.design_fire_protection(
        project_id=project_id,
        building_data=building_data,
        user_id=user_id,
        unit_system="imperial",
    )

    # Assert
    assert result is not None
    assert "sprinkler_design" in result
    assert "total_demand" in result
    assert "residual_pressure" in result
    assert "main_pipe_size" in result
    assert "riser_size" in result
    assert "system_type" in result

    # Verify sprinkler design details
    sprinkler_design = result["sprinkler_design"]
    assert sprinkler_design["density"] > 0
    assert sprinkler_design["area_of_application"] > 0
    assert sprinkler_design["number_of_heads"] > 0
    assert sprinkler_design["flow_per_head"] > 0

    # Verify total demand is reasonable
    assert result["total_demand"] > 0
    assert result["residual_pressure"] > 0

    # Verify pipe sizes are returned
    assert result["main_pipe_size"] is not None
    assert result["riser_size"] is not None

    # Verify system type
    assert result["system_type"] == "wet_pipe"


@pytest.mark.asyncio
async def test_design_fire_protection_light_hazard(test_db_session):
    """Test fire protection design for light hazard occupancy."""
    # Arrange
    service = MEPCalculationService(test_db_session)
    project_id = "test-project-123"
    user_id = "test-user-456"

    building_data = {
        "floor_area": 3000.0,
        "ceiling_height": 10.0,
        "occupancy_hazard": "light_hazard",
        "construction_type": "Type I",
    }

    # Act
    result = await service.design_fire_protection(
        project_id=project_id,
        building_data=building_data,
        user_id=user_id,
    )

    # Assert
    assert result is not None
    # Light hazard should have lower density
    assert result["sprinkler_design"]["density"] == 0.10


@pytest.mark.asyncio
async def test_design_fire_protection_extra_hazard(test_db_session):
    """Test fire protection design for extra hazard occupancy."""
    # Arrange
    service = MEPCalculationService(test_db_session)
    project_id = "test-project-123"
    user_id = "test-user-456"

    building_data = {
        "floor_area": 8000.0,
        "ceiling_height": 15.0,
        "occupancy_hazard": "extra_hazard_2",
        "construction_type": "Type III",
    }

    # Act
    result = await service.design_fire_protection(
        project_id=project_id,
        building_data=building_data,
        user_id=user_id,
    )

    # Assert
    assert result is not None
    # Extra hazard should have higher density
    assert result["sprinkler_design"]["density"] == 0.40
    # Extra hazard should have larger area of application
    assert result["sprinkler_design"]["area_of_application"] == 2500


@pytest.mark.asyncio
async def test_design_fire_protection_invalid_floor_area(test_db_session):
    """Test fire protection design with invalid floor area."""
    # Arrange
    service = MEPCalculationService(test_db_session)
    project_id = "test-project-123"
    user_id = "test-user-456"

    building_data = {
        "floor_area": 0.0,  # Invalid
        "ceiling_height": 10.0,
        "occupancy_hazard": "ordinary_hazard_1",
        "construction_type": "Type II",
    }

    # Act & Assert
    with pytest.raises(ValueError, match="Floor area must be positive"):
        await service.design_fire_protection(
            project_id=project_id,
            building_data=building_data,
            user_id=user_id,
        )


@pytest.mark.asyncio
async def test_design_fire_protection_invalid_ceiling_height(test_db_session):
    """Test fire protection design with invalid ceiling height."""
    # Arrange
    service = MEPCalculationService(test_db_session)
    project_id = "test-project-123"
    user_id = "test-user-456"

    building_data = {
        "floor_area": 5000.0,
        "ceiling_height": -5.0,  # Invalid
        "occupancy_hazard": "ordinary_hazard_1",
        "construction_type": "Type II",
    }

    # Act & Assert
    with pytest.raises(ValueError, match="Ceiling height must be positive"):
        await service.design_fire_protection(
            project_id=project_id,
            building_data=building_data,
            user_id=user_id,
        )


@pytest.mark.asyncio
async def test_design_fire_protection_empty_building_data(test_db_session):
    """Test fire protection design with empty building data."""
    # Arrange
    service = MEPCalculationService(test_db_session)
    project_id = "test-project-123"
    user_id = "test-user-456"

    # Act & Assert
    with pytest.raises(ValueError, match="Building data must be provided"):
        await service.design_fire_protection(
            project_id=project_id,
            building_data={},
            user_id=user_id,
        )


@pytest.mark.asyncio
async def test_design_fire_protection_default_values(test_db_session):
    """Test fire protection design with minimal data (uses defaults)."""
    # Arrange
    service = MEPCalculationService(test_db_session)
    project_id = "test-project-123"
    user_id = "test-user-456"

    building_data = {
        "floor_area": 4000.0,
        "ceiling_height": 12.0,
        # occupancy_hazard defaults to ordinary_hazard_1
        # construction_type defaults to Type II
        # supply_pressure defaults to 80.0
        # system_type defaults to wet_pipe
    }

    # Act
    result = await service.design_fire_protection(
        project_id=project_id,
        building_data=building_data,
        user_id=user_id,
    )

    # Assert
    assert result is not None
    assert result["system_type"] == "wet_pipe"
    # Should use ordinary_hazard_1 defaults
    assert result["sprinkler_design"]["density"] == 0.15
