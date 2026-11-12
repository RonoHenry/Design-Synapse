"""Unit tests for StructuralCalculationService."""

from datetime import datetime
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest
from src.calculations.load_calculator import (BuildingData, Component,
                                              LoadCalculator, OccupancyType,
                                              SeismicData, SeismicLoadResult,
                                              WindLoadResult)
from src.models.calculation_sheet import CalculationSheet
from src.repositories.calculation_sheet_repository import \
    CalculationSheetRepository
from src.repositories.structural_design_repository import \
    StructuralDesignRepository
from src.services.structural_calculation_service import (
    LoadCalculationResult, StructuralCalculationService)


class TestStructuralCalculationServiceCalculateLoads:
    """Test calculate_loads method of StructuralCalculationService."""

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
        repo.create = AsyncMock()
        return repo

    @pytest.fixture
    def mock_structural_design_repo(self):
        """Create a mock structural design repository."""
        repo = AsyncMock(spec=StructuralDesignRepository)
        repo.create = AsyncMock()
        return repo

    @pytest.fixture
    def service(
        self, mock_db_session, mock_calculation_sheet_repo, mock_structural_design_repo
    ):
        """Create a StructuralCalculationService instance with mocked dependencies."""
        return StructuralCalculationService(
            db_session=mock_db_session,
            calculation_sheet_repo=mock_calculation_sheet_repo,
            structural_design_repo=mock_structural_design_repo,
        )

    @pytest.fixture
    def basic_building_data(self) -> Dict[str, Any]:
        """Create basic building data for testing."""
        return {
            "height": 30.0,
            "width": 50.0,
            "length": 100.0,
            "exposure_category": "C",
            "occupancy": "office",
            "floor_area": 5000.0,
        }

    @pytest.mark.asyncio
    async def test_calculate_loads_dead_and_live_only(
        self, service, basic_building_data, mock_calculation_sheet_repo, mock_db_session
    ):
        """Test calculating only dead and live loads."""
        # Arrange
        project_id = "test-project-123"
        user_id = "test-user-456"
        load_types = ["dead", "live"]

        building_data = basic_building_data.copy()
        building_data["components"] = [
            {"name": "Concrete Slab", "weight_per_area": 150.0, "area": 5000.0},
            {"name": "Roofing", "weight_per_area": 10.0, "area": 5000.0},
        ]

        # Act
        result = await service.calculate_loads(
            project_id=project_id,
            building_data=building_data,
            load_types=load_types,
            user_id=user_id,
            unit_system="imperial",
        )

        # Assert
        assert isinstance(result, LoadCalculationResult)
        assert result.project_id == project_id
        assert result.dead_load == 800000.0  # (150 + 10) * 5000
        assert result.live_load == 250000.0  # 50 psf * 5000 sf (office)
        assert result.wind_load is None
        assert result.seismic_load is None
        assert result.total_load == 1050000.0
        assert result.unit_system == "imperial"

        # Verify calculation sheet was created and saved
        mock_calculation_sheet_repo.create.assert_called_once()
        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_calculate_loads_all_load_types(
        self, service, basic_building_data, mock_calculation_sheet_repo, mock_db_session
    ):
        """Test calculating all load types (dead, live, wind, seismic)."""
        # Arrange
        project_id = "test-project-123"
        user_id = "test-user-456"
        load_types = ["dead", "live", "wind", "seismic"]

        building_data = basic_building_data.copy()
        building_data["components"] = [
            {"name": "Concrete Slab", "weight_per_area": 150.0, "area": 5000.0},
        ]
        building_data["wind_speed"] = 115.0
        building_data["seismic"] = {
            "ss": 1.5,
            "s1": 0.6,
            "site_class": "D",
            "importance_factor": 1.0,
            "response_modification_factor": 8.0,
        }

        # Act
        result = await service.calculate_loads(
            project_id=project_id,
            building_data=building_data,
            load_types=load_types,
            user_id=user_id,
            unit_system="imperial",
        )

        # Assert
        assert isinstance(result, LoadCalculationResult)
        assert result.project_id == project_id
        assert result.dead_load == 750000.0  # 150 * 5000
        assert result.live_load == 250000.0  # 50 psf * 5000 sf (office)
        assert result.wind_load is not None
        assert result.wind_load > 0
        assert result.seismic_load is not None
        assert result.seismic_load > 0
        assert result.total_load > 0
        assert result.unit_system == "imperial"

        # Verify calculation sheet was created and saved
        mock_calculation_sheet_repo.create.assert_called_once()
        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_calculate_loads_wind_only(
        self, service, basic_building_data, mock_calculation_sheet_repo, mock_db_session
    ):
        """Test calculating only wind loads."""
        # Arrange
        project_id = "test-project-123"
        user_id = "test-user-456"
        load_types = ["wind"]

        building_data = basic_building_data.copy()
        building_data["wind_speed"] = 115.0

        # Act
        result = await service.calculate_loads(
            project_id=project_id,
            building_data=building_data,
            load_types=load_types,
            user_id=user_id,
            unit_system="imperial",
        )

        # Assert
        assert isinstance(result, LoadCalculationResult)
        assert result.dead_load == 0.0
        assert result.live_load == 0.0
        assert result.wind_load is not None
        assert result.wind_load > 0
        assert result.seismic_load is None

        # Verify calculation sheet was created and saved
        mock_calculation_sheet_repo.create.assert_called_once()
        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_calculate_loads_seismic_only(
        self, service, basic_building_data, mock_calculation_sheet_repo, mock_db_session
    ):
        """Test calculating only seismic loads."""
        # Arrange
        project_id = "test-project-123"
        user_id = "test-user-456"
        load_types = ["seismic"]

        building_data = basic_building_data.copy()
        building_data["seismic"] = {
            "ss": 1.5,
            "s1": 0.6,
            "site_class": "D",
            "importance_factor": 1.0,
            "response_modification_factor": 8.0,
        }

        # Act
        result = await service.calculate_loads(
            project_id=project_id,
            building_data=building_data,
            load_types=load_types,
            user_id=user_id,
            unit_system="imperial",
        )

        # Assert
        assert isinstance(result, LoadCalculationResult)
        assert result.dead_load == 0.0
        assert result.live_load == 0.0
        assert result.wind_load is None
        assert result.seismic_load is not None
        assert result.seismic_load > 0

        # Verify calculation sheet was created and saved
        mock_calculation_sheet_repo.create.assert_called_once()
        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_calculate_loads_metric_units(
        self, service, basic_building_data, mock_calculation_sheet_repo, mock_db_session
    ):
        """Test calculating loads with metric unit system."""
        # Arrange
        project_id = "test-project-123"
        user_id = "test-user-456"
        load_types = ["dead", "live"]

        building_data = basic_building_data.copy()
        building_data["components"] = [
            {"name": "Concrete Slab", "weight_per_area": 150.0, "area": 5000.0},
        ]

        # Act
        result = await service.calculate_loads(
            project_id=project_id,
            building_data=building_data,
            load_types=load_types,
            user_id=user_id,
            unit_system="metric",
        )

        # Assert
        assert isinstance(result, LoadCalculationResult)
        assert result.unit_system == "metric"
        assert result.dead_load > 0
        assert result.live_load > 0

        # Verify calculation sheet was created with metric units
        mock_calculation_sheet_repo.create.assert_called_once()
        call_args = mock_calculation_sheet_repo.create.call_args
        calculation_sheet = call_args[0][0]
        assert calculation_sheet.units == "metric"

    @pytest.mark.asyncio
    async def test_calculate_loads_no_components_defaults_to_zero(
        self, service, basic_building_data, mock_calculation_sheet_repo, mock_db_session
    ):
        """Test that dead load defaults to zero when no components provided."""
        # Arrange
        project_id = "test-project-123"
        user_id = "test-user-456"
        load_types = ["dead"]

        building_data = basic_building_data.copy()
        # No components provided

        # Act
        result = await service.calculate_loads(
            project_id=project_id,
            building_data=building_data,
            load_types=load_types,
            user_id=user_id,
            unit_system="imperial",
        )

        # Assert
        assert result.dead_load == 0.0

    @pytest.mark.asyncio
    async def test_calculate_loads_uses_default_wind_speed(
        self, service, basic_building_data, mock_calculation_sheet_repo, mock_db_session
    ):
        """Test that default wind speed is used when not provided."""
        # Arrange
        project_id = "test-project-123"
        user_id = "test-user-456"
        load_types = ["wind"]

        building_data = basic_building_data.copy()
        # No wind_speed provided, should use default 90.0 mph

        # Act
        result = await service.calculate_loads(
            project_id=project_id,
            building_data=building_data,
            load_types=load_types,
            user_id=user_id,
            unit_system="imperial",
        )

        # Assert
        assert result.wind_load is not None
        assert result.wind_load > 0

    @pytest.mark.asyncio
    async def test_calculate_loads_calculation_sheet_has_correct_structure(
        self, service, basic_building_data, mock_calculation_sheet_repo, mock_db_session
    ):
        """Test that the created calculation sheet has the correct structure."""
        # Arrange
        project_id = "test-project-123"
        user_id = "test-user-456"
        load_types = ["dead", "live"]

        building_data = basic_building_data.copy()
        building_data["components"] = [
            {"name": "Concrete Slab", "weight_per_area": 150.0, "area": 5000.0},
        ]

        # Act
        await service.calculate_loads(
            project_id=project_id,
            building_data=building_data,
            load_types=load_types,
            user_id=user_id,
            unit_system="imperial",
        )

        # Assert
        mock_calculation_sheet_repo.create.assert_called_once()
        call_args = mock_calculation_sheet_repo.create.call_args
        calculation_sheet = call_args[0][0]

        assert isinstance(calculation_sheet, CalculationSheet)
        assert calculation_sheet.project_id == project_id
        assert calculation_sheet.calculation_type == "structural_loads"
        assert calculation_sheet.created_by == user_id
        assert calculation_sheet.status == "approved"
        assert calculation_sheet.units == "imperial"
        assert "building_data" in calculation_sheet.inputs
        assert "load_types" in calculation_sheet.inputs
        assert "dead_load" in calculation_sheet.outputs
        assert "live_load" in calculation_sheet.outputs
        assert "total_load" in calculation_sheet.outputs
        assert len(calculation_sheet.formulas) > 0
        assert "ASCE 7-16" in calculation_sheet.references

    @pytest.mark.asyncio
    async def test_calculate_loads_different_occupancy_types(
        self, service, basic_building_data, mock_calculation_sheet_repo, mock_db_session
    ):
        """Test calculating live loads for different occupancy types."""
        # Arrange
        project_id = "test-project-123"
        user_id = "test-user-456"
        load_types = ["live"]

        # Test residential (40 psf)
        building_data_residential = basic_building_data.copy()
        building_data_residential["occupancy"] = "residential"
        building_data_residential["floor_area"] = 1000.0

        result_residential = await service.calculate_loads(
            project_id=project_id,
            building_data=building_data_residential,
            load_types=load_types,
            user_id=user_id,
            unit_system="imperial",
        )

        assert result_residential.live_load == 40000.0  # 40 psf * 1000 sf

        # Test retail (100 psf)
        building_data_retail = basic_building_data.copy()
        building_data_retail["occupancy"] = "retail"
        building_data_retail["floor_area"] = 1000.0

        result_retail = await service.calculate_loads(
            project_id=project_id,
            building_data=building_data_retail,
            load_types=load_types,
            user_id=user_id,
            unit_system="imperial",
        )

        assert result_retail.live_load == 100000.0  # 100 psf * 1000 sf

    @pytest.mark.asyncio
    async def test_calculate_loads_total_load_calculation(
        self, service, basic_building_data, mock_calculation_sheet_repo, mock_db_session
    ):
        """Test that total load is correctly calculated from all load components."""
        # Arrange
        project_id = "test-project-123"
        user_id = "test-user-456"
        load_types = ["dead", "live", "wind", "seismic"]

        building_data = basic_building_data.copy()
        building_data["components"] = [
            {"name": "Concrete Slab", "weight_per_area": 100.0, "area": 1000.0},
        ]
        building_data["wind_speed"] = 115.0
        building_data["seismic"] = {
            "ss": 1.5,
            "s1": 0.6,
            "site_class": "D",
            "importance_factor": 1.0,
            "response_modification_factor": 8.0,
        }

        # Act
        result = await service.calculate_loads(
            project_id=project_id,
            building_data=building_data,
            load_types=load_types,
            user_id=user_id,
            unit_system="imperial",
        )

        # Assert
        expected_total = (
            result.dead_load
            + result.live_load
            + (result.wind_load or 0)
            + (result.seismic_load or 0)
        )
        assert result.total_load == expected_total

    @pytest.mark.asyncio
    async def test_calculate_loads_empty_load_types(
        self, service, basic_building_data, mock_calculation_sheet_repo, mock_db_session
    ):
        """Test calculating loads with empty load types list."""
        # Arrange
        project_id = "test-project-123"
        user_id = "test-user-456"
        load_types = []

        building_data = basic_building_data.copy()

        # Act
        result = await service.calculate_loads(
            project_id=project_id,
            building_data=building_data,
            load_types=load_types,
            user_id=user_id,
            unit_system="imperial",
        )

        # Assert
        assert result.dead_load == 0.0
        assert result.live_load == 0.0
        assert result.wind_load is None
        assert result.seismic_load is None
        assert result.total_load == 0.0

    @pytest.mark.asyncio
    async def test_calculate_loads_uses_floor_area_from_building_data(
        self, service, basic_building_data, mock_calculation_sheet_repo, mock_db_session
    ):
        """Test that floor_area from building_data is used for live load calculation."""
        # Arrange
        project_id = "test-project-123"
        user_id = "test-user-456"
        load_types = ["live"]

        building_data = basic_building_data.copy()
        building_data["floor_area"] = 2000.0
        building_data["occupancy"] = "office"

        # Act
        result = await service.calculate_loads(
            project_id=project_id,
            building_data=building_data,
            load_types=load_types,
            user_id=user_id,
            unit_system="imperial",
        )

        # Assert
        assert result.live_load == 100000.0  # 50 psf * 2000 sf

    @pytest.mark.asyncio
    async def test_calculate_loads_calculates_floor_area_when_not_provided(
        self, service, basic_building_data, mock_calculation_sheet_repo, mock_db_session
    ):
        """Test that floor area is calculated from width * length when not provided."""
        # Arrange
        project_id = "test-project-123"
        user_id = "test-user-456"
        load_types = ["live"]

        building_data = basic_building_data.copy()
        building_data.pop("floor_area", None)  # Remove floor_area
        building_data["width"] = 50.0
        building_data["length"] = 100.0
        building_data["occupancy"] = "office"

        # Act
        result = await service.calculate_loads(
            project_id=project_id,
            building_data=building_data,
            load_types=load_types,
            user_id=user_id,
            unit_system="imperial",
        )

        # Assert
        # floor_area = 50 * 100 = 5000 sf
        # live_load = 50 psf * 5000 sf = 250000 lbs
        assert result.live_load == 250000.0

    @pytest.mark.asyncio
    async def test_calculate_loads_returns_calculation_id(
        self, service, basic_building_data, mock_calculation_sheet_repo, mock_db_session
    ):
        """Test that calculate_loads returns a valid calculation_id."""
        # Arrange
        project_id = "test-project-123"
        user_id = "test-user-456"
        load_types = ["dead"]

        building_data = basic_building_data.copy()
        building_data["components"] = [
            {"name": "Concrete Slab", "weight_per_area": 150.0, "area": 1000.0},
        ]

        # Act
        result = await service.calculate_loads(
            project_id=project_id,
            building_data=building_data,
            load_types=load_types,
            user_id=user_id,
            unit_system="imperial",
        )

        # Assert
        assert result.calculation_id is not None
        assert isinstance(result.calculation_id, UUID)

    @pytest.mark.asyncio
    async def test_calculate_loads_has_created_at_timestamp(
        self, service, basic_building_data, mock_calculation_sheet_repo, mock_db_session
    ):
        """Test that calculate_loads result has a created_at timestamp."""
        # Arrange
        project_id = "test-project-123"
        user_id = "test-user-456"
        load_types = ["dead"]

        building_data = basic_building_data.copy()
        building_data["components"] = [
            {"name": "Concrete Slab", "weight_per_area": 150.0, "area": 1000.0},
        ]

        # Act
        result = await service.calculate_loads(
            project_id=project_id,
            building_data=building_data,
            load_types=load_types,
            user_id=user_id,
            unit_system="imperial",
        )

        # Assert
        assert result.created_at is not None
        assert isinstance(result.created_at, datetime)


