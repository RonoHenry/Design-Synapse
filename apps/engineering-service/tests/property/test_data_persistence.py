"""Property-based tests for data persistence round-trip.

**Validates: Requirements 12**

This module tests that serialization and deserialization of engineering
data preserves data integrity across all model types.
"""

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.audit_log import AuditLog
from src.models.calculation_sheet import CalculationSheet
from src.models.civil_design import CivilDesign
from src.models.compliance_report import ComplianceReport
from src.models.mep_design import MEPDesign
from src.models.structural_design import StructuralDesign

# Hypothesis strategies for generating test data


@st.composite
def json_dict_strategy(draw):
    """Generate a JSON-serializable dictionary."""
    return draw(
        st.dictionaries(
            keys=st.text(
                min_size=1,
                max_size=20,
                alphabet=st.characters(
                    whitelist_categories=("Lu", "Ll", "Nd"),
                    min_codepoint=65,
                    max_codepoint=122,
                ),
            ),
            values=st.one_of(
                st.integers(min_value=-1000000, max_value=1000000),
                st.floats(
                    min_value=-1000000.0,
                    max_value=1000000.0,
                    allow_nan=False,
                    allow_infinity=False,
                ),
                st.text(min_size=0, max_size=100),
                st.booleans(),
            ),
            min_size=1,
            max_size=10,
        )
    )


@st.composite
def calculation_sheet_strategy(draw):
    """Generate a valid CalculationSheet."""
    return CalculationSheet(
        project_id=draw(st.text(min_size=1, max_size=50)),
        title=draw(st.text(min_size=1, max_size=100)),
        description=draw(st.one_of(st.none(), st.text(max_size=500))),
        calculation_type=draw(st.sampled_from(["structural", "mep", "civil"])),
        inputs=draw(json_dict_strategy()),
        outputs=draw(json_dict_strategy()),
        formulas=draw(
            st.one_of(st.none(), st.lists(st.text(max_size=100), max_size=5))
        ),
        units=draw(st.sampled_from(["imperial", "metric"])),
        version=draw(st.integers(min_value=1, max_value=100)),
        created_by=draw(st.text(min_size=1, max_size=50)),
    )


@st.composite
def structural_design_strategy(draw):
    """Generate a valid StructuralDesign."""
    return StructuralDesign(
        project_id=draw(st.text(min_size=1, max_size=50)),
        title=draw(st.text(min_size=1, max_size=100)),
        description=draw(st.one_of(st.none(), st.text(max_size=500))),
        design_type=draw(
            st.sampled_from(["beam", "column", "foundation", "slab", "wall"])
        ),
        loads=draw(json_dict_strategy()),
        material_properties=draw(json_dict_strategy()),
        geometry=draw(json_dict_strategy()),
        design_results=draw(json_dict_strategy()),
        stress_ratios=draw(json_dict_strategy()),
        units=draw(st.sampled_from(["imperial", "metric"])),
        status=draw(st.sampled_from(["draft", "approved", "rejected"])),
        created_by=draw(st.text(min_size=1, max_size=50)),
    )


@st.composite
def mep_design_strategy(draw):
    """Generate a valid MEPDesign."""
    return MEPDesign(
        project_id=draw(st.text(min_size=1, max_size=50)),
        title=draw(st.text(min_size=1, max_size=100)),
        description=draw(st.one_of(st.none(), st.text(max_size=500))),
        system_type=draw(
            st.sampled_from(["hvac", "electrical", "plumbing", "fire_protection"])
        ),
        loads=draw(json_dict_strategy()),
        equipment=draw(json_dict_strategy()),
        distribution=draw(json_dict_strategy()),
        sizing_results=draw(json_dict_strategy()),
        units=draw(st.sampled_from(["imperial", "metric"])),
        status=draw(st.sampled_from(["draft", "approved", "rejected"])),
        created_by=draw(st.text(min_size=1, max_size=50)),
    )


@st.composite
def civil_design_strategy(draw):
    """Generate a valid CivilDesign."""
    return CivilDesign(
        project_id=draw(st.text(min_size=1, max_size=50)),
        title=draw(st.text(min_size=1, max_size=100)),
        description=draw(st.one_of(st.none(), st.text(max_size=500))),
        design_type=draw(
            st.sampled_from(["grading", "stormwater", "utilities", "paving"])
        ),
        site_parameters=draw(json_dict_strategy()),
        design_criteria=draw(json_dict_strategy()),
        design_results=draw(json_dict_strategy()),
        units=draw(st.sampled_from(["imperial", "metric"])),
        status=draw(st.sampled_from(["draft", "approved", "rejected"])),
        created_by=draw(st.text(min_size=1, max_size=50)),
    )


@st.composite
def audit_log_strategy(draw):
    """Generate a valid AuditLog."""
    return AuditLog(
        user_id=draw(st.text(min_size=1, max_size=50)),
        project_id=draw(st.one_of(st.none(), st.text(min_size=1, max_size=50))),
        action_type=draw(
            st.sampled_from(["create", "update", "delete", "validate", "export"])
        ),
        entity_type=draw(
            st.sampled_from(["calculation", "design", "report", "document"])
        ),
        entity_id=draw(st.text(min_size=1, max_size=50)),
        changes=draw(st.one_of(st.none(), json_dict_strategy())),
        description=draw(st.one_of(st.none(), st.text(max_size=200))),
        status=draw(st.sampled_from(["success", "failure", "error"])),
    )


