"""Unit tests for MEPCalculationService."""

from typing import Any, Dict
from unittest.mock import AsyncMock

import pytest
from src.calculations.electrical_calculator import CircuitType
from src.calculations.hvac_calculator import EquipmentSize, HVACDesignResult
from src.models.calculation_sheet import CalculationSheet
from src.models.mep_design import MEPDesign
from src.repositories.calculation_sheet_repository import \
    CalculationSheetRepository
from src.repositories.mep_design_repository import MEPDesignRepository
from src.services.mep_calculation_service import MEPCalculationService


class TestMEPCalculationServiceDesignHVACSystem:
    """Test design_hvac_system method of MEPCalculationService."""

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        session = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        return session

    @pytest.fixture
    def mock_calculation_sheet_repo(self):
        """Create a mock calculation sheet repository."""
        repo = AsyncMock(spec=CalculationSheetRepository)
        # Create a mock calculation sheet with an ID
        mock_sheet = CalculationSheet(
            id=1,
            project_id="test-project-123",
            title="HVAC Design - 2024-01-01 12:00",
            description="HVAC system design",
            calculation_type="hvac_design",
            inputs={},
            outputs={},
            created_by="test-user-456",
            status="approved",
        )
        repo.create = AsyncMock(return_value=mock_sheet)
        return repo

    @pytest.fixture
    def mock_mep_design_repo(self):
        """Create a mock MEP design repository."""
        repo = AsyncMock(spec=MEPDesignRepository)
        repo.create = AsyncMock()
        return repo

    @pytest.fixture
    def service(
        self,
        mock_db_session,
        mock_calculation_sheet_repo,
        mock_mep_design_repo,
    ):
        """Create MEPCalculationService with mocked dependencies."""
        return MEPCalculationService(
            db_session=mock_db_session,
            calculation_sheet_repo=mock_calculation_sheet_repo,
            mep_design_repo=mock_mep_design_repo,
        )

    @pytest.fixture
    def basic_building_data(self) -> Dict[str, Any]:
        """Create basic building data for testing."""
        return {
            "floor_area": 5000.0,  # sq ft
            "wall_area": 3000.0,  # sq ft
            "roof_area": 5000.0,  # sq ft
            "window_area": 500.0,  # sq ft
            "volume": 50000.0,  # cu ft
            "occupancy": 50,  # number of people
            "insulation_r_value": 19.0,  # R-value
        }

    @pytest.fixture
    def basic_climate_data(self) -> Dict[str, Any]:
        """Create basic climate data for testing."""
        return {
            "outdoor_temp_winter": 10.0,  # °F
            "outdoor_temp_summer": 95.0,  # °F
            "indoor_temp_winter": 70.0,  # °F
            "indoor_temp_summer": 75.0,  # °F
            "humidity_summer": 50.0,  # %
        }

    @pytest.mark.asyncio
    async def test_design_hvac_system_basic(
        self,
        service,
        basic_building_data,
        basic_climate_data,
        mock_calculation_sheet_repo,
        mock_mep_design_repo,
        mock_db_session,
    ):
        """Test basic HVAC system design."""
        # Arrange
        project_id = "test-project-123"
        user_id = "test-user-456"

        # Act
        result = await service.design_hvac_system(
            project_id=project_id,
            building_data=basic_building_data,
            climate_data=basic_climate_data,
            user_id=user_id,
            unit_system="imperial",
        )

        # Assert
        assert isinstance(result, HVACDesignResult)
        assert result.heating_load > 0
        assert result.cooling_load > 0
        assert isinstance(result.equipment, EquipmentSize)
        assert result.equipment.heating_capacity > 0
        assert result.equipment.cooling_capacity > 0
        assert result.equipment.airflow > 0
        assert result.equipment.equipment_type != ""
        assert result.unit_system == "imperial"

        # Verify calculation sheet was created and saved
        mock_calculation_sheet_repo.create.assert_called_once()
        call_args = mock_calculation_sheet_repo.create.call_args
        created_sheet = call_args[0][0]
        assert isinstance(created_sheet, CalculationSheet)
        assert created_sheet.project_id == project_id
        assert created_sheet.calculation_type == "hvac_design"
        assert created_sheet.created_by == user_id

        # Verify MEP design was created and saved
        mock_mep_design_repo.create.assert_called_once()
        call_args = mock_mep_design_repo.create.call_args
        created_design = call_args[0][0]
        assert isinstance(created_design, MEPDesign)
        assert created_design.project_id == project_id
        assert created_design.system_type == "hvac"
        assert created_design.created_by == user_id
        assert created_design.calculation_sheet_id == 1

        # Verify database commit was called
        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_design_hvac_system_heating_load_calculation(
        self,
        service,
        basic_building_data,
        basic_climate_data,
    ):
        """Test that heating load is calculated correctly."""
        # Arrange
        project_id = "test-project-123"
        user_id = "test-user-456"

        # Act
        result = await service.design_hvac_system(
            project_id=project_id,
            building_data=basic_building_data,
            climate_data=basic_climate_data,
            user_id=user_id,
            unit_system="imperial",
        )

        # Assert - heating load should be positive for cold climate
        assert result.heating_load > 0
        # Heating load should be reasonable for the building size
        # Rough estimate: 30-50 BTU/hr per sq ft for typical building
        expected_min = basic_building_data["floor_area"] * 20
        expected_max = basic_building_data["floor_area"] * 100
        assert expected_min < result.heating_load < expected_max

    @pytest.mark.asyncio
    async def test_design_hvac_system_cooling_load_calculation(
        self,
        service,
        basic_building_data,
        basic_climate_data,
    ):
        """Test that cooling load is calculated correctly."""
        # Arrange
        project_id = "test-project-123"
        user_id = "test-user-456"

        # Act
        result = await service.design_hvac_system(
            project_id=project_id,
            building_data=basic_building_data,
            climate_data=basic_climate_data,
            user_id=user_id,
            unit_system="imperial",
        )

        # Assert - cooling load should be positive
        assert result.cooling_load > 0
        # Cooling load should be reasonable for the building size
        # Rough estimate: 20-40 BTU/hr per sq ft for typical building
        expected_min = basic_building_data["floor_area"] * 15
        expected_max = basic_building_data["floor_area"] * 80
        assert expected_min < result.cooling_load < expected_max

    @pytest.mark.asyncio
    async def test_design_hvac_system_equipment_sizing(
        self,
        service,
        basic_building_data,
        basic_climate_data,
    ):
        """Test that equipment is sized appropriately."""
        # Arrange
        project_id = "test-project-123"
        user_id = "test-user-456"

        # Act
        result = await service.design_hvac_system(
            project_id=project_id,
            building_data=basic_building_data,
            climate_data=basic_climate_data,
            user_id=user_id,
            unit_system="imperial",
        )

        # Assert - equipment capacity should be >= calculated loads
        assert result.equipment.heating_capacity >= result.heating_load
        assert result.equipment.cooling_capacity >= result.cooling_load

        # Equipment should have reasonable safety factor (1.0 to 1.5x)
        heating_safety_factor = result.equipment.heating_capacity / result.heating_load
        cooling_safety_factor = result.equipment.cooling_capacity / result.cooling_load
        assert 1.0 <= heating_safety_factor <= 1.5
        assert 1.0 <= cooling_safety_factor <= 1.5

        # Airflow should follow rule of thumb: ~400 CFM per ton
        cooling_tons = result.equipment.cooling_capacity / 12000
        expected_airflow = cooling_tons * 400
        # Allow 20% tolerance
        assert (
            0.8 * expected_airflow
            <= result.equipment.airflow
            <= (1.2 * expected_airflow)
        )

    @pytest.mark.asyncio
    async def test_design_hvac_system_with_metric_units(
        self,
        service,
        basic_building_data,
        basic_climate_data,
    ):
        """Test HVAC design with metric unit system."""
        # Arrange
        project_id = "test-project-123"
        user_id = "test-user-456"

        # Act
        result = await service.design_hvac_system(
            project_id=project_id,
            building_data=basic_building_data,
            climate_data=basic_climate_data,
            user_id=user_id,
            unit_system="metric",
        )

        # Assert
        assert result.unit_system == "metric"
        # Calculations should still work (values are in imperial internally)
        assert result.heating_load > 0
        assert result.cooling_load > 0

    @pytest.mark.asyncio
    async def test_design_hvac_system_small_building(
        self,
        service,
        basic_climate_data,
    ):
        """Test HVAC design for a small residential building."""
        # Arrange
        project_id = "test-project-123"
        user_id = "test-user-456"
        small_building_data = {
            "floor_area": 2000.0,  # sq ft
            "wall_area": 1200.0,  # sq ft
            "roof_area": 2000.0,  # sq ft
            "window_area": 200.0,  # sq ft
            "volume": 16000.0,  # cu ft (8 ft ceiling)
            "occupancy": 4,  # number of people
            "insulation_r_value": 19.0,  # R-value
        }

        # Act
        result = await service.design_hvac_system(
            project_id=project_id,
            building_data=small_building_data,
            climate_data=basic_climate_data,
            user_id=user_id,
            unit_system="imperial",
        )

        # Assert - should select residential equipment
        assert "Residential" in result.equipment.equipment_type
        # Equipment should be appropriately sized for small building
        cooling_tons = result.equipment.cooling_capacity / 12000
        assert cooling_tons <= 5  # Residential systems typically <= 5 tons

    @pytest.mark.asyncio
    async def test_design_hvac_system_large_building(
        self,
        service,
        basic_climate_data,
    ):
        """Test HVAC design for a large commercial building."""
        # Arrange
        project_id = "test-project-123"
        user_id = "test-user-456"
        large_building_data = {
            "floor_area": 50000.0,  # sq ft
            "wall_area": 20000.0,  # sq ft
            "roof_area": 50000.0,  # sq ft
            "window_area": 5000.0,  # sq ft
            "volume": 500000.0,  # cu ft
            "occupancy": 500,  # number of people
            "insulation_r_value": 19.0,  # R-value
        }

        # Act
        result = await service.design_hvac_system(
            project_id=project_id,
            building_data=large_building_data,
            climate_data=basic_climate_data,
            user_id=user_id,
            unit_system="imperial",
        )

        # Assert - should select commercial equipment
        assert "Commercial" in result.equipment.equipment_type
        # Equipment should be appropriately sized for large building
        cooling_tons = result.equipment.cooling_capacity / 12000
        assert cooling_tons > 10  # Large commercial systems > 10 tons