class TestStructuralCalculationServiceDesignBeam:
    """Test design_beam method of StructuralCalculationService."""

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
        repo.create = AsyncMock()
        return repo

    @pytest.fixture
    def mock_structural_design_repo(self):
        """Create a mock structural design repository."""
        repo = AsyncMock(spec=StructuralDesignRepository)
        repo.create = AsyncMock()
        return repo

    @pytest.fixture
    def service(
        self, mock_db_session, mock_calculation_sheet_repo, mock_structural_design_repo
    ):
        """Create service instance with mocked dependencies."""
        return StructuralCalculationService(
            db_session=mock_db_session,
            calculation_sheet_repo=mock_calculation_sheet_repo,
            structural_design_repo=mock_structural_design_repo,
        )

    @pytest.fixture
    def basic_beam_loads(self):
        """Create basic beam loads for testing."""
        return {
            "uniform_load": 1000.0,  # lb/ft
            "point_loads": [],
            "moment_loads": [],
        }

    @pytest.fixture
    def basic_material(self):
        """Create basic material properties for testing."""
        return {
            "material_type": "steel",
            "yield_strength": 36000.0,  # psi
            "elastic_modulus": 29000000.0,  # psi
            "density": 490.0,  # lb/ft³
            "allowable_stress_factor": 0.6,
        }

    @pytest.mark.asyncio
    async def test_design_beam_with_valid_inputs(
        self,
        service,
        basic_beam_loads,
        basic_material,
        mock_calculation_sheet_repo,
        mock_structural_design_repo,
        mock_db_session,
    ):
        """Test beam design with valid inputs."""
        # Arrange
        project_id = "test-project-123"
        user_id = "test-user-456"
        span = 20.0  # feet

        # Act
        result = await service.design_beam(
            project_id=project_id,
            loads=basic_beam_loads,
            span=span,
            material=basic_material,
            user_id=user_id,
            unit_system="imperial",
        )

        # Assert
        from src.calculations.beam_designer import BeamDesignResult

        assert isinstance(result, BeamDesignResult)
        assert result.max_moment > 0
        assert result.max_shear > 0
        assert result.geometry is not None

        # Verify calculation sheet was created
        mock_calculation_sheet_repo.create.assert_called_once()
        calc_sheet_call = mock_calculation_sheet_repo.create.call_args[0][0]
        assert calc_sheet_call.project_id == project_id
        assert calc_sheet_call.calculation_type == "beam_design"
        assert calc_sheet_call.created_by == user_id

        # Verify structural design was created
        mock_structural_design_repo.create.assert_called_once()
        design_call = mock_structural_design_repo.create.call_args[0][0]
        assert design_call.project_id == project_id
        assert design_call.design_type == "beam"
        assert design_call.created_by == user_id

        # Verify database commit
        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_design_beam_with_point_loads(
        self,
        service,
        basic_material,
        mock_calculation_sheet_repo,
        mock_structural_design_repo,
        mock_db_session,
    ):
        """Test beam design with point loads."""
        # Arrange
        project_id = "test-project-123"
        user_id = "test-user-456"
        span = 20.0
        loads = {
            "uniform_load": 500.0,
            "point_loads": [(5000.0, 10.0), (3000.0, 15.0)],
            "moment_loads": [],
        }

        # Act
        result = await service.design_beam(
            project_id=project_id,
            loads=loads,
            span=span,
            material=basic_material,
            user_id=user_id,
        )

        # Assert
        from src.calculations.beam_designer import BeamDesignResult

        assert isinstance(result, BeamDesignResult)
        assert result.max_moment > 0
        assert result.max_shear > 0

        # Verify repos were called
        mock_calculation_sheet_repo.create.assert_called_once()
        mock_structural_design_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_design_beam_with_trial_geometry(
        self,
        service,
        basic_beam_loads,
        basic_material,
        mock_calculation_sheet_repo,
        mock_structural_design_repo,
        mock_db_session,
    ):
        """Test beam design with trial geometry provided."""
        # Arrange
        project_id = "test-project-123"
        user_id = "test-user-456"
        span = 20.0
        trial_geometry = {
            "depth": 12.0,
            "width": 6.0,
            "web_thickness": None,
            "flange_thickness": None,
        }

        # Act
        result = await service.design_beam(
            project_id=project_id,
            loads=basic_beam_loads,
            span=span,
            material=basic_material,
            user_id=user_id,
            trial_geometry=trial_geometry,
        )

        # Assert
        from src.calculations.beam_designer import BeamDesignResult

        assert isinstance(result, BeamDesignResult)
        assert result.geometry.depth == 12.0
        assert result.geometry.width == 6.0

    @pytest.mark.asyncio
    async def test_design_beam_different_support_types(
        self,
        service,
        basic_beam_loads,
        basic_material,
        mock_calculation_sheet_repo,
        mock_structural_design_repo,
        mock_db_session,
    ):
        """Test beam design with different support types."""
        project_id = "test-project-123"
        user_id = "test-user-456"
        span = 20.0

        support_types = [
            "simply_supported",
            "cantilever",
            "fixed_fixed",
            "fixed_pinned",
        ]

        for support_type in support_types:
            # Reset mocks
            mock_calculation_sheet_repo.reset_mock()
            mock_structural_design_repo.reset_mock()
            mock_db_session.reset_mock()

            # Act
            result = await service.design_beam(
                project_id=project_id,
                loads=basic_beam_loads,
                span=span,
                material=basic_material,
                user_id=user_id,
                support_type=support_type,
            )

            # Assert
            from src.calculations.beam_designer import BeamDesignResult

            assert isinstance(result, BeamDesignResult)
            mock_calculation_sheet_repo.create.assert_called_once()
            mock_structural_design_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_design_beam_different_materials(
        self,
        service,
        basic_beam_loads,
        mock_calculation_sheet_repo,
        mock_structural_design_repo,
        mock_db_session,
    ):
        """Test beam design with different material types."""
        project_id = "test-project-123"
        user_id = "test-user-456"
        span = 20.0

        materials = [
            {
                "material_type": "steel",
                "yield_strength": 36000.0,
                "elastic_modulus": 29000000.0,
                "density": 490.0,
            },
            {
                "material_type": "concrete",
                "yield_strength": 4000.0,
                "elastic_modulus": 3600000.0,
                "density": 150.0,
            },
            {
                "material_type": "timber",
                "yield_strength": 1200.0,
                "elastic_modulus": 1600000.0,
                "density": 35.0,
            },
        ]

        for material in materials:
            # Reset mocks
            mock_calculation_sheet_repo.reset_mock()
            mock_structural_design_repo.reset_mock()
            mock_db_session.reset_mock()

            # Act
            result = await service.design_beam(
                project_id=project_id,
                loads=basic_beam_loads,
                span=span,
                material=material,
                user_id=user_id,
            )

            # Assert
            from src.calculations.beam_designer import BeamDesignResult

            assert isinstance(result, BeamDesignResult)

    @pytest.mark.asyncio
    async def test_design_beam_metric_units(
        self,
        service,
        basic_beam_loads,
        basic_material,
        mock_calculation_sheet_repo,
        mock_structural_design_repo,
        mock_db_session,
    ):
        """Test beam design with metric unit system."""
        # Arrange
        project_id = "test-project-123"
        user_id = "test-user-456"
        span = 6.0  # meters (converted to feet internally)

        # Act
        result = await service.design_beam(
            project_id=project_id,
            loads=basic_beam_loads,
            span=span,
            material=basic_material,
            user_id=user_id,
            unit_system="metric",
        )

        # Assert
        from src.calculations.beam_designer import BeamDesignResult

        assert isinstance(result, BeamDesignResult)

        # Verify calculation sheet has metric units
        calc_sheet_call = mock_calculation_sheet_repo.create.call_args[0][0]
        assert calc_sheet_call.units == "metric"

        # Verify structural design has metric units
        design_call = mock_structural_design_repo.create.call_args[0][0]
        assert design_call.units == "metric"

    @pytest.mark.asyncio
    async def test_design_beam_calculation_sheet_structure(
        self,
        service,
        basic_beam_loads,
        basic_material,
        mock_calculation_sheet_repo,
        mock_structural_design_repo,
        mock_db_session,
    ):
        """Test that calculation sheet has correct structure."""
        # Arrange
        project_id = "test-project-123"
        user_id = "test-user-456"
        span = 20.0

        # Act
        await service.design_beam(
            project_id=project_id,
            loads=basic_beam_loads,
            span=span,
            material=basic_material,
            user_id=user_id,
        )

        # Assert
        calc_sheet = mock_calculation_sheet_repo.create.call_args[0][0]
        assert calc_sheet.project_id == project_id
        assert calc_sheet.calculation_type == "beam_design"
        assert calc_sheet.created_by == user_id
        assert calc_sheet.status == "approved"

        # Check inputs
        assert "span" in calc_sheet.inputs
        assert "loads" in calc_sheet.inputs
        assert "material" in calc_sheet.inputs
        assert "support_type" in calc_sheet.inputs

        # Check outputs
        assert "is_adequate" in calc_sheet.outputs
        assert "max_moment" in calc_sheet.outputs
        assert "max_shear" in calc_sheet.outputs
        assert "max_stress" in calc_sheet.outputs
        assert "stress_ratio" in calc_sheet.outputs
        assert "deflection_ratio" in calc_sheet.outputs

        # Check formulas and references
        assert len(calc_sheet.formulas) > 0
        assert len(calc_sheet.references) > 0

    @pytest.mark.asyncio
    async def test_design_beam_structural_design_structure(
        self,
        service,
        basic_beam_loads,
        basic_material,
        mock_calculation_sheet_repo,
        mock_structural_design_repo,
        mock_db_session,
    ):
        """Test that structural design record has correct structure."""
        # Arrange
        project_id = "test-project-123"
        user_id = "test-user-456"
        span = 20.0

        # Act
        await service.design_beam(
            project_id=project_id,
            loads=basic_beam_loads,
            span=span,
            material=basic_material,
            user_id=user_id,
        )

        # Assert
        design = mock_structural_design_repo.create.call_args[0][0]
        assert design.project_id == project_id
        assert design.design_type == "beam"
        assert design.created_by == user_id
        assert design.status == "draft"

        # Check loads, material_properties, geometry
        assert design.loads == basic_beam_loads
        assert design.material_properties == basic_material
        assert "depth" in design.geometry
        assert "width" in design.geometry
        assert "span" in design.geometry

        # Check design_results
        assert "is_adequate" in design.design_results
        assert "max_moment" in design.design_results
        assert "max_stress" in design.design_results

        # Check stress_ratios
        assert "stress_ratio" in design.stress_ratios
        assert "deflection_ratio" in design.stress_ratios
        assert "utilization_ratio" in design.stress_ratios

    @pytest.mark.asyncio
    async def test_design_beam_links_calculation_sheet_to_design(
        self,
        service,
        basic_beam_loads,
        basic_material,
        mock_calculation_sheet_repo,
        mock_structural_design_repo,
        mock_db_session,
    ):
        """Test that structural design is linked to calculation sheet."""
        # Arrange
        project_id = "test-project-123"
        user_id = "test-user-456"
        span = 20.0

        # Act
        await service.design_beam(
            project_id=project_id,
            loads=basic_beam_loads,
            span=span,
            material=basic_material,
            user_id=user_id,
        )

        # Assert
        calc_sheet = mock_calculation_sheet_repo.create.call_args[0][0]
        design = mock_structural_design_repo.create.call_args[0][0]

        # Verify the design references the calculation sheet
        assert design.calculation_sheet_id == calc_sheet.id

    @pytest.mark.asyncio
    async def test_design_beam_with_i_beam_geometry(
        self,
        service,
        basic_beam_loads,
        basic_material,
        mock_calculation_sheet_repo,
        mock_structural_design_repo,
        mock_db_session,
    ):
        """Test beam design with I-beam geometry."""
        # Arrange
        project_id = "test-project-123"
        user_id = "test-user-456"
        span = 20.0
        trial_geometry = {
            "depth": 12.0,
            "width": 8.0,
            "web_thickness": 0.5,
            "flange_thickness": 0.75,
        }

        # Act
        result = await service.design_beam(
            project_id=project_id,
            loads=basic_beam_loads,
            span=span,
            material=basic_material,
            user_id=user_id,
            trial_geometry=trial_geometry,
        )

        # Assert
        from src.calculations.beam_designer import BeamDesignResult

        assert isinstance(result, BeamDesignResult)
        assert result.geometry.web_thickness == 0.5
        assert result.geometry.flange_thickness == 0.75

    @pytest.mark.asyncio
    async def test_design_beam_returns_beam_design_result(
        self,
        service,
        basic_beam_loads,
        basic_material,
        mock_calculation_sheet_repo,
        mock_structural_design_repo,
        mock_db_session,
    ):
        """Test that design_beam returns BeamDesignResult."""
        # Arrange
        project_id = "test-project-123"
        user_id = "test-user-456"
        span = 20.0

        # Act
        result = await service.design_beam(
            project_id=project_id,
            loads=basic_beam_loads,
            span=span,
            material=basic_material,
            user_id=user_id,
        )

        # Assert
        from src.calculations.beam_designer import BeamDesignResult

        assert isinstance(result, BeamDesignResult)
        assert hasattr(result, "is_adequate")
        assert hasattr(result, "max_moment")
        assert hasattr(result, "max_shear")
        assert hasattr(result, "max_stress")
        assert hasattr(result, "allowable_stress")
        assert hasattr(result, "max_deflection")
        assert hasattr(result, "allowable_deflection")
        assert hasattr(result, "stress_ratio")
        assert hasattr(result, "deflection_ratio")
        assert hasattr(result, "geometry")
        assert hasattr(result, "warnings")

    @pytest.mark.asyncio
    async def test_design_beam_with_moment_loads(
        self,
        service,
        basic_material,
        mock_calculation_sheet_repo,
        mock_structural_design_repo,
        mock_db_session,
    ):
        """Test beam design with moment loads."""
        # Arrange
        project_id = "test-project-123"
        user_id = "test-user-456"
        span = 20.0
        loads = {
            "uniform_load": 500.0,
            "point_loads": [],
            "moment_loads": [(10000.0, 10.0)],
        }

        # Act
        result = await service.design_beam(
            project_id=project_id,
            loads=loads,
            span=span,
            material=basic_material,
            user_id=user_id,
        )

        # Assert
        from src.calculations.beam_designer import BeamDesignResult

        assert isinstance(result, BeamDesignResult)

    @pytest.mark.asyncio
    async def test_design_beam_commits_transaction(
        self,
        service,
        basic_beam_loads,
        basic_material,
        mock_calculation_sheet_repo,
        mock_structural_design_repo,
        mock_db_session,
    ):
        """Test that design_beam commits the database transaction."""
        # Arrange
        project_id = "test-project-123"
        user_id = "test-user-456"
        span = 20.0

        # Act
        await service.design_beam(
            project_id=project_id,
            loads=basic_beam_loads,
            span=span,
            material=basic_material,
            user_id=user_id,
        )

        # Assert
        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_design_beam_with_zero_uniform_load(
        self,
        service,
        basic_material,
        mock_calculation_sheet_repo,
        mock_structural_design_repo,
        mock_db_session,
    ):
        """Test beam design with zero uniform load."""
        # Arrange
        project_id = "test-project-123"
        user_id = "test-user-456"
        span = 20.0
        loads = {
            "uniform_load": 0.0,
            "point_loads": [(5000.0, 10.0)],
            "moment_loads": [],
        }

        # Act
        result = await service.design_beam(
            project_id=project_id,
            loads=loads,
            span=span,
            material=basic_material,
            user_id=user_id,
        )

        # Assert
        from src.calculations.beam_designer import BeamDesignResult

        assert isinstance(result, BeamDesignResult)
        assert result.max_moment > 0  # From point load

    @pytest.mark.asyncio
    async def test_design_beam_default_support_type(
        self,
        service,
        basic_beam_loads,
        basic_material,
        mock_calculation_sheet_repo,
        mock_structural_design_repo,
        mock_db_session,
    ):
        """Test that default support type is simply_supported."""
        # Arrange
        project_id = "test-project-123"
        user_id = "test-user-456"
        span = 20.0

        # Act (not specifying support_type)
        await service.design_beam(
            project_id=project_id,
            loads=basic_beam_loads,
            span=span,
            material=basic_material,
            user_id=user_id,
        )

        # Assert
        calc_sheet = mock_calculation_sheet_repo.create.call_args[0][0]
        assert calc_sheet.inputs["support_type"] == "simply_supported"

    @pytest.mark.asyncio
    async def test_design_beam_default_unit_system(
        self,
        service,
        basic_beam_loads,
        basic_material,
        mock_calculation_sheet_repo,
        mock_structural_design_repo,
        mock_db_session,
    ):
        """Test that default unit system is imperial."""
        # Arrange
        project_id = "test-project-123"
        user_id = "test-user-456"
        span = 20.0

        # Act (not specifying unit_system)
        await service.design_beam(
            project_id=project_id,
            loads=basic_beam_loads,
            span=span,
            material=basic_material,
            user_id=user_id,
        )

        # Assert
        calc_sheet = mock_calculation_sheet_repo.create.call_args[0][0]
        assert calc_sheet.units == "imperial"

        design = mock_structural_design_repo.create.call_args[0][0]
        assert design.units == "imperial"


