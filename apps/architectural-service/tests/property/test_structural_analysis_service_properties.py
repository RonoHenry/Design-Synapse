"""Property-based tests for StructuralAnalysisService."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from src.api.v1.schemas.analysis import (LoadParameters,
                                         StructuralAnalysisRequest)
from src.api.v1.schemas.enums import (AnalysisType, CheckStatus,
                                      StructuralSystem)
from src.models.design import Design
from src.models.structural_analysis import StructuralAnalysis
from src.repositories.design_repository import DesignRepository
from src.repositories.structural_analysis_repository import \
    StructuralAnalysisRepository
from src.services.structural_analysis_service import StructuralAnalysisService


# Hypothesis strategies for generating test data
@st.composite
def load_parameters_strategy(draw):
    """Generate valid LoadParameters."""
    return LoadParameters(
        dead_load_factor=draw(st.floats(min_value=0.5, max_value=2.0)),
        live_load_factor=draw(st.floats(min_value=0.5, max_value=3.0)),
        wind_speed=draw(st.one_of(st.none(), st.floats(min_value=50, max_value=200))),
        seismic_zone=draw(
            st.one_of(st.none(), st.sampled_from(["A", "B", "C", "D", "E", "F"]))
        ),
        snow_load=draw(st.one_of(st.none(), st.floats(min_value=0, max_value=100))),
    )


@st.composite
def structural_analysis_request_strategy(draw):
    """Generate valid StructuralAnalysisRequest."""
    return StructuralAnalysisRequest(
        structural_system=draw(st.sampled_from(StructuralSystem)),
        load_parameters=draw(load_parameters_strategy()),
        analysis_type=draw(st.sampled_from(AnalysisType)),
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
            st.sampled_from(
                ["office", "residential", "retail", "warehouse", "assembly"]
            )
        ),
        location_data={
            "address": draw(st.text(min_size=1, max_size=200)),
            "city": draw(st.text(min_size=1, max_size=100)),
            "state": draw(st.text(min_size=1, max_size=100)),
        },
        current_version="1.0",
        version_number=1,
        status="active",
        is_deleted=False,
        metadata={
            "building_area": draw(st.floats(min_value=1000, max_value=100000)),
            "building_height": draw(st.floats(min_value=10, max_value=500)),
            "building_width": draw(st.floats(min_value=20, max_value=300)),
            "building_weight": draw(st.floats(min_value=100000, max_value=5000000)),
            "structural_system": draw(
                st.sampled_from(["steel_frame", "concrete", "wood_frame", "masonry"])
            ),
        },
        created_by=str(uuid4()),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


class TestStructuralAnalysisServiceProperties:
    """Property-based tests for StructuralAnalysisService."""

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

    @given(
        design=design_strategy(),
        request=structural_analysis_request_strategy(),
    )
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    async def test_property_12_structural_load_calculation_completeness(
        self,
        service,
        mock_structural_repository,
        mock_design_repository,
        design,
        request,
    ):
        """
        Property 12: Structural load calculation completeness

        For any valid design and load parameters, the calculated loads should include
        all required load types (dead, live) and optional loads (wind, seismic) when
        parameters are provided.

        **Validates: Requirements 3.2, 3.4, 3.6**
        """
        # Setup mocks
        mock_design_repository.get.return_value = design
        mock_structural_repository.create.return_value = None
        mock_structural_repository.update.return_value = None

        # Execute analysis
        response = await service.analyze_structure(UUID(design.id), request)

        # Verify load calculation completeness
        assert response.load_calculations is not None
        load_calcs = response.load_calculations

        # Dead loads and live loads should always be present
        assert load_calcs.dead_loads is not None
        assert len(load_calcs.dead_loads) > 0
        assert load_calcs.live_loads is not None
        assert len(load_calcs.live_loads) > 0

        # All dead load values should be positive
        for element, load in load_calcs.dead_loads.items():
            assert load > 0, f"Dead load for {element} should be positive"

        # All live load values should be positive
        for element, load in load_calcs.live_loads.items():
            assert load > 0, f"Live load for {element} should be positive"

        # Wind loads should be present if wind speed provided
        if request.load_parameters.wind_speed is not None:
            assert load_calcs.wind_loads is not None
            assert len(load_calcs.wind_loads) > 0
            for element, load in load_calcs.wind_loads.items():
                assert load > 0, f"Wind load for {element} should be positive"
        else:
            assert load_calcs.wind_loads is None or len(load_calcs.wind_loads) == 0

        # Seismic loads should be present if seismic zone provided
        if request.load_parameters.seismic_zone is not None:
            assert load_calcs.seismic_loads is not None
            assert len(load_calcs.seismic_loads) > 0
            for element, load in load_calcs.seismic_loads.items():
                assert load > 0, f"Seismic load for {element} should be positive"
        else:
            assert (
                load_calcs.seismic_loads is None or len(load_calcs.seismic_loads) == 0
            )

        # Load factors should be applied correctly
        # Dead loads should reflect the dead load factor
        expected_min_dead = (
            design.metadata["building_area"]
            * 10.0
            * request.load_parameters.dead_load_factor
        )
        actual_total_dead = sum(load_calcs.dead_loads.values())
        assert actual_total_dead >= expected_min_dead * 0.8  # Allow some tolerance

        # Live loads should reflect the live load factor
        expected_min_live = (
            design.metadata["building_area"]
            * 40.0
            * request.load_parameters.live_load_factor
        )
        actual_total_live = sum(load_calcs.live_loads.values())
        assert actual_total_live >= expected_min_live * 0.8  # Allow some tolerance

    @given(
        design=design_strategy(),
        request=structural_analysis_request_strategy(),
    )
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    async def test_property_13_structural_issue_flagging(
        self,
        service,
        mock_structural_repository,
        mock_design_repository,
        design,
        request,
    ):
        """
        Property 13: Structural issue flagging

        For any structural analysis, if loads exceed capacity limits or structural
        adequacy thresholds, appropriate issues should be flagged with correct
        severity levels and recommendations.

        **Validates: Requirements 3.2, 3.4, 3.6**
        """
        # Setup mocks
        mock_design_repository.get.return_value = design
        mock_structural_repository.create.return_value = None
        mock_structural_repository.update.return_value = None

        # Execute analysis
        response = await service.analyze_structure(UUID(design.id), request)

        # Verify issue flagging logic
        issues = response.issues

        # Issues should be properly structured
        for issue in issues:
            assert issue.element_id is not None and len(issue.element_id) > 0
            assert issue.issue_type is not None and len(issue.issue_type) > 0
            assert issue.description is not None and len(issue.description) > 0
            assert issue.severity in ["critical", "major", "minor"]
            assert issue.recommendation is not None and len(issue.recommendation) > 0

        # Critical issues should have appropriate recommendations
        critical_issues = [issue for issue in issues if issue.severity == "critical"]
        for issue in critical_issues:
            assert (
                "increase" in issue.recommendation.lower()
                or "add" in issue.recommendation.lower()
                or "upgrade" in issue.recommendation.lower()
            )

        # If no issues found, analysis should still be valid
        if len(issues) == 0:
            assert response.status == CheckStatus.COMPLETED
            assert len(response.recommendations) > 0

        # Issue types should be consistent with their descriptions
        for issue in issues:
            if "load" in issue.issue_type:
                assert "load" in issue.description.lower()
            if "capacity" in issue.issue_type:
                assert (
                    "capacity" in issue.description.lower()
                    or "utilization" in issue.description.lower()
                )
            if "deflection" in issue.issue_type:
                assert "deflection" in issue.description.lower()
            if "connection" in issue.issue_type:
                assert "connection" in issue.description.lower()

    @given(
        design=design_strategy(),
        request=structural_analysis_request_strategy(),
    )
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    async def test_property_14_audit_trail_completeness(
        self,
        service,
        mock_structural_repository,
        mock_design_repository,
        design,
        request,
    ):
        """
        Property 14: Audit trail completeness

        For any structural analysis, a complete audit trail should be maintained
        including analysis parameters, timestamps, results, and all intermediate
        calculations for traceability.

        **Validates: Requirements 3.2, 3.4, 3.6**
        """
        # Setup mocks
        mock_design_repository.get.return_value = design

        # Capture the created analysis
        created_analysis = None

        async def capture_create(analysis):
            nonlocal created_analysis
            created_analysis = analysis
            return analysis

        mock_structural_repository.create.side_effect = capture_create
        mock_structural_repository.update.return_value = None

        # Execute analysis
        start_time = datetime.utcnow()
        response = await service.analyze_structure(UUID(design.id), request)
        end_time = datetime.utcnow()

        # Verify audit trail completeness
        assert response.id is not None
        assert response.design_id == UUID(design.id)
        assert response.design_version == design.current_version

        # Analysis parameters should be preserved
        assert response.structural_system == request.structural_system
        assert response.analysis_type == request.analysis_type

        # Timestamps should be present and logical
        assert response.started_at is not None
        assert response.completed_at is not None
        assert start_time <= response.started_at <= end_time
        assert response.started_at <= response.completed_at <= end_time

        # Status should indicate completion
        assert response.status == CheckStatus.COMPLETED

        # Load calculations should be preserved for audit
        assert response.load_calculations is not None
        load_calcs = response.load_calculations

        # All calculation components should be traceable
        assert isinstance(load_calcs.dead_loads, dict)
        assert isinstance(load_calcs.live_loads, dict)

        # Load calculation values should be deterministic for same inputs
        # (Re-running with same parameters should give same results)
        response2 = await service.analyze_structure(UUID(design.id), request)
        assert (
            response2.load_calculations.dead_loads
            == response.load_calculations.dead_loads
        )
        assert (
            response2.load_calculations.live_loads
            == response.load_calculations.live_loads
        )

        # Issues and recommendations should be preserved
        assert isinstance(response.issues, list)
        assert isinstance(response.recommendations, list)

        # Each issue should have complete audit information
        for issue in response.issues:
            assert hasattr(issue, "element_id")
            assert hasattr(issue, "issue_type")
            assert hasattr(issue, "description")
            assert hasattr(issue, "severity")
            assert hasattr(issue, "recommendation")

        # Repository interactions should maintain audit trail
        # Note: create may be called multiple times due to hypothesis running multiple examples
        assert mock_structural_repository.create.call_count >= 1
        assert mock_structural_repository.update.call_count >= 1

        # Created analysis should have all required audit fields
        assert created_analysis is not None
        assert created_analysis.design_id == str(design.id)
        assert created_analysis.design_version == design.current_version
        assert created_analysis.structural_system == request.structural_system
        assert created_analysis.analysis_type == request.analysis_type
        assert created_analysis.started_at is not None

    @given(
        design=design_strategy(),
        load_params=load_parameters_strategy(),
    )
    @settings(
        max_examples=50,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    async def test_load_calculation_consistency(
        self,
        service,
        mock_structural_repository,
        mock_design_repository,
        design,
        load_params,
    ):
        """
        Test that load calculations are consistent and deterministic.

        For the same design and load parameters, calculations should always
        produce the same results.
        """
        # Setup mocks
        mock_design_repository.get.return_value = design

        # Calculate loads twice with same parameters
        loads1 = await service.calculate_loads(design, load_params)
        loads2 = await service.calculate_loads(design, load_params)

        # Results should be identical
        assert loads1.dead_loads == loads2.dead_loads
        assert loads1.live_loads == loads2.live_loads
        assert loads1.wind_loads == loads2.wind_loads
        assert loads1.seismic_loads == loads2.seismic_loads

        # Load factors should be properly applied
        if load_params.dead_load_factor != 1.0:
            # Dead loads should reflect the factor
            total_dead = sum(loads1.dead_loads.values())
            building_area = design.metadata.get("building_area", 10000)
            base_dead_load = building_area * 10.0  # Minimum expected
            expected_factored = base_dead_load * load_params.dead_load_factor
            assert total_dead >= expected_factored * 0.5  # Allow reasonable tolerance

        if load_params.live_load_factor != 1.0:
            # Live loads should reflect the factor
            total_live = sum(loads1.live_loads.values())
            building_area = design.metadata.get("building_area", 10000)
            base_live_load = building_area * 40.0  # Minimum expected
            expected_factored = base_live_load * load_params.live_load_factor
            assert total_live >= expected_factored * 0.5  # Allow reasonable tolerance

    @given(
        structural_system=st.sampled_from(StructuralSystem),
        building_area=st.floats(min_value=1000, max_value=50000),
        load_factor=st.floats(min_value=0.5, max_value=2.0),
    )
    @settings(
        max_examples=50,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    async def test_load_scaling_properties(
        self, service, structural_system, building_area, load_factor
    ):
        """
        Test that loads scale appropriately with building size and load factors.

        Larger buildings should have proportionally larger loads, and load factors
        should scale loads appropriately.
        """
        # Create test design
        design = Design(
            id=str(uuid4()),
            project_id=str(uuid4()),
            name="Test Design",
            building_type="office",
            location_data={"city": "Test City"},
            current_version="1.0",
            version_number=1,
            status="active",
            is_deleted=False,
            metadata={
                "building_area": building_area,
                "building_height": 30,
                "building_width": 100,
                "structural_system": structural_system.value,
            },
            created_by=str(uuid4()),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        load_params = LoadParameters(
            dead_load_factor=load_factor,
            live_load_factor=load_factor,
        )

        # Calculate loads
        loads = await service.calculate_loads(design, load_params)

        # Verify scaling properties
        total_dead = sum(loads.dead_loads.values())
        total_live = sum(loads.live_loads.values())

        # Loads should be positive
        assert total_dead > 0
        assert total_live > 0

        # Loads should scale with building area
        # Larger buildings should have larger total loads
        expected_dead_min = (
            building_area * 10.0 * load_factor * 0.5
        )  # Conservative estimate
        expected_live_min = (
            building_area * 40.0 * load_factor * 0.5
        )  # Conservative estimate

        assert total_dead >= expected_dead_min
        assert total_live >= expected_live_min

        # Load factor should affect the results
        if load_factor > 1.0:
            # Higher load factor should result in higher loads
            base_loads = await service.calculate_loads(
                design,
                LoadParameters(
                    dead_load_factor=1.0,
                    live_load_factor=1.0,
                ),
            )
            base_dead = sum(base_loads.dead_loads.values())
            base_live = sum(base_loads.live_loads.values())

            assert total_dead > base_dead
            assert total_live > base_live
