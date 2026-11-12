"""Unit tests for StructuralDesign model."""

from datetime import datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.structural_design import StructuralDesign


class TestStructuralDesignModel:
    """Test suite for StructuralDesign model."""

    @pytest.mark.asyncio
    async def test_create_structural_design(self, test_db_session: AsyncSession):
        """Test creating a structural design."""
        design = StructuralDesign(
            project_id="proj_123",
            title="Main Floor Beam Design",
            description="Design for 20ft span beam",
            design_type="beam",
            loads={
                "dead_load": 100,
                "live_load": 200,
                "total_load": 300,
            },
            material_properties={
                "type": "steel",
                "grade": "A36",
                "fy": 36000,
            },
            geometry={
                "span": 20,
                "spacing": 10,
            },
            design_results={
                "required_section": "W12x26",
                "deflection": 0.5,
            },
            stress_ratios={
                "bending": 0.85,
                "shear": 0.45,
            },
            units="imperial",
            created_by="user_123",
        )

        test_db_session.add(design)
        await test_db_session.commit()
        await test_db_session.refresh(design)

        assert design.id is not None
        assert design.project_id == "proj_123"
        assert design.title == "Main Floor Beam Design"
        assert design.design_type == "beam"
        assert design.loads["dead_load"] == 100
        assert design.material_properties["grade"] == "A36"
        assert design.design_results["required_section"] == "W12x26"
        assert design.stress_ratios["bending"] == 0.85
        assert design.status == "draft"
        assert isinstance(design.created_at, datetime)

    @pytest.mark.asyncio
    async def test_structural_design_required_fields(
        self, test_db_session: AsyncSession
    ):
        """Test that required fields are enforced."""
        with pytest.raises(Exception):
            design = StructuralDesign()
            test_db_session.add(design)
            await test_db_session.commit()

    @pytest.mark.asyncio
    async def test_structural_design_types(self, test_db_session: AsyncSession):
        """Test different structural design types."""
        design_types = ["beam", "column", "foundation", "slab", "wall"]

        for design_type in design_types:
            design = StructuralDesign(
                project_id="proj_123",
                title=f"Test {design_type}",
                design_type=design_type,
                loads={"total": 100},
                material_properties={"type": "concrete"},
                geometry={"size": 10},
                design_results={"capacity": 150},
                stress_ratios={"ratio": 0.67},
                created_by="user_123",
            )

            test_db_session.add(design)
            await test_db_session.commit()
            await test_db_session.refresh(design)

            assert design.design_type == design_type
            await test_db_session.rollback()

    @pytest.mark.asyncio
    async def test_structural_design_json_fields(self, test_db_session: AsyncSession):
        """Test JSON field storage and retrieval."""
        complex_loads = {
            "dead_load": 100,
            "live_load": 200,
            "wind_load": {
                "direction": "north",
                "magnitude": 50,
            },
            "seismic_load": {
                "zone": "4",
                "factor": 1.2,
            },
        }

        design = StructuralDesign(
            project_id="proj_123",
            title="Complex Load Design",
            design_type="column",
            loads=complex_loads,
            material_properties={"type": "steel"},
            geometry={"height": 12},
            design_results={"section": "W14x90"},
            stress_ratios={"axial": 0.75, "bending": 0.60},
            created_by="user_123",
        )

        test_db_session.add(design)
        await test_db_session.commit()
        await test_db_session.refresh(design)

        assert design.loads["dead_load"] == 100
        assert design.loads["wind_load"]["direction"] == "north"
        assert design.loads["seismic_load"]["factor"] == 1.2
        assert design.stress_ratios["axial"] == 0.75

    @pytest.mark.asyncio
    async def test_structural_design_status_workflow(
        self, test_db_session: AsyncSession
    ):
        """Test status workflow from draft to approved."""
        design = StructuralDesign(
            project_id="proj_123",
            title="Status Test",
            design_type="beam",
            loads={"total": 100},
            material_properties={"type": "steel"},
            geometry={"span": 20},
            design_results={"section": "W12x26"},
            stress_ratios={"bending": 0.80},
            created_by="user_123",
        )

        test_db_session.add(design)
        await test_db_session.commit()
        await test_db_session.refresh(design)

        assert design.status == "draft"

        # Approve design
        design.status = "approved"
        design.updated_by = "engineer_456"
        await test_db_session.commit()
        await test_db_session.refresh(design)

        assert design.status == "approved"
        assert design.updated_by == "engineer_456"

    @pytest.mark.asyncio
    async def test_structural_design_timestamps(self, test_db_session: AsyncSession):
        """Test automatic timestamp management."""
        design = StructuralDesign(
            project_id="proj_123",
            title="Timestamp Test",
            design_type="foundation",
            loads={"bearing": 5000},
            material_properties={"type": "concrete"},
            geometry={"width": 8, "length": 8},
            design_results={"depth": 3},
            stress_ratios={"bearing": 0.70},
            created_by="user_123",
        )

        test_db_session.add(design)
        await test_db_session.commit()
        await test_db_session.refresh(design)

        assert design.created_at is not None
        assert design.updated_at is not None
        assert design.created_at <= design.updated_at

        # Update and check timestamp changes
        original_updated_at = design.updated_at
        design.title = "Updated Foundation"
        await test_db_session.commit()
        await test_db_session.refresh(design)

        assert design.updated_at > original_updated_at

    @pytest.mark.asyncio
    async def test_structural_design_soft_delete(self, test_db_session: AsyncSession):
        """Test soft delete functionality."""
        design = StructuralDesign(
            project_id="proj_123",
            title="Delete Test",
            design_type="slab",
            loads={"uniform": 150},
            material_properties={"type": "concrete"},
            geometry={"thickness": 6},
            design_results={"reinforcement": "#4@12"},
            stress_ratios={"flexure": 0.65},
            created_by="user_123",
        )

        test_db_session.add(design)
        await test_db_session.commit()
        await test_db_session.refresh(design)

        assert design.deleted_at is None

        # Soft delete
        design.deleted_at = datetime.utcnow()
        await test_db_session.commit()
        await test_db_session.refresh(design)

        assert design.deleted_at is not None

    @pytest.mark.asyncio
    async def test_structural_design_string_representation(
        self, test_db_session: AsyncSession
    ):
        """Test string representation of model."""
        design = StructuralDesign(
            project_id="proj_123",
            title="String Test",
            design_type="wall",
            loads={"lateral": 50},
            material_properties={"type": "masonry"},
            geometry={"height": 10, "length": 20},
            design_results={"thickness": 8},
            stress_ratios={"shear": 0.55},
            created_by="user_123",
        )

        test_db_session.add(design)
        await test_db_session.commit()
        await test_db_session.refresh(design)

        str_repr = str(design)
        assert "String Test" in str_repr
        assert "wall" in str_repr
        assert "draft" in str_repr

    @pytest.mark.asyncio
    async def test_structural_design_with_calculation_sheet(
        self, test_db_session: AsyncSession
    ):
        """Test linking structural design to calculation sheet."""
        from src.models.calculation_sheet import CalculationSheet

        # Create calculation sheet first
        sheet = CalculationSheet(
            project_id="proj_123",
            title="Beam Calculations",
            calculation_type="structural",
            inputs={"span": 20},
            outputs={"moment": 5000},
            created_by="user_123",
        )

        test_db_session.add(sheet)
        await test_db_session.commit()
        await test_db_session.refresh(sheet)

        # Create structural design linked to sheet
        design = StructuralDesign(
            project_id="proj_123",
            calculation_sheet_id=sheet.id,
            title="Beam Design from Calculations",
            design_type="beam",
            loads={"moment": 5000},
            material_properties={"type": "steel"},
            geometry={"span": 20},
            design_results={"section": "W12x26"},
            stress_ratios={"bending": 0.80},
            created_by="user_123",
        )

        test_db_session.add(design)
        await test_db_session.commit()
        await test_db_session.refresh(design)

        assert design.calculation_sheet_id == sheet.id
