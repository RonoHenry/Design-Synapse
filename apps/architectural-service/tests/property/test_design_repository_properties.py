"""Property-based tests for DesignRepository."""

from datetime import datetime
from uuid import uuid4

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from src.repositories.design_repository import DesignRepository


@st.composite
def design_data(draw):
    """Generate valid design data for testing."""
    return {
        "project_id": str(uuid4()),
        "name": draw(
            st.text(
                min_size=1,
                max_size=255,
                alphabet=st.characters(blacklist_characters=["\x00"]),
            )
        ),
        "description": draw(
            st.one_of(
                st.none(),
                st.text(
                    max_size=1000, alphabet=st.characters(blacklist_characters=["\x00"])
                ),
            )
        ),
        "building_type": draw(
            st.sampled_from(
                [
                    "residential",
                    "commercial",
                    "industrial",
                    "institutional",
                    "mixed_use",
                ]
            )
        ),
        "location_data": {
            "address": draw(
                st.text(
                    min_size=1,
                    max_size=200,
                    alphabet=st.characters(blacklist_characters=["\x00"]),
                )
            ),
            "city": draw(
                st.text(
                    min_size=1,
                    max_size=100,
                    alphabet=st.characters(blacklist_characters=["\x00"]),
                )
            ),
            "state": draw(
                st.text(
                    min_size=2,
                    max_size=2,
                    alphabet=st.characters(whitelist_categories=("Lu",)),
                )
            ),
            "zip_code": draw(
                st.text(
                    min_size=5,
                    max_size=10,
                    alphabet=st.characters(whitelist_categories=("Nd",)),
                )
            ),
            "latitude": draw(
                st.floats(
                    min_value=-90, max_value=90, allow_nan=False, allow_infinity=False
                )
            ),
            "longitude": draw(
                st.floats(
                    min_value=-180, max_value=180, allow_nan=False, allow_infinity=False
                )
            ),
        },
        "design_metadata": draw(
            st.dictionaries(
                keys=st.text(
                    min_size=1,
                    max_size=50,
                    alphabet=st.characters(blacklist_characters=["\x00"]),
                ),
                values=st.one_of(
                    st.text(
                        max_size=100,
                        alphabet=st.characters(blacklist_characters=["\x00"]),
                    ),
                    st.integers(),
                    st.floats(allow_nan=False, allow_infinity=False),
                    st.booleans(),
                ),
                max_size=5,
            )
        ),
        "created_by": str(uuid4()),
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }


@pytest.mark.property
@pytest.mark.asyncio
class TestDesignRepositoryProperties:
    """Property-based tests for DesignRepository."""

    @settings(
        max_examples=10,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    @given(data=design_data())
    async def test_property_design_initialization_consistency(self, data, test_session):
        """
        Property 1: Design initialization consistency

        For any new design document creation request, the created design
        should have a unique identifier, version "1.0", version_number 1,
        and all required metadata fields populated.

        Validates: Requirements 1.1, 1.7
        """
        repo = DesignRepository(test_session)
        design = await repo.create(**data)
        await test_session.commit()

        assert design.id is not None
        assert len(design.id) == 36
        assert design.current_version == "1.0"
        assert design.version_number == 1
        assert design.created_at is not None
        assert design.updated_at is not None
        assert design.created_by == data["created_by"]
        assert design.project_id == data["project_id"]
        assert design.name == data["name"]
        assert design.building_type == data["building_type"]
        assert design.location_data == data["location_data"]
        assert design.status == "draft"
        assert design.is_deleted == False
        assert design.deleted_at is None
        assert design.design_metadata == data["design_metadata"]
