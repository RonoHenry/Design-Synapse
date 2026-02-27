"""Unit tests for EnergyAnalysisService."""

from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from src.api.v1.schemas.analysis import (BuildingParameters,
                                         EnergyAnalysisRequest, EnergyEstimate,
                                         EnvelopeMetrics)
from src.core.exceptions import NotFoundError, ValidationError
from src.models.design import Design
from src.models.energy_analysis import EnergyAnalysis
from src.repositories.design_repository import DesignRepository
from src.repositories.energy_analysis_repository import \
    EnergyAnalysisRepository
from src.services.energy_analysis_service import EnergyAnalysisService


class TestEnergyAnalysisService:
    """Unit tests for EnergyAnalysisService."""

    @pytest.fixture
    def mock_energy_repo(self):
        """Mock energy analysis repository."""
        return AsyncMock(spec=EnergyAnalysisRepository)

    @pytest.fixture
    def mock_design_repo(self):
        """Mock design repository."""
        return AsyncMock(spec=DesignRepository)

    @pytest.fixture
    def energy_service(self, mock_energy_repo, mock_design_repo):
        """EnergyAnalysisService instance with mocked dependencies."""
        return EnergyAnalysisService(mock_energy_repo, mock_design_repo)

    @pytest.fixture
    def sample_design(self):
        """Sample design for testing."""
        return Design(
            id=str(uuid4()),
            project_id=str(uuid4()),
            name="Test Office Building",
            description="A test office building",
            building_type="commercial",
            location_data={
                "address": "123 Main St",
                "city": "San Francisco",
                "state": "California",
                "country": "USA",
                "postal_code": "94102",
                "latitude": 37.7749,
                "longitude": -122.4194,
                "jurisdiction": "City and County of San Francisco",
            },
            current_version="1.0",
            version_number=1,
            status="draft",
            design_metadata={},
            created_by=str(uuid4()),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            is_deleted=False,
        )

    @pytest.fixture
    def sample_building_parameters(self):
        """Sample building parameters."""
        return BuildingParameters(
            total_area=50000.0,
            number_of_floors=5,
            occupancy_type="office",
            hvac_system="VAV",
            envelope_properties={
                "wall_type": "steel_frame",
                "roof_type": "built_up",
                "window_type": "double_pane",
            },
        )

    @pytest.fixture
    def sample_request(self, sample_building_parameters):
        """Sample energy analysis request."""
        return EnergyAnalysisRequest(
            standards=["ASHRAE-90.1", "LEED"],
            climate_zone="4A",
            building_parameters=sample_building_parameters,
        )

    @pytest.mark.asyncio
    async def test_analyze_energy_design_not_found(
        self, energy_service, mock_design_repo, sample_request
    ):
        """Test energy analysis with non-existent design."""
        # Setup
        design_id = uuid4()
        mock_design_repo.get.return_value = None

        # Execute & Verify
        with pytest.raises(NotFoundError) as exc_info:
            await energy_service.analyze_energy(design_id, sample_request)

        assert f"Design {design_id} not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_analyze_energy_deleted_design(
        self, energy_service, mock_design_repo, sample_design, sample_request
    ):
        """Test energy analysis with deleted design."""
        # Setup
        sample_design.is_deleted = True
        mock_design_repo.get.return_value = sample_design

        # Execute & Verify
        with pytest.raises(ValidationError) as exc_info:
            await energy_service.analyze_energy(UUID(sample_design.id), sample_request)

        assert f"Cannot analyze energy for deleted design {sample_design.id}" in str(
            exc_info.value
        )

    @pytest.mark.asyncio
    async def test_analyze_energy_success(
        self,
        energy_service,
        mock_energy_repo,
        mock_design_repo,
        sample_design,
        sample_request,
    ):
        """Test successful energy analysis initiation."""
        # Setup
        mock_design_repo.get.return_value = sample_design

        analysis_id = str(uuid4())

        def create_side_effect(energy_analysis):
            energy_analysis.id = analysis_id
            return energy_analysis

        mock_energy_repo.create.side_effect = create_side_effect
        mock_energy_repo.update = AsyncMock()

        # Execute
        response = await energy_service.analyze_energy(
            UUID(sample_design.id), sample_request
        )

        # Verify
        assert response.id is not None
        assert response.design_id == UUID(sample_design.id)
        assert response.design_version == sample_design.current_version
        assert response.standards == sample_request.standards
        assert response.climate_zone == sample_request.climate_zone
        assert response.started_at is not None

        mock_design_repo.get.assert_called_once_with(sample_design.id)
        mock_energy_repo.create.assert_called_once()

    # ============================================================================
    # R-value Calculation Tests
    # ============================================================================

    @pytest.mark.asyncio
    async def test_calculate_wall_r_value_wood_frame(self, energy_service):
        """Test R-value calculations for wood frame wall assemblies."""
        # Setup wood frame wall data
        wall_data = {
            "construction_type": "wood_frame",
            "insulation_r_value": 13.0,  # R-13 batt insulation
            "sheathing_r_value": 0.6,  # OSB sheathing
            "siding_r_value": 0.8,  # Vinyl siding
            "interior_finish_r_value": 0.9,  # Drywall
            "air_film_r_values": 1.0,  # Interior and exterior air films
        }

        # Execute
        r_value = await energy_service._calculate_wall_r_value(wall_data, "4A")

        # Verify
        # Total R-value = 13.0 + 0.6 + 0.8 + 0.9 + 1.0 = 16.3
        # With thermal bridging factor of 0.8: 16.3 * 0.8 = 13.04
        expected_r_value = 16.3 * 0.8
        assert abs(r_value - expected_r_value) < 0.01
        assert r_value > 0

    @pytest.mark.asyncio
    async def test_calculate_wall_r_value_steel_frame(self, energy_service):
        """Test R-value calculations for steel frame wall assemblies."""
        # Setup steel frame wall data (higher thermal bridging)
        wall_data = {
            "construction_type": "steel_frame",
            "insulation_r_value": 19.0,  # R-19 batt insulation
            "sheathing_r_value": 0.6,  # OSB sheathing
            "siding_r_value": 1.2,  # Brick veneer
            "interior_finish_r_value": 0.9,  # Drywall
            "air_film_r_values": 1.0,  # Interior and exterior air films
        }

        # Execute
        r_value = await energy_service._calculate_wall_r_value(wall_data, "4A")

        # Verify
        # Total R-value = 19.0 + 0.6 + 1.2 + 0.9 + 1.0 = 22.7
        # With thermal bridging factor of 0.8: 22.7 * 0.8 = 18.16
        expected_r_value = 22.7 * 0.8
        assert abs(r_value - expected_r_value) < 0.01
        assert r_value > 0

    @pytest.mark.asyncio
    async def test_calculate_roof_r_value_pitched_roof(self, energy_service):
        """Test R-value calculations for pitched roof assemblies."""
        # Setup pitched roof data
        roof_data = {
            "construction_type": "pitched_roof",
            "insulation_r_value": 30.0,  # R-30 blown insulation
            "sheathing_r_value": 0.6,  # Plywood sheathing
            "roofing_r_value": 0.4,  # Asphalt shingles
            "air_film_r_values": 1.2,  # Air films
        }

        # Execute
        r_value = await energy_service._calculate_roof_r_value(roof_data, "4A")

        # Verify
        # Total R-value = 30.0 + 0.6 + 0.4 + 1.2 = 32.2
        # With thermal bridging factor of 0.9: 32.2 * 0.9 = 28.98
        expected_r_value = 32.2 * 0.9
        assert abs(r_value - expected_r_value) < 0.01
        assert r_value > 0

    @pytest.mark.asyncio
    async def test_calculate_roof_r_value_flat_roof(self, energy_service):
        """Test R-value calculations for flat roof assemblies."""
        # Setup flat roof data
        roof_data = {
            "construction_type": "flat_roof",
            "insulation_r_value": 25.0,  # R-25 rigid insulation
            "sheathing_r_value": 0.8,  # Concrete deck
            "roofing_r_value": 0.3,  # Built-up roofing
            "air_film_r_values": 1.0,  # Air films
        }

        # Execute
        r_value = await energy_service._calculate_roof_r_value(roof_data, "4A")

        # Verify
        # Total R-value = 25.0 + 0.8 + 0.3 + 1.0 = 27.1
        # With thermal bridging factor of 0.9: 27.1 * 0.9 = 24.39
        expected_r_value = 27.1 * 0.9
        assert abs(r_value - expected_r_value) < 0.01
        assert r_value > 0

    # ============================================================================
    # U-factor Calculation Tests
    # ============================================================================

    @pytest.mark.asyncio
    async def test_calculate_window_u_factor_single_pane(self, energy_service):
        """Test U-factor calculations for single pane windows."""
        # Setup single pane window data
        window_data = {
            "glazing_type": "single_pane",
            "frame_type": "aluminum",
            "low_e_coating": False,
            "gas_fill": "air",
            "u_factor": 1.0,  # Base U-factor for single pane
        }

        # Execute
        u_factor = await energy_service._calculate_window_u_factor(window_data, "4A")

        # Verify
        # Base U-factor = 1.0
        # Aluminum frame adjustment = 1.0 (no improvement)
        # No low-E coating = 1.0 (no improvement)
        # Air fill = 1.0 (no improvement)
        # Final U-factor = 1.0 * 1.0 * 1.0 * 1.0 = 1.0
        expected_u_factor = 1.0
        assert abs(u_factor - expected_u_factor) < 0.01
        assert u_factor > 0

    @pytest.mark.asyncio
    async def test_calculate_window_u_factor_double_pane_vinyl(self, energy_service):
        """Test U-factor calculations for double pane vinyl windows."""
        # Setup double pane vinyl window data
        window_data = {
            "glazing_type": "double_pane",
            "frame_type": "vinyl",
            "low_e_coating": True,
            "gas_fill": "argon",
            "u_factor": 0.50,  # Base U-factor for double pane
        }

        # Execute
        u_factor = await energy_service._calculate_window_u_factor(window_data, "4A")

        # Verify
        # Base U-factor = 0.50
        # Vinyl frame adjustment = 0.95 (5% improvement)
        # Low-E coating = 0.85 (15% improvement)
        # Argon fill = 0.90 (10% improvement)
        # Final U-factor = 0.50 * 0.95 * 0.85 * 0.90 = 0.36225
        expected_u_factor = 0.50 * 0.95 * 0.85 * 0.90
        assert abs(u_factor - expected_u_factor) < 0.01
        assert u_factor > 0

    @pytest.mark.asyncio
    async def test_calculate_window_u_factor_triple_pane_fiberglass(
        self, energy_service
    ):
        """Test U-factor calculations for triple pane fiberglass windows."""
        # Setup triple pane fiberglass window data
        window_data = {
            "glazing_type": "triple_pane",
            "frame_type": "fiberglass",
            "low_e_coating": True,
            "gas_fill": "krypton",
            "u_factor": 0.30,  # Base U-factor for triple pane
        }

        # Execute
        u_factor = await energy_service._calculate_window_u_factor(window_data, "4A")

        # Verify
        # Base U-factor = 0.30
        # Fiberglass frame adjustment = 0.85 (15% improvement)
        # Low-E coating = 0.85 (15% improvement)
        # Krypton fill = 0.85 (15% improvement)
        # Final U-factor = 0.30 * 0.85 * 0.85 * 0.85 = 0.184
        expected_u_factor = 0.30 * 0.85 * 0.85 * 0.85
        assert abs(u_factor - expected_u_factor) < 0.01
        assert u_factor > 0

    # ============================================================================
    # Energy Consumption Tests for Different Climate Zones
    # ============================================================================

    @pytest.mark.asyncio
    async def test_estimate_consumption_hot_climate_1a(
        self, energy_service, sample_design, sample_building_parameters
    ):
        """Test consumption estimates for hot climate zone 1A (Very Hot-Humid)."""
        # Setup envelope metrics for hot climate
        envelope_metrics = EnvelopeMetrics(
            wall_r_value=13.0,
            roof_r_value=19.0,
            window_u_factor=0.40,
            infiltration_rate=0.35,
        )

        # Execute
        energy_estimate = await energy_service.estimate_consumption(
            sample_design, sample_building_parameters, envelope_metrics, "1A"
        )

        # Verify
        assert isinstance(energy_estimate, EnergyEstimate)
        assert energy_estimate.annual_consumption_kwh > 0
        assert energy_estimate.heating_kwh >= 0
        assert energy_estimate.cooling_kwh > 0  # Should have significant cooling
        assert energy_estimate.lighting_kwh > 0
        assert energy_estimate.equipment_kwh > 0

        # In hot climate, cooling should be significant
        hvac_total = energy_estimate.heating_kwh + energy_estimate.cooling_kwh
        if hvac_total > 0:
            cooling_ratio = energy_estimate.cooling_kwh / hvac_total
            assert cooling_ratio > 0.1, "Hot climate should have some cooling energy"

        # Verify cost calculation
        assert energy_estimate.estimated_cost > 0
        expected_cost_range = Decimal(
            str(energy_estimate.annual_consumption_kwh * 0.08)
        )
        assert energy_estimate.estimated_cost >= expected_cost_range

    @pytest.mark.asyncio
    async def test_estimate_consumption_mixed_climate_4a(
        self, energy_service, sample_design, sample_building_parameters
    ):
        """Test consumption estimates for mixed climate zone 4A (Mixed-Humid)."""
        # Setup envelope metrics for mixed climate
        envelope_metrics = EnvelopeMetrics(
            wall_r_value=15.0,
            roof_r_value=25.0,
            window_u_factor=0.35,
            infiltration_rate=0.30,
        )

        # Execute
        energy_estimate = await energy_service.estimate_consumption(
            sample_design, sample_building_parameters, envelope_metrics, "4A"
        )

        # Verify
        assert isinstance(energy_estimate, EnergyEstimate)
        assert energy_estimate.annual_consumption_kwh > 0
        assert energy_estimate.heating_kwh > 0  # Should have heating
        assert energy_estimate.cooling_kwh > 0  # Should have cooling
        assert energy_estimate.lighting_kwh > 0
        assert energy_estimate.equipment_kwh > 0

        # In mixed climate, both heating and cooling should be present
        assert energy_estimate.heating_kwh > 0
        assert energy_estimate.cooling_kwh > 0

        # Verify reasonable consumption per square foot
        consumption_per_sqft = (
            energy_estimate.annual_consumption_kwh
            / sample_building_parameters.total_area
        )
        assert (
            10.0 <= consumption_per_sqft <= 500.0
        ), "Consumption per sq ft should be reasonable"

    @pytest.mark.asyncio
    async def test_estimate_consumption_cold_climate_7(
        self, energy_service, sample_design, sample_building_parameters
    ):
        """Test consumption estimates for cold climate zone 7 (Very Cold)."""
        # Setup envelope metrics for cold climate
        envelope_metrics = EnvelopeMetrics(
            wall_r_value=20.0,
            roof_r_value=38.0,
            window_u_factor=0.25,
            infiltration_rate=0.25,
        )

        # Execute
        energy_estimate = await energy_service.estimate_consumption(
            sample_design, sample_building_parameters, envelope_metrics, "7"
        )

        # Verify
        assert isinstance(energy_estimate, EnergyEstimate)
        assert energy_estimate.annual_consumption_kwh > 0
        assert energy_estimate.heating_kwh > 0  # Should have significant heating
        assert energy_estimate.cooling_kwh >= 0  # May have minimal cooling
        assert energy_estimate.lighting_kwh > 0
        assert energy_estimate.equipment_kwh > 0

        # In cold climate, heating should dominate
        hvac_total = energy_estimate.heating_kwh + energy_estimate.cooling_kwh
        if hvac_total > 0:
            heating_ratio = energy_estimate.heating_kwh / hvac_total
            assert (
                heating_ratio > 0.7
            ), "Cold climate should have much more heating than cooling"

    # ============================================================================
    # Building Type Specific Tests
    # ============================================================================

    @pytest.mark.asyncio
    async def test_calculate_lighting_energy_office(self, energy_service):
        """Test lighting energy calculations for office buildings."""
        # Setup office building parameters
        building_parameters = BuildingParameters(
            total_area=20000.0,
            number_of_floors=4,
            occupancy_type="office",
        )

        # Execute
        lighting_kwh = await energy_service._calculate_lighting_energy(
            building_parameters, "office"
        )

        # Verify
        # Office lighting density = 1.1 W/sq ft
        # Operating hours = 3000 hours/year
        # Expected energy = 1.1 * 20000 * 3000 / 1000 = 66,000 kWh
        expected_lighting = 1.1 * 20000.0 * 3000 / 1000
        assert abs(lighting_kwh - expected_lighting) < 0.01
        assert lighting_kwh > 0

    @pytest.mark.asyncio
    async def test_calculate_lighting_energy_retail(self, energy_service):
        """Test lighting energy calculations for retail buildings."""
        # Setup retail building parameters
        building_parameters = BuildingParameters(
            total_area=15000.0,
            number_of_floors=2,
            occupancy_type="retail",
        )

        # Execute
        lighting_kwh = await energy_service._calculate_lighting_energy(
            building_parameters, "retail"
        )

        # Verify
        # Retail lighting density = 1.5 W/sq ft
        # Operating hours = 4000 hours/year
        # Expected energy = 1.5 * 15000 * 4000 / 1000 = 90,000 kWh
        expected_lighting = 1.5 * 15000.0 * 4000 / 1000
        assert abs(lighting_kwh - expected_lighting) < 0.01
        assert lighting_kwh > 0

    @pytest.mark.asyncio
    async def test_calculate_equipment_energy_industrial(self, energy_service):
        """Test equipment energy calculations for industrial buildings."""
        # Setup industrial building parameters
        building_parameters = BuildingParameters(
            total_area=50000.0,
            number_of_floors=1,
            occupancy_type="industrial",
        )

        # Execute
        equipment_kwh = await energy_service._calculate_equipment_energy(
            building_parameters, "industrial"
        )

        # Verify
        # Industrial equipment density = 3.0 W/sq ft
        # Operating hours = 4000 hours/year
        # Expected energy = 3.0 * 50000 * 4000 / 1000 = 600,000 kWh
        expected_equipment = 3.0 * 50000.0 * 4000 / 1000
        assert abs(equipment_kwh - expected_equipment) < 0.01
        assert equipment_kwh > 0

    @pytest.mark.asyncio
    async def test_calculate_equipment_energy_residential(self, energy_service):
        """Test equipment energy calculations for residential buildings."""
        # Setup residential building parameters
        building_parameters = BuildingParameters(
            total_area=2500.0,
            number_of_floors=2,
            occupancy_type="residential",
        )

        # Execute
        equipment_kwh = await energy_service._calculate_equipment_energy(
            building_parameters, "residential"
        )

        # Verify
        # Residential equipment density = 2.0 W/sq ft
        # Operating hours = 4000 hours/year
        # Expected energy = 2.0 * 2500 * 4000 / 1000 = 20,000 kWh
        expected_equipment = 2.0 * 2500.0 * 4000 / 1000
        assert abs(equipment_kwh - expected_equipment) < 0.01
        assert equipment_kwh > 0

    # ============================================================================
    # Edge Cases and Error Handling
    # ============================================================================

    @pytest.mark.asyncio
    async def test_calculate_envelope_performance_missing_data(
        self, energy_service, sample_design, sample_building_parameters
    ):
        """Test envelope performance calculation with missing design data."""
        # Execute - should handle missing data gracefully
        envelope_metrics = await energy_service.calculate_envelope_performance(
            sample_design, sample_building_parameters, "4A"
        )

        # Verify - should return reasonable defaults
        assert isinstance(envelope_metrics, EnvelopeMetrics)
        assert envelope_metrics.wall_r_value > 0
        assert envelope_metrics.roof_r_value > 0
        assert envelope_metrics.window_u_factor > 0
        assert envelope_metrics.infiltration_rate > 0

    @pytest.mark.asyncio
    async def test_estimate_consumption_minimum_area(
        self, energy_service, sample_design
    ):
        """Test consumption estimation with minimum building area."""
        # Setup building parameters with minimum area
        building_parameters = BuildingParameters(
            total_area=1.0,  # Minimum area
            number_of_floors=1,
            occupancy_type="office",
        )

        envelope_metrics = EnvelopeMetrics(
            wall_r_value=15.0,
            roof_r_value=25.0,
            window_u_factor=0.35,
            infiltration_rate=0.30,
        )

        # Execute
        energy_estimate = await energy_service.estimate_consumption(
            sample_design, building_parameters, envelope_metrics, "4A"
        )

        # Verify - should handle minimum area gracefully
        assert isinstance(energy_estimate, EnergyEstimate)
        assert energy_estimate.annual_consumption_kwh > 0
        assert energy_estimate.heating_kwh >= 0
        assert energy_estimate.cooling_kwh >= 0
        assert energy_estimate.lighting_kwh > 0
        assert energy_estimate.equipment_kwh > 0

    @pytest.mark.asyncio
    async def test_get_climate_data_unknown_zone(self, energy_service):
        """Test climate data retrieval for unknown climate zone."""
        # Execute
        climate_data = energy_service._get_climate_data("UNKNOWN")

        # Verify - should return default climate zone 4A data
        expected_data = energy_service._get_climate_data("4A")
        assert climate_data == expected_data
        assert "hdd" in climate_data
        assert "cdd" in climate_data
        assert "name" in climate_data

    @pytest.mark.asyncio
    async def test_generate_certificate_success(self, energy_service):
        """Test successful certificate generation."""
        # Setup
        analysis_id = uuid4()
        envelope_metrics = EnvelopeMetrics(
            wall_r_value=15.0,
            roof_r_value=25.0,
            window_u_factor=0.35,
            infiltration_rate=0.30,
        )
        energy_estimate = EnergyEstimate(
            annual_consumption_kwh=50000.0,
            heating_kwh=20000.0,
            cooling_kwh=15000.0,
            lighting_kwh=10000.0,
            equipment_kwh=5000.0,
            estimated_cost=Decimal("6000.00"),
        )
        standards = ["ASHRAE-90.1", "LEED"]

        # Execute
        certificate_url = await energy_service.generate_certificate(
            analysis_id, envelope_metrics, energy_estimate, standards
        )

        # Verify
        assert isinstance(certificate_url, str)
        assert len(certificate_url) > 0
        assert certificate_url.startswith(("http://", "https://"))
        assert str(analysis_id) in certificate_url

    @pytest.mark.asyncio
    async def test_get_analysis_results_not_found(
        self, energy_service, mock_energy_repo
    ):
        """Test getting analysis results for non-existent analysis."""
        # Setup
        analysis_id = uuid4()
        mock_energy_repo.get.return_value = None

        # Execute & Verify
        with pytest.raises(NotFoundError) as exc_info:
            await energy_service.get_analysis_results(analysis_id)

        assert f"Energy analysis {analysis_id} not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_infiltration_rate_calculation_multi_floor(self, energy_service):
        """Test infiltration rate calculation for multi-floor buildings."""
        # Setup multi-floor building parameters
        building_parameters = BuildingParameters(
            total_area=100000.0,
            number_of_floors=10,  # Tall building
            occupancy_type="office",
        )

        envelope_data = {
            "walls": {"construction_type": "steel_frame"},
            "roof": {"construction_type": "flat_roof"},
            "windows": {"glazing_type": "double_pane"},
        }

        # Execute
        infiltration_rate = await energy_service._calculate_infiltration_rate(
            envelope_data, building_parameters
        )

        # Verify
        assert infiltration_rate > 0
        # Taller buildings should have higher infiltration due to stack effect
        # Height factor = 1.0 + (10 - 1) * 0.05 = 1.45
        # Base infiltration = 0.35 ACH
        # Natural infiltration = 0.35 * 1.0 * 1.45 / 20 = 0.025375 ACH
        expected_rate = 0.35 * 1.0 * 1.45 / 20
        assert abs(infiltration_rate - expected_rate) < 0.01
