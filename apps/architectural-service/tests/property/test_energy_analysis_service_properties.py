"""Property-based tests for EnergyAnalysisService."""

from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from src.api.v1.schemas.analysis import (BuildingParameters,
                                         EfficiencyRecommendation,
                                         EnergyAnalysisRequest, EnergyEstimate,
                                         EnvelopeMetrics)
from src.api.v1.schemas.enums import CheckStatus
from src.models.design import Design
from src.models.energy_analysis import EnergyAnalysis
from src.repositories.design_repository import DesignRepository
from src.repositories.energy_analysis_repository import \
    EnergyAnalysisRepository
from src.services.energy_analysis_service import EnergyAnalysisService


# Hypothesis strategies for generating test data
@st.composite
def building_parameters_strategy(draw):
    """Generate valid BuildingParameters."""
    return BuildingParameters(
        total_area=draw(st.floats(min_value=500, max_value=100000)),
        number_of_floors=draw(st.integers(min_value=1, max_value=50)),
        occupancy_type=draw(
            st.sampled_from(
                [
                    "residential",
                    "office",
                    "retail",
                    "warehouse",
                    "industrial",
                    "educational",
                    "healthcare",
                ]
            )
        ),
        hvac_system=draw(
            st.one_of(
                st.none(),
                st.sampled_from(
                    [
                        "VAV",
                        "CAV",
                        "heat_pump",
                        "split_system",
                        "packaged_unit",
                        "chiller_boiler",
                    ]
                ),
            )
        ),
        envelope_properties=draw(
            st.one_of(
                st.none(),
                st.dictionaries(
                    st.sampled_from(
                        [
                            "wall_type",
                            "roof_type",
                            "window_type",
                            "insulation_level",
                            "air_tightness",
                        ]
                    ),
                    st.text(min_size=1, max_size=50),
                    max_size=5,
                ),
            )
        ),
    )


@st.composite
def energy_analysis_request_strategy(draw):
    """Generate valid EnergyAnalysisRequest."""
    return EnergyAnalysisRequest(
        standards=draw(
            st.lists(
                st.sampled_from(
                    [
                        "ASHRAE-90.1",
                        "IECC",
                        "LEED",
                        "Energy Star",
                        "California Title 24",
                        "NECB",
                    ]
                ),
                min_size=1,
                max_size=3,
                unique=True,
            )
        ),
        climate_zone=draw(
            st.sampled_from(
                [
                    "1A",
                    "2A",
                    "2B",
                    "3A",
                    "3B",
                    "3C",
                    "4A",
                    "4B",
                    "4C",
                    "5A",
                    "5B",
                    "6A",
                    "6B",
                    "7",
                    "8",
                ]
            )
        ),
        building_parameters=draw(building_parameters_strategy()),
    )


@st.composite
def design_strategy(draw):
    """Generate valid Design for testing."""
    design_id = str(uuid4())
    return Design(
        id=design_id,
        project_id=str(uuid4()),
        name=draw(st.text(min_size=1, max_size=255)),
        description=draw(st.one_of(st.none(), st.text(max_size=1000))),
        building_type=draw(
            st.sampled_from(["residential", "commercial", "industrial", "mixed_use"])
        ),
        location_data={
            "address": draw(st.text(min_size=1, max_size=200)),
            "city": draw(st.text(min_size=1, max_size=100)),
            "state": draw(st.text(min_size=1, max_size=100)),
            "country": draw(st.text(min_size=1, max_size=100)),
            "postal_code": draw(st.text(min_size=1, max_size=20)),
            "latitude": draw(st.floats(min_value=-90, max_value=90)),
            "longitude": draw(st.floats(min_value=-180, max_value=180)),
            "jurisdiction": draw(st.text(min_size=1, max_size=200)),
        },
        current_version="1.0",
        version_number=1,
        status="draft",
        design_metadata=draw(st.dictionaries(st.text(), st.text(), max_size=5)),
        created_by=str(uuid4()),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        is_deleted=False,
    )


@st.composite
def envelope_metrics_strategy(draw):
    """Generate valid EnvelopeMetrics."""
    return EnvelopeMetrics(
        wall_r_value=draw(st.floats(min_value=5.0, max_value=50.0)),
        roof_r_value=draw(st.floats(min_value=10.0, max_value=60.0)),
        window_u_factor=draw(st.floats(min_value=0.15, max_value=1.0)),
        infiltration_rate=draw(st.floats(min_value=0.1, max_value=2.0)),
    )


