"""Unit tests for MEPDesign model."""

from datetime import datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.mep_design import MEPDesign


class TestMEPDesignModel:
    """Test suite for MEPDesign model."""

    @pytest.mark.asyncio
    async def test_create_mep_design(self, test_db_session: AsyncSession):
        """Test creating an MEP design."""
        design = MEPDesign(
            project_id="proj_123",
            title="Office HVAC System",
            description="HVAC design for 10,000 sqft office",
            system_type="hvac",
            loads={
                "heating_load": 250000,
                "cooling_load": 300000,
            },
            equipment={
                "furnace": "80% AFUE, 250 MBH",
                "ac_unit": "3 ton, 14 SEER",
            },
            distribution={
                "ductwork": "sheet metal, insulated",
                "supply_cfm": 1200,
            },
            sizing_results={
                "equipment_size": "3 ton",
                "duct_sizes": {"main": 16, "branch": 8},
            },
            units="imperial",
            created_by="user_123",
        )

        test_db_session.add(design)
        await test_db_session.commit()
        await test_db_session.refresh(design)

        assert design.id is not None
        assert design.system_type == "hvac"
        assert design.loads["heating_load"] == 250000
        assert design.status == "draft"

    @pytest.mark.asyncio
    async def test_mep_system_types(self, test_db_session: AsyncSession):
        """Test different MEP system types."""
        system_types = ["hvac", "electrical", "plumbing", "fire_protection"]

        for system_type in system_types:
            design = MEPDesign(
                project_id="proj_123",
                title=f"Test {system_type}",
                system_type=system_type,
                loads={"total": 100},
                equipment={"type": "standard"},
                distribution={"method": "standard"},
                sizing_results={"size": "medium"},
                created_by="user_123",
            )

            test_db_session.add(design)
            await test_db_session.commit()
            await test_db_session.refresh(design)

            assert design.system_type == system_type
            await test_db_session.rollback()

    @pytest.mark.asyncio
    async def test_mep_design_json_fields(self, test_db_session: AsyncSession):
        """Test JSON field storage for complex MEP data."""
        design = MEPDesign(
            project_id="proj_123",
            title="Complex Electrical System",
            system_type="electrical",
            loads={
                "lighting": 5000,
                "receptacles": 8000,
                "hvac": 12000,
                "total": 25000,
            },
            equipment={
                "main_panel": "200A, 120/240V",
                "sub_panels": ["100A", "60A"],
            },
            distribution={
                "feeders": {"size": "#2/0 AWG", "conduit": "2 inch"},
                "branch_circuits": {"count": 24, "size": "#12 AWG"},
            },
            sizing_results={
                "service_size": "200A",
                "panel_schedule": {"main": 200, "sub1": 100, "sub2": 60},
            },
            created_by="user_123",
        )

        test_db_session.add(design)
        await test_db_session.commit()
        await test_db_session.refresh(design)

        assert design.loads["lighting"] == 5000
        assert design.equipment["sub_panels"] == ["100A", "60A"]
        assert design.distribution["feeders"]["size"] == "#2/0 AWG"

    @pytest.mark.asyncio
    async def test_mep_design_string_representation(
        self, test_db_session: AsyncSession
    ):
        """Test string representation."""
        design = MEPDesign(
            project_id="proj_123",
            title="Plumbing System",
            system_type="plumbing",
            loads={"fixtures": 20},
            equipment={"water_heater": "50 gallon"},
            distribution={"piping": "copper"},
            sizing_results={"main_size": "1 inch"},
            created_by="user_123",
        )

        test_db_session.add(design)
        await test_db_session.commit()
        await test_db_session.refresh(design)

        str_repr = str(design)
        assert "Plumbing System" in str_repr
        assert "plumbing" in str_repr
