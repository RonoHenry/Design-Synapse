"""Unit tests for CivilDesign model."""

from datetime import datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.civil_design import CivilDesign


class TestCivilDesignModel:
    """Test suite for CivilDesign model."""

    @pytest.mark.asyncio
    async def test_create_civil_design(self, test_db_session: AsyncSession):
        """Test creating a civil design."""
        design = CivilDesign(
            project_id="proj_123",
            title="Site Grading Plan",
            description="Grading design for 2-acre site",
            design_type="grading",
            site_parameters={
                "area": 87120,  # sqft
                "existing_elevation": 100,
                "soil_type": "clay",
            },
            design_criteria={
                "max_slope": 0.02,
                "min_slope": 0.005,
                "drainage_direction": "north",
            },
            design_results={
                "cut_volume": 500,  # cubic yards
                "fill_volume": 300,
                "net_export": 200,
            },
            units="imperial",
            created_by="user_123",
        )

        test_db_session.add(design)
        await test_db_session.commit()
        await test_db_session.refresh(design)

        assert design.id is not None
        assert design.design_type == "grading"
        assert design.site_parameters["area"] == 87120
        assert design.design_results["cut_volume"] == 500
        assert design.status == "draft"

    @pytest.mark.asyncio
    async def test_civil_design_types(self, test_db_session: AsyncSession):
        """Test different civil design types."""
        design_types = ["grading", "stormwater", "utilities", "paving"]

        for design_type in design_types:
            design = CivilDesign(
                project_id="proj_123",
                title=f"Test {design_type}",
                design_type=design_type,
                site_parameters={"area": 10000},
                design_criteria={"standard": "local"},
                design_results={"result": "complete"},
                created_by="user_123",
            )

            test_db_session.add(design)
            await test_db_session.commit()
            await test_db_session.refresh(design)

            assert design.design_type == design_type
            await test_db_session.rollback()

    @pytest.mark.asyncio
    async def test_civil_design_json_fields(self, test_db_session: AsyncSession):
        """Test JSON field storage for complex civil data."""
        design = CivilDesign(
            project_id="proj_123",
            title="Stormwater Management System",
            design_type="stormwater",
            site_parameters={
                "area": 43560,  # 1 acre
                "imperviousness": 0.65,
                "time_of_concentration": 15,  # minutes
            },
            design_criteria={
                "storm_frequency": "10-year",
                "rainfall_intensity": 4.5,  # inches/hour
                "runoff_coefficient": 0.75,
            },
            design_results={
                "peak_runoff": 2.2,  # cfs
                "detention_volume": 5000,  # cubic feet
                "outlet_size": 12,  # inches
                "pipe_sizes": {"inlet": 15, "outlet": 12},
            },
            units="imperial",
            created_by="user_123",
        )

        test_db_session.add(design)
        await test_db_session.commit()
        await test_db_session.refresh(design)

        assert design.site_parameters["imperviousness"] == 0.65
        assert design.design_criteria["storm_frequency"] == "10-year"
        assert design.design_results["detention_volume"] == 5000

    @pytest.mark.asyncio
    async def test_civil_design_string_representation(
        self, test_db_session: AsyncSession
    ):
        """Test string representation."""
        design = CivilDesign(
            project_id="proj_123",
            title="Utility Design",
            design_type="utilities",
            site_parameters={"area": 20000},
            design_criteria={"depth": 4},
            design_results={"pipe_length": 500},
            created_by="user_123",
        )

        test_db_session.add(design)
        await test_db_session.commit()
        await test_db_session.refresh(design)

        str_repr = str(design)
        assert "Utility Design" in str_repr
        assert "utilities" in str_repr
