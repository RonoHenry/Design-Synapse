"""Unit tests for RecalculationService."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from src.models.calculation_dependency import CalculationDependency
from src.models.calculation_sheet import CalculationSheet
from src.services.recalculation_service import RecalculationService


@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    session = AsyncMock()
    session.commit = AsyncMock()
    return session


@pytest.fixture
def mock_calculation_sheet_repo():
    """Create a mock calculation sheet repository."""
    repo = AsyncMock()
    return repo


@pytest.fixture
def mock_dependency_repo():
    """Create a mock dependency repository."""
    repo = AsyncMock()
    return repo


@pytest.fixture
def recalculation_service(
    mock_db_session, mock_calculation_sheet_repo, mock_dependency_repo
):
    """Create a RecalculationService instance with mocked dependencies."""
    return RecalculationService(
        db_session=mock_db_session,
        calculation_sheet_repo=mock_calculation_sheet_repo,
        dependency_repo=mock_dependency_repo,
    )


@pytest.mark.asyncio
async def test_add_dependency_success(recalculation_service, mock_dependency_repo):
    """Test adding a dependency between calculations."""
    # Arrange
    source_id = 1
    target_id = 2
    dependency_type = "load_input"
    user_id = "user123"

    mock_dependency_repo.has_circular_dependency.return_value = False
    mock_dependency = CalculationDependency(
        id=1,
        source_calculation_id=source_id,
        target_calculation_id=target_id,
        dependency_type=dependency_type,
        created_by=user_id,
    )
    mock_dependency_repo.add_dependency.return_value = mock_dependency

    # Act
    result = await recalculation_service.add_dependency(
        source_calculation_id=source_id,
        target_calculation_id=target_id,
        dependency_type=dependency_type,
        user_id=user_id,
    )

    # Assert
    assert result == mock_dependency
    mock_dependency_repo.has_circular_dependency.assert_called_once_with(
        source_id, target_id
    )
    mock_dependency_repo.add_dependency.assert_called_once()


@pytest.mark.asyncio
async def test_add_dependency_circular_error(
    recalculation_service, mock_dependency_repo
):
    """Test that adding a circular dependency raises an error."""
    # Arrange
    source_id = 1
    target_id = 2
    dependency_type = "load_input"
    user_id = "user123"

    mock_dependency_repo.has_circular_dependency.return_value = True

    # Act & Assert
    with pytest.raises(ValueError, match="circular dependency"):
        await recalculation_service.add_dependency(
            source_calculation_id=source_id,
            target_calculation_id=target_id,
            dependency_type=dependency_type,
            user_id=user_id,
        )


@pytest.mark.asyncio
async def test_get_dependents(
    recalculation_service, mock_dependency_repo, mock_calculation_sheet_repo
):
    """Test getting dependent calculations."""
    # Arrange
    calculation_id = 1
    dependent_id = 2

    mock_dependency = CalculationDependency(
        id=1,
        source_calculation_id=dependent_id,
        target_calculation_id=calculation_id,
        dependency_type="load_input",
        created_by="user123",
    )
    mock_dependency_repo.get_dependents.return_value = [mock_dependency]

    mock_sheet = CalculationSheet(
        id=dependent_id,
        project_id="proj123",
        title="Test Calculation",
        calculation_type="beam_design",
        inputs={},
        outputs={},
        created_by="user123",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    mock_calculation_sheet_repo.get_by_id.return_value = mock_sheet

    # Act
    result = await recalculation_service.get_dependents(calculation_id)

    # Assert
    assert len(result) == 1
    assert result[0] == mock_sheet
    mock_dependency_repo.get_dependents.assert_called_once_with(calculation_id)


@pytest.mark.asyncio
async def test_trigger_recalculation_cascade_no_dependents(
    recalculation_service, mock_dependency_repo
):
    """Test recalculation cascade with no dependents."""
    # Arrange
    calculation_id = 1
    user_id = "user123"

    mock_dependency_repo.get_dependency_chain.return_value = []

    # Act
    result = await recalculation_service.trigger_recalculation_cascade(
        calculation_id=calculation_id,
        user_id=user_id,
    )

    # Assert
    assert result == []
    mock_dependency_repo.get_dependency_chain.assert_called_once_with(calculation_id)


@pytest.mark.asyncio
async def test_trigger_recalculation_cascade_with_dependents(
    recalculation_service,
    mock_dependency_repo,
    mock_calculation_sheet_repo,
):
    """Test recalculation cascade with dependents."""
    # Arrange
    calculation_id = 1
    dependent_id = 2
    user_id = "user123"

    mock_dependency_repo.get_dependency_chain.return_value = [dependent_id]

    mock_sheet = CalculationSheet(
        id=dependent_id,
        project_id="proj123",
        title="Test Calculation",
        calculation_type="beam_design",
        inputs={},
        outputs={},
        created_by="user123",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        status="approved",
    )
    mock_calculation_sheet_repo.get_by_id.return_value = mock_sheet
    mock_calculation_sheet_repo.update.return_value = mock_sheet

    # Act
    result = await recalculation_service.trigger_recalculation_cascade(
        calculation_id=calculation_id,
        user_id=user_id,
    )

    # Assert
    assert result == [dependent_id]
    mock_calculation_sheet_repo.get_by_id.assert_called_once_with(dependent_id)
    mock_calculation_sheet_repo.update.assert_called_once()
    assert mock_sheet.status == "draft"


@pytest.mark.asyncio
async def test_update_calculation_with_cascade(
    recalculation_service,
    mock_calculation_sheet_repo,
    mock_dependency_repo,
):
    """Test updating a calculation and triggering cascade."""
    # Arrange
    calculation_id = 1
    user_id = "user123"
    updates = {"inputs": {"new_value": 100}}

    mock_sheet = CalculationSheet(
        id=calculation_id,
        project_id="proj123",
        title="Test Calculation",
        calculation_type="beam_design",
        inputs={},
        outputs={},
        created_by="user123",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    mock_calculation_sheet_repo.get_by_id.return_value = mock_sheet
    mock_calculation_sheet_repo.update.return_value = mock_sheet
    mock_dependency_repo.get_dependency_chain.return_value = []

    # Act
    result = await recalculation_service.update_calculation_with_cascade(
        calculation_id=calculation_id,
        updates=updates,
        user_id=user_id,
    )

    # Assert
    assert result == mock_sheet
    mock_calculation_sheet_repo.update.assert_called_once()
    mock_dependency_repo.get_dependency_chain.assert_called_once()


@pytest.mark.asyncio
async def test_get_dependency_graph(recalculation_service, mock_dependency_repo):
    """Test getting the dependency graph for a calculation."""
    # Arrange
    calculation_id = 1

    dependencies = [
        CalculationDependency(
            id=1,
            source_calculation_id=calculation_id,
            target_calculation_id=2,
            dependency_type="load_input",
            source_field="outputs.total_load",
            created_by="user123",
        )
    ]

    dependents = [
        CalculationDependency(
            id=2,
            source_calculation_id=3,
            target_calculation_id=calculation_id,
            dependency_type="material_property",
            dependent_field="inputs.material",
            created_by="user123",
        )
    ]

    mock_dependency_repo.get_dependencies.return_value = dependencies
    mock_dependency_repo.get_dependents.return_value = dependents

    # Act
    result = await recalculation_service.get_dependency_graph(calculation_id)

    # Assert
    assert "dependencies" in result
    assert "dependents" in result
    assert len(result["dependencies"]) == 1
    assert len(result["dependents"]) == 1
    assert result["dependencies"][0]["id"] == 2
    assert result["dependents"][0]["id"] == 3