class TestStructuralCalculationServiceDesignColumn:
    """Test design_column method of StructuralCalculationService."""

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
        repo.create = AsyncMock()
        return repo

    @pytest.fixture
    def mock_structural_design_repo(self):
        """Create a mock structural design repository."""
        repo = AsyncMock(spec=StructuralDesignRepository)
        repo.create = AsyncMock()
        return repo

    @pytest.fixture
    def service(
        self, mock_db_session, mock_calculation_sheet_repo, mock_structural_design_repo
    ):
        """Create service instance with mocked dependencies."""
        return StructuralCalculationService(
            db_session=mock_db_session,
            calculation_sheet_repo=mock_calculation_sheet_repo,
            structural_design_repo=mock_structural_design_repo,
        )

    @pytest.fixture
    def basic_column_loads(self):
        """Create basic column loads for testing."""
        return {
            "axial_load": 50000.0,  # lb
            "moment_x": 0.0,  # lb-in
            "moment_y": 0.0,  # lb-in
        }

    @pytest.fixture
    def basic_material(self):
        """Create basic material properties for testing."""
        return {
            "material_type": "steel",
            "yield_strength": 36000.0,  # psi
            "elastic_modulus": 29000000.0,  # psi
            "density": 490.0,  # lb/ft³
            "allowable_stress_factor": 0.6,
        }

    @pytest.fixture
    def rectangular_geometry(self):
        """Create rectangular column geometry for testing."""
        return {
            "depth": 12.0,  # inches
            "width": 12.0,  # inches
            "diameter": None,
        }

    @pytest.fixture
    def circular_geometry(self):
        """Create circular column geometry for testing."""
        return {
            "depth": None,
            "width": None,
            "diameter": 12.0,  # inches
        }

    @pytest.mark.asyncio
    async def test_design_column_with_valid_inputs(
        self,
        service,
        basic_column_loads,
        basic_material,
        rectangular_geometry,
        mock_calculation_sheet_repo,
        mock_structural_design_repo,
        mock_db_session,
    ):
        """Test column design with valid inputs."""
        # Arrange
        project_id = "test-project-123"
        user_id = "test-user-456"
        length = 120.0  # inches (10 feet)

        # Act
        result = await service.design_column(
            project_id=project_id,
            loads=basic_column_loads,
            length=length,
            material=basic_material,
            geometry=rectangular_geometry,
            user_id=user_id,
            unit_system="imperial",
        )

        # Assert
        from src.calculations.column_designer import ColumnDesignResult

        assert isinstance(result, ColumnDesignResult)
        assert result.axial_capacity > 0
        assert result.buckling_capacity > 0
        assert result.slenderness_ratio > 0
        assert result.geometry is not None

        # Verify calculation sheet was created
        mock_calculation_sheet_repo.create.assert_called_once()
        calc_sheet_call = mock_calculation_sheet_repo.create.call_args[0][0]
        assert calc_sheet_call.project_id == project_id
        assert calc_sheet_call.calculation_type == "column_design"
        assert calc_sheet_call.created_by == user_id

        # Verify structural design was created
        mock_structural_design_repo.create.assert_called_once()
        design_call = mock_structural_design_repo.create.call_args[0][0]
        assert design_call.project_id == project_id
        assert design_call.design_type == "column"
        assert design_call.created_by == user_id

        # Verify database commit
        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_design_column_with_circular_geometry(
        self,
        service,
        basic_column_loads,
        basic_material,
        circular_geometry,
        mock_calculation_sheet_repo,
        mock_structural_design_repo,
        mock_db_session,
    ):
        """Test column design with circular geometry."""
        # Arrange
        project_id = "test-project-123"
        user_id = "test-user-456"
        length = 120.0

        # Act
        result = await service.design_column(
            project_id=project_id,
            loads=basic_column_loads,
            length=length,
            material=basic_material,
            geometry=circular_geometry,
            user_id=user_id,
        )

        # Assert
        from src.calculations.column_designer import ColumnDesignResult

        assert isinstance(result, ColumnDesignResult)
        assert result.geometry.diameter == 12.0
        assert result.axial_capacity > 0

        # Verify repos were called
        mock_calculation_sheet_repo.create.assert_called_once()
        mock_structural_design_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_design_column_with_moments(
        self,
        service,
        basic_material,
        rectangular_geometry,
        mock_calculation_sheet_repo,
        mock_structural_design_repo,
        mock_db_session,
    ):
        """Test column design with bending moments."""
        # Arrange
        project_id = "test-project-123"
        user_id = "test-user-456"
        length = 120.0
        loads = {
            "axial_load": 50000.0,
            "moment_x": 50000.0,  # lb-in
            "moment_y": 30000.0,  # lb-in
        }

        # Act
        result = await service.design_column(
            project_id=project_id,
            loads=loads,
            length=length,
            material=basic_material,
            geometry=rectangular_geometry,
            user_id=user_id,
        )

        # Assert
        from src.calculations.column_designer import ColumnDesignResult

        assert isinstance(result, ColumnDesignResult)
        assert result.moment_capacity_x > 0
        assert result.moment_capacity_y > 0
        assert result.combined_stress_ratio > 0

    @pytest.mark.asyncio
    async def test_design_column_different_end_conditions(
        self,
        service,
        basic_column_loads,
        basic_material,
        rectangular_geometry,
        mock_calculation_sheet_repo,
        mock_structural_design_repo,
        mock_db_session,
    ):
        """Test column design with different end conditions."""
        project_id = "test-project-123"
        user_id = "test-user-456"
        length = 120.0

        end_conditions = ["fixed_fixed", "fixed_pinned", "pinned_pinned", "fixed_free"]

        for end_condition in end_conditions:
            # Reset mocks
            mock_calculation_sheet_repo.reset_mock()
            mock_structural_design_repo.reset_mock()
            mock_db_session.reset_mock()

            # Act
            result = await service.design_column(
                project_id=project_id,
                loads=basic_column_loads,
                length=length,
                material=basic_material,
                geometry=rectangular_geometry,
                user_id=user_id,
                end_condition=end_condition,
            )

            # Assert
            from src.calculations.column_designer import ColumnDesignResult

            assert isinstance(result, ColumnDesignResult)
            mock_calculation_sheet_repo.create.assert_called_once()
            mock_structural_design_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_design_column_different_materials(
        self,
        service,
        basic_column_loads,
        rectangular_geometry,
        mock_calculation_sheet_repo,
        mock_structural_design_repo,
        mock_db_session,
    ):
        """Test column design with different material types."""
        project_id = "test-project-123"
        user_id = "test-user-456"
        length = 120.0

        materials = [
            {
                "material_type": "steel",
                "yield_strength": 36000.0,
                "elastic_modulus": 29000000.0,
                "density": 490.0,
            },
            {
                "material_type": "concrete",
                "yield_strength": 4000.0,
                "elastic_modulus": 3600000.0,
                "density": 150.0,
            },
        ]

        for material in materials:
            # Reset mocks
            mock_calculation_sheet_repo.reset_mock()
            mock_structural_design_repo.reset_mock()
            mock_db_session.reset_mock()

            # Act
            result = await service.design_column(
                project_id=project_id,
                loads=basic_column_loads,
                length=length,
                material=material,
                geometry=rectangular_geometry,
                user_id=user_id,
            )

            # Assert
            from src.calculations.column_designer import ColumnDesignResult

            assert isinstance(result, ColumnDesignResult)

    @pytest.mark.asyncio
    async def test_design_column_metric_units(
        self,
        service,
        basic_column_loads,
        basic_material,
        rectangular_geometry,
        mock_calculation_sheet_repo,
        mock_structural_design_repo,
        mock_db_session,
    ):
        """Test column design with metric unit system."""
        # Arrange
        project_id = "test-project-123"
        user_id = "test-user-456"
        length = 3000.0  # mm (converted internally)

        # Act
        result = await service.design_column(
            project_id=project_id,
            loads=basic_column_loads,
            length=length,
            material=basic_material,
            geometry=rectangular_geometry,
            user_id=user_id,
            unit_system="metric",
        )

        # Assert
        from src.calculations.column_designer import ColumnDesignResult

        assert isinstance(result, ColumnDesignResult)

        # Verify calculation sheet has metric units
        calc_sheet_call = mock_calculation_sheet_repo.create.call_args[0][0]
        assert calc_sheet_call.units == "metric"

        # Verify structural design has metric units
        design_call = mock_structural_design_repo.create.call_args[0][0]
        assert design_call.units == "metric"

    @pytest.mark.asyncio
    async def test_design_column_calculation_sheet_structure(
        self,
        service,
        basic_column_loads,
        basic_material,
        rectangular_geometry,
        mock_calculation_sheet_repo,
        mock_structural_design_repo,
        mock_db_session,
    ):
        """Test that calculation sheet has correct structure."""
        # Arrange
        project_id = "test-project-123"
        user_id = "test-user-456"
        length = 120.0

        # Act
        await service.design_column(
            project_id=project_id,
            loads=basic_column_loads,
            length=length,
            material=basic_material,
            geometry=rectangular_geometry,
            user_id=user_id,
        )

        # Assert
        calc_sheet = mock_calculation_sheet_repo.create.call_args[0][0]
        assert calc_sheet.project_id == project_id
        assert calc_sheet.calculation_type == "column_design"
        assert calc_sheet.created_by == user_id
        assert calc_sheet.status == "approved"

        # Check inputs
        assert "length" in calc_sheet.inputs
        assert "loads" in calc_sheet.inputs
        assert "material" in calc_sheet.inputs
        assert "geometry" in calc_sheet.inputs
        assert "end_condition" in calc_sheet.inputs

        # Check outputs
        assert "is_adequate" in calc_sheet.outputs
        assert "axial_capacity" in calc_sheet.outputs
        assert "buckling_capacity" in calc_sheet.outputs
        assert "moment_capacity_x" in calc_sheet.outputs
        assert "moment_capacity_y" in calc_sheet.outputs
        assert "combined_stress_ratio" in calc_sheet.outputs
        assert "slenderness_ratio" in calc_sheet.outputs
        assert "effective_length" in calc_sheet.outputs

        # Check formulas and references
        assert len(calc_sheet.formulas) > 0
        assert len(calc_sheet.references) > 0

    @pytest.mark.asyncio
    async def test_design_column_structural_design_structure(
        self,
        service,
        basic_column_loads,
        basic_material,
        rectangular_geometry,
        mock_calculation_sheet_repo,
        mock_structural_design_repo,
        mock_db_session,
    ):
        """Test that structural design record has correct structure."""
        # Arrange
        project_id = "test-project-123"
        user_id = "test-user-456"
        length = 120.0

        # Act
        await service.design_column(
            project_id=project_id,
            loads=basic_column_loads,
            length=length,
            material=basic_material,
            geometry=rectangular_geometry,
            user_id=user_id,
        )

        # Assert
        design = mock_structural_design_repo.create.call_args[0][0]
        assert design.project_id == project_id
        assert design.design_type == "column"
        assert design.created_by == user_id
        assert design.status == "draft"

        # Check loads, material_properties, geometry
        assert design.loads == basic_column_loads
        assert design.material_properties == basic_material
        assert "depth" in design.geometry
        assert "width" in design.geometry
        assert "length" in design.geometry
        assert "end_condition" in design.geometry

        # Check design_results
        assert "is_adequate" in design.design_results
        assert "axial_capacity" in design.design_results
        assert "buckling_capacity" in design.design_results
        assert "moment_capacity_x" in design.design_results
        assert "moment_capacity_y" in design.design_results

        # Check stress_ratios
        assert "combined_stress_ratio" in design.stress_ratios
        assert "slenderness_ratio" in design.stress_ratios

    @pytest.mark.asyncio
    async def test_design_column_links_calculation_sheet_to_design(
        self,
        service,
        basic_column_loads,
        basic_material,
        rectangular_geometry,
        mock_calculation_sheet_repo,
        mock_structural_design_repo,
        mock_db_session,
    ):
        """Test that structural design is linked to calculation sheet."""
        # Arrange
        project_id = "test-project-123"
        user_id = "test-user-456"
        length = 120.0

        # Act
        await service.design_column(
            project_id=project_id,
            loads=basic_column_loads,
            length=length,
            material=basic_material,
            geometry=rectangular_geometry,
            user_id=user_id,
        )

        # Assert
        calc_sheet = mock_calculation_sheet_repo.create.call_args[0][0]
        design = mock_structural_design_repo.create.call_args[0][0]

        # Verify the design references the calculation sheet
        assert design.calculation_sheet_id == calc_sheet.id

    @pytest.mark.asyncio
    async def test_design_column_returns_column_design_result(
        self,
        service,
        basic_column_loads,
        basic_material,
        rectangular_geometry,
        mock_calculation_sheet_repo,
        mock_structural_design_repo,
        mock_db_session,
    ):
        """Test that design_column returns ColumnDesignResult."""
        # Arrange
        project_id = "test-project-123"
        user_id = "test-user-456"
        length = 120.0

        # Act
        result = await service.design_column(
            project_id=project_id,
            loads=basic_column_loads,
            length=length,
            material=basic_material,
            geometry=rectangular_geometry,
            user_id=user_id,
        )

        # Assert
        from src.calculations.column_designer import ColumnDesignResult

        assert isinstance(result, ColumnDesignResult)
        assert hasattr(result, "is_adequate")
        assert hasattr(result, "axial_capacity")
        assert hasattr(result, "buckling_capacity")
        assert hasattr(result, "moment_capacity_x")
        assert hasattr(result, "moment_capacity_y")
        assert hasattr(result, "combined_stress_ratio")
        assert hasattr(result, "slenderness_ratio")
        assert hasattr(result, "effective_length")
        assert hasattr(result, "geometry")
        assert hasattr(result, "warnings")

    @pytest.mark.asyncio
    async def test_design_column_commits_transaction(
        self,
        service,
        basic_column_loads,
        basic_material,
        rectangular_geometry,
        mock_calculation_sheet_repo,
        mock_structural_design_repo,
        mock_db_session,
    ):
        """Test that design_column commits the database transaction."""
        # Arrange
        project_id = "test-project-123"
        user_id = "test-user-456"
        length = 120.0

        # Act
        await service.design_column(
            project_id=project_id,
            loads=basic_column_loads,
            length=length,
            material=basic_material,
            geometry=rectangular_geometry,
            user_id=user_id,
        )

        # Assert
        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_design_column_default_end_condition(
        self,
        service,
        basic_column_loads,
        basic_material,
        rectangular_geometry,
        mock_calculation_sheet_repo,
        mock_structural_design_repo,
        mock_db_session,
    ):
        """Test that default end condition is pinned_pinned."""
        # Arrange
        project_id = "test-project-123"
        user_id = "test-user-456"
        length = 120.0

        # Act (not specifying end_condition)
        await service.design_column(
            project_id=project_id,
            loads=basic_column_loads,
            length=length,
            material=basic_material,
            geometry=rectangular_geometry,
            user_id=user_id,
        )

        # Assert
        calc_sheet = mock_calculation_sheet_repo.create.call_args[0][0]
        assert calc_sheet.inputs["end_condition"] == "pinned_pinned"

    @pytest.mark.asyncio
    async def test_design_column_default_unit_system(
        self,
        service,
        basic_column_loads,
        basic_material,
        rectangular_geometry,
        mock_calculation_sheet_repo,
        mock_structural_design_repo,
        mock_db_session,
    ):
        """Test that default unit system is imperial."""
        # Arrange
        project_id = "test-project-123"
        user_id = "test-user-456"
        length = 120.0

        # Act (not specifying unit_system)
        await service.design_column(
            project_id=project_id,
            loads=basic_column_loads,
            length=length,
            material=basic_material,
            geometry=rectangular_geometry,
            user_id=user_id,
        )

        # Assert
        calc_sheet = mock_calculation_sheet_repo.create.call_args[0][0]
        assert calc_sheet.units == "imperial"

        design = mock_structural_design_repo.create.call_args[0][0]
        assert design.units == "imperial"

    @pytest.mark.asyncio
    async def test_design_column_with_zero_moments(
        self,
        service,
        basic_material,
        rectangular_geometry,
        mock_calculation_sheet_repo,
        mock_structural_design_repo,
        mock_db_session,
    ):
        """Test column design with zero moments (pure axial load)."""
        # Arrange
        project_id = "test-project-123"
        user_id = "test-user-456"
        length = 120.0
        loads = {
            "axial_load": 50000.0,
            "moment_x": 0.0,
            "moment_y": 0.0,
        }

        # Act
        result = await service.design_column(
            project_id=project_id,
            loads=loads,
            length=length,
            material=basic_material,
            geometry=rectangular_geometry,
            user_id=user_id,
        )

        # Assert
        from src.calculations.column_designer import ColumnDesignResult

        assert isinstance(result, ColumnDesignResult)
        assert result.axial_capacity > 0
        assert result.buckling_capacity > 0

    @pytest.mark.asyncio
    async def test_design_column_short_column(
        self,
        service,
        basic_column_loads,
        basic_material,
        rectangular_geometry,
        mock_calculation_sheet_repo,
        mock_structural_design_repo,
        mock_db_session,
    ):
        """Test design of short column (low slenderness)."""
        # Arrange
        project_id = "test-project-123"
        user_id = "test-user-456"
        length = 36.0  # 3 feet - short column

        # Act
        result = await service.design_column(
            project_id=project_id,
            loads=basic_column_loads,
            length=length,
            material=basic_material,
            geometry=rectangular_geometry,
            user_id=user_id,
        )

        # Assert
        from src.calculations.column_designer import ColumnDesignResult

        assert isinstance(result, ColumnDesignResult)
        # Short columns have low slenderness ratios
        assert result.slenderness_ratio < 50.0

    @pytest.mark.asyncio
    async def test_design_column_long_column(
        self,
        service,
        basic_column_loads,
        basic_material,
        rectangular_geometry,
        mock_calculation_sheet_repo,
        mock_structural_design_repo,
        mock_db_session,
    ):
        """Test design of long column (high slenderness)."""
        # Arrange
        project_id = "test-project-123"
        user_id = "test-user-456"
        length = 240.0  # 20 feet - long column

        # Act
        result = await service.design_column(
            project_id=project_id,
            loads=basic_column_loads,
            length=length,
            material=basic_material,
            geometry=rectangular_geometry,
            user_id=user_id,
        )

        # Assert
        from src.calculations.column_designer import ColumnDesignResult

        assert isinstance(result, ColumnDesignResult)
        # Long columns have higher slenderness ratios
        assert result.slenderness_ratio > 30.0

    @pytest.mark.asyncio
    async def test_design_column_fixed_fixed_has_lower_effective_length(
        self,
        service,
        basic_column_loads,
        basic_material,
        rectangular_geometry,
        mock_calculation_sheet_repo,
        mock_structural_design_repo,
        mock_db_session,
    ):
        """Test that fixed-fixed columns have lower effective length."""
        # Arrange
        project_id = "test-project-123"
        user_id = "test-user-456"
        length = 120.0

        # Act - fixed-fixed
        mock_calculation_sheet_repo.reset_mock()
        mock_structural_design_repo.reset_mock()
        result_fixed = await service.design_column(
            project_id=project_id,
            loads=basic_column_loads,
            length=length,
            material=basic_material,
            geometry=rectangular_geometry,
            user_id=user_id,
            end_condition="fixed_fixed",
        )

        # Act - pinned-pinned
        mock_calculation_sheet_repo.reset_mock()
        mock_structural_design_repo.reset_mock()
        result_pinned = await service.design_column(
            project_id=project_id,
            loads=basic_column_loads,
            length=length,
            material=basic_material,
            geometry=rectangular_geometry,
            user_id=user_id,
            end_condition="pinned_pinned",
        )

        # Assert
        # Fixed-fixed (K=0.5) should have lower effective length than
        # pinned-pinned (K=1.0)
        assert result_fixed.effective_length < result_pinned.effective_length

    @pytest.mark.asyncio
    async def test_design_column_handles_buckling_analysis(
        self,
        service,
        basic_column_loads,
        basic_material,
        rectangular_geometry,
        mock_calculation_sheet_repo,
        mock_structural_design_repo,
        mock_db_session,
    ):
        """Test that column design includes buckling analysis."""
        # Arrange
        project_id = "test-project-123"
        user_id = "test-user-456"
        length = 120.0

        # Act
        result = await service.design_column(
            project_id=project_id,
            loads=basic_column_loads,
            length=length,
            material=basic_material,
            geometry=rectangular_geometry,
            user_id=user_id,
        )

        # Assert
        from src.calculations.column_designer import ColumnDesignResult

        assert isinstance(result, ColumnDesignResult)
        assert result.buckling_capacity > 0
        assert result.effective_length > 0
        assert result.slenderness_ratio > 0
        # Buckling capacity should be less than or equal to axial capacity
        assert result.buckling_capacity <= result.axial_capacity


