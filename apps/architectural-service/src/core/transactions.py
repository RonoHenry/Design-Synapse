"""Transaction management utilities and decorators."""

import functools
import logging
from typing import Any, Callable, TypeVar

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


def transactional(func: F) -> F:
    """
    Decorator for service methods that require database transactions.

    Automatically commits successful operations and rolls back on exceptions.
    Provides transaction logging for debugging and audit purposes.

    Usage:
        @transactional
        async def create_design(self, session: AsyncSession, ...):
            # Database operations here
            # Transaction will be committed automatically

    Args:
        func: Async function to wrap with transaction management

    Returns:
        Wrapped function with transaction management

    Raises:
        SQLAlchemyError: If database operation fails
        Exception: Re-raises any exception after rollback
    """

    @functools.wraps(func)
    async def wrapper(*args, **kwargs) -> Any:
        # Extract session from arguments
        session = None

        # Look for session in args (typically self, session, ...)
        for arg in args:
            if isinstance(arg, AsyncSession):
                session = arg
                break

        # Look for session in kwargs
        if session is None:
            session = kwargs.get("session")

        if session is None:
            raise ValueError(
                f"Function {func.__name__} decorated with @transactional "
                "must have an AsyncSession parameter named 'session'"
            )

        # Get function name for logging
        func_name = f"{func.__module__}.{func.__qualname__}"

        logger.debug(f"Starting transaction for {func_name}")

        try:
            # Execute the function
            result = await func(*args, **kwargs)

            # Commit the transaction
            await session.commit()

            logger.debug(f"Transaction committed successfully for {func_name}")

            return result

        except SQLAlchemyError as e:
            # Database error - rollback and re-raise
            await session.rollback()
            logger.error(
                f"Database error in {func_name}, transaction rolled back: {e}",
                exc_info=True,
            )
            raise

        except Exception as e:
            # Any other error - rollback and re-raise
            await session.rollback()
            logger.error(
                f"Error in {func_name}, transaction rolled back: {e}", exc_info=True
            )
            raise

    return wrapper


class TransactionManager:
    """
    Context manager for explicit transaction management.

    Provides more control over transaction boundaries than the decorator.
    Useful for complex operations that span multiple service calls.
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize transaction manager.

        Args:
            session: Database session to manage
        """
        self.session = session
        self._committed = False
        self._rolled_back = False

    async def __aenter__(self) -> "TransactionManager":
        """Enter transaction context."""
        logger.debug("Starting explicit transaction")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Exit transaction context.

        Automatically rolls back if not explicitly committed.
        """
        if exc_type is not None:
            # Exception occurred - rollback
            if not self._rolled_back:
                await self.rollback()
            return False

        if not self._committed and not self._rolled_back:
            # No explicit commit or rollback - rollback by default
            logger.warning("Transaction not explicitly committed, rolling back")
            await self.rollback()

    async def commit(self) -> None:
        """
        Commit the transaction.

        Raises:
            SQLAlchemyError: If commit fails
            RuntimeError: If already committed or rolled back
        """
        if self._committed:
            raise RuntimeError("Transaction already committed")
        if self._rolled_back:
            raise RuntimeError("Transaction already rolled back")

        try:
            await self.session.commit()
            self._committed = True
            logger.debug("Explicit transaction committed successfully")
        except SQLAlchemyError as e:
            logger.error(f"Failed to commit transaction: {e}", exc_info=True)
            await self.rollback()
            raise

    async def rollback(self) -> None:
        """
        Rollback the transaction.

        Raises:
            SQLAlchemyError: If rollback fails
            RuntimeError: If already committed or rolled back
        """
        if self._committed:
            raise RuntimeError("Cannot rollback committed transaction")
        if self._rolled_back:
            return  # Already rolled back

        try:
            await self.session.rollback()
            self._rolled_back = True
            logger.debug("Explicit transaction rolled back")
        except SQLAlchemyError as e:
            logger.error(f"Failed to rollback transaction: {e}", exc_info=True)
            raise


async def execute_in_transaction(
    session: AsyncSession, operation: Callable[[], Any]
) -> Any:
    """
    Execute an operation within a transaction.

    Utility function for one-off transactional operations.

    Args:
        session: Database session
        operation: Async callable to execute

    Returns:
        Result of the operation

    Raises:
        Exception: Re-raises any exception after rollback
    """
    async with TransactionManager(session) as tx:
        result = await operation()
        await tx.commit()
        return result
