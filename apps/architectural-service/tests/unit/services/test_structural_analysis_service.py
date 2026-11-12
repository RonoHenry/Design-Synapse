"""Unit tests for StructuralAnalysisService load calculations."""

from datetime import datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from src.api.v1.schemas.analysis import LoadParameters
from src.models.design import Design
from src.repositories.design_repository import DesignRepository
from src.repositories.structural_analysis_repository import \
    StructuralAnalysisRepository
from src.services.structural_analysis_service import StructuralAnalysisService


class TestStructuralAnalysisServiceLoadCalculations:
    """Unit tests for load calculation methods."""

    @pytest.fixture
    def mock_structural_repository(self):
        """Mock StructuralAnalysisRepository."""
        return AsyncMock(spec=StructuralAnalysisRepository)

    @pytest.fixture
    def mock_design_repository(self):
        """Mock DesignRepository."""
        return AsyncMock(spec=DesignRepository)

    @pytest.fixture
    def service(self, mock_structural_repository, mock_design_repository):
        """Create StructuralAnalysisService with mocked dependencies."""
        return StructuralAnalysisService(
            structural_repository=mock_structural_repository,
            design_repository=mock_design_repository,
        )

    @pytest.fixture
    def base_design(self):
        """Create a base design for testing."""
        return Design(
            id=str(uuid4()),
            project_id=str(uuid4()),
            name="Test Design",
            building_type="office",
            location_data={"city": "Test City", "state": "CA"},
            current_version="1.0",
            version_number=1,
            status="active",
            is_deleted=False,
            metadata={
                "building_area": 10000,  # sq ft
                "building_height": 30,  # feet
                "building_width": 100,  # feet
                "building_weight": 1000000,  # lbs
                "structural_system": "steel_frame",
            },
            created_by=str(uuid4()),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

    async def test_dead_load_calculations_steel_frame(self, service, base_design):
        """Test dead load calculations for steel frame construction."""
        base_design.metadata["structural_system"] = "steel_frame"
        load_params = LoadParameters(dead_load_factor=1.2)

        loads = await service.calculate_loads(base_design, load_params)

        # Verify dead loads are calculated
        assert loads.dead_loads is not None
        assert len(loads.dead_loads) > 0

        # Check specific load components for steel frame
        assert "structure" in loads.dead_loads
        assert "floor_system" in loads.dead_loads
        assert "roof_system" in loads.dead_loads

        # Verify load factor is applied (steel frame: 15 psf * 10000 sf * 1.2 = 180,000 lbs)
        expected_structure_load = 10000 * 15.0 * 1.2
        assert loads.dead_loads["structure"] == expected_structure_load

        # Verify all loads are positive
        for load in loads.dead_loads.values():
            assert load > 0

    async def test_dead_load_calculations_concrete(self, service, base_design):
        """Test dead load calculations for concrete construction."""
        base_design.metadata["structural_system"] = "concrete"
        load_params = LoadParameters(dead_load_factor=1.3)

        loads = await service.calculate_loads(base_design, load_params)

        # Check concrete-specific loads (25 psf for structure)
        expected_structure_load = 10000 * 25.0 * 1.3
        assert loads.dead_loads["structure"] == expected_structure_load

        # Concrete should have higher loads than steel
        steel_design = Design(
            id=str(uuid4()),
            project_id=base_design.project_id,
            name=base_design.name,
            building_type=base_design.building_type,
            location_data=base_design.location_data,
            current_version=base_design.current_version,
            version_number=base_design.version_number,
            status=base_design.status,
            is_deleted=base_design.is_deleted,
            metadata={**base_design.metadata, "structural_system": "steel_frame"},
            created_by=base_design.created_by,
            created_at=base_design.created_at,
            updated_at=base_design.updated_at,
        )
        steel_loads = await service.calculate_loads(steel_design, load_params)

        assert loads.dead_loads["structure"] > steel_loads.dead_loads["structure"]

    async def test_dead_load_calculations_wood_frame(self, service, base_design):
        """Test dead load calculations for wood frame construction."""
        base_design.metadata["structural_system"] = "wood_frame"
        load_params = LoadParameters(dead_load_factor=1.1)

        loads = await service.calculate_loads(base_design, load_params)

        # Check wood frame loads (10 psf for structure)
        expected_structure_load = 10000 * 10.0 * 1.1
        assert loads.dead_loads["structure"] == expected_structure_load

        # Wood should have lower loads than steel and concrete
        steel_design = Design(
            id=str(uuid4()),
            project_id=base_design.project_id,
            name=base_design.name,
            building_type=base_design.building_type,
            location_data=base_design.location_data,
            current_version=base_design.current_version,
            version_number=base_design.version_number,
            status=base_design.status,
            is_deleted=base_design.is_deleted,
            metadata={**base_design.metadata, "structural_system": "steel_frame"},
            created_by=base_design.created_by,
            created_at=base_design.created_at,
            updated_at=base_design.updated_at,
        )
        steel_loads = await service.calculate_loads(steel_design, load_params)

        assert loads.dead_loads["structure"] < steel_loads.dead_loads["structure"]

    async def test_live_load_calculations_office(self, service, base_design):
        """Test live load calculations for office building."""
        base_design.building_type = "office"
        load_params = LoadParameters(live_load_factor=1.6)

        loads = await service.calculate_loads(base_design, load_params)

        # Office live load: 50 psf * 10000 sf * 1.6 = 800,000 lbs
        expected_floor_load = 10000 * 50.0 * 1.6
        assert loads.live_loads["floor"] == expected_floor_load

        # Roof live load: 20 psf * 10000 sf * 1.6 = 320,000 lbs
        expected_roof_load = 10000 * 20.0 * 1.6
        assert loads.live_loads["roof"] == expected_roof_load

    async def test_live_load_calculations_residential(self, service, base_design):
        """Test live load calculations for residential building."""
        base_design.building_type = "residential"
        load_params = LoadParameters(live_load_factor=1.4)

        loads = await service.calculate_loads(base_design, load_params)

        # Residential live load: 40 psf * 10000 sf * 1.4 = 560,000 lbs
        expected_floor_load = 10000 * 40.0 * 1.4
        assert loads.live_loads["floor"] == expected_floor_load

    async def test_live_load_calculations_retail(self, service, base_design):
        """Test live load calculations for retail building."""
        base_design.building_type = "retail"
        load_params = LoadParameters(live_load_factor=1.5)

        loads = await service.calculate_loads(base_design, load_params)

        # Retail live load: 75 psf * 10000 sf * 1.5 = 1,125,000 lbs
        expected_floor_load = 10000 * 75.0 * 1.5
        assert loads.live_loads["floor"] == expected_floor_load

        # Retail should have higher live loads than office
        office_design = Design(
            id=str(uuid4()),
            project_id=base_design.project_id,
            name=base_design.name,
            building_type="office",
            location_data=base_design.location_data,
            current_version=base_design.current_version,
            version_number=base_design.version_number,
            status=base_design.status,
            is_deleted=base_design.is_deleted,
            metadata=base_design.metadata.copy(),
            created_by=base_design.created_by,
            created_at=base_design.created_at,
            updated_at=base_design.updated_at,
        )
        office_loads = await service.calculate_loads(office_design, load_params)

        assert loads.live_loads["floor"] > office_loads.live_loads["floor"]

    async def test_live_load_calculations_warehouse(self, service, base_design):
        """Test live load calculations for warehouse building."""
        base_design.building_type = "warehouse"
        load_params = LoadParameters(live_load_factor=1.6)

        loads = await service.calculate_loads(base_design, load_params)

        # Warehouse live load: 125 psf * 10000 sf * 1.6 = 2,000,000 lbs
        expected_floor_load = 10000 * 125.0 * 1.6
        assert loads.live_loads["floor"] == expected_floor_load

        # Warehouse should have the highest live loads
        office_design = Design(
            id=str(uuid4()),
            project_id=base_design.project_id,
            name=base_design.name,
            building_type="office",
            location_data=base_design.location_data,
            current_version=base_design.current_version,
            version_number=base_design.version_number,
            status=base_design.status,
            is_deleted=base_design.is_deleted,
            metadata=base_design.metadata.copy(),
            created_by=base_design.created_by,
            created_at=base_design.created_at,
            updated_at=base_design.updated_at,
        )
        office_loads = await service.calculate_loads(office_design, load_params)

        assert loads.live_loads["floor"] > office_loads.live_loads["floor"]

    async def test_wind_load_calculations_basic(self, service, base_design):
        """Test wind load calculations with basic wind speed."""
        load_params = LoadParameters(wind_speed=90.0)  # mph

        loads = await service.calculate_loads(base_design, load_params)

        # Wind loads should be present
        assert loads.wind_loads is not None
        assert len(loads.wind_loads) > 0

        # Check wind load components
        assert "windward_wall" in loads.wind_loads
        assert "leeward_wall" in loads.wind_loads
        assert "side_walls" in loads.wind_loads
        assert "roof" in loads.wind_loads

        # Verify velocity pressure calculation: qz = 0.00256 * 0.85 * 1.0 * 1.0 * 90^2
        expected_velocity_pressure = 0.00256 * 0.85 * 1.0 * 1.0 * (90**2)
        building_height = base_design.metadata["building_height"]
        building_width = base_design.metadata["building_width"]

        # Windward wall: height * width * velocity_pressure * 0.8
        expected_windward = (
            building_height * building_width * expected_velocity_pressure * 0.8
        )
        assert abs(loads.wind_loads["windward_wall"] - expected_windward) < 0.01

        # All wind loads should be positive
        for load in loads.wind_loads.values():
            assert load > 0

    async def test_wind_load_calculations_high_speed(self, service, base_design):
        """Test wind load calculations with high wind speed."""
        load_params_low = LoadParameters(wind_speed=90.0)
        load_params_high = LoadParameters(wind_speed=120.0)

        loads_low = await service.calculate_loads(base_design, load_params_low)
        loads_high = await service.calculate_loads(base_design, load_params_high)

        # Higher wind speed should result in higher loads (quadratic relationship)
        for component in loads_low.wind_loads:
            assert loads_high.wind_loads[component] > loads_low.wind_loads[component]

        # Verify quadratic relationship: (120/90)^2 = 1.78
        ratio = (
            loads_high.wind_loads["windward_wall"]
            / loads_low.wind_loads["windward_wall"]
        )
        expected_ratio = (120 / 90) ** 2
        assert abs(ratio - expected_ratio) < 0.01

    async def test_wind_load_calculations_no_wind(self, service, base_design):
        """Test that no wind loads are calculated when wind speed is not provided."""
        load_params = LoadParameters(wind_speed=None)

        loads = await service.calculate_loads(base_design, load_params)

        # Wind loads should be None or empty
        assert loads.wind_loads is None or len(loads.wind_loads) == 0

    async def test_seismic_load_calculations_zone_d(self, service, base_design):
        """Test seismic load calculations for seismic design category D."""
        load_params = LoadParameters(seismic_zone="D")

        loads = await service.calculate_loads(base_design, load_params)

        # Seismic loads should be present
        assert loads.seismic_loads is not None
        assert len(loads.seismic_loads) > 0

        # Check seismic load components
        assert "base_shear" in loads.seismic_loads
        assert "story_forces" in loads.seismic_loads
        assert "overturning_moment" in loads.seismic_loads

        # Verify base shear calculation: V = Cs * W, where Cs = 0.20 for zone D
        building_weight = base_design.metadata["building_weight"]
        expected_base_shear = 0.20 * building_weight
        assert loads.seismic_loads["base_shear"] == expected_base_shear

        # Story forces should be 80% of base shear
        expected_story_forces = expected_base_shear * 0.8
        assert loads.seismic_loads["story_forces"] == expected_story_forces

        # Overturning moment should include building height
        building_height = base_design.metadata["building_height"]
        expected_overturning = expected_base_shear * building_height
        assert loads.seismic_loads["overturning_moment"] == expected_overturning

    async def test_seismic_load_calculations_different_zones(
        self, service, base_design
    ):
        """Test seismic load calculations for different seismic zones."""
        zones_and_coefficients = [
            ("A", 0.05),
            ("B", 0.10),
            ("C", 0.15),
            ("D", 0.20),
            ("E", 0.25),
            ("F", 0.30),
        ]

        building_weight = base_design.metadata["building_weight"]
        previous_base_shear = 0

        for zone, expected_cs in zones_and_coefficients:
            load_params = LoadParameters(seismic_zone=zone)
            loads = await service.calculate_loads(base_design, load_params)

            expected_base_shear = expected_cs * building_weight
            assert loads.seismic_loads["base_shear"] == expected_base_shear

            # Higher zones should have higher loads
            assert loads.seismic_loads["base_shear"] > previous_base_shear
            previous_base_shear = loads.seismic_loads["base_shear"]

    async def test_seismic_load_calculations_no_seismic(self, service, base_design):
        """Test that no seismic loads are calculated when seismic zone is not provided."""
        load_params = LoadParameters(seismic_zone=None)

        loads = await service.calculate_loads(base_design, load_params)

        # Seismic loads should be None or empty
        assert loads.seismic_loads is None or len(loads.seismic_loads) == 0

    async def test_load_factor_scaling(self, service, base_design):
        """Test that load factors properly scale the calculated loads."""
        # Test with different load factors
        load_params_1 = LoadParameters(dead_load_factor=1.0, live_load_factor=1.0)
        load_params_2 = LoadParameters(dead_load_factor=1.5, live_load_factor=2.0)

        loads_1 = await service.calculate_loads(base_design, load_params_1)
        loads_2 = await service.calculate_loads(base_design, load_params_2)

        # Dead loads should scale by factor of 1.5
        for component in loads_1.dead_loads:
            expected_scaled = loads_1.dead_loads[component] * 1.5
            assert abs(loads_2.dead_loads[component] - expected_scaled) < 0.01

        # Live loads should scale by factor of 2.0
        for component in loads_1.live_loads:
            expected_scaled = loads_1.live_loads[component] * 2.0
            assert abs(loads_2.live_loads[component] - expected_scaled) < 0.01

    async def test_building_area_scaling(self, service, base_design):
        """Test that loads scale appropriately with building area."""
        # Test with different building areas
        base_design.metadata["building_area"] = 5000  # Half the original area
        load_params = LoadParameters(dead_load_factor=1.0, live_load_factor=1.0)

        loads_small = await service.calculate_loads(base_design, load_params)

        # Double the building area
        base_design.metadata["building_area"] = 10000
        loads_large = await service.calculate_loads(base_design, load_params)

        # Loads should scale proportionally with area
        for component in loads_small.dead_loads:
            expected_scaled = loads_small.dead_loads[component] * 2.0
            assert abs(loads_large.dead_loads[component] - expected_scaled) < 0.01

        for component in loads_small.live_loads:
            expected_scaled = loads_small.live_loads[component] * 2.0
            assert abs(loads_large.live_loads[component] - expected_scaled) < 0.01

    async def test_combined_load_calculations(self, service, base_design):
        """Test load calculations with all load types present."""
        load_params = LoadParameters(
            dead_load_factor=1.2,
            live_load_factor=1.6,
            wind_speed=100.0,
            seismic_zone="C",
            snow_load=30.0,
        )

        loads = await service.calculate_loads(base_design, load_params)

        # All load types should be present
        assert loads.dead_loads is not None and len(loads.dead_loads) > 0
        assert loads.live_loads is not None and len(loads.live_loads) > 0
        assert loads.wind_loads is not None and len(loads.wind_loads) > 0
        assert loads.seismic_loads is not None and len(loads.seismic_loads) > 0

        # All loads should be positive
        for load in loads.dead_loads.values():
            assert load > 0
        for load in loads.live_loads.values():
            assert load > 0
        for load in loads.wind_loads.values():
            assert load > 0
        for load in loads.seismic_loads.values():
            assert load > 0

    async def test_edge_case_zero_building_area(self, service, base_design):
        """Test load calculations with zero building area."""
        base_design.metadata["building_area"] = 0
        load_params = LoadParameters()

        loads = await service.calculate_loads(base_design, load_params)

        # All loads should be zero
        for load in loads.dead_loads.values():
            assert load == 0
        for load in loads.live_loads.values():
            assert load == 0

    async def test_edge_case_missing_metadata(self, service, base_design):
        """Test load calculations with missing metadata."""
        # Remove building area from metadata
        del base_design.metadata["building_area"]
        load_params = LoadParameters()

        loads = await service.calculate_loads(base_design, load_params)

        # Should use default values (10000 sq ft)
        assert loads.dead_loads is not None
        assert loads.live_loads is not None

        # Verify default area is used - steel frame is used when structural_system is not in metadata
        expected_structure_load = 10000 * 15.0 * 1.2  # Default steel frame
        assert loads.dead_loads["structure"] == expected_structure_load

    async def test_unknown_building_type(self, service, base_design):
        """Test load calculations with unknown building type."""
        base_design.building_type = "unknown_type"
        load_params = LoadParameters(live_load_factor=1.0)

        loads = await service.calculate_loads(base_design, load_params)

        # Should use default live load (50 psf for office)
        expected_floor_load = 10000 * 50.0 * 1.0
        assert loads.live_loads["floor"] == expected_floor_load
