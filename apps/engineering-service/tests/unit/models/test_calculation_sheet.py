"""Unit tests for CalculationSheet model."""

from datetime import datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.calculation_sheet import CalculationSheet


class TestCalculationSheetModel:
    """Test suite for CalculationSheet model."""

    @pytest.mark.asyncio
    async def test_create_calculation_sheet(self, test_db_session: AsyncSession):
        """Test creating a calculation sheet."""
        sheet = CalculationSheet(
            project_id="proj_123",
            title="Beam Load Calculation",
            description="Calculate loads for main floor beam",
            calculation_type="structural",
            inputs={"span": 20, "load": 100},
            outputs={"moment": 5000, "shear": 1000},
            formulas=["M = wL^2/8", "V = wL/2"],
            units="imperial",
            created_by="user_123",
        )

        test_db_session.add(sheet)
        await test_db_session.commit()
        await test_db_session.refresh(sheet)

        assert sheet.id is not None
        assert sheet.project_id == "proj_123"
        assert sheet.title == "Beam Load Calculation"
        assert sheet.calculation_type == "structural"
        assert sheet.inputs["span"] == 20
        assert sheet.outputs["moment"] == 5000
        assert isinstance(sheet.created_at, datetime)
        assert sheet.version == 1

    @pytest.mark.asyncio
    async def test_calculation_sheet_required_fields(
        self, test_db_session: AsyncSession
    ):
        """Test that required fields are enforced."""
        with pytest.raises(Exception):  # Will raise IntegrityError or similar
            sheet = CalculationSheet()
            test_db_session.add(sheet)
            await test_db_session.commit()

    @pytest.mark.asyncio
    async def test_calculation_sheet_versioning(self, test_db_session: AsyncSession):
        """Test version incrementing on updates."""
        sheet = CalculationSheet(
            project_id="proj_123",
            title="Test Calculation",
            calculation_type="structural",
            inputs={"value": 10},
            outputs={"result": 20},
            created_by="user_123",
        )

        test_db_session.add(sheet)
        await test_db_session.commit()
        await test_db_session.refresh(sheet)

        initial_version = sheet.version
        # Manually increment version (this would be done in service layer)
        sheet.version = initial_version + 1
        sheet.inputs = {"value": 15}
        await test_db_session.commit()
        await test_db_session.refresh(sheet)

        assert sheet.version == initial_version + 1

    @pytest.mark.asyncio
    async def test_calculation_sheet_json_fields(self, test_db_session: AsyncSession):
        """Test JSON field storage and retrieval."""
        complex_inputs = {
            "loads": [100, 200, 300],
            "dimensions": {"length": 20, "width": 10},
            "material": {"type": "steel", "grade": "A36"},
        }

        sheet = CalculationSheet(
            project_id="proj_123",
            title="Complex Calculation",
            calculation_type="structural",
            inputs=complex_inputs,
            outputs={"total_load": 600},
            created_by="user_123",
        )

        test_db_session.add(sheet)
        await test_db_session.commit()
        await test_db_session.refresh(sheet)

        assert sheet.inputs["loads"] == [100, 200, 300]
        assert sheet.inputs["dimensions"]["length"] == 20
        assert sheet.inputs["material"]["grade"] == "A36"

    @pytest.mark.asyncio
    async def test_calculation_sheet_timestamps(self, test_db_session: AsyncSession):
        """Test automatic timestamp management."""
        sheet = CalculationSheet(
            project_id="proj_123",
            title="Timestamp Test",
            calculation_type="structural",
            inputs={"value": 10},
            outputs={"result": 20},
            created_by="user_123",
        )

        test_db_session.add(sheet)
        await test_db_session.commit()
        await test_db_session.refresh(sheet)

        assert sheet.created_at is not None
        assert sheet.updated_at is not None
        assert sheet.created_at <= sheet.updated_at

        # Update and check timestamp changes
        original_updated_at = sheet.updated_at
        sheet.title = "Updated Title"
        await test_db_session.commit()
        await test_db_session.refresh(sheet)

        assert sheet.updated_at > original_updated_at

    @pytest.mark.asyncio
    async def test_calculation_sheet_soft_delete(self, test_db_session: AsyncSession):
        """Test soft delete functionality."""
        sheet = CalculationSheet(
            project_id="proj_123",
            title="Delete Test",
            calculation_type="structural",
            inputs={"value": 10},
            outputs={"result": 20},
            created_by="user_123",
        )

        test_db_session.add(sheet)
        await test_db_session.commit()
        await test_db_session.refresh(sheet)

        assert sheet.deleted_at is None

        # Soft delete
        sheet.deleted_at = datetime.utcnow()
        await test_db_session.commit()
        await test_db_session.refresh(sheet)

        assert sheet.deleted_at is not None

    @pytest.mark.asyncio
    async def test_calculation_sheet_string_representation(
        self, test_db_session: AsyncSession
    ):
        """Test string representation of model."""
        sheet = CalculationSheet(
            project_id="proj_123",
            title="String Test",
            calculation_type="structural",
            inputs={"value": 10},
            outputs={"result": 20},
            created_by="user_123",
        )

        test_db_session.add(sheet)
        await test_db_session.commit()
        await test_db_session.refresh(sheet)

        str_repr = str(sheet)
        assert "String Test" in str_repr
        assert "structural" in str_repr