class TestStructuralCalculationServiceDesignFoundation:
    """Test design_foundation method of StructuralCalculationService."""

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
        repo.create = AsyncMock()
        return repo

    @pytest.fixture
    def mock_structural_design_repo(self):
        """Create a mock structural design repository."""
        repo = AsyncMock(spec=StructuralDesignRepository)
        repo.create = AsyncMock()
        return repo

    @pytest.fixture
    def service(
        self, mock_db_session, mock_calculation_sheet_repo, mock_structural_design_repo
    ):
        """Create service instance with mocked dependencies."""
        return StructuralCalculationService(
            db_session=mock_db_session,
            calculation_sheet_repo=mock_calculation_sheet_repo,
            structural_design_repo=mock_structural_design_repo,
        )

    @pytest.fixture
    def basic_foundation_loads(self):
        """Create basic foundation loads for testing."""
        return {
            "vertical_load": 100000.0,  # lb
            "moment_x": 0.0,  # lb-ft
            "moment_y": 0.0,  # lb-ft
            "horizontal_x": 0.0,  # lb
            "horizontal_y": 0.0,  # lb
        }

    @pytest.fixture
    def basic_soil_properties(self):
        """Create basic soil properties for testing."""
        return {
            "bearing_capacity": 3000.0,  # psf
            "unit_weight": 120.0,  # pcf
            "friction_angle": 30.0,  # degrees
            "cohesion": 0.0,  # psf
            "elastic_modulus": 5000.0,  # psi
        }

    @pytest.fixture
    def spread_footing_geometry(self):
        """Create spread footing geometry for testing."""
        return {
            "foundation_type": "spread_footing",
            "length": 10.0,  # feet
            "width": 10.0,  # feet
            "diameter": None,
            "depth": 3.0,  # feet
            "thickness": 18.0,  # inches
        }

    @pytest.mark.asyncio
    async def test_design_foundation_with_valid_inputs(
        self,
        service,
        basic_foundation_loads,
        basic_soil_properties,
        spread_footing_geometry,
        mock_calculation_sheet_repo,
        mock_structural_design_repo,
        mock_db_session,
    ):
        """Test foundation design with valid inputs."""
        # Arrange
        project_id = "test-project-123"
        user_id = "test-user-456"

        # Act
        result = await service.design_foundation(
            project_id=project_id,
            loads=basic_foundation_loads,
            soil_properties=basic_soil_properties,
            geometry=spread_footing_geometry,
            user_id=user_id,
            unit_system="imperial",
        )

        # Assert
        from src.calculations.foundation_designer import FoundationDesignResult

        assert isinstance(result, FoundationDesignResult)
        assert result.bearing_pressure > 0
        assert result.allowable_bearing_capacity > 0
        assert result.bearing_ratio > 0
        assert result.settlement >= 0
        assert result.reinforcement_area > 0
        assert result.geometry is not None

        # Verify calculation sheet was created
        mock_calculation_sheet_repo.create.assert_called_once()
        calc_sheet_call = mock_calculation_sheet_repo.create.call_args[0][0]
        assert calc_sheet_call.project_id == project_id
        assert calc_sheet_call.calculation_type == "foundation_design"
        assert calc_sheet_call.created_by == user_id

        # Verify structural design was created
        mock_structural_design_repo.create.assert_called_once()
        design_call = mock_structural_design_repo.create.call_args[0][0]
        assert design_call.project_id == project_id
        assert design_call.design_type == "foundation"
        assert design_call.created_by == user_id

        # Verify database commit
        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_design_foundation_with_eccentric_loading(
        self,
        service,
        basic_soil_properties,
        spread_footing_geometry,
        mock_calculation_sheet_repo,
        mock_structural_design_repo,
        mock_db_session,
    ):
        """Test foundation design with eccentric loading (moments)."""
        # Arrange
        project_id = "test-project-123"
        user_id = "test-user-456"
        loads = {
            "vertical_load": 100000.0,
            "moment_x": 50000.0,  # lb-ft
            "moment_y": 30000.0,  # lb-ft
            "horizontal_x": 5000.0,
            "horizontal_y": 3000.0,
        }

        # Act
        result = await service.design_foundation(
            project_id=project_id,
            loads=loads,
            soil_properties=basic_soil_properties,
            geometry=spread_footing_geometry,
            user_id=user_id,
        )

        # Assert
        from src.calculations.foundation_designer import FoundationDesignResult

        assert isinstance(result, FoundationDesignResult)
        # Bearing pressure should be higher due to eccentric loading
        assert result.bearing_pressure > 0

    @pytest.mark.asyncio
    async def test_design_foundation_different_types(
        self,
        service,
        basic_foundation_loads,
        basic_soil_properties,
        mock_calculation_sheet_repo,
        mock_structural_design_repo,
        mock_db_session,
    ):
        """Test foundation design with different foundation types."""
        project_id = "test-project-123"
        user_id = "test-user-456"

        foundation_types = [
            {
                "foundation_type": "spread_footing",
                "length": 10.0,
                "width": 10.0,
                "diameter": None,
                "depth": 3.0,
                "thickness": 18.0,
            },
            {
                "foundation_type": "continuous_footing",
                "length": 20.0,
                "width": 5.0,
                "diameter": None,
                "depth": 3.0,
                "thickness": 18.0,
            },
            {
                "foundation_type": "mat_foundation",
                "length": 50.0,
                "width": 50.0,
                "diameter": None,
                "depth": 4.0,
                "thickness": 24.0,
            },
        ]

        for geometry in foundation_types:
            # Reset mocks
            mock_calculation_sheet_repo.reset_mock()
            mock_structural_design_repo.reset_mock()
            mock_db_session.reset_mock()

            # Act
            result = await service.design_foundation(
                project_id=project_id,
                loads=basic_foundation_loads,
                soil_properties=basic_soil_properties,
                geometry=geometry,
                user_id=user_id,
            )

            # Assert
            from src.calculations.foundation_designer import \
                FoundationDesignResult

            assert isinstance(result, FoundationDesignResult)
            mock_calculation_sheet_repo.create.assert_called_once()
            mock_structural_design_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_design_foundation_metric_units(
        self,
        service,
        basic_foundation_loads,
        basic_soil_properties,
        spread_footing_geometry,
        mock_calculation_sheet_repo,
        mock_structural_design_repo,
        mock_db_session,
    ):
        """Test foundation design with metric unit system."""
        # Arrange
        project_id = "test-project-123"
        user_id = "test-user-456"

        # Act
        result = await service.design_foundation(
            project_id=project_id,
            loads=basic_foundation_loads,
            soil_properties=basic_soil_properties,
            geometry=spread_footing_geometry,
            user_id=user_id,
            unit_system="metric",
        )

        # Assert
        from src.calculations.foundation_designer import FoundationDesignResult

        assert isinstance(result, FoundationDesignResult)

        # Verify calculation sheet has metric units
        calc_sheet_call = mock_calculation_sheet_repo.create.call_args[0][0]
        assert calc_sheet_call.units == "metric"

        # Verify structural design has metric units
        design_call = mock_structural_design_repo.create.call_args[0][0]
        assert design_call.units == "metric"

    @pytest.mark.asyncio
    async def test_design_foundation_calculation_sheet_structure(
        self,
        service,
        basic_foundation_loads,
        basic_soil_properties,
        spread_footing_geometry,
        mock_calculation_sheet_repo,
        mock_structural_design_repo,
        mock_db_session,
    ):
        """Test that calculation sheet has correct structure."""
        # Arrange
        project_id = "test-project-123"
        user_id = "test-user-456"

        # Act
        await service.design_foundation(
            project_id=project_id,
            loads=basic_foundation_loads,
            soil_properties=basic_soil_properties,
            geometry=spread_footing_geometry,
            user_id=user_id,
        )

        # Assert
        calc_sheet = mock_calculation_sheet_repo.create.call_args[0][0]
        assert calc_sheet.project_id == project_id
        assert calc_sheet.calculation_type == "foundation_design"
        assert calc_sheet.created_by == user_id
        assert calc_sheet.status == "approved"

        # Check inputs
        assert "loads" in calc_sheet.inputs
        assert "soil_properties" in calc_sheet.inputs
        assert "geometry" in calc_sheet.inputs

        # Check outputs
        assert "is_adequate" in calc_sheet.outputs
        assert "bearing_pressure" in calc_sheet.outputs
        assert "allowable_bearing_capacity" in calc_sheet.outputs
        assert "bearing_ratio" in calc_sheet.outputs
        assert "settlement" in calc_sheet.outputs
        assert "allowable_settlement" in calc_sheet.outputs
        assert "reinforcement_area" in calc_sheet.outputs

        # Check formulas and references
        assert len(calc_sheet.formulas) > 0
        assert len(calc_sheet.references) > 0

    @pytest.mark.asyncio
    async def test_design_foundation_structural_design_structure(
        self,
        service,
        basic_foundation_loads,
        basic_soil_properties,
        spread_footing_geometry,
        mock_calculation_sheet_repo,
        mock_structural_design_repo,
        mock_db_session,
    ):
        """Test that structural design record has correct structure."""
        # Arrange
        project_id = "test-project-123"
        user_id = "test-user-456"

        # Act
        await service.design_foundation(
            project_id=project_id,
            loads=basic_foundation_loads,
            soil_properties=basic_soil_properties,
            geometry=spread_footing_geometry,
            user_id=user_id,
        )

        # Assert
        design = mock_structural_design_repo.create.call_args[0][0]
        assert design.project_id == project_id
        assert design.design_type == "foundation"
        assert design.created_by == user_id
        assert design.status == "draft"

        # Check loads, material_properties, geometry
        assert design.loads == basic_foundation_loads
        assert design.material_properties == basic_soil_properties
        assert "foundation_type" in design.geometry
        assert "length" in design.geometry or "diameter" in design.geometry
        assert "depth" in design.geometry

        # Check design_results
        assert "is_adequate" in design.design_results
        assert "bearing_pressure" in design.design_results
        assert "settlement" in design.design_results

        # Check stress_ratios
        assert "bearing_ratio" in design.stress_ratios

    @pytest.mark.asyncio
    async def test_design_foundation_links_calculation_sheet_to_design(
        self,
        service,
        basic_foundation_loads,
        basic_soil_properties,
        spread_footing_geometry,
        mock_calculation_sheet_repo,
        mock_structural_design_repo,
        mock_db_session,
    ):
        """Test that structural design is linked to calculation sheet."""
        # Arrange
        project_id = "test-project-123"
        user_id = "test-user-456"

        # Act
        await service.design_foundation(
            project_id=project_id,
            loads=basic_foundation_loads,
            soil_properties=basic_soil_properties,
            geometry=spread_footing_geometry,
            user_id=user_id,
        )

        # Assert
        calc_sheet = mock_calculation_sheet_repo.create.call_args[0][0]
        design = mock_structural_design_repo.create.call_args[0][0]

        # Verify the design references the calculation sheet
        assert design.calculation_sheet_id == calc_sheet.id

    @pytest.mark.asyncio
    async def test_design_foundation_returns_foundation_design_result(
        self,
        service,
        basic_foundation_loads,
        basic_soil_properties,
        spread_footing_geometry,
        mock_calculation_sheet_repo,
        mock_structural_design_repo,
        mock_db_session,
    ):
        """Test that design_foundation returns FoundationDesignResult."""
        # Arrange
        project_id = "test-project-123"
        user_id = "test-user-456"

        # Act
        result = await service.design_foundation(
            project_id=project_id,
            loads=basic_foundation_loads,
            soil_properties=basic_soil_properties,
            geometry=spread_footing_geometry,
            user_id=user_id,
        )

        # Assert
        from src.calculations.foundation_designer import FoundationDesignResult

        assert isinstance(result, FoundationDesignResult)
        assert hasattr(result, "is_adequate")
        assert hasattr(result, "bearing_pressure")
        assert hasattr(result, "allowable_bearing_capacity")
        assert hasattr(result, "bearing_ratio")
        assert hasattr(result, "settlement")
        assert hasattr(result, "allowable_settlement")
        assert hasattr(result, "reinforcement_area")
        assert hasattr(result, "geometry")
        assert hasattr(result, "warnings")

    @pytest.mark.asyncio
    async def test_design_foundation_commits_transaction(
        self,
        service,
        basic_foundation_loads,
        basic_soil_properties,
        spread_footing_geometry,
        mock_calculation_sheet_repo,
        mock_structural_design_repo,
        mock_db_session,
    ):
        """Test that design_foundation commits the database transaction."""
        # Arrange
        project_id = "test-project-123"
        user_id = "test-user-456"

        # Act
        await service.design_foundation(
            project_id=project_id,
            loads=basic_foundation_loads,
            soil_properties=basic_soil_properties,
            geometry=spread_footing_geometry,
            user_id=user_id,
        )

        # Assert
        mock_db_session.commit.assert_called_once()


