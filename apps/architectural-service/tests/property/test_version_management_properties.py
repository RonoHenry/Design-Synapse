"""Property-based tests for version management in DesignRepository.

**Property 3: Version history preservation**
For any design document with N updates, there should exist exactly N+1
versions (original plus N updates), and all versions should be retrievable.
**Validates: Requirements 1.3**

**Property 4: Version retrieval round-trip**
For any design document and any valid version number, retrieving that
version should return design data that matches the snapshot stored when
that version was created.
**Validates: Requirements 1.4**
"""

from datetime import datetime
from uuid import uuid4

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from src.repositories.design_repository import DesignRepository


@pytest.mark.asyncio
class TestVersionManagementProperties:
    """Property-based tests for version management."""

    @settings(
        suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None
    )
    @given(
        num_updates=st.integers(min_value=0, max_value=5),
        name=st.text(min_size=1, max_size=100),
        building_type=st.sampled_from(
            ["residential", "commercial", "industrial", "mixed_use"]
        ),
    )
    async def test_property_version_history_preservation(
        self,
        test_session,
        num_updates: int,
        name: str,
        building_type: str,
    ):
        """Property 3: Version history preservation.

        For any design with N updates, there should be exactly N+1 versions.
        **Validates: Requirements 1.3**
        """
        # Arrange
        repo = DesignRepository(test_session)
        project_id = str(uuid4())
        created_by = str(uuid4())

        # Create initial design
        initial_data = {
            "project_id": project_id,
            "name": name,
            "building_type": building_type,
            "location_data": {"address": "123 Test St"},
            "created_by": created_by,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        design = await repo.create(**initial_data)
        await test_session.commit()

        # Create initial version snapshot
        await repo.create_version(
            design_id=design.id,
            version=design.current_version,
            version_number=design.version_number,
            design_data={
                "name": design.name,
                "building_type": design.building_type,
                "location_data": design.location_data,
            },
            created_by=created_by,
        )
        await test_session.commit()

        # Act: Perform N updates
        for i in range(num_updates):
            design.name = f"{name} - Update {i+1}"
            design.version_number += 1
            design.current_version = f"{design.version_number}.0"
            await repo.create_version(
                design_id=design.id,
                version=design.current_version,
                version_number=design.version_number,
                design_data={
                    "name": design.name,
                    "building_type": design.building_type,
                    "location_data": design.location_data,
                },
                created_by=created_by,
            )
            await test_session.commit()

        # Assert: Should have exactly N+1 versions
        versions = await repo.list_versions(design.id)
        assert len(versions) == num_updates + 1

        # Assert: All versions should be retrievable
        for version_num in range(1, num_updates + 2):
            version = await repo.get_by_version(design.id, f"{version_num}.0")
            assert version is not None
            assert version.version_number == version_num

    @settings(
        suppress_health_check=[HealthCheck.function_scoped_fixture], deadline=None
    )
    @given(
        name=st.text(min_size=1, max_size=100),
        description=st.text(min_size=0, max_size=500),
        building_type=st.sampled_from(
            ["residential", "commercial", "industrial", "mixed_use"]
        ),
        version_to_retrieve=st.integers(min_value=1, max_value=3),
    )
    async def test_property_version_retrieval_round_trip(
        self,
        test_session,
        name: str,
        description: str,
        building_type: str,
        version_to_retrieve: int,
    ):
        """Property 4: Version retrieval round-trip.

        Retrieving a version should return data matching the snapshot.
        **Validates: Requirements 1.4**
        """
        # Arrange
        repo = DesignRepository(test_session)
        project_id = str(uuid4())
        created_by = str(uuid4())

        # Create initial design
        initial_data = {
            "project_id": project_id,
            "name": name,
            "description": description,
            "building_type": building_type,
            "location_data": {"address": "123 Test St"},
            "created_by": created_by,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        design = await repo.create(**initial_data)
        await test_session.commit()

        # Create versions with different data
        version_data = {}
        for version_num in range(1, 4):
            # Store current state
            version_data[version_num] = {
                "name": design.name,
                "description": design.description,
                "building_type": design.building_type,
                "version_number": design.version_number,
            }

            # Create version snapshot
            await repo.create_version(
                design_id=design.id,
                version=design.current_version,
                version_number=design.version_number,
                design_data={
                    "name": design.name,
                    "description": design.description,
                    "building_type": design.building_type,
                    "location_data": design.location_data,
                },
                created_by=created_by,
            )
            await test_session.commit()

            # Update design for next version
            design.name = f"{name} - Version {version_num + 1}"
            design.description = f"{description} - Updated {version_num}"
            design.version_number += 1
            design.current_version = f"{design.version_number}.0"

        # Act: Retrieve the specified version
        retrieved = await repo.get_by_version(design.id, f"{version_to_retrieve}.0")

        # Assert: Retrieved data should match stored snapshot
        assert retrieved is not None
        expected = version_data[version_to_retrieve]
        assert retrieved.name == expected["name"]
        assert retrieved.description == expected["description"]
        assert retrieved.building_type == expected["building_type"]
        assert retrieved.version_number == expected["version_number"]