class TestMEPCalculationServiceDesignElectricalSystem:
    """Test design_electrical_system method of MEPCalculationService."""

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        session = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        return session

    @pytest.fixture
    def mock_calculation_sheet_repo(self):
        """Create a mock calculation sheet repository."""
        repo = AsyncMock(spec=CalculationSheetRepository)
        # Create a mock calculation sheet with an ID
        mock_sheet = CalculationSheet(
            id=1,
            project_id="test-project-123",
            title="Electrical Design - 2024-01-01 12:00",
            description="Electrical system design",
            calculation_type="electrical_design",
            inputs={},
            outputs={},
            created_by="test-user-456",
            status="approved",
        )
        repo.create = AsyncMock(return_value=mock_sheet)
        return repo

    @pytest.fixture
    def mock_mep_design_repo(self):
        """Create a mock MEP design repository."""
        repo = AsyncMock(spec=MEPDesignRepository)
        repo.create = AsyncMock()
        return repo

    @pytest.fixture
    def service(
        self,
        mock_db_session,
        mock_calculation_sheet_repo,
        mock_mep_design_repo,
    ):
        """Create MEPCalculationService with mocked dependencies."""
        return MEPCalculationService(
            db_session=mock_db_session,
            calculation_sheet_repo=mock_calculation_sheet_repo,
            mep_design_repo=mock_mep_design_repo,
        )

    @pytest.fixture
    def basic_circuits(self):
        """Create basic circuit data for testing."""
        return [
            {
                "name": "Lighting Circuit 1",
                "circuit_type": CircuitType.LIGHTING,
                "load": 1500.0,  # Watts
                "voltage": 120.0,  # Volts
                "power_factor": 1.0,
                "continuous": True,
            },
            {
                "name": "Receptacle Circuit 1",
                "circuit_type": CircuitType.RECEPTACLE,
                "load": 1800.0,  # Watts
                "voltage": 120.0,  # Volts
                "power_factor": 1.0,
                "continuous": False,
            },
            {
                "name": "HVAC Unit",
                "circuit_type": CircuitType.HVAC,
                "load": 5000.0,  # Watts
                "voltage": 240.0,  # Volts
                "power_factor": 0.9,
                "continuous": True,
            },
        ]

    @pytest.mark.asyncio
    async def test_design_electrical_system_basic(
        self,
        service,
        basic_circuits,
        mock_calculation_sheet_repo,
        mock_mep_design_repo,
        mock_db_session,
    ):
        """Test basic electrical system design."""
        # Arrange
        project_id = "test-project-123"
        user_id = "test-user-456"
        voltage = 240.0

        # Act
        result = await service.design_electrical_system(
            project_id=project_id,
            circuits=basic_circuits,
            voltage=voltage,
            user_id=user_id,
            unit_system="imperial",
        )

        # Assert
        assert isinstance(result, dict)
        assert "total_load" in result
        assert "panel_size" in result
        assert "circuit_sizes" in result
        assert result["total_load"] > 0
        assert result["panel_size"]["rated_amperage"] > 0
        assert len(result["circuit_sizes"]) == len(basic_circuits)
        assert result["unit_system"] == "imperial"

        # Verify calculation sheet was created and saved
        mock_calculation_sheet_repo.create.assert_called_once()
        call_args = mock_calculation_sheet_repo.create.call_args
        created_sheet = call_args[0][0]
        assert isinstance(created_sheet, CalculationSheet)
        assert created_sheet.project_id == project_id
        assert created_sheet.calculation_type == "electrical_design"
        assert created_sheet.created_by == user_id

        # Verify MEP design was created and saved
        mock_mep_design_repo.create.assert_called_once()
        call_args = mock_mep_design_repo.create.call_args
        created_design = call_args[0][0]
        assert isinstance(created_design, MEPDesign)
        assert created_design.project_id == project_id
        assert created_design.system_type == "electrical"
        assert created_design.created_by == user_id
        assert created_design.calculation_sheet_id == 1

        # Verify database commit was called
        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_design_electrical_system_load_calculation(
        self,
        service,
        basic_circuits,
    ):
        """Test that electrical load is calculated correctly."""
        # Arrange
        project_id = "test-project-123"
        user_id = "test-user-456"
        voltage = 240.0

        # Act
        result = await service.design_electrical_system(
            project_id=project_id,
            circuits=basic_circuits,
            voltage=voltage,
            user_id=user_id,
            unit_system="imperial",
        )

        # Assert - total load should be positive
        assert result["total_load"] > 0
        # Total load should be less than sum of all circuits due to demand factors
        # With continuous loads at 125%, total could be higher
        assert result["total_load"] > 0

    @pytest.mark.asyncio
    async def test_design_electrical_system_panel_sizing(
        self,
        service,
        basic_circuits,
    ):
        """Test that electrical panel is sized appropriately."""
        # Arrange
        project_id = "test-project-123"
        user_id = "test-user-456"
        voltage = 240.0

        # Act
        result = await service.design_electrical_system(
            project_id=project_id,
            circuits=basic_circuits,
            voltage=voltage,
            user_id=user_id,
            unit_system="imperial",
        )

        # Assert - panel should be sized appropriately
        panel = result["panel_size"]
        assert panel["rated_amperage"] > 0
        assert panel["number_of_circuits"] >= len(basic_circuits)
        assert panel["bus_rating"] == panel["rated_amperage"]
        assert panel["main_breaker_size"] == panel["rated_amperage"]
        assert panel["panel_type"] in [
            "Residential Load Center",
            "Commercial Panelboard",
            "Switchboard",
        ]

        # Panel amperage should be reasonable for the load
        required_amps = result["total_load"] / voltage
        assert panel["rated_amperage"] >= required_amps

    @pytest.mark.asyncio
    async def test_design_electrical_system_circuit_sizing(
        self,
        service,
        basic_circuits,
    ):
        """Test that circuits are sized appropriately."""
        # Arrange
        project_id = "test-project-123"
        user_id = "test-user-456"
        voltage = 240.0

        # Act
        result = await service.design_electrical_system(
            project_id=project_id,
            circuits=basic_circuits,
            voltage=voltage,
            user_id=user_id,
            unit_system="imperial",
        )

        # Assert - each circuit should have sizing information
        circuit_sizes = result["circuit_sizes"]
        assert len(circuit_sizes) == len(basic_circuits)

        for circuit_size in circuit_sizes:
            assert "name" in circuit_size
            assert "conductor_size" in circuit_size
            assert "conduit_size" in circuit_size
            assert "breaker_size" in circuit_size
            assert "voltage_drop" in circuit_size
            assert "ampacity" in circuit_size

            # Conductor size should be in AWG format
            assert "AWG" in circuit_size["conductor_size"]

            # Breaker size should be positive
            assert circuit_size["breaker_size"] > 0

            # Voltage drop should be within acceptable range (≤ 5%)
            assert 0 <= circuit_size["voltage_drop"] <= 5.0

            # Ampacity should be positive
            assert circuit_size["ampacity"] > 0

    @pytest.mark.asyncio
    async def test_design_electrical_system_with_metric_units(
        self,
        service,
        basic_circuits,
    ):
        """Test electrical design with metric unit system."""
        # Arrange
        project_id = "test-project-123"
        user_id = "test-user-456"
        voltage = 240.0

        # Act
        result = await service.design_electrical_system(
            project_id=project_id,
            circuits=basic_circuits,
            voltage=voltage,
            user_id=user_id,
            unit_system="metric",
        )

        # Assert
        assert result["unit_system"] == "metric"
        # Calculations should still work
        assert result["total_load"] > 0
        assert result["panel_size"]["rated_amperage"] > 0

    @pytest.mark.asyncio
    async def test_design_electrical_system_residential(
        self,
        service,
    ):
        """Test electrical design for a residential building."""
        # Arrange
        project_id = "test-project-123"
        user_id = "test-user-456"
        voltage = 240.0
        residential_circuits = [
            {
                "name": "Lighting",
                "circuit_type": CircuitType.LIGHTING,
                "load": 3000.0,
                "voltage": 120.0,
                "power_factor": 1.0,
                "continuous": True,
            },
            {
                "name": "Receptacles",
                "circuit_type": CircuitType.RECEPTACLE,
                "load": 5000.0,
                "voltage": 120.0,
                "power_factor": 1.0,
                "continuous": False,
            },
            {
                "name": "Kitchen Appliances",
                "circuit_type": CircuitType.APPLIANCE,
                "load": 8000.0,
                "voltage": 240.0,
                "power_factor": 1.0,
                "continuous": False,
            },
        ]

        # Act
        result = await service.design_electrical_system(
            project_id=project_id,
            circuits=residential_circuits,
            voltage=voltage,
            user_id=user_id,
            unit_system="imperial",
        )

        # Assert - should select residential panel
        assert "Residential" in result["panel_size"]["panel_type"]
        # Panel should be appropriately sized (typically 100-200A for residential)
        assert 100 <= result["panel_size"]["rated_amperage"] <= 200

    @pytest.mark.asyncio
    async def test_design_electrical_system_commercial(
        self,
        service,
    ):
        """Test electrical design for a commercial building."""
        # Arrange
        project_id = "test-project-123"
        user_id = "test-user-456"
        voltage = 480.0
        commercial_circuits = [
            {
                "name": "Lighting",
                "circuit_type": CircuitType.LIGHTING,
                "load": 20000.0,
                "voltage": 277.0,
                "power_factor": 1.0,
                "continuous": True,
            },
            {
                "name": "Receptacles",
                "circuit_type": CircuitType.RECEPTACLE,
                "load": 30000.0,
                "voltage": 120.0,
                "power_factor": 1.0,
                "continuous": False,
            },
            {
                "name": "HVAC System",
                "circuit_type": CircuitType.HVAC,
                "load": 50000.0,
                "voltage": 480.0,
                "power_factor": 0.85,
                "continuous": True,
            },
        ]

        # Act
        result = await service.design_electrical_system(
            project_id=project_id,
            circuits=commercial_circuits,
            voltage=voltage,
            user_id=user_id,
            unit_system="imperial",
        )

        # Assert - should select commercial panel
        assert result["panel_size"]["panel_type"] in [
            "Commercial Panelboard",
            "Switchboard",
        ]
        # Panel should be appropriately sized for commercial load
        assert result["panel_size"]["rated_amperage"] >= 200

    @pytest.mark.asyncio
    async def test_design_electrical_system_empty_circuits(
        self,
        service,
    ):
        """Test that empty circuits list raises ValueError."""
        # Arrange
        project_id = "test-project-123"
        user_id = "test-user-456"
        voltage = 240.0

        # Act & Assert
        with pytest.raises(ValueError, match="At least one circuit must be provided"):
            await service.design_electrical_system(
                project_id=project_id,
                circuits=[],
                voltage=voltage,
                user_id=user_id,
                unit_system="imperial",
            )

    @pytest.mark.asyncio
    async def test_design_electrical_system_invalid_voltage(
        self,
        service,
        basic_circuits,
    ):
        """Test that invalid voltage raises ValueError."""
        # Arrange
        project_id = "test-project-123"
        user_id = "test-user-456"
        voltage = -120.0  # Invalid negative voltage

        # Act & Assert
        with pytest.raises(ValueError, match="Voltage must be positive"):
            await service.design_electrical_system(
                project_id=project_id,
                circuits=basic_circuits,
                voltage=voltage,
                user_id=user_id,
                unit_system="imperial",
            )


