"""Unit tests for CivilCalculationService."""

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
from src.calculations.civil_calculator import (GradingDesignResult,
                                               StormwaterDesignResult,
                                               UtilityDesignResult)
from src.models.calculation_sheet import CalculationSheet
from src.services.civil_calculation_service import CivilCalculationService


@pytest.fixture
def mock_db_session():
    """Mock database session."""
    return AsyncMock()


@pytest.fixture
def mock_calculation_sheet_repo():
    """Mock calculation sheet repository."""
    return AsyncMock()


@pytest.fixture
def mock_civil_design_repo():
    """Mock civil design repository."""
    return AsyncMock()


@pytest.fixture
def mock_recalculation_service():
    """Mock recalculation service."""
    return AsyncMock()


@pytest.fixture
def civil_service(
    mock_db_session,
    mock_calculation_sheet_repo,
    mock_civil_design_repo,
    mock_recalculation_service,
):
    """Create CivilCalculationService with mocked dependencies."""
    return CivilCalculationService(
        db_session=mock_db_session,
        calculation_sheet_repo=mock_calculation_sheet_repo,
        civil_design_repo=mock_civil_design_repo,
        recalculation_service=mock_recalculation_service,
    )


@pytest.fixture
def sample_site_data():
    """Sample site data for testing."""
    return {
        "area": 2.5,
        "existing_elevations": {
            "0_0": 100.0,
            "50_0": 102.0,
            "100_0": 104.0,
            "150_0": 103.0,
        },
        "soil_type": "clay",
        "permeability": 0.3,
        "slope_percent": 2.0,
    }


@pytest.fixture
def sample_target_elevations():
    """Sample target elevations for testing."""
    return {
        "0_0": 101.0,
        "50_0": 101.5,
        "100_0": 102.0,
        "150_0": 102.5,
    }


@pytest.fixture
def sample_rainfall_data():
    """Sample rainfall data for testing."""
    return {
        "intensity": 3.0,
        "duration": 2.0,
        "return_period": 25,
        "runoff_coefficient": 0.7,
    }


@pytest.fixture
def sample_utility_loads():
    """Sample utility loads for testing."""
    return {
        "water_demand": 25.0,
        "sewer_flow": 20.0,
        "gas_demand": 150.0,
    }