class TestStructuralCalculationServiceRecalculation:
    """Test automatic recalculation logic of StructuralCalculationService."""

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
        repo.create = AsyncMock()
        repo.get_by_id = AsyncMock()
        repo.update = AsyncMock()
        return repo

    @pytest.fixture
    def mock_structural_design_repo(self):
        """Create a mock structural design repository."""
        repo = AsyncMock(spec=StructuralDesignRepository)
        repo.create = AsyncMock()
        return repo

    @pytest.fixture
    def mock_recalculation_service(self):
        """Create a mock recalculation service."""
        from src.services.recalculation_service import RecalculationService

        service = AsyncMock(spec=RecalculationService)
        service.add_dependency = AsyncMock()
        service.trigger_recalculation_cascade = AsyncMock()
        service.get_dependents = AsyncMock(return_value=[])
        service.get_dependencies = AsyncMock(return_value=[])
        service.get_dependency_graph = AsyncMock(
            return_value={"dependencies": [], "dependents": []}
        )
        return service

    @pytest.fixture
    def service(
        self,
        mock_db_session,
        mock_calculation_sheet_repo,
        mock_structural_design_repo,
        mock_recalculation_service,
    ):
        """Create service instance with mocked dependencies."""
        return StructuralCalculationService(
            db_session=mock_db_session,
            calculation_sheet_repo=mock_calculation_sheet_repo,
            structural_design_repo=mock_structural_design_repo,
            recalculation_service=mock_recalculation_service,
        )

    @pytest.mark.asyncio
    async def test_add_calculation_dependency(
        self, service, mock_recalculation_service
    ):
        """Test adding a dependency between calculations."""
        # Arrange
        source_id = 1
        target_id = 2
        dependency_type = "load_input"
        user_id = "test-user-456"
        dependent_field = "loads"
        source_field = "outputs.total_load"

        # Mock the return value
        from src.models.calculation_dependency import CalculationDependency

        mock_dependency = MagicMock(spec=CalculationDependency)
        mock_recalculation_service.add_dependency.return_value = mock_dependency

        # Act
        result = await service.add_calculation_dependency(
            source_calculation_id=source_id,
            target_calculation_id=target_id,
            dependency_type=dependency_type,
            user_id=user_id,
            dependent_field=dependent_field,
            source_field=source_field,
        )

        # Assert
        mock_recalculation_service.add_dependency.assert_called_once_with(
            source_calculation_id=source_id,
            target_calculation_id=target_id,
            dependency_type=dependency_type,
            user_id=user_id,
            dependent_field=dependent_field,
            source_field=source_field,
        )
        assert result == mock_dependency

    @pytest.mark.asyncio
    async def test_update_calculation_inputs_triggers_recalculation(
        self,
        service,
        mock_calculation_sheet_repo,
        mock_recalculation_service,
        mock_db_session,
    ):
        """Test that updating calculation inputs triggers recalculation."""
        # Arrange
        calculation_id = 1
        new_inputs = {"span": 25.0, "loads": {"uniform_load": 1500.0}}
        user_id = "test-user-456"

        # Mock the calculation sheet
        mock_sheet = MagicMock(spec=CalculationSheet)
        mock_sheet.id = calculation_id
        mock_sheet.inputs = {"span": 20.0, "loads": {"uniform_load": 1000.0}}
        mock_calculation_sheet_repo.get_by_id.return_value = mock_sheet
        mock_calculation_sheet_repo.update.return_value = mock_sheet

        # Act
        result = await service.update_calculation_inputs(
            calculation_id=calculation_id,
            new_inputs=new_inputs,
            user_id=user_id,
            trigger_recalculation=True,
        )

        # Assert
        mock_calculation_sheet_repo.get_by_id.assert_called_once_with(calculation_id)
        mock_calculation_sheet_repo.update.assert_called_once()
        mock_db_session.commit.assert_called()
        mock_recalculation_service.trigger_recalculation_cascade.assert_called_once()

        # Verify inputs were updated
        assert mock_sheet.inputs["span"] == 25.0
        assert mock_sheet.inputs["loads"]["uniform_load"] == 1500.0
        assert mock_sheet.status == "draft"

    @pytest.mark.asyncio
    async def test_update_calculation_inputs_without_recalculation(
        self,
        service,
        mock_calculation_sheet_repo,
        mock_recalculation_service,
        mock_db_session,
    ):
        """Test updating calculation inputs without triggering recalculation."""
        # Arrange
        calculation_id = 1
        new_inputs = {"span": 25.0}
        user_id = "test-user-456"

        # Mock the calculation sheet
        mock_sheet = MagicMock(spec=CalculationSheet)
        mock_sheet.id = calculation_id
        mock_sheet.inputs = {"span": 20.0}
        mock_calculation_sheet_repo.get_by_id.return_value = mock_sheet
        mock_calculation_sheet_repo.update.return_value = mock_sheet

        # Act
        result = await service.update_calculation_inputs(
            calculation_id=calculation_id,
            new_inputs=new_inputs,
            user_id=user_id,
            trigger_recalculation=False,
        )

        # Assert
        mock_calculation_sheet_repo.get_by_id.assert_called_once_with(calculation_id)
        mock_calculation_sheet_repo.update.assert_called_once()
        mock_db_session.commit.assert_called_once()
        mock_recalculation_service.trigger_recalculation_cascade.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_calculation_inputs_raises_error_if_not_found(
        self, service, mock_calculation_sheet_repo
    ):
        """Test that updating non-existent calculation raises error."""
        # Arrange
        calculation_id = 999
        new_inputs = {"span": 25.0}
        user_id = "test-user-456"

        # Mock the calculation sheet not found
        mock_calculation_sheet_repo.get_by_id.return_value = None

        # Act & Assert
        with pytest.raises(ValueError, match="not found"):
            await service.update_calculation_inputs(
                calculation_id=calculation_id,
                new_inputs=new_inputs,
                user_id=user_id,
            )

    @pytest.mark.asyncio
    async def test_get_calculation_dependents(
        self, service, mock_recalculation_service
    ):
        """Test getting calculations that depend on a given calculation."""
        # Arrange
        calculation_id = 1
        mock_dependents = [
            MagicMock(spec=CalculationSheet, id=2),
            MagicMock(spec=CalculationSheet, id=3),
        ]
        mock_recalculation_service.get_dependents.return_value = mock_dependents

        # Act
        result = await service.get_calculation_dependents(calculation_id)

        # Assert
        mock_recalculation_service.get_dependents.assert_called_once_with(
            calculation_id
        )
        assert result == mock_dependents

    @pytest.mark.asyncio
    async def test_get_calculation_dependencies(
        self, service, mock_recalculation_service
    ):
        """Test getting calculations that a given calculation depends on."""
        # Arrange
        calculation_id = 1
        mock_dependencies = [
            MagicMock(spec=CalculationSheet, id=4),
            MagicMock(spec=CalculationSheet, id=5),
        ]
        mock_recalculation_service.get_dependencies.return_value = mock_dependencies

        # Act
        result = await service.get_calculation_dependencies(calculation_id)

        # Assert
        mock_recalculation_service.get_dependencies.assert_called_once_with(
            calculation_id
        )
        assert result == mock_dependencies

    @pytest.mark.asyncio
    async def test_get_dependency_graph(self, service, mock_recalculation_service):
        """Test getting the full dependency graph for a calculation."""
        # Arrange
        calculation_id = 1
        mock_graph = {
            "dependencies": [{"id": 2, "type": "load_input", "field": "total_load"}],
            "dependents": [{"id": 3, "type": "beam_design", "field": "loads"}],
        }
        mock_recalculation_service.get_dependency_graph.return_value = mock_graph

        # Act
        result = await service.get_dependency_graph(calculation_id)

        # Assert
        mock_recalculation_service.get_dependency_graph.assert_called_once_with(
            calculation_id
        )
        assert result == mock_graph
        assert "dependencies" in result
        assert "dependents" in result
