"""Property-based tests for pagination functionality."""

import uuid
from datetime import datetime, timedelta
from typing import List

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from src.core.pagination import (PaginationCursor, PaginationHelper,
                                 PaginationParams, create_pagination_params,
                                 decode_cursor, encode_cursor)
from src.models.design import Design
from src.repositories.design_repository import DesignRepository
from src.services.design_service import DesignService


class TestPaginationProperties:
    """Property-based tests for pagination consistency."""

    @given(
        limit=st.integers(min_value=1, max_value=100),
        sort_direction=st.sampled_from(["asc", "desc"]),
        sort_field=st.sampled_from(["created_at", "updated_at", "name"]),
        num_items=st.integers(min_value=0, max_value=200),
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    async def test_property_pagination_consistency(
        self,
        limit: int,
        sort_direction: str,
        sort_field: str,
        num_items: int,
        db_session,
        design_repository_factory,
        mock_project_client,
    ):
        """
        Property 48: Pagination consistency
        For any list endpoint, pagination should work correctly: page size should
        be respected, cursors should be stable, and iterating through all pages
        should return all items exactly once.

        **Validates: Requirements 12.6**
        """
        # Create test designs
        designs = []
        base_time = datetime.utcnow()

        for i in range(num_items):
            design = Design(
                id=str(uuid.uuid4()),
                project_id=str(uuid.uuid4()),
                name=f"Test Design {i:03d}",
                description=f"Test description {i}",
                building_type="commercial",
                location_data={"country": "United States"},
                current_version="1.0",
                version_number=1,
                status="draft",
                metadata={},
                created_by=str(uuid.uuid4()),
                created_at=base_time + timedelta(minutes=i),
                updated_at=base_time + timedelta(minutes=i),
                is_deleted=False,
            )
            designs.append(design)
            db_session.add(design)

        await db_session.commit()

        # Create design repository and service
        design_repository = design_repository_factory(db_session)
        design_service = DesignService(design_repository, mock_project_client)

        # Collect all items through pagination
        all_paginated_items = []
        cursor = None
        page_count = 0
        max_pages = (num_items // limit) + 2  # Safety limit

        while page_count < max_pages:
            params = create_pagination_params(
                limit=limit,
                cursor=cursor,
                sort_field=sort_field,
                sort_direction=sort_direction,
            )

            paginated_response = await design_service.list_designs(
                params=params, include_deleted=False, include_total=False
            )

            # Verify page size is respected
            assert len(paginated_response.items) <= limit

            # Add items to collection
            all_paginated_items.extend(paginated_response.items)

            # Check if we have more pages
            if not paginated_response.has_next:
                break

            # Verify cursor is provided when has_next is True
            assert paginated_response.next_cursor is not None

            # Verify cursor is stable (can be decoded)
            decoded_cursor = decode_cursor(paginated_response.next_cursor)
            assert decoded_cursor.id is not None
            assert decoded_cursor.sort_value is not None

            cursor = paginated_response.next_cursor
            page_count += 1

        # Verify we got all items exactly once
        paginated_ids = [design.id for design in all_paginated_items]
        expected_ids = [design.id for design in designs]

        # All items should be returned
        assert len(paginated_ids) == len(expected_ids)

        # No duplicates
        assert len(set(paginated_ids)) == len(paginated_ids)

        # All expected items are present
        assert set(paginated_ids) == set(expected_ids)

        # Verify sorting is correct
        if num_items > 0:
            sort_values = []
            for design in all_paginated_items:
                if sort_field == "created_at":
                    sort_values.append(design.created_at)
                elif sort_field == "updated_at":
                    sort_values.append(design.updated_at)
                elif sort_field == "name":
                    sort_values.append(design.name)

            if sort_direction == "asc":
                assert sort_values == sorted(sort_values)
            else:
                assert sort_values == sorted(sort_values, reverse=True)

    @given(
        sort_value=st.one_of(
            st.datetimes(),
            st.text(min_size=1, max_size=100),
            st.integers(),
            st.floats(allow_nan=False, allow_infinity=False),
        ),
        item_id=st.uuids(),
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    async def test_property_cursor_encoding_round_trip(self, sort_value, item_id):
        """
        Property: Cursor encoding round-trip
        For any sort value and item ID, encoding to cursor and then decoding
        should return the original values.

        **Validates: Requirements 12.6**
        """
        # Encode cursor
        cursor_str = encode_cursor(sort_value, item_id)

        # Verify cursor is a valid string
        assert isinstance(cursor_str, str)
        assert len(cursor_str) > 0

        # Decode cursor
        decoded_cursor = decode_cursor(cursor_str)

        # Verify round-trip consistency
        assert str(decoded_cursor.id) == str(item_id)

        # Handle different types for sort_value comparison
        if isinstance(sort_value, datetime):
            # For datetime, compare string representations since JSON serialization
            # may change the format slightly
            assert str(decoded_cursor.sort_value) == str(sort_value)
        else:
            assert decoded_cursor.sort_value == sort_value

    @given(
        invalid_cursor=st.one_of(
            st.text(min_size=1, max_size=50).filter(
                lambda x: not x.replace("=", "")
                .replace("+", "")
                .replace("/", "")
                .isalnum()
            ),
            st.binary(min_size=1, max_size=50),
            st.just("invalid_base64!@#"),
            st.just(""),
        )
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    async def test_property_invalid_cursor_handling(self, invalid_cursor):
        """
        Property: Invalid cursor handling
        For any invalid cursor string, decoding should raise a ValueError
        with appropriate error message.

        **Validates: Requirements 12.6**
        """
        with pytest.raises(ValueError) as exc_info:
            decode_cursor(str(invalid_cursor))

        # Verify error message contains useful information
        error_message = str(exc_info.value)
        assert "Invalid cursor format" in error_message

    @given(
        page_sizes=st.lists(
            st.integers(min_value=1, max_value=50), min_size=1, max_size=5
        ),
        total_items=st.integers(min_value=0, max_value=100),
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    async def test_property_pagination_different_page_sizes(
        self,
        page_sizes: List[int],
        total_items: int,
        db_session,
        design_repository_factory,
        mock_project_client,
    ):
        """
        Property: Pagination with different page sizes
        For any set of page sizes and total items, pagination should return
        all items regardless of page size used.

        **Validates: Requirements 12.6**
        """
        # Create test designs
        designs = []
        base_time = datetime.utcnow()

        for i in range(total_items):
            design = Design(
                id=str(uuid.uuid4()),
                project_id=str(uuid.uuid4()),
                name=f"Design {i:03d}",
                description=f"Description {i}",
                building_type="residential",
                location_data={"country": "Canada"},
                current_version="1.0",
                version_number=1,
                status="draft",
                metadata={},
                created_by=str(uuid.uuid4()),
                created_at=base_time + timedelta(seconds=i),
                updated_at=base_time + timedelta(seconds=i),
                is_deleted=False,
            )
            designs.append(design)
            db_session.add(design)

        await db_session.commit()

        # Create design repository and service
        design_repository = design_repository_factory(db_session)
        design_service = DesignService(design_repository, mock_project_client)

        # Test each page size
        for page_size in page_sizes:
            all_items = []
            cursor = None
            page_count = 0
            max_pages = (total_items // page_size) + 2

            while page_count < max_pages:
                params = create_pagination_params(
                    limit=page_size,
                    cursor=cursor,
                    sort_field="created_at",
                    sort_direction="asc",
                )

                response = await design_service.list_designs(
                    params=params, include_deleted=False, include_total=False
                )

                # Verify page size constraint
                assert len(response.items) <= page_size

                all_items.extend(response.items)

                if not response.has_next:
                    break

                cursor = response.next_cursor
                page_count += 1

            # Verify we got all items
            assert len(all_items) == total_items

            # Verify no duplicates
            item_ids = [item.id for item in all_items]
            assert len(set(item_ids)) == len(item_ids)

    @given(
        limit=st.integers(min_value=1, max_value=20),
        num_items=st.integers(min_value=0, max_value=50),
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    async def test_property_empty_and_single_page_results(
        self,
        limit: int,
        num_items: int,
        db_session,
        design_repository_factory,
        mock_project_client,
    ):
        """
        Property: Empty and single page results
        For any limit and number of items, pagination should handle empty
        results and single-page results correctly.

        **Validates: Requirements 12.6**
        """
        # Create test designs
        designs = []
        for i in range(num_items):
            design = Design(
                id=str(uuid.uuid4()),
                project_id=str(uuid.uuid4()),
                name=f"Design {i}",
                description=f"Description {i}",
                building_type="industrial",
                location_data={"country": "Mexico"},
                current_version="1.0",
                version_number=1,
                status="draft",
                metadata={},
                created_by=str(uuid.uuid4()),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                is_deleted=False,
            )
            designs.append(design)
            db_session.add(design)

        await db_session.commit()

        # Create design repository and service
        design_repository = design_repository_factory(db_session)
        design_service = DesignService(design_repository, mock_project_client)

        # Test pagination
        params = create_pagination_params(
            limit=limit, cursor=None, sort_field="created_at", sort_direction="desc"
        )

        response = await design_service.list_designs(
            params=params, include_deleted=False, include_total=False
        )

        # Verify response structure
        assert isinstance(response.items, list)
        assert isinstance(response.has_next, bool)
        assert len(response.items) <= limit

        if num_items == 0:
            # Empty results
            assert len(response.items) == 0
            assert response.has_next is False
            assert response.next_cursor is None
        elif num_items <= limit:
            # Single page results
            assert len(response.items) == num_items
            assert response.has_next is False
            assert response.next_cursor is None
        else:
            # Multiple pages
            assert len(response.items) == limit
            assert response.has_next is True
            assert response.next_cursor is not None

    @given(
        params=st.builds(
            PaginationParams,
            limit=st.integers(min_value=1, max_value=100),
            cursor=st.one_of(st.none(), st.text(min_size=1, max_size=100)),
            sort_field=st.sampled_from(["created_at", "updated_at", "name"]),
            sort_direction=st.sampled_from(["asc", "desc"]),
        )
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    async def test_property_pagination_params_validation(
        self, params: PaginationParams
    ):
        """
        Property: Pagination parameters validation
        For any pagination parameters, the PaginationParams model should
        validate correctly and maintain constraints.

        **Validates: Requirements 12.6**
        """
        # Verify limit constraints
        assert 1 <= params.limit <= 100

        # Verify sort direction
        assert params.sort_direction in ["asc", "desc"]

        # Verify sort field is set
        assert params.sort_field is not None
        assert len(params.sort_field) > 0

        # If cursor is provided, it should be a non-empty string
        if params.cursor is not None:
            assert isinstance(params.cursor, str)
            assert len(params.cursor) > 0