class TestDataPersistenceRoundTrip:
    """Property-based tests for data persistence round-trip."""

    @pytest.mark.asyncio
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(sheet=calculation_sheet_strategy())
    async def test_calculation_sheet_round_trip(
        self, test_db_session: AsyncSession, sheet: CalculationSheet
    ):
        """Test CalculationSheet serialization/deserialization preserves data.

        **Validates: Requirements 12.3**
        """
        # Save to database
        test_db_session.add(sheet)
        await test_db_session.commit()
        await test_db_session.refresh(sheet)

        # Retrieve from database
        from sqlalchemy import select

        result = await test_db_session.execute(
            select(CalculationSheet).where(CalculationSheet.id == sheet.id)
        )
        retrieved = result.scalar_one()

        # Verify all fields match
        assert retrieved.project_id == sheet.project_id
        assert retrieved.title == sheet.title
        assert retrieved.description == sheet.description
        assert retrieved.calculation_type == sheet.calculation_type
        assert retrieved.inputs == sheet.inputs
        assert retrieved.outputs == sheet.outputs
        assert retrieved.formulas == sheet.formulas
        assert retrieved.units == sheet.units
        assert retrieved.version == sheet.version
        assert retrieved.created_by == sheet.created_by

    @pytest.mark.asyncio
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(design=structural_design_strategy())
    async def test_structural_design_round_trip(
        self, test_db_session: AsyncSession, design: StructuralDesign
    ):
        """Test StructuralDesign serialization/deserialization preserves data.

        **Validates: Requirements 12.3**
        """
        # Save to database
        test_db_session.add(design)
        await test_db_session.commit()
        await test_db_session.refresh(design)

        # Retrieve from database
        from sqlalchemy import select

        result = await test_db_session.execute(
            select(StructuralDesign).where(StructuralDesign.id == design.id)
        )
        retrieved = result.scalar_one()

        # Verify all fields match
        assert retrieved.project_id == design.project_id
        assert retrieved.title == design.title
        assert retrieved.design_type == design.design_type
        assert retrieved.loads == design.loads
        assert retrieved.material_properties == design.material_properties
        assert retrieved.geometry == design.geometry
        assert retrieved.design_results == design.design_results
        assert retrieved.stress_ratios == design.stress_ratios
        assert retrieved.status == design.status

    @pytest.mark.asyncio
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(design=mep_design_strategy())
    async def test_mep_design_round_trip(
        self, test_db_session: AsyncSession, design: MEPDesign
    ):
        """Test MEPDesign serialization/deserialization preserves data.

        **Validates: Requirements 12.3**
        """
        # Save to database
        test_db_session.add(design)
        await test_db_session.commit()
        await test_db_session.refresh(design)

        # Retrieve from database
        from sqlalchemy import select

        result = await test_db_session.execute(
            select(MEPDesign).where(MEPDesign.id == design.id)
        )
        retrieved = result.scalar_one()

        # Verify all fields match
        assert retrieved.project_id == design.project_id
        assert retrieved.title == design.title
        assert retrieved.system_type == design.system_type
        assert retrieved.loads == design.loads
        assert retrieved.equipment == design.equipment
        assert retrieved.distribution == design.distribution
        assert retrieved.sizing_results == design.sizing_results

    @pytest.mark.asyncio
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(design=civil_design_strategy())
    async def test_civil_design_round_trip(
        self, test_db_session: AsyncSession, design: CivilDesign
    ):
        """Test CivilDesign serialization/deserialization preserves data.

        **Validates: Requirements 12.3**
        """
        # Save to database
        test_db_session.add(design)
        await test_db_session.commit()
        await test_db_session.refresh(design)

        # Retrieve from database
        from sqlalchemy import select

        result = await test_db_session.execute(
            select(CivilDesign).where(CivilDesign.id == design.id)
        )
        retrieved = result.scalar_one()

        # Verify all fields match
        assert retrieved.project_id == design.project_id
        assert retrieved.title == design.title
        assert retrieved.design_type == design.design_type
        assert retrieved.site_parameters == design.site_parameters
        assert retrieved.design_criteria == design.design_criteria
        assert retrieved.design_results == design.design_results

    @pytest.mark.asyncio
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(log=audit_log_strategy())
    async def test_audit_log_round_trip(
        self, test_db_session: AsyncSession, log: AuditLog
    ):
        """Test AuditLog serialization/deserialization preserves data.

        **Validates: Requirements 12.3**
        """
        # Save to database
        test_db_session.add(log)
        await test_db_session.commit()
        await test_db_session.refresh(log)

        # Retrieve from database
        from sqlalchemy import select

        result = await test_db_session.execute(
            select(AuditLog).where(AuditLog.id == log.id)
        )
        retrieved = result.scalar_one()

        # Verify all fields match
        assert retrieved.user_id == log.user_id
        assert retrieved.project_id == log.project_id
        assert retrieved.action_type == log.action_type
        assert retrieved.entity_type == log.entity_type
        assert retrieved.entity_id == log.entity_id
        assert retrieved.changes == log.changes
        assert retrieved.status == log.status