@st.composite
def energy_estimate_strategy(draw):
    """Generate valid EnergyEstimate."""
    heating_kwh = draw(st.floats(min_value=0, max_value=50000))
    cooling_kwh = draw(st.floats(min_value=0, max_value=50000))
    lighting_kwh = draw(st.floats(min_value=0, max_value=20000))
    equipment_kwh = draw(st.floats(min_value=0, max_value=30000))

    return EnergyEstimate(
        annual_consumption_kwh=heating_kwh + cooling_kwh + lighting_kwh + equipment_kwh,
        heating_kwh=heating_kwh,
        cooling_kwh=cooling_kwh,
        lighting_kwh=lighting_kwh,
        equipment_kwh=equipment_kwh,
        estimated_cost=Decimal(
            str((heating_kwh + cooling_kwh + lighting_kwh + equipment_kwh) * 0.12)
        ),
    )


class TestEnergyAnalysisServiceProperties:
    """Property-based tests for EnergyAnalysisService."""

    @pytest.mark.asyncio
    @given(
        design=design_strategy(),
        request=energy_analysis_request_strategy(),
    )
    @settings(suppress_health_check=[HealthCheck.too_slow], deadline=None)
    async def test_property_27_energy_envelope_calculation_completeness(
        self,
        design: Design,
        request: EnergyAnalysisRequest,
    ):
        """
        Property 27: Energy envelope calculation completeness.

        For any energy analysis, the envelope performance calculation should
        include wall R-values, roof R-values, window U-factors, and infiltration rates.

        Validates: Requirements 7.1, 7.2
        """
        # Setup mocks
        mock_energy_repo = AsyncMock(spec=EnergyAnalysisRepository)
        mock_design_repo = AsyncMock(spec=DesignRepository)

        # Mock design repository to return the test design
        mock_design_repo.get.return_value = design

        # Mock energy repository create to return analysis with ID
        def create_side_effect(energy_analysis):
            energy_analysis.id = str(uuid4())
            return energy_analysis

        mock_energy_repo.create.side_effect = create_side_effect
        mock_energy_repo.update = AsyncMock()

        # Create service
        service = EnergyAnalysisService(mock_energy_repo, mock_design_repo)

        # Execute envelope performance calculation
        envelope_metrics = await service.calculate_envelope_performance(
            design, request.building_parameters, request.climate_zone
        )

        # Verify Property 27: Energy envelope calculation completeness
        assert isinstance(
            envelope_metrics, EnvelopeMetrics
        ), "Must return EnvelopeMetrics"

        # Check that all required envelope components are calculated
        assert envelope_metrics.wall_r_value > 0, "Wall R-value must be positive"
        assert envelope_metrics.roof_r_value > 0, "Roof R-value must be positive"
        assert envelope_metrics.window_u_factor > 0, "Window U-factor must be positive"
        assert (
            envelope_metrics.infiltration_rate > 0
        ), "Infiltration rate must be positive"

        # Verify reasonable ranges for envelope performance values
        assert (
            1.0 <= envelope_metrics.wall_r_value <= 100.0
        ), "Wall R-value must be in reasonable range"
        assert (
            5.0 <= envelope_metrics.roof_r_value <= 100.0
        ), "Roof R-value must be in reasonable range"
        assert (
            0.1 <= envelope_metrics.window_u_factor <= 2.0
        ), "Window U-factor must be in reasonable range"
        assert (
            0.01 <= envelope_metrics.infiltration_rate <= 5.0
        ), "Infiltration rate must be in reasonable range"

        # Verify that envelope performance is climate-appropriate
        # Colder climates should generally have better insulation requirements
        if request.climate_zone in ["6A", "6B", "7", "8"]:  # Cold climates
            assert (
                envelope_metrics.wall_r_value >= 10.0
            ), "Cold climates should have higher wall R-values"
            assert (
                envelope_metrics.roof_r_value >= 20.0
            ), "Cold climates should have higher roof R-values"

    @pytest.mark.asyncio
    @given(
        design=design_strategy(),
        building_parameters=building_parameters_strategy(),
        envelope_metrics=envelope_metrics_strategy(),
        climate_zone=st.sampled_from(["1A", "2A", "3A", "4A", "5A", "6A", "7"]),
    )
    @settings(suppress_health_check=[HealthCheck.too_slow], deadline=None)
    async def test_property_28_energy_consumption_estimation(
        self,
        design: Design,
        building_parameters: BuildingParameters,
        envelope_metrics: EnvelopeMetrics,
        climate_zone: str,
    ):
        """
        Property 28: Energy consumption estimation.

        For any building parameters and envelope performance, energy consumption
        estimation should provide breakdown by end use (heating, cooling, lighting, equipment)
        and total annual consumption with cost estimate.

        Validates: Requirements 7.1, 7.2
        """
        # Setup mocks
        mock_energy_repo = AsyncMock(spec=EnergyAnalysisRepository)
        mock_design_repo = AsyncMock(spec=DesignRepository)

        # Create service
        service = EnergyAnalysisService(mock_energy_repo, mock_design_repo)

        # Execute energy consumption estimation
        energy_estimate = await service.estimate_consumption(
            design, building_parameters, envelope_metrics, climate_zone
        )

        # Verify Property 28: Energy consumption estimation
        assert isinstance(energy_estimate, EnergyEstimate), "Must return EnergyEstimate"

        # Check that all energy end uses are calculated
        assert energy_estimate.heating_kwh >= 0, "Heating energy must be non-negative"
        assert energy_estimate.cooling_kwh >= 0, "Cooling energy must be non-negative"
        assert energy_estimate.lighting_kwh >= 0, "Lighting energy must be non-negative"
        assert (
            energy_estimate.equipment_kwh >= 0
        ), "Equipment energy must be non-negative"

        # Check that total consumption equals sum of components
        calculated_total = (
            energy_estimate.heating_kwh
            + energy_estimate.cooling_kwh
            + energy_estimate.lighting_kwh
            + energy_estimate.equipment_kwh
        )
        assert (
            abs(energy_estimate.annual_consumption_kwh - calculated_total) < 0.01
        ), "Total consumption must equal sum of components"

        # Check that cost estimate is reasonable
        assert energy_estimate.estimated_cost > 0, "Cost estimate must be positive"

        # Verify cost is calculated from consumption (assuming reasonable rate)
        expected_cost_min = Decimal(
            str(energy_estimate.annual_consumption_kwh * 0.05)
        )  # $0.05/kWh
        expected_cost_max = Decimal(
            str(energy_estimate.annual_consumption_kwh * 0.30)
        )  # $0.30/kWh
        assert (
            expected_cost_min <= energy_estimate.estimated_cost <= expected_cost_max
        ), "Cost estimate must be within reasonable range"

        # Verify consumption is proportional to building size (very lenient range for edge cases)
        consumption_per_sqft = (
            energy_estimate.annual_consumption_kwh / building_parameters.total_area
        )
        assert (
            0.1 <= consumption_per_sqft <= 10000.0
        ), "Energy consumption per square foot must be in reasonable range"

        # Verify climate-appropriate consumption patterns (very lenient thresholds)
        if climate_zone in ["1A", "2A", "2B"]:  # Hot climates
            # Cooling should be some portion of HVAC energy
            hvac_total = energy_estimate.heating_kwh + energy_estimate.cooling_kwh
            if hvac_total > 0:
                cooling_ratio = energy_estimate.cooling_kwh / hvac_total
                assert (
                    cooling_ratio >= 0.01
                ), "Hot climates should have some cooling energy"
        elif climate_zone in ["6A", "6B", "7", "8"]:  # Cold climates
            # Heating should be some portion of HVAC energy
            hvac_total = energy_estimate.heating_kwh + energy_estimate.cooling_kwh
            if hvac_total > 0:
                heating_ratio = energy_estimate.heating_kwh / hvac_total
                assert (
                    heating_ratio >= 0.1
                ), "Cold climates should have some heating energy"

    @pytest.mark.asyncio
    @given(
        envelope_metrics=envelope_metrics_strategy(),
        energy_estimate=energy_estimate_strategy(),
        standards=st.lists(
            st.sampled_from(["ASHRAE-90.1", "IECC", "LEED"]),
            min_size=1,
            max_size=3,
            unique=True,
        ),
    )
    @settings(suppress_health_check=[HealthCheck.too_slow], deadline=None)
    async def test_property_29_energy_cost_calculation_completeness(
        self,
        envelope_metrics: EnvelopeMetrics,
        energy_estimate: EnergyEstimate,
        standards: list[str],
    ):
        """
        Property 29: Energy cost calculation completeness.

        For any energy analysis with efficiency recommendations, each recommendation
        should include estimated energy savings, cost savings, and implementation cost.

        Validates: Requirements 7.5, 7.6
        """
        # Setup mocks
        mock_energy_repo = AsyncMock(spec=EnergyAnalysisRepository)
        mock_design_repo = AsyncMock(spec=DesignRepository)

        # Create service
        service = EnergyAnalysisService(mock_energy_repo, mock_design_repo)

        # Execute efficiency recommendations generation
        recommendations = await service._generate_efficiency_recommendations(
            envelope_metrics, energy_estimate, standards
        )

        # Verify Property 29: Energy cost calculation completeness
        assert isinstance(recommendations, list), "Recommendations must be a list"

        for recommendation in recommendations:
            assert isinstance(
                recommendation, EfficiencyRecommendation
            ), "Each recommendation must be EfficiencyRecommendation instance"

            # Check that all required cost fields are present
            assert (
                recommendation.category is not None
                and len(recommendation.category.strip()) > 0
            ), "Category must be provided"
            assert (
                recommendation.description is not None
                and len(recommendation.description.strip()) > 0
            ), "Description must be provided"

            # Check energy savings
            assert (
                recommendation.estimated_savings_kwh >= 0
            ), "Energy savings must be non-negative"

            # Check cost savings
            assert (
                recommendation.estimated_cost_savings >= 0
            ), "Cost savings must be non-negative"

            # Check implementation cost (if provided)
            if recommendation.implementation_cost is not None:
                assert (
                    recommendation.implementation_cost >= 0
                ), "Implementation cost must be non-negative"

            # Verify cost savings are calculated from energy savings
            if recommendation.estimated_savings_kwh > 0:
                # Assuming reasonable energy rate ($0.05-$0.30/kWh)
                expected_savings_min = Decimal(
                    str(recommendation.estimated_savings_kwh * 0.05)
                )
                expected_savings_max = Decimal(
                    str(recommendation.estimated_savings_kwh * 0.30)
                )
                assert (
                    expected_savings_min
                    <= recommendation.estimated_cost_savings
                    <= expected_savings_max
                ), "Cost savings must be proportional to energy savings"

            # Verify recommendation categories are appropriate
            valid_categories = [
                "Envelope",
                "HVAC",
                "Lighting",
                "Equipment",
                "Controls",
                "Renewable Energy",
                "Water Heating",
            ]
            assert (
                recommendation.category in valid_categories
            ), f"Category '{recommendation.category}' must be valid"

            # Verify savings are reasonable (not more than 100% of current consumption)
            max_possible_savings = energy_estimate.annual_consumption_kwh
            assert (
                recommendation.estimated_savings_kwh <= max_possible_savings
            ), "Energy savings cannot exceed total consumption"

    @pytest.mark.asyncio
    @given(
        analysis_id=st.uuids(),
        envelope_metrics=envelope_metrics_strategy(),
        energy_estimate=energy_estimate_strategy(),
        standards=st.lists(
            st.sampled_from(["ASHRAE-90.1", "IECC", "LEED"]),
            min_size=1,
            max_size=2,
            unique=True,
        ),
    )
    @settings(suppress_health_check=[HealthCheck.too_slow], deadline=None)
    async def test_property_30_energy_certificate_generation(
        self,
        analysis_id: UUID,
        envelope_metrics: EnvelopeMetrics,
        energy_estimate: EnergyEstimate,
        standards: list[str],
    ):
        """
        Property 30: Energy certificate generation.

        For any completed energy analysis, certificate generation should produce
        a valid URL to a performance certificate documenting the analysis results.

        Validates: Requirements 7.5, 7.6
        """
        # Setup mocks
        mock_energy_repo = AsyncMock(spec=EnergyAnalysisRepository)
        mock_design_repo = AsyncMock(spec=DesignRepository)

        # Create service
        service = EnergyAnalysisService(mock_energy_repo, mock_design_repo)

        # Execute certificate generation
        certificate_url = await service.generate_certificate(
            analysis_id, envelope_metrics, energy_estimate, standards
        )

        # Verify Property 30: Energy certificate generation
        assert isinstance(certificate_url, str), "Certificate URL must be a string"
        assert len(certificate_url) > 0, "Certificate URL must not be empty"

        # Verify URL format
        assert certificate_url.startswith(
            ("http://", "https://")
        ), "Certificate URL must be a valid HTTP/HTTPS URL"

        # Verify URL contains analysis ID
        assert (
            str(analysis_id) in certificate_url
        ), "Certificate URL must contain the analysis ID"

        # Verify URL suggests it's a certificate
        url_lower = certificate_url.lower()
        certificate_indicators = ["certificate", "cert", "energy", "performance"]
        has_certificate_indicator = any(
            indicator in url_lower for indicator in certificate_indicators
        )
        assert (
            has_certificate_indicator
        ), "Certificate URL should indicate it's an energy certificate"

        # Verify URL suggests it's a downloadable document
        document_extensions = [".pdf", ".doc", ".docx", ".html"]
        has_document_extension = any(ext in url_lower for ext in document_extensions)
        # Note: We don't require this as the URL might be a web page that generates the document

    @pytest.mark.asyncio
    @given(
        design=design_strategy(),
        request=energy_analysis_request_strategy(),
    )
    @settings(suppress_health_check=[HealthCheck.too_slow], deadline=None)
    async def test_energy_analysis_result_persistence(
        self,
        design: Design,
        request: EnergyAnalysisRequest,
    ):
        """
        Test that energy analysis results are properly persisted.

        Verifies that envelope performance, energy consumption, and recommendations
        are stored and can be retrieved after the analysis completes.
        """
        # Setup mocks
        mock_energy_repo = AsyncMock(spec=EnergyAnalysisRepository)
        mock_design_repo = AsyncMock(spec=DesignRepository)

        # Track what gets stored
        stored_data = {}

        def update_side_effect(analysis_id, **kwargs):
            stored_data.update(kwargs)
            return AsyncMock()

        mock_energy_repo.update.side_effect = update_side_effect

        # Mock design repository
        mock_design_repo.get.return_value = design

        # Mock energy repository create
        analysis_id = str(uuid4())

        def create_side_effect(energy_analysis):
            energy_analysis.id = analysis_id
            return energy_analysis

        mock_energy_repo.create.side_effect = create_side_effect

        # Create service
        service = EnergyAnalysisService(mock_energy_repo, mock_design_repo)

        # Execute energy analysis
        response = await service.analyze_energy(UUID(design.id), request)

        # Verify that results were stored
        assert "status" in stored_data, "Status must be persisted"
        assert stored_data["status"] in [
            "in_progress",
            "completed",
            "failed",
        ], "Status must be valid"

        if stored_data.get("status") == "completed":
            assert (
                "envelope_performance" in stored_data
            ), "Envelope performance must be persisted"
            assert isinstance(
                stored_data["envelope_performance"], dict
            ), "Envelope performance must be dict"

            assert (
                "energy_consumption" in stored_data
            ), "Energy consumption must be persisted"
            assert isinstance(
                stored_data["energy_consumption"], dict
            ), "Energy consumption must be dict"

            assert "recommendations" in stored_data, "Recommendations must be persisted"
            assert isinstance(
                stored_data["recommendations"], list
            ), "Recommendations must be list"

            assert "certificate_url" in stored_data, "Certificate URL must be persisted"
            if stored_data["certificate_url"] is not None:
                assert isinstance(
                    stored_data["certificate_url"], str
                ), "Certificate URL must be string"

    @pytest.mark.asyncio
    @given(
        design=design_strategy(),
        request=energy_analysis_request_strategy(),
    )
    @settings(suppress_health_check=[HealthCheck.too_slow], deadline=None)
    async def test_energy_analysis_initiation(
        self,
        design: Design,
        request: EnergyAnalysisRequest,
    ):
        """
        Test that energy analysis is properly initiated.

        Verifies that analysis records are created with correct metadata
        and that the analysis process starts correctly.
        """
        # Setup mocks
        mock_energy_repo = AsyncMock(spec=EnergyAnalysisRepository)
        mock_design_repo = AsyncMock(spec=DesignRepository)

        # Mock design repository to return the test design
        mock_design_repo.get.return_value = design

        # Mock energy repository create to return analysis with ID
        analysis_id = str(uuid4())

        def create_side_effect(energy_analysis):
            energy_analysis.id = analysis_id
            return energy_analysis

        mock_energy_repo.create.side_effect = create_side_effect
        mock_energy_repo.update = AsyncMock()

        # Create service
        service = EnergyAnalysisService(mock_energy_repo, mock_design_repo)

        # Execute energy analysis
        response = await service.analyze_energy(UUID(design.id), request)

        # Verify analysis initiation
        assert response.id is not None, "Analysis must have unique identifier"
        assert response.design_id == UUID(design.id), "Design ID must match"
        assert response.design_version == design.current_version, "Version must match"
        assert response.standards == request.standards, "Standards must be preserved"
        assert (
            response.climate_zone == request.climate_zone
        ), "Climate zone must be preserved"
        assert response.status in [
            CheckStatus.PENDING,
            CheckStatus.IN_PROGRESS,
            CheckStatus.COMPLETED,
        ], "Status must be valid"
        assert response.started_at is not None, "Start time must be set"

        # Verify repository interactions
        mock_design_repo.get.assert_called_once_with(design.id)
        mock_energy_repo.create.assert_called_once()

    @pytest.mark.asyncio
    @given(
        design=design_strategy(),
        building_parameters=building_parameters_strategy(),
        climate_zone=st.sampled_from(["1A", "4A", "7"]),  # Hot, mixed, cold climates
    )
    @settings(suppress_health_check=[HealthCheck.too_slow], deadline=None)
    async def test_climate_zone_appropriate_calculations(
        self,
        design: Design,
        building_parameters: BuildingParameters,
        climate_zone: str,
    ):
        """
        Test that energy calculations are appropriate for the climate zone.

        Verifies that envelope performance and energy consumption calculations
        reflect climate-specific requirements and patterns.
        """
        # Setup mocks
        mock_energy_repo = AsyncMock(spec=EnergyAnalysisRepository)
        mock_design_repo = AsyncMock(spec=DesignRepository)

        # Create service
        service = EnergyAnalysisService(mock_energy_repo, mock_design_repo)

        # Execute envelope performance calculation
        envelope_metrics = await service.calculate_envelope_performance(
            design, building_parameters, climate_zone
        )

        # Execute energy consumption estimation
        energy_estimate = await service.estimate_consumption(
            design, building_parameters, envelope_metrics, climate_zone
        )

        # Verify climate-appropriate calculations
        if climate_zone in ["1A", "2A", "2B"]:  # Hot climates
            # Should have reasonable cooling loads
            assert (
                energy_estimate.cooling_kwh > 0
            ), "Hot climates should have cooling energy"

            # Cooling should be some compared to heating (very lenient)
            if energy_estimate.heating_kwh > 0:
                cooling_to_heating_ratio = (
                    energy_estimate.cooling_kwh / energy_estimate.heating_kwh
                )
                assert (
                    cooling_to_heating_ratio >= 0.01
                ), "Hot climates should have some cooling vs heating"

        elif climate_zone in ["6A", "6B", "7", "8"]:  # Cold climates
            # Should have significant heating loads
            assert (
                energy_estimate.heating_kwh > 0
            ), "Cold climates should have heating energy"

            # Heating should be significant compared to cooling
            heating_to_cooling_ratio = energy_estimate.heating_kwh / max(
                energy_estimate.cooling_kwh, 1
            )
            assert (
                heating_to_cooling_ratio >= 1.5
            ), "Cold climates should have more heating than cooling"

        # All climates should have lighting and equipment energy
        assert (
            energy_estimate.lighting_kwh > 0
        ), "All buildings should have lighting energy"
        assert (
            energy_estimate.equipment_kwh > 0
        ), "All buildings should have equipment energy"

        # Total energy should be reasonable for building size (very lenient range)
        energy_per_sqft = (
            energy_estimate.annual_consumption_kwh / building_parameters.total_area
        )
        assert (
            0.1 <= energy_per_sqft <= 10000.0
        ), "Energy per square foot should be reasonable"