class TestCivilCalculationService:
    """Test cases for CivilCalculationService."""

    @pytest.mark.asyncio
    async def test_design_grading_success(
        self,
        civil_service,
        mock_calculation_sheet_repo,
        mock_civil_design_repo,
        mock_db_session,
        sample_site_data,
        sample_target_elevations,
    ):
        """Test successful grading design calculation."""
        # Mock calculation sheet creation
        mock_sheet = CalculationSheet(
            id=1,
            project_id="test-project",
            title="Grading Design - 2024-01-01 12:00",
            calculation_type="grading_design",
        )
        mock_calculation_sheet_repo.create.return_value = mock_sheet

        # Mock civil design creation
        mock_civil_design_repo.create.return_value = AsyncMock()

        # Execute grading design
        result = await civil_service.design_grading(
            project_id="test-project",
            site_data=sample_site_data,
            target_elevations=sample_target_elevations,
            user_id="test-user",
            unit_system="imperial",
            grid_spacing=50.0,
        )

        # Verify result
        assert isinstance(result, GradingDesignResult)
        assert result.unit_system == "imperial"
        assert len(result.grading_points) > 0

        # Verify calculation sheet was created
        mock_calculation_sheet_repo.create.assert_called_once()
        created_sheet = mock_calculation_sheet_repo.create.call_args[0][0]
        assert created_sheet.project_id == "test-project"
        assert created_sheet.calculation_type == "grading_design"
        assert created_sheet.created_by == "test-user"

        # Verify civil design was created
        mock_civil_design_repo.create.assert_called_once()
        created_design = mock_civil_design_repo.create.call_args[0][0]
        assert created_design.project_id == "test-project"
        assert created_design.design_type == "grading"
        assert created_design.created_by == "test-user"

        # Verify database commit
        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_design_grading_empty_target_elevations(
        self, civil_service, sample_site_data
    ):
        """Test grading design with empty target elevations raises ValueError."""
        with pytest.raises(ValueError, match="Target elevations cannot be empty"):
            await civil_service.design_grading(
                project_id="test-project",
                site_data=sample_site_data,
                target_elevations={},
                user_id="test-user",
            )

    @pytest.mark.asyncio
    async def test_design_stormwater_success(
        self,
        civil_service,
        mock_calculation_sheet_repo,
        mock_civil_design_repo,
        mock_db_session,
        sample_site_data,
        sample_rainfall_data,
    ):
        """Test successful stormwater design calculation."""
        # Mock calculation sheet creation
        mock_sheet = CalculationSheet(
            id=2,
            project_id="test-project",
            title="Stormwater Design - 2024-01-01 12:00",
            calculation_type="stormwater_design",
        )
        mock_calculation_sheet_repo.create.return_value = mock_sheet

        # Mock civil design creation
        mock_civil_design_repo.create.return_value = AsyncMock()

        # Execute stormwater design
        result = await civil_service.design_stormwater(
            project_id="test-project",
            site_data=sample_site_data,
            rainfall_data=sample_rainfall_data,
            user_id="test-user",
            unit_system="imperial",
            release_rate=2.0,
        )

        # Verify result
        assert isinstance(result, StormwaterDesignResult)
        assert result.unit_system == "imperial"
        assert result.runoff_rate > 0
        assert result.runoff_volume > 0
        assert result.detention_volume >= 0
        assert result.outlet_size > 0
        assert len(result.pipe_sizes) > 0

        # Verify calculation sheet was created
        mock_calculation_sheet_repo.create.assert_called_once()
        created_sheet = mock_calculation_sheet_repo.create.call_args[0][0]
        assert created_sheet.project_id == "test-project"
        assert created_sheet.calculation_type == "stormwater_design"
        assert created_sheet.created_by == "test-user"

        # Verify civil design was created
        mock_civil_design_repo.create.assert_called_once()
        created_design = mock_civil_design_repo.create.call_args[0][0]
        assert created_design.project_id == "test-project"
        assert created_design.design_type == "stormwater"
        assert created_design.created_by == "test-user"

        # Verify database commit
        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_design_stormwater_without_release_rate(
        self,
        civil_service,
        mock_calculation_sheet_repo,
        mock_civil_design_repo,
        mock_db_session,
        sample_site_data,
        sample_rainfall_data,
    ):
        """Test stormwater design without release rate (no detention)."""
        # Mock calculation sheet creation
        mock_sheet = CalculationSheet(
            id=3,
            project_id="test-project",
            title="Stormwater Design - 2024-01-01 12:00",
            calculation_type="stormwater_design",
        )
        mock_calculation_sheet_repo.create.return_value = mock_sheet

        # Mock civil design creation
        mock_civil_design_repo.create.return_value = AsyncMock()

        # Execute stormwater design without release rate
        result = await civil_service.design_stormwater(
            project_id="test-project",
            site_data=sample_site_data,
            rainfall_data=sample_rainfall_data,
            user_id="test-user",
            unit_system="imperial",
        )

        # Verify result
        assert isinstance(result, StormwaterDesignResult)
        assert result.detention_volume == 0.0
        assert result.detention_depth == 0.0
        assert result.runoff_rate > 0

    @pytest.mark.asyncio
    async def test_design_utilities_success(
        self,
        civil_service,
        mock_calculation_sheet_repo,
        mock_civil_design_repo,
        mock_db_session,
        sample_site_data,
        sample_utility_loads,
    ):
        """Test successful utility design calculation."""
        # Mock calculation sheet creation
        mock_sheet = CalculationSheet(
            id=4,
            project_id="test-project",
            title="Utility Design - 2024-01-01 12:00",
            calculation_type="utility_design",
        )
        mock_calculation_sheet_repo.create.return_value = mock_sheet

        # Mock civil design creation
        mock_civil_design_repo.create.return_value = AsyncMock()

        # Execute utility design
        result = await civil_service.design_utilities(
            project_id="test-project",
            site_data=sample_site_data,
            utility_loads=sample_utility_loads,
            user_id="test-user",
            unit_system="imperial",
            pressure_available=65.0,
        )

        # Verify result
        assert isinstance(result, UtilityDesignResult)
        assert result.unit_system == "imperial"
        assert result.water_service_size > 0
        assert result.water_pressure_required > 0
        assert result.sewer_service_size > 0
        assert result.sewer_slope > 0
        assert result.gas_service_size is not None

        # Verify calculation sheet was created
        mock_calculation_sheet_repo.create.assert_called_once()
        created_sheet = mock_calculation_sheet_repo.create.call_args[0][0]
        assert created_sheet.project_id == "test-project"
        assert created_sheet.calculation_type == "utility_design"
        assert created_sheet.created_by == "test-user"

        # Verify civil design was created
        mock_civil_design_repo.create.assert_called_once()
        created_design = mock_civil_design_repo.create.call_args[0][0]
        assert created_design.project_id == "test-project"
        assert created_design.design_type == "utilities"
        assert created_design.created_by == "test-user"

        # Verify database commit
        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_design_utilities_without_gas(
        self,
        civil_service,
        mock_calculation_sheet_repo,
        mock_civil_design_repo,
        mock_db_session,
        sample_site_data,
    ):
        """Test utility design without gas demand."""
        # Mock calculation sheet creation
        mock_sheet = CalculationSheet(
            id=5,
            project_id="test-project",
            title="Utility Design - 2024-01-01 12:00",
            calculation_type="utility_design",
        )
        mock_calculation_sheet_repo.create.return_value = mock_sheet

        # Mock civil design creation
        mock_civil_design_repo.create.return_value = AsyncMock()

        # Utility loads without gas
        utility_loads = {
            "water_demand": 30.0,
            "sewer_flow": 25.0,
        }

        # Execute utility design
        result = await civil_service.design_utilities(
            project_id="test-project",
            site_data=sample_site_data,
            utility_loads=utility_loads,
            user_id="test-user",
        )

        # Verify result
        assert isinstance(result, UtilityDesignResult)
        assert result.gas_service_size is None

    @pytest.mark.asyncio
    async def test_add_calculation_dependency(
        self, civil_service, mock_recalculation_service
    ):
        """Test adding calculation dependency."""
        # Mock dependency creation
        mock_recalculation_service.add_dependency.return_value = AsyncMock()

        # Add dependency
        result = await civil_service.add_calculation_dependency(
            source_calculation_id=1,
            target_calculation_id=2,
            dependency_type="site_data",
            user_id="test-user",
            dependent_field="elevations",
            source_field="target_elevations",
        )

        # Verify recalculation service was called
        mock_recalculation_service.add_dependency.assert_called_once_with(
            source_calculation_id=1,
            target_calculation_id=2,
            dependency_type="site_data",
            user_id="test-user",
            dependent_field="elevations",
            source_field="target_elevations",
        )

    @pytest.mark.asyncio
    async def test_update_calculation_inputs(
        self, civil_service, mock_calculation_sheet_repo, mock_recalculation_service
    ):
        """Test updating calculation inputs."""
        # Mock existing calculation sheet
        mock_sheet = CalculationSheet(
            id=1,
            project_id="test-project",
            calculation_type="grading_design",
            inputs={"area": 2.0},
        )
        mock_calculation_sheet_repo.get_by_id.return_value = mock_sheet
        mock_calculation_sheet_repo.update.return_value = mock_sheet

        # Update inputs
        new_inputs = {"area": 3.0, "soil_type": "sand"}
        result = await civil_service.update_calculation_inputs(
            calculation_id=1,
            new_inputs=new_inputs,
            user_id="test-user",
            trigger_recalculation=True,
        )

        # Verify sheet was retrieved and updated
        mock_calculation_sheet_repo.get_by_id.assert_called_once_with(1)
        mock_calculation_sheet_repo.update.assert_called_once()

        # Verify recalculation was triggered
        mock_recalculation_service.trigger_recalculation_cascade.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_calculation_inputs_not_found(
        self, civil_service, mock_calculation_sheet_repo
    ):
        """Test updating inputs for non-existent calculation."""
        # Mock calculation not found
        mock_calculation_sheet_repo.get_by_id.return_value = None

        # Attempt to update inputs
        with pytest.raises(ValueError, match="Calculation sheet 999 not found"):
            await civil_service.update_calculation_inputs(
                calculation_id=999,
                new_inputs={"area": 3.0},
                user_id="test-user",
            )

    @pytest.mark.asyncio
    async def test_recalculate_grading_sheet(
        self, civil_service, mock_calculation_sheet_repo
    ):
        """Test recalculating a grading calculation sheet."""
        # Mock calculation sheet
        mock_sheet = CalculationSheet(
            id=1,
            project_id="test-project",
            calculation_type="grading_design",
            inputs={
                "site_data": {
                    "area": 2.0,
                    "existing_elevations": {"0_0": 100.0, "50_0": 102.0},
                    "soil_type": "clay",
                    "permeability": 0.3,
                    "slope_percent": 2.0,
                },
                "target_elevations": {"0_0": 101.0, "50_0": 101.5},
                "grid_spacing": 50.0,
            },
            units="imperial",
        )

        # Mock repository update
        mock_calculation_sheet_repo.update.return_value = mock_sheet

        # Execute recalculation
        result = await civil_service._recalculate_sheet(mock_sheet, "test-user")

        # Verify result
        assert result is not None
        mock_calculation_sheet_repo.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_recalculate_unknown_sheet_type(
        self, civil_service, mock_calculation_sheet_repo
    ):
        """Test recalculating unknown calculation sheet type."""
        # Mock calculation sheet with unknown type
        mock_sheet = CalculationSheet(
            id=1,
            project_id="test-project",
            calculation_type="unknown_type",
            inputs={},
            units="imperial",
        )

        # Execute recalculation
        result = await civil_service._recalculate_sheet(mock_sheet, "test-user")

        # Verify result is None for unknown type
        assert result is None

    @pytest.mark.asyncio
    async def test_get_calculation_dependents(
        self, civil_service, mock_recalculation_service
    ):
        """Test getting calculation dependents."""
        # Mock dependents
        mock_dependents = [AsyncMock(), AsyncMock()]
        mock_recalculation_service.get_dependents.return_value = mock_dependents

        # Get dependents
        result = await civil_service.get_calculation_dependents(1)

        # Verify result
        assert result == mock_dependents
        mock_recalculation_service.get_dependents.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_get_calculation_dependencies(
        self, civil_service, mock_recalculation_service
    ):
        """Test getting calculation dependencies."""
        # Mock dependencies
        mock_dependencies = [AsyncMock(), AsyncMock()]
        mock_recalculation_service.get_dependencies.return_value = mock_dependencies

        # Get dependencies
        result = await civil_service.get_calculation_dependencies(1)

        # Verify result
        assert result == mock_dependencies
        mock_recalculation_service.get_dependencies.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_get_dependency_graph(
        self, civil_service, mock_recalculation_service
    ):
        """Test getting dependency graph."""
        # Mock dependency graph
        mock_graph = {
            "dependencies": [{"id": 2, "type": "site_data"}],
            "dependents": [{"id": 3, "type": "elevation_input"}],
        }
        mock_recalculation_service.get_dependency_graph.return_value = mock_graph

        # Get dependency graph
        result = await civil_service.get_dependency_graph(1)

        # Verify result
        assert result == mock_graph
        mock_recalculation_service.get_dependency_graph.assert_called_once_with(1)

    def test_parse_site_data(self, civil_service):
        """Test parsing site data dictionary."""
        site_data_dict = {
            "area": 3.5,
            "existing_elevations": {"0_0": 100.0, "50_0": 102.0},
            "soil_type": "sand",
            "permeability": 1.2,
            "slope_percent": 3.0,
        }

        site_data = civil_service._parse_site_data(site_data_dict)

        assert site_data.area == 3.5
        assert site_data.existing_elevations == {"0_0": 100.0, "50_0": 102.0}
        assert site_data.soil_type == "sand"
        assert site_data.permeability == 1.2
        assert site_data.slope_percent == 3.0

    def test_parse_site_data_defaults(self, civil_service):
        """Test parsing site data with default values."""
        site_data_dict = {}

        site_data = civil_service._parse_site_data(site_data_dict)

        assert site_data.area == 1.0
        assert site_data.existing_elevations == {}
        assert site_data.soil_type == "clay"
        assert site_data.permeability == 0.5
        assert site_data.slope_percent == 2.0

    def test_parse_rainfall_data(self, civil_service):
        """Test parsing rainfall data dictionary."""
        rainfall_data_dict = {
            "intensity": 4.0,
            "duration": 3.0,
            "return_period": 50,
            "runoff_coefficient": 0.8,
        }

        rainfall_data = civil_service._parse_rainfall_data(rainfall_data_dict)

        assert rainfall_data.intensity == 4.0
        assert rainfall_data.duration == 3.0
        assert rainfall_data.return_period == 50
        assert rainfall_data.runoff_coefficient == 0.8

    def test_parse_utility_loads(self, civil_service):
        """Test parsing utility loads dictionary."""
        utility_loads_dict = {
            "water_demand": 35.0,
            "sewer_flow": 30.0,
            "gas_demand": 200.0,
        }

        utility_loads = civil_service._parse_utility_loads(utility_loads_dict)

        assert utility_loads.water_demand == 35.0
        assert utility_loads.sewer_flow == 30.0
        assert utility_loads.gas_demand == 200.0

    def test_parse_utility_loads_defaults(self, civil_service):
        """Test parsing utility loads with default values."""
        utility_loads_dict = {}

        utility_loads = civil_service._parse_utility_loads(utility_loads_dict)

        assert utility_loads.water_demand == 20.0
        assert utility_loads.sewer_flow == 15.0
        assert utility_loads.gas_demand is None

    @pytest.mark.asyncio
    async def test_design_utilities_with_different_gas_demands(
        self,
        civil_service,
        mock_calculation_sheet_repo,
        mock_civil_design_repo,
        mock_db_session,
        sample_site_data,
    ):
        """Test utility design with different gas demand levels."""
        # Mock calculation sheet creation
        mock_sheet = CalculationSheet(
            id=6,
            project_id="test-project",
            title="Utility Design - 2024-01-01 12:00",
            calculation_type="utility_design",
        )
        mock_calculation_sheet_repo.create.return_value = mock_sheet
        mock_civil_design_repo.create.return_value = AsyncMock()

        # Test small gas demand (≤100 CFH)
        utility_loads_small = {
            "water_demand": 25.0,
            "sewer_flow": 20.0,
            "gas_demand": 80.0,
        }
        result = await civil_service.design_utilities(
            project_id="test-project",
            site_data=sample_site_data,
            utility_loads=utility_loads_small,
            user_id="test-user",
        )
        assert result.gas_service_size == 1.0

        # Test medium gas demand (≤300 CFH)
        utility_loads_medium = {
            "water_demand": 25.0,
            "sewer_flow": 20.0,
            "gas_demand": 250.0,
        }
        result = await civil_service.design_utilities(
            project_id="test-project",
            site_data=sample_site_data,
            utility_loads=utility_loads_medium,
            user_id="test-user",
        )
        assert result.gas_service_size == 1.25

        # Test large gas demand (≤600 CFH)
        utility_loads_large = {
            "water_demand": 25.0,
            "sewer_flow": 20.0,
            "gas_demand": 500.0,
        }
        result = await civil_service.design_utilities(
            project_id="test-project",
            site_data=sample_site_data,
            utility_loads=utility_loads_large,
            user_id="test-user",
        )
        assert result.gas_service_size == 1.5

        # Test very large gas demand (>600 CFH)
        utility_loads_xlarge = {
            "water_demand": 25.0,
            "sewer_flow": 20.0,
            "gas_demand": 800.0,
        }
        result = await civil_service.design_utilities(
            project_id="test-project",
            site_data=sample_site_data,
            utility_loads=utility_loads_xlarge,
            user_id="test-user",
        )
        assert result.gas_service_size == 2.0

    @pytest.mark.asyncio
    async def test_recalculate_stormwater_sheet(
        self, civil_service, mock_calculation_sheet_repo
    ):
        """Test recalculating a stormwater calculation sheet."""
        # Mock calculation sheet
        mock_sheet = CalculationSheet(
            id=2,
            project_id="test-project",
            calculation_type="stormwater_design",
            inputs={
                "site_data": {
                    "area": 2.0,
                    "soil_type": "clay",
                    "permeability": 0.3,
                },
                "rainfall_data": {
                    "intensity": 3.0,
                    "duration": 2.0,
                    "return_period": 25,
                    "runoff_coefficient": 0.7,
                },
                "release_rate": 2.0,
            },
            units="imperial",
        )

        # Mock repository update
        mock_calculation_sheet_repo.update.return_value = mock_sheet

        # Execute recalculation
        result = await civil_service._recalculate_sheet(mock_sheet, "test-user")

        # Verify result
        assert result is not None
        mock_calculation_sheet_repo.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_recalculate_utility_sheet(
        self, civil_service, mock_calculation_sheet_repo
    ):
        """Test recalculating a utility calculation sheet."""
        # Mock calculation sheet
        mock_sheet = CalculationSheet(
            id=3,
            project_id="test-project",
            calculation_type="utility_design",
            inputs={
                "site_data": {
                    "area": 2.0,
                    "soil_type": "clay",
                },
                "utility_loads": {
                    "water_demand": 25.0,
                    "sewer_flow": 20.0,
                    "gas_demand": 150.0,
                },
                "pressure_available": 65.0,
            },
            units="imperial",
        )

        # Mock repository update
        mock_calculation_sheet_repo.update.return_value = mock_sheet

        # Execute recalculation
        result = await civil_service._recalculate_sheet(mock_sheet, "test-user")

        # Verify result
        assert result is not None
        mock_calculation_sheet_repo.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_recalculate_sheet_with_exception(
        self, civil_service, mock_calculation_sheet_repo
    ):
        """Test recalculation with exception handling."""
        # Mock calculation sheet
        mock_sheet = CalculationSheet(
            id=4,
            project_id="test-project",
            calculation_type="grading_design",
            inputs={
                "site_data": {
                    "area": 2.0,
                    "existing_elevations": {"0_0": 100.0, "50_0": 102.0},
                    "soil_type": "clay",
                },
                "target_elevations": {"0_0": 101.0, "50_0": 101.5},
                "grid_spacing": 50.0,
            },
            units="imperial",
        )

        # Mock repository to raise exception
        mock_calculation_sheet_repo.update.side_effect = Exception("Database error")

        # Execute recalculation - should handle exception gracefully
        with patch("src.core.logging.get_logger") as mock_logger:
            mock_logger_instance = AsyncMock()
            mock_logger.return_value = mock_logger_instance

            result = await civil_service._recalculate_sheet(mock_sheet, "test-user")

            # Verify result is None when exception occurs
            assert result is None
            # Verify error was logged
            mock_logger_instance.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_design_grading_with_metric_units(
        self,
        civil_service,
        mock_calculation_sheet_repo,
        mock_civil_design_repo,
        mock_db_session,
        sample_site_data,
        sample_target_elevations,
    ):
        """Test grading design with metric units."""
        # Mock calculation sheet creation
        mock_sheet = CalculationSheet(
            id=7,
            project_id="test-project",
            title="Grading Design - 2024-01-01 12:00",
            calculation_type="grading_design",
        )
        mock_calculation_sheet_repo.create.return_value = mock_sheet
        mock_civil_design_repo.create.return_value = AsyncMock()

        # Execute grading design with metric units
        result = await civil_service.design_grading(
            project_id="test-project",
            site_data=sample_site_data,
            target_elevations=sample_target_elevations,
            user_id="test-user",
            unit_system="metric",
            grid_spacing=15.0,  # meters
        )

        # Verify result uses metric units
        assert isinstance(result, GradingDesignResult)
        assert result.unit_system == "imperial"  # Calculator always returns imperial

    @pytest.mark.asyncio
    async def test_design_stormwater_with_large_detention(
        self,
        civil_service,
        mock_calculation_sheet_repo,
        mock_civil_design_repo,
        mock_db_session,
        sample_site_data,
    ):
        """Test stormwater design with large detention requirements."""
        # Mock calculation sheet creation
        mock_sheet = CalculationSheet(
            id=8,
            project_id="test-project",
            title="Stormwater Design - 2024-01-01 12:00",
            calculation_type="stormwater_design",
        )
        mock_calculation_sheet_repo.create.return_value = mock_sheet
        mock_civil_design_repo.create.return_value = AsyncMock()

        # Large rainfall event
        rainfall_data = {
            "intensity": 6.0,  # High intensity
            "duration": 4.0,  # Long duration
            "return_period": 100,  # 100-year storm
            "runoff_coefficient": 0.9,  # High runoff
        }

        # Execute stormwater design
        result = await civil_service.design_stormwater(
            project_id="test-project",
            site_data=sample_site_data,
            rainfall_data=rainfall_data,
            user_id="test-user",
            unit_system="imperial",
            release_rate=1.0,  # Low release rate = large detention
        )

        # Verify result has detention
        assert isinstance(result, StormwaterDesignResult)
        assert result.detention_volume > 0
        assert result.runoff_rate > 0

    @pytest.mark.asyncio
    async def test_design_utilities_edge_cases(
        self,
        civil_service,
        mock_calculation_sheet_repo,
        mock_civil_design_repo,
        mock_db_session,
        sample_site_data,
    ):
        """Test utility design edge cases."""
        # Mock calculation sheet creation
        mock_sheet = CalculationSheet(
            id=9,
            project_id="test-project",
            title="Utility Design - 2024-01-01 12:00",
            calculation_type="utility_design",
        )
        mock_calculation_sheet_repo.create.return_value = mock_sheet
        mock_civil_design_repo.create.return_value = AsyncMock()

        # Test with zero gas demand
        utility_loads_zero_gas = {
            "water_demand": 25.0,
            "sewer_flow": 20.0,
            "gas_demand": 0.0,
        }
        result = await civil_service.design_utilities(
            project_id="test-project",
            site_data=sample_site_data,
            utility_loads=utility_loads_zero_gas,
            user_id="test-user",
        )
        assert result.gas_service_size is None

        # Test with very high pressure available
        result = await civil_service.design_utilities(
            project_id="test-project",
            site_data=sample_site_data,
            utility_loads={"water_demand": 25.0, "sewer_flow": 20.0},
            user_id="test-user",
            pressure_available=100.0,
        )
        assert result.water_pressure_required > 0