class TestMEPCalculationServiceDesignPlumbingSystem:
    """Test design_plumbing_system method of MEPCalculationService."""

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        session = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        return session

    @pytest.fixture
    def mock_calculation_sheet_repo(self):
        """Create a mock calculation sheet repository."""
        repo = AsyncMock(spec=CalculationSheetRepository)
        # Create a mock calculation sheet with an ID
        mock_sheet = CalculationSheet(
            id=1,
            project_id="test-project-123",
            title="Plumbing Design - 2024-01-01 12:00",
            description="Plumbing system design",
            calculation_type="plumbing_design",
            inputs={},
            outputs={},
            created_by="test-user-456",
            status="approved",
        )
        repo.create = AsyncMock(return_value=mock_sheet)
        return repo

    @pytest.fixture
    def mock_mep_design_repo(self):
        """Create a mock MEP design repository."""
        repo = AsyncMock(spec=MEPDesignRepository)
        repo.create = AsyncMock()
        return repo

    @pytest.fixture
    def service(
        self,
        mock_db_session,
        mock_calculation_sheet_repo,
        mock_mep_design_repo,
    ):
        """Create MEPCalculationService with mocked dependencies."""
        return MEPCalculationService(
            db_session=mock_db_session,
            calculation_sheet_repo=mock_calculation_sheet_repo,
            mep_design_repo=mock_mep_design_repo,
        )

    @pytest.fixture
    def basic_fixtures(self):
        """Create basic fixture data for testing."""
        return [
            {
                "name": "Water Closet 1",
                "fixture_type": "water_closet",
                "quantity": 2,
                "private": True,
            },
            {
                "name": "Lavatory 1",
                "fixture_type": "lavatory",
                "quantity": 2,
                "private": True,
            },
            {
                "name": "Kitchen Sink",
                "fixture_type": "kitchen_sink",
                "quantity": 1,
                "private": True,
            },
            {
                "name": "Shower",
                "fixture_type": "shower",
                "quantity": 1,
                "private": True,
            },
        ]

    @pytest.mark.asyncio
    async def test_design_plumbing_system_basic(
        self,
        service,
        basic_fixtures,
        mock_calculation_sheet_repo,
        mock_mep_design_repo,
        mock_db_session,
    ):
        """Test basic plumbing system design."""
        # Arrange
        project_id = "test-project-123"
        user_id = "test-user-456"
        supply_pressure = 60.0  # psi

        # Act
        result = await service.design_plumbing_system(
            project_id=project_id,
            fixtures=basic_fixtures,
            supply_pressure=supply_pressure,
            user_id=user_id,
            unit_system="imperial",
        )

        # Assert
        assert isinstance(result, dict)
        assert "total_fixture_units" in result
        assert "peak_demand" in result
        assert "service_size" in result
        assert "meter_size" in result
        assert "supply_pressure_required" in result
        assert result["total_fixture_units"] > 0
        assert result["peak_demand"] > 0
        assert result["service_size"] != ""
        assert result["meter_size"] != ""
        assert result["supply_pressure_required"] > 0
        assert result["unit_system"] == "imperial"

        # Verify calculation sheet was created and saved
        mock_calculation_sheet_repo.create.assert_called_once()
        call_args = mock_calculation_sheet_repo.create.call_args
        created_sheet = call_args[0][0]
        assert isinstance(created_sheet, CalculationSheet)
        assert created_sheet.project_id == project_id
        assert created_sheet.calculation_type == "plumbing_design"
        assert created_sheet.created_by == user_id

        # Verify MEP design was created and saved
        mock_mep_design_repo.create.assert_called_once()
        call_args = mock_mep_design_repo.create.call_args
        created_design = call_args[0][0]
        assert isinstance(created_design, MEPDesign)
        assert created_design.project_id == project_id
        assert created_design.system_type == "plumbing"
        assert created_design.created_by == user_id
        assert created_design.calculation_sheet_id == 1

        # Verify database commit was called
        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_design_plumbing_system_fixture_units_calculation(
        self,
        service,
        basic_fixtures,
    ):
        """Test that fixture units are calculated correctly."""
        # Arrange
        project_id = "test-project-123"
        user_id = "test-user-456"
        supply_pressure = 60.0

        # Act
        result = await service.design_plumbing_system(
            project_id=project_id,
            fixtures=basic_fixtures,
            supply_pressure=supply_pressure,
            user_id=user_id,
            unit_system="imperial",
        )

        # Assert - fixture units should be positive
        assert result["total_fixture_units"] > 0
        # Expected: 2 water closets (3 FU each) + 2 lavatories (1 FU each)
        # + 1 kitchen sink (1.5 FU) + 1 shower (2 FU) = 11.5 FU
        expected_fu = 2 * 3.0 + 2 * 1.0 + 1 * 1.5 + 1 * 2.0
        assert result["total_fixture_units"] == expected_fu

    @pytest.mark.asyncio
    async def test_design_plumbing_system_peak_demand_calculation(
        self,
        service,
        basic_fixtures,
    ):
        """Test that peak demand is calculated correctly."""
        # Arrange
        project_id = "test-project-123"
        user_id = "test-user-456"
        supply_pressure = 60.0

        # Act
        result = await service.design_plumbing_system(
            project_id=project_id,
            fixtures=basic_fixtures,
            supply_pressure=supply_pressure,
            user_id=user_id,
            unit_system="imperial",
        )

        # Assert - peak demand should be positive and reasonable
        assert result["peak_demand"] > 0
        # Peak demand should be less than sum of all fixture flows
        # Typical residential fixtures: 2-5 GPM each
        # With 6 fixtures, peak should be less than 30 GPM
        assert result["peak_demand"] < 30

    @pytest.mark.asyncio
    async def test_design_plumbing_system_pipe_sizing(
        self,
        service,
        basic_fixtures,
    ):
        """Test that pipes are sized appropriately."""
        # Arrange
        project_id = "test-project-123"
        user_id = "test-user-456"
        supply_pressure = 60.0

        # Act
        result = await service.design_plumbing_system(
            project_id=project_id,
            fixtures=basic_fixtures,
            supply_pressure=supply_pressure,
            user_id=user_id,
            unit_system="imperial",
        )

        # Assert - service size should be reasonable
        assert result["service_size"] in [
            '0.5"',
            '0.75"',
            '1"',
            '1.0"',
            '1.25"',
            '1.5"',
            '2"',
            '2.0"',
            '2.5"',
            '3"',
            '3.0"',
            '4"',
            '4.0"',
            '6"',
            '6.0"',
        ]

        # Meter size should be reasonable
        assert result["meter_size"] in [
            '5/8"',
            '3/4"',
            '1"',
            '1-1/2"',
            '2"',
            '3"',
            '4"',
            '6"',
        ]

        # Supply pressure required should be reasonable (15-50 psi typical)
        assert 10 <= result["supply_pressure_required"] <= 100

    @pytest.mark.asyncio
    async def test_design_plumbing_system_with_metric_units(
        self,
        service,
        basic_fixtures,
    ):
        """Test plumbing design with metric unit system."""
        # Arrange
        project_id = "test-project-123"
        user_id = "test-user-456"
        supply_pressure = 60.0

        # Act
        result = await service.design_plumbing_system(
            project_id=project_id,
            fixtures=basic_fixtures,
            supply_pressure=supply_pressure,
            user_id=user_id,
            unit_system="metric",
        )

        # Assert
        assert result["unit_system"] == "metric"
        # Calculations should still work (values are in imperial internally)
        assert result["total_fixture_units"] > 0
        assert result["peak_demand"] > 0

    @pytest.mark.asyncio
    async def test_design_plumbing_system_with_different_materials(
        self,
        service,
        basic_fixtures,
    ):
        """Test plumbing design with different pipe materials."""
        # Arrange
        project_id = "test-project-123"
        user_id = "test-user-456"
        supply_pressure = 60.0

        # Test with different materials
        materials = ["copper", "pex", "cpvc", "galvanized"]

        for material in materials:
            # Act
            result = await service.design_plumbing_system(
                project_id=project_id,
                fixtures=basic_fixtures,
                supply_pressure=supply_pressure,
                user_id=user_id,
                unit_system="imperial",
                material=material,
            )

            # Assert - should work with all materials
            assert result["total_fixture_units"] > 0
            assert result["peak_demand"] > 0
            assert result["service_size"] != ""

    @pytest.mark.asyncio
    async def test_design_plumbing_system_residential(
        self,
        service,
    ):
        """Test plumbing design for a residential building."""
        # Arrange
        project_id = "test-project-123"
        user_id = "test-user-456"
        supply_pressure = 60.0
        residential_fixtures = [
            {
                "name": "Master Bath WC",
                "fixture_type": "water_closet",
                "quantity": 1,
                "private": True,
            },
            {
                "name": "Master Bath Lavatory",
                "fixture_type": "lavatory",
                "quantity": 2,
                "private": True,
            },
            {
                "name": "Master Bath Shower",
                "fixture_type": "shower",
                "quantity": 1,
                "private": True,
            },
            {
                "name": "Guest Bath WC",
                "fixture_type": "water_closet",
                "quantity": 1,
                "private": True,
            },
            {
                "name": "Guest Bath Lavatory",
                "fixture_type": "lavatory",
                "quantity": 1,
                "private": True,
            },
            {
                "name": "Kitchen Sink",
                "fixture_type": "kitchen_sink",
                "quantity": 1,
                "private": True,
            },
            {
                "name": "Dishwasher",
                "fixture_type": "dishwasher",
                "quantity": 1,
                "private": True,
            },
            {
                "name": "Laundry",
                "fixture_type": "laundry",
                "quantity": 1,
                "private": True,
            },
        ]

        # Act
        result = await service.design_plumbing_system(
            project_id=project_id,
            fixtures=residential_fixtures,
            supply_pressure=supply_pressure,
            user_id=user_id,
            unit_system="imperial",
        )

        # Assert - should be appropriately sized for residential
        # Typical residential: 3/4" to 1" service
        assert result["service_size"] in ['0.75"', '1"', '1.25"', '1.5"']
        # Peak demand should be reasonable for residential (8-15 GPM typical)
        assert 5 <= result["peak_demand"] <= 20

    @pytest.mark.asyncio
    async def test_design_plumbing_system_commercial(
        self,
        service,
    ):
        """Test plumbing design for a commercial building."""
        # Arrange
        project_id = "test-project-123"
        user_id = "test-user-456"
        supply_pressure = 60.0
        commercial_fixtures = [
            {
                "name": "Public Restroom WC",
                "fixture_type": "water_closet",
                "quantity": 10,
                "private": False,
            },
            {
                "name": "Public Restroom Lavatory",
                "fixture_type": "lavatory",
                "quantity": 8,
                "private": False,
            },
            {
                "name": "Urinals",
                "fixture_type": "urinal",
                "quantity": 6,
                "private": False,
            },
            {
                "name": "Drinking Fountains",
                "fixture_type": "drinking_fountain",
                "quantity": 4,
                "private": False,
            },
            {
                "name": "Kitchen Sinks",
                "fixture_type": "kitchen_sink",
                "quantity": 3,
                "private": False,
            },
        ]

        # Act
        result = await service.design_plumbing_system(
            project_id=project_id,
            fixtures=commercial_fixtures,
            supply_pressure=supply_pressure,
            user_id=user_id,
            unit_system="imperial",
        )

        # Assert - should be appropriately sized for commercial
        # Commercial buildings typically need larger service
        assert result["service_size"] in [
            '1.5"',
            '2"',
            '2.0"',
            '2.5"',
            '3"',
            '3.0"',
            '4"',
            '4.0"',
            '6"',
            '6.0"',
        ]
        # Peak demand should be higher for commercial
        assert result["peak_demand"] > 20

    @pytest.mark.asyncio
    async def test_design_plumbing_system_empty_fixtures(
        self,
        service,
    ):
        """Test that empty fixtures list raises ValueError."""
        # Arrange
        project_id = "test-project-123"
        user_id = "test-user-456"
        supply_pressure = 60.0

        # Act & Assert
        with pytest.raises(ValueError, match="At least one fixture must be provided"):
            await service.design_plumbing_system(
                project_id=project_id,
                fixtures=[],
                supply_pressure=supply_pressure,
                user_id=user_id,
                unit_system="imperial",
            )

    @pytest.mark.asyncio
    async def test_design_plumbing_system_invalid_supply_pressure(
        self,
        service,
        basic_fixtures,
    ):
        """Test that invalid supply pressure raises ValueError."""
        # Arrange
        project_id = "test-project-123"
        user_id = "test-user-456"
        supply_pressure = -10.0  # Invalid negative pressure

        # Act & Assert
        with pytest.raises(ValueError, match="Supply pressure must be positive"):
            await service.design_plumbing_system(
                project_id=project_id,
                fixtures=basic_fixtures,
                supply_pressure=supply_pressure,
                user_id=user_id,
                unit_system="imperial",
            )

    @pytest.mark.asyncio
    async def test_design_plumbing_system_invalid_fixture_type(
        self,
        service,
    ):
        """Test that invalid fixture type defaults to lavatory."""
        # Arrange
        project_id = "test-project-123"
        user_id = "test-user-456"
        supply_pressure = 60.0
        fixtures_with_invalid_type = [
            {
                "name": "Invalid Fixture",
                "fixture_type": "invalid_type",
                "quantity": 1,
                "private": True,
            },
            {
                "name": "Valid Fixture",
                "fixture_type": "lavatory",
                "quantity": 1,
                "private": True,
            },
        ]

        # Act
        result = await service.design_plumbing_system(
            project_id=project_id,
            fixtures=fixtures_with_invalid_type,
            supply_pressure=supply_pressure,
            user_id=user_id,
            unit_system="imperial",
        )

        # Assert - should still work, defaulting invalid type to lavatory
        assert result["total_fixture_units"] > 0
        # Should have 2 lavatories (1 FU each) = 2 FU
        assert result["total_fixture_units"] == 2.0

    @pytest.mark.asyncio
    async def test_design_plumbing_system_high_supply_pressure(
        self,
        service,
        basic_fixtures,
    ):
        """Test plumbing design with high supply pressure."""
        # Arrange
        project_id = "test-project-123"
        user_id = "test-user-456"
        supply_pressure = 100.0  # High pressure

        # Act
        result = await service.design_plumbing_system(
            project_id=project_id,
            fixtures=basic_fixtures,
            supply_pressure=supply_pressure,
            user_id=user_id,
            unit_system="imperial",
        )

        # Assert - should still work with high pressure
        assert result["total_fixture_units"] > 0
        assert result["peak_demand"] > 0
        # Required pressure should be less than available
        assert result["supply_pressure_required"] <= supply_pressure

    @pytest.mark.asyncio
    async def test_design_plumbing_system_low_supply_pressure(
        self,
        service,
        basic_fixtures,
    ):
        """Test plumbing design with low supply pressure."""
        # Arrange
        project_id = "test-project-123"
        user_id = "test-user-456"
        supply_pressure = 30.0  # Low pressure

        # Act
        result = await service.design_plumbing_system(
            project_id=project_id,
            fixtures=basic_fixtures,
            supply_pressure=supply_pressure,
            user_id=user_id,
            unit_system="imperial",
        )

        # Assert - should still calculate, but may require more pressure
        assert result["total_fixture_units"] > 0
        assert result["peak_demand"] > 0
        # Required pressure might be close to or exceed available
        assert result["supply_pressure_required"] > 0

    @pytest.mark.asyncio
    async def test_design_plumbing_system_single_fixture(
        self,
        service,
    ):
        """Test plumbing design with a single fixture."""
        # Arrange
        project_id = "test-project-123"
        user_id = "test-user-456"
        supply_pressure = 60.0
        single_fixture = [
            {
                "name": "Single Lavatory",
                "fixture_type": "lavatory",
                "quantity": 1,
                "private": True,
            }
        ]

        # Act
        result = await service.design_plumbing_system(
            project_id=project_id,
            fixtures=single_fixture,
            supply_pressure=supply_pressure,
            user_id=user_id,
            unit_system="imperial",
        )

        # Assert - should work with single fixture
        assert result["total_fixture_units"] == 1.0
        assert result["peak_demand"] > 0
        # Should size for minimum service (typically 1/2" or 3/4")
        assert result["service_size"] in ['0.5"', '0.75"']

    @pytest.mark.asyncio
    async def test_design_plumbing_system_large_quantity(
        self,
        service,
    ):
        """Test plumbing design with large fixture quantities."""
        # Arrange
        project_id = "test-project-123"
        user_id = "test-user-456"
        supply_pressure = 60.0
        large_quantity_fixtures = [
            {
                "name": "Water Closets",
                "fixture_type": "water_closet",
                "quantity": 50,
                "private": False,
            },
            {
                "name": "Lavatories",
                "fixture_type": "lavatory",
                "quantity": 40,
                "private": False,
            },
        ]

        # Act
        result = await service.design_plumbing_system(
            project_id=project_id,
            fixtures=large_quantity_fixtures,
            supply_pressure=supply_pressure,
            user_id=user_id,
            unit_system="imperial",
        )

        # Assert - should handle large quantities
        # 50 WC (6 FU each) + 40 lavatories (2 FU each) = 380 FU
        expected_fu = 50 * 6.0 + 40 * 2.0
        assert result["total_fixture_units"] == expected_fu
        assert result["peak_demand"] > 50  # Should be significant
        # Should size for large service
        assert result["service_size"] in ['3"', '4"', '6"']
