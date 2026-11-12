"""Property-based tests for transaction management."""

from unittest.mock import AsyncMock, Mock

import pytest
from hypothesis import given
from hypothesis import strategies as st
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.transactions import (TransactionManager, execute_in_transaction,
                                   transactional)


class TestTransactionProperties:
    """Property-based tests for transaction management functionality."""

    @given(
        operation_count=st.integers(min_value=1, max_value=10),
        should_fail=st.booleans(),
        fail_at_step=st.integers(min_value=0, max_value=9),
    )
    @pytest.mark.asyncio
    async def test_property_49_transaction_atomicity(
        self, operation_count: int, should_fail: bool, fail_at_step: int
    ):
        """
        Property 49: Transaction atomicity

        For any sequence of database operations within a transaction,
        either ALL operations succeed and are committed,
        or ALL operations are rolled back if any operation fails.

        **Validates: Requirements 13.3, 13.4**
        """
        # Create mock session
        session = AsyncMock(spec=AsyncSession)
        session.commit = AsyncMock()
        session.rollback = AsyncMock()

        # Track operations performed
        operations_performed = []

        @transactional
        async def test_operation(session: AsyncSession, ops: list):
            """Test operation that performs multiple database operations."""
            for i in range(operation_count):
                if should_fail and i == fail_at_step:
                    # Simulate database error at specific step
                    raise SQLAlchemyError("Simulated database error")

                # Simulate database operation
                ops.append(f"operation_{i}")

        if should_fail and fail_at_step < operation_count:
            # Operation should fail and rollback
            with pytest.raises(SQLAlchemyError):
                await test_operation(session, operations_performed)

            # Verify rollback was called
            session.rollback.assert_called_once()
            session.commit.assert_not_called()

            # Verify operations were attempted up to failure point
            assert len(operations_performed) == fail_at_step

        else:
            # Operation should succeed and commit
            await test_operation(session, operations_performed)

            # Verify commit was called
            session.commit.assert_called_once()
            session.rollback.assert_not_called()

            # Verify all operations were performed
            assert len(operations_performed) == operation_count
            for i in range(operation_count):
                assert f"operation_{i}" in operations_performed

    @given(
        exception_type=st.sampled_from(
            [
                SQLAlchemyError("DB error"),
                ValueError("Value error"),
                RuntimeError("Runtime error"),
                Exception("Generic error"),
            ]
        )
    )
    @pytest.mark.asyncio
    async def test_property_50_transaction_rollback_completeness(
        self, exception_type: Exception
    ):
        """
        Property 50: Transaction rollback completeness

        For any exception type that occurs during a transaction,
        the transaction must be completely rolled back and the
        original exception must be re-raised.

        **Validates: Requirements 13.3, 13.4**
        """
        # Create mock session
        session = AsyncMock(spec=AsyncSession)
        session.commit = AsyncMock()
        session.rollback = AsyncMock()

        @transactional
        async def failing_operation(session: AsyncSession):
            """Operation that raises the test exception."""
            raise exception_type

        # Operation should fail with the original exception
        with pytest.raises(type(exception_type)) as exc_info:
            await failing_operation(session)

        # Verify the original exception is preserved
        assert str(exc_info.value) == str(exception_type)

        # Verify rollback was called
        session.rollback.assert_called_once()
        session.commit.assert_not_called()

    @given(
        nested_levels=st.integers(min_value=1, max_value=5),
        fail_at_level=st.integers(min_value=0, max_value=4),
    )
    @pytest.mark.asyncio
    async def test_transaction_manager_atomicity(
        self, nested_levels: int, fail_at_level: int
    ):
        """
        Test TransactionManager atomicity with nested operations.

        Verifies that explicit transaction management maintains
        atomicity even with complex nested operations.
        """
        session = AsyncMock(spec=AsyncSession)
        session.commit = AsyncMock()
        session.rollback = AsyncMock()

        operations_performed = []

        async def nested_operation(level: int):
            """Recursive operation that may fail at specified level."""
            operations_performed.append(f"level_{level}")

            if level == fail_at_level and fail_at_level < nested_levels:
                raise ValueError(f"Failure at level {level}")

            if level < nested_levels - 1:
                await nested_operation(level + 1)

        if fail_at_level < nested_levels:
            # Should fail and rollback
            with pytest.raises(ValueError):
                async with TransactionManager(session) as tx:
                    await nested_operation(0)
                    await tx.commit()

            # Verify rollback was called
            session.rollback.assert_called_once()
            session.commit.assert_not_called()

            # Verify operations up to failure point
            assert len(operations_performed) == fail_at_level + 1

        else:
            # Should succeed and commit
            async with TransactionManager(session) as tx:
                await nested_operation(0)
                await tx.commit()

            # Verify commit was called
            session.commit.assert_called_once()
            session.rollback.assert_not_called()

            # Verify all operations were performed
            assert len(operations_performed) == nested_levels

    @given(commit_explicitly=st.booleans(), should_fail=st.booleans())
    @pytest.mark.asyncio
    async def test_transaction_manager_context_behavior(
        self, commit_explicitly: bool, should_fail: bool
    ):
        """
        Test TransactionManager context manager behavior.

        Verifies proper handling of explicit commits vs automatic rollbacks.
        """
        session = AsyncMock(spec=AsyncSession)
        session.commit = AsyncMock()
        session.rollback = AsyncMock()

        if should_fail:
            # Exception during operation
            with pytest.raises(RuntimeError):
                async with TransactionManager(session) as tx:
                    raise RuntimeError("Test error")

            # Should rollback automatically
            session.rollback.assert_called_once()
            session.commit.assert_not_called()

        elif commit_explicitly:
            # Explicit commit
            async with TransactionManager(session) as tx:
                await tx.commit()

            # Should commit
            session.commit.assert_called_once()
            session.rollback.assert_not_called()

        else:
            # No explicit commit - should rollback by default
            async with TransactionManager(session):
                pass  # No explicit commit

            # Should rollback by default
            session.rollback.assert_called_once()
            session.commit.assert_not_called()

    @given(
        operation_results=st.lists(
            st.one_of(st.integers(), st.text(), st.booleans()), min_size=1, max_size=10
        )
    )
    @pytest.mark.asyncio
    async def test_execute_in_transaction_utility(self, operation_results: list):
        """
        Test execute_in_transaction utility function.

        Verifies that the utility function properly manages transactions
        for one-off operations.
        """
        session = AsyncMock(spec=AsyncSession)
        session.commit = AsyncMock()
        session.rollback = AsyncMock()

        results_returned = []

        async def test_operation():
            """Operation that returns multiple results."""
            for result in operation_results:
                results_returned.append(result)
            return operation_results

        # Execute operation
        result = await execute_in_transaction(session, test_operation)

        # Verify result is correct
        assert result == operation_results
        assert results_returned == operation_results

        # Verify transaction was committed
        session.commit.assert_called_once()
        session.rollback.assert_not_called()

    @pytest.mark.asyncio
    async def test_transactional_decorator_session_detection(self):
        """
        Test that @transactional decorator properly detects session parameter.

        Verifies error handling when session is not provided.
        """

        @transactional
        async def operation_without_session():
            """Operation without session parameter."""
            pass

        @transactional
        async def operation_with_session(session: AsyncSession):
            """Operation with session parameter."""
            pass

        # Should raise ValueError when no session found
        with pytest.raises(ValueError, match="must have an AsyncSession parameter"):
            await operation_without_session()

        # Should work with session
        session = AsyncMock(spec=AsyncSession)
        session.commit = AsyncMock()
        session.rollback = AsyncMock()

        await operation_with_session(session)
        session.commit.assert_called_once()
