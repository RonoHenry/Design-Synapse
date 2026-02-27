"""Property-based tests for optimistic locking functionality."""

from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from hypothesis import given
from hypothesis import strategies as st
from src.core.exceptions import ConflictError, NotFoundError
from src.models.design import Design
from src.repositories.design_repository import DesignRepository


class TestOptimisticLockingProperties:
    """Property-based tests for optimistic locking functionality."""

    @given(
        initial_version=st.integers(min_value=1, max_value=100),
        concurrent_updates=st.integers(min_value=2, max_value=10),
        update_delay=st.integers(min_value=0, max_value=5),
    )
    @pytest.mark.asyncio
    async def test_property_51_optimistic_locking_conflict_detection(
        self, initial_version: int, concurrent_updates: int, update_delay: int
    ):
        """
        Property 51: Optimistic locking conflict detection

        For any design with version N, when multiple concurrent updates attempt
        to modify the design, only ONE update should succeed and all others
        should raise ConflictError with version mismatch details.

        **Validates: Requirements 13.5**
        """
        # Create mock session and repository
        session = AsyncMock()
        repository = DesignRepository(session)

        # Create mock design with initial version
        design_id = str(uuid4())
        mock_design = Mock(spec=Design)
        mock_design.id = design_id
        mock_design.version_number = initial_version
        mock_design.current_version = f"{initial_version}.0"
        mock_design.name = "Test Design"
        mock_design.description = "Test Description"
        mock_design.building_type = "office"
        mock_design.location_data = {"city": "Test City"}
        mock_design.metadata = {}
        mock_design.status = "draft"
        mock_design.is_deleted = False

        # Mock repository.get to return the design
        repository.get = AsyncMock(return_value=mock_design)

        # Track successful and failed updates
        successful_updates = 0
        conflict_errors = 0

        # Simulate concurrent updates
        for i in range(concurrent_updates):
            try:
                # Each update expects the initial version (simulating concurrent access)
                expected_version = initial_version

                # Mock the version check behavior
                if successful_updates == 0:
                    # First update succeeds
                    mock_design.version_number = initial_version + 1
                    mock_design.current_version = f"{initial_version + 1}.0"
                    result = await repository.update_with_version_check(
                        design_id=design_id,
                        expected_version_number=expected_version,
                        name=f"Updated Design {i}",
                    )
                    successful_updates += 1

                    # Verify the update succeeded
                    assert result is not None
                    assert result.version_number == initial_version + 1

                else:
                    # Subsequent updates should fail due to version mismatch
                    # Mock the version conflict
                    repository.get = AsyncMock(
                        return_value=mock_design
                    )  # Design now has higher version

                    with pytest.raises(ValueError, match="Version conflict"):
                        await repository.update_with_version_check(
                            design_id=design_id,
                            expected_version_number=expected_version,  # Still expects old version
                            name=f"Failed Update {i}",
                        )
                    conflict_errors += 1

            except ValueError:
                conflict_errors += 1

        # Verify exactly one update succeeded
        assert successful_updates == 1
        assert conflict_errors == concurrent_updates - 1

    @given(
        version_numbers=st.lists(
            st.integers(min_value=1, max_value=1000),
            min_size=2,
            max_size=10,
            unique=True,
        )
    )
    @pytest.mark.asyncio
    async def test_version_conflict_error_details(self, version_numbers: list):
        """
        Test that version conflicts provide detailed error information.

        Verifies that ConflictError contains specific details about
        expected vs actual version numbers.
        """
        session = AsyncMock()
        repository = DesignRepository(session)

        design_id = str(uuid4())

        for i, current_version in enumerate(version_numbers):
            # Create mock design with current version
            mock_design = Mock(spec=Design)
            mock_design.id = design_id
            mock_design.version_number = current_version
            mock_design.current_version = f"{current_version}.0"

            repository.get = AsyncMock(return_value=mock_design)

            # Try to update with different expected version
            for expected_version in version_numbers:
                if expected_version != current_version:
                    # Should raise ValueError with version details
                    with pytest.raises(ValueError) as exc_info:
                        await repository.update_with_version_check(
                            design_id=design_id,
                            expected_version_number=expected_version,
                            name="Test Update",
                        )

                    # Verify error message contains version information
                    error_message = str(exc_info.value)
                    assert f"expected {expected_version}" in error_message
                    assert f"got {current_version}" in error_message

    @given(
        design_exists=st.booleans(),
        version_number=st.integers(min_value=1, max_value=100),
    )
    @pytest.mark.asyncio
    async def test_optimistic_locking_with_nonexistent_design(
        self, design_exists: bool, version_number: int
    ):
        """
        Test optimistic locking behavior when design doesn't exist.

        Verifies that attempting to update a non-existent design
        returns None regardless of version number.
        """
        session = AsyncMock()
        repository = DesignRepository(session)

        design_id = str(uuid4())

        if design_exists:
            # Create mock design
            mock_design = Mock(spec=Design)
            mock_design.id = design_id
            mock_design.version_number = version_number
            repository.get = AsyncMock(return_value=mock_design)

            # Update should work if version matches
            result = await repository.update_with_version_check(
                design_id=design_id,
                expected_version_number=version_number,
                name="Test Update",
            )
            assert result is not None

        else:
            # Design doesn't exist
            repository.get = AsyncMock(return_value=None)

            # Update should return None
            result = await repository.update_with_version_check(
                design_id=design_id,
                expected_version_number=version_number,
                name="Test Update",
            )
            assert result is None

    @given(
        update_fields=st.dictionaries(
            keys=st.sampled_from(["name", "description", "status", "metadata"]),
            values=st.one_of(
                st.text(min_size=1, max_size=100),
                st.dictionaries(
                    st.text(min_size=1, max_size=10), st.text(min_size=1, max_size=50)
                ),
            ),
            min_size=1,
            max_size=4,
        ),
        initial_version=st.integers(min_value=1, max_value=50),
    )
    @pytest.mark.asyncio
    async def test_successful_optimistic_update_increments_version(
        self, update_fields: dict, initial_version: int
    ):
        """
        Test that successful optimistic updates increment version number.

        Verifies that when an update succeeds with correct version,
        the version number is incremented and current_version is updated.
        """
        session = AsyncMock()
        repository = DesignRepository(session)

        design_id = str(uuid4())

        # Create mock design
        mock_design = Mock(spec=Design)
        mock_design.id = design_id
        mock_design.version_number = initial_version
        mock_design.current_version = f"{initial_version}.0"

        # Add all possible fields to mock
        for field in ["name", "description", "status", "metadata"]:
            setattr(mock_design, field, f"initial_{field}")

        repository.get = AsyncMock(return_value=mock_design)

        # Mock session operations
        session.flush = AsyncMock()
        session.refresh = AsyncMock()
        session.rollback = AsyncMock()

        # Perform update
        result = await repository.update_with_version_check(
            design_id=design_id,
            expected_version_number=initial_version,
            **update_fields,
        )

        # Verify result
        assert result is not None
        assert result.version_number == initial_version + 1
        assert result.current_version == f"{initial_version + 1}.0"

        # Verify fields were updated
        for field, value in update_fields.items():
            if hasattr(result, field):
                assert getattr(result, field) == value

    @given(
        sequence_length=st.integers(min_value=2, max_value=10),
        version_gaps=st.lists(
            st.integers(min_value=1, max_value=5), min_size=1, max_size=9
        ),
    )
    @pytest.mark.asyncio
    async def test_version_sequence_integrity(
        self, sequence_length: int, version_gaps: list
    ):
        """
        Test that version sequences maintain integrity under various scenarios.

        Verifies that version numbers follow expected patterns and
        gaps in version expectations are properly detected.
        """
        session = AsyncMock()
        repository = DesignRepository(session)

        design_id = str(uuid4())
        current_version = 1

        for i in range(sequence_length):
            # Create mock design with current version
            mock_design = Mock(spec=Design)
            mock_design.id = design_id
            mock_design.version_number = current_version
            mock_design.current_version = f"{current_version}.0"
            mock_design.name = f"Design v{current_version}"

            repository.get = AsyncMock(return_value=mock_design)
            session.flush = AsyncMock()
            session.refresh = AsyncMock()

            # Test correct version update
            result = await repository.update_with_version_check(
                design_id=design_id,
                expected_version_number=current_version,
                name=f"Updated Design v{current_version + 1}",
            )

            assert result is not None
            assert result.version_number == current_version + 1

            # Test incorrect version (if we have gaps to test)
            if i < len(version_gaps):
                gap = version_gaps[i]
                wrong_expected_version = current_version + gap

                with pytest.raises(ValueError):
                    await repository.update_with_version_check(
                        design_id=design_id,
                        expected_version_number=wrong_expected_version,
                        name="Should Fail",
                    )

            current_version += 1
