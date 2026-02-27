"""Database Integration Testing (TDD Implementation)

Following strict TDD methodology - these tests define expected behavior
for database integration scenarios. All tests will fail initially
and then we implement functionality to make them pass.

Requirements covered:
- 1.4: CASCADE delete behavior
- 1.5: Foreign key constraint violations
- 4.3: Database connection pooling under load
- 4.4: Database error recovery scenarios
"""
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List

import asyncpg
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import sessionmaker

from packages.common.testing.database import DatabaseTestManager


class TestDatabaseCascadeDeletes:
    """Test CASCADE delete behavior across all services (TDD)."""

    @pytest.mark.asyncio
    async def test_knowledge_service_cascade_deletes(self, knowledge_db_session):
        """
        FAILING TEST: Resource deletion cascades to Citations and Bookmarks.

        Expected behavior:
        - When a Resource is deleted, all associated Citations are deleted
        - When a Resource is deleted, all associated Bookmarks are deleted
        - Cascade deletes happen automatically without manual intervention
        - No orphaned records remain after cascade delete

        This test will fail initially because:
        1. CASCADE constraints may not be properly defined in migrations
        2. SQLAlchemy relationships may not have proper cascade settings
        3. Database foreign key constraints may be missing
        """
        # Import models dynamically to avoid import issues
        try:
            from apps.knowledge_service.knowledge_service.models.bookmark import \
                Bookmark
            from apps.knowledge_service.knowledge_service.models.resource import (
                Citation, Resource)
        except ImportError:
            pytest.skip("Knowledge service models not available")

        # Create a resource with citations and bookmarks
        resource = Resource(
            title="Test Resource for Cascade",
            url="https://example.com/cascade-test",
            content_type="article",
            description="Testing cascade delete behavior",
            created_by=1,  # Assuming user ID 1 exists
        )
        knowledge_db_session.add(resource)
        knowledge_db_session.flush()  # Get the resource ID

        # Create citations for this resource
        citation1 = Citation(
            resource_id=resource.id,
            citation_text="First citation for cascade test",
            page_number=1,
            created_by=1,
        )
        citation2 = Citation(
            resource_id=resource.id,
            citation_text="Second citation for cascade test",
            page_number=2,
            created_by=1,
        )

        # Create bookmarks for this resource
        bookmark1 = Bookmark(
            resource_id=resource.id, user_id=1, notes="First bookmark for cascade test"
        )
        bookmark2 = Bookmark(
            resource_id=resource.id,
            user_id=2,  # Different user
            notes="Second bookmark for cascade test",
        )

        knowledge_db_session.add_all([citation1, citation2, bookmark1, bookmark2])
        knowledge_db_session.commit()

        # Verify data was created
        assert (
            knowledge_db_session.query(Resource).filter_by(id=resource.id).first()
            is not None
        )
        assert (
            knowledge_db_session.query(Citation)
            .filter_by(resource_id=resource.id)
            .count()
            == 2
        )
        assert (
            knowledge_db_session.query(Bookmark)
            .filter_by(resource_id=resource.id)
            .count()
            == 2
        )

        # Delete the resource - this should cascade to citations and bookmarks
        knowledge_db_session.delete(resource)
        knowledge_db_session.commit()

        # Verify cascade delete worked
        assert (
            knowledge_db_session.query(Resource).filter_by(id=resource.id).first()
            is None
        )
        assert (
            knowledge_db_session.query(Citation)
            .filter_by(resource_id=resource.id)
            .count()
            == 0
        )
        assert (
            knowledge_db_session.query(Bookmark)
            .filter_by(resource_id=resource.id)
            .count()
            == 0
        )

    @pytest.mark.asyncio
    async def test_project_service_cascade_deletes(self, project_db_session):
        """
        FAILING TEST: Project deletion cascades to Comments.

        Expected behavior:
        - When a Project is deleted, all associated Comments are deleted
        - Cascade deletes preserve data integrity
        - No orphaned comments remain after project deletion

        This test will fail initially because:
        1. CASCADE constraints may not be properly defined
        2. Comment model foreign key may not have proper cascade settings
        """
        # Import models dynamically to avoid import issues
        try:
            from apps.project_service.src.models.comment import Comment
            from apps.project_service.src.models.project import Project
        except ImportError:
            pytest.skip("Project service models not available")

        # Create a project with comments
        project = Project(
            name="Test Project for Cascade",
            description="Testing cascade delete behavior",
            status="active",
            created_by=1,
        )
        project_db_session.add(project)
        project_db_session.flush()  # Get the project ID

        # Create comments for this project
        comment1 = Comment(
            project_id=project.id,
            content="First comment for cascade test",
            created_by=1,
        )
        comment2 = Comment(
            project_id=project.id,
            content="Second comment for cascade test",
            created_by=2,
        )

        project_db_session.add_all([comment1, comment2])
        project_db_session.commit()

        # Verify data was created
        assert (
            project_db_session.query(Project).filter_by(id=project.id).first()
            is not None
        )
        assert (
            project_db_session.query(Comment).filter_by(project_id=project.id).count()
            == 2
        )

        # Delete the project - this should cascade to comments
        project_db_session.delete(project)
        project_db_session.commit()

        # Verify cascade delete worked
        assert (
            project_db_session.query(Project).filter_by(id=project.id).first() is None
        )
        assert (
            project_db_session.query(Comment).filter_by(project_id=project.id).count()
            == 0
        )

    @pytest.mark.asyncio
    async def test_user_service_role_constraints(self, user_db_session):
        """
        FAILING TEST: User deletion handles role relationships properly.

        Expected behavior:
        - Users with roles can be deleted without constraint violations
        - Role assignments are cleaned up when users are deleted
        - System maintains referential integrity

        This test will fail initially because:
        1. User-Role relationship constraints may not be properly defined
        2. Cascade behavior may not be configured correctly
        """
        # Import models dynamically to avoid import issues
        try:
            from apps.user_service.src.models.role import Role
            from apps.user_service.src.models.user import User
        except ImportError:
            pytest.skip("User service models not available")

        # Create a role
        role = Role(
            name="test_cascade_role", description="Role for testing cascade behavior"
        )
        user_db_session.add(role)
        user_db_session.flush()

        # Create a user with this role
        user = User(
            email="cascade.test@example.com",
            password_hash="hashed_password",
            first_name="Cascade",
            last_name="Test",
            role_id=role.id,
        )
        user_db_session.add(user)
        user_db_session.commit()

        # Verify data was created
        assert user_db_session.query(User).filter_by(id=user.id).first() is not None
        assert user_db_session.query(Role).filter_by(id=role.id).first() is not None

        # Delete the user - should not cause constraint violations
        user_db_session.delete(user)
        user_db_session.commit()

        # Role should still exist (users don't cascade delete roles)
        assert user_db_session.query(User).filter_by(id=user.id).first() is None
        assert user_db_session.query(Role).filter_by(id=role.id).first() is not None


class TestForeignKeyConstraints:
    """Test foreign key constraint violations (TDD)."""

    @pytest.mark.asyncio
    async def test_citation_requires_valid_resource(self, knowledge_db_session):
        """
        FAILING TEST: Citations cannot be created with invalid resource_id.

        Expected behavior:
        - Creating Citation with non-existent resource_id raises IntegrityError
        - Database enforces foreign key constraints
        - Error message is clear and actionable

        This test will fail initially because:
        1. Foreign key constraints may not be properly defined
        2. Error handling may not be implemented
        """
        # Import models dynamically to avoid import issues
        try:
            from apps.knowledge_service.knowledge_service.models.resource import \
                Citation
        except ImportError:
            pytest.skip("Knowledge service models not available")

        # Try to create citation with non-existent resource_id
        citation = Citation(
            resource_id=99999,  # Non-existent resource
            citation_text="This should fail",
            page_number=1,
            created_by=1,
        )
        knowledge_db_session.add(citation)

        # This should raise an IntegrityError due to foreign key constraint
        with pytest.raises(IntegrityError) as exc_info:
            knowledge_db_session.commit()

        # Verify the error is related to foreign key constraint
        assert "foreign key constraint" in str(exc_info.value).lower()
        assert "resource_id" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_bookmark_requires_valid_resource(self, knowledge_db_session):
        """
        FAILING TEST: Bookmarks cannot be created with invalid resource_id.

        Expected behavior:
        - Creating Bookmark with non-existent resource_id raises IntegrityError
        - Database enforces referential integrity
        - Error provides clear indication of constraint violation
        """
        # Import models dynamically to avoid import issues
        try:
            from apps.knowledge_service.knowledge_service.models.bookmark import \
                Bookmark
        except ImportError:
            pytest.skip("Knowledge service models not available")

        # Try to create bookmark with non-existent resource_id
        bookmark = Bookmark(
            resource_id=99999,  # Non-existent resource
            user_id=1,
            notes="This should fail",
        )
        knowledge_db_session.add(bookmark)

        # This should raise an IntegrityError due to foreign key constraint
        with pytest.raises(IntegrityError) as exc_info:
            knowledge_db_session.commit()

        # Verify the error is related to foreign key constraint
        assert "foreign key constraint" in str(exc_info.value).lower()
        assert "resource_id" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_comment_requires_valid_project(self, project_db_session):
        """
        FAILING TEST: Comments cannot be created with invalid project_id.

        Expected behavior:
        - Creating Comment with non-existent project_id raises IntegrityError
        - Database maintains referential integrity
        - Error message indicates foreign key violation
        """
        # Import models dynamically to avoid import issues
        try:
            from apps.project_service.src.models.comment import Comment
        except ImportError:
            pytest.skip("Project service models not available")

        # Try to create comment with non-existent project_id
        comment = Comment(
            project_id=99999,  # Non-existent project
            content="This should fail",
            created_by=1,
        )
        project_db_session.add(comment)

        # This should raise an IntegrityError due to foreign key constraint
        with pytest.raises(IntegrityError) as exc_info:
            project_db_session.commit()

        # Verify the error is related to foreign key constraint
        assert "foreign key constraint" in str(exc_info.value).lower()
        assert "project_id" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_user_requires_valid_role(self, user_db_session):
        """
        FAILING TEST: Users cannot be created with invalid role_id.

        Expected behavior:
        - Creating User with non-existent role_id raises IntegrityError
        - Database enforces role existence constraint
        - Error message is clear about role constraint violation
        """
        # Import models dynamically to avoid import issues
        try:
            from apps.user_service.src.models.user import User
        except ImportError:
            pytest.skip("User service models not available")

        # Try to create user with non-existent role_id
        user = User(
            email="invalid.role@example.com",
            password_hash="hashed_password",
            first_name="Invalid",
            last_name="Role",
            role_id=99999,  # Non-existent role
        )
        user_db_session.add(user)

        # This should raise an IntegrityError due to foreign key constraint
        with pytest.raises(IntegrityError) as exc_info:
            user_db_session.commit()

        # Verify the error is related to foreign key constraint
        assert "foreign key constraint" in str(exc_info.value).lower()
        assert "role_id" in str(exc_info.value).lower()


class TestConnectionPoolingUnderLoad:
    """Test database connection pooling under load (TDD)."""

    @pytest.mark.asyncio
    async def test_concurrent_database_connections(self, db_test_manager):
        """
        FAILING TEST: Database handles concurrent connections properly.

        Expected behavior:
        - Multiple concurrent database operations succeed
        - Connection pool manages connections efficiently
        - No connection leaks or timeouts under normal load
        - Proper connection cleanup after operations

        This test will fail initially because:
        1. Connection pooling may not be properly configured
        2. Connection limits may be too low
        3. Connection cleanup may not be implemented
        """

        async def create_and_query_resource(session_id: int) -> Dict[str, Any]:
            """Create a resource and query it back."""
            try:
                # Get a database session
                session = db_test_manager.get_knowledge_session()

                # Create a resource
                resource = Resource(
                    title=f"Concurrent Resource {session_id}",
                    url=f"https://example.com/concurrent-{session_id}",
                    content_type="article",
                    description=f"Resource created by session {session_id}",
                    created_by=1,
                )
                session.add(resource)
                session.commit()

                # Query it back
                queried_resource = (
                    session.query(Resource).filter_by(id=resource.id).first()
                )

                # Clean up
                session.delete(queried_resource)
                session.commit()
                session.close()

                return {
                    "session_id": session_id,
                    "success": True,
                    "resource_id": resource.id,
                }
            except Exception as e:
                return {"session_id": session_id, "success": False, "error": str(e)}

        # Run 20 concurrent database operations
        concurrent_operations = 20
        tasks = [create_and_query_resource(i) for i in range(concurrent_operations)]

        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Verify all operations succeeded
        successful_operations = [
            r for r in results if isinstance(r, dict) and r.get("success")
        ]
        failed_operations = [
            r for r in results if isinstance(r, dict) and not r.get("success")
        ]
        exception_operations = [r for r in results if isinstance(r, Exception)]

        # All operations should succeed
        assert (
            len(successful_operations) == concurrent_operations
        ), f"Failed operations: {failed_operations}, Exceptions: {exception_operations}"
        assert (
            len(failed_operations) == 0
        ), f"Some operations failed: {failed_operations}"
        assert (
            len(exception_operations) == 0
        ), f"Some operations raised exceptions: {exception_operations}"

    @pytest.mark.asyncio
    async def test_connection_pool_exhaustion_recovery(self, db_test_manager):
        """
        FAILING TEST: System recovers gracefully from connection pool exhaustion.

        Expected behavior:
        - When connection pool is exhausted, new requests wait appropriately
        - System recovers when connections are released
        - No permanent damage to connection pool
        - Proper error handling for connection timeouts

        This test will fail initially because:
        1. Connection pool limits may not be configured
        2. Timeout handling may not be implemented
        3. Recovery mechanisms may not exist
        """
        # Get connection pool configuration
        pool_size = 5  # Assume small pool for testing

        async def hold_connection_briefly(duration: float) -> Dict[str, Any]:
            """Hold a database connection for specified duration."""
            try:
                session = db_test_manager.get_knowledge_session()

                # Hold the connection
                await asyncio.sleep(duration)

                # Do a simple query to keep connection active
                result = session.execute(text("SELECT 1")).scalar()

                session.close()
                return {"success": True, "result": result}
            except Exception as e:
                return {"success": False, "error": str(e)}

        # Start operations that will exhaust the pool
        long_running_tasks = [hold_connection_briefly(2.0) for _ in range(pool_size)]

        # Start additional operations that should wait
        quick_tasks = [hold_connection_briefly(0.1) for _ in range(3)]

        # Execute long-running tasks first
        long_results = await asyncio.gather(*long_running_tasks, return_exceptions=True)

        # Then execute quick tasks (pool should be available again)
        quick_results = await asyncio.gather(*quick_tasks, return_exceptions=True)

        # Verify recovery
        successful_long = [
            r for r in long_results if isinstance(r, dict) and r.get("success")
        ]
        successful_quick = [
            r for r in quick_results if isinstance(r, dict) and r.get("success")
        ]

        assert (
            len(successful_long) == pool_size
        ), f"Long operations failed: {long_results}"
        assert len(successful_quick) == 3, f"Quick operations failed: {quick_results}"

    @pytest.mark.asyncio
    async def test_database_connection_cleanup(self, db_test_manager):
        """
        FAILING TEST: Database connections are properly cleaned up.

        Expected behavior:
        - Connections are returned to pool after use
        - No connection leaks occur
        - Pool maintains healthy connection count
        - Abandoned connections are detected and cleaned up

        This test will fail initially because:
        1. Connection cleanup may not be automatic
        2. Connection leak detection may not exist
        3. Pool monitoring may not be implemented
        """
        initial_pool_info = db_test_manager.get_connection_pool_info()

        # Perform multiple database operations
        try:
            from apps.knowledge_service.knowledge_service.models.resource import \
                Resource
        except ImportError:
            pytest.skip("Knowledge service models not available")

        for i in range(10):
            session = db_test_manager.get_knowledge_session()

            # Create and delete a resource
            resource = Resource(
                title=f"Cleanup Test Resource {i}",
                url=f"https://example.com/cleanup-{i}",
                content_type="article",
                description="Testing connection cleanup",
                created_by=1,
            )
            session.add(resource)
            session.commit()
            session.delete(resource)
            session.commit()
            session.close()

        # Check pool status after operations
        final_pool_info = db_test_manager.get_connection_pool_info()

        # Pool should be in same state as initial (all connections returned)
        assert (
            final_pool_info["active_connections"]
            == initial_pool_info["active_connections"]
        )
        assert final_pool_info["pool_size"] == initial_pool_info["pool_size"]
        assert (
            final_pool_info["checked_out_connections"]
            <= initial_pool_info["checked_out_connections"]
        )


class TestDatabaseErrorRecovery:
    """Test database error recovery scenarios (TDD)."""

    @pytest.mark.asyncio
    async def test_deadlock_detection_and_retry(self, db_test_manager):
        """
        FAILING TEST: System detects and recovers from database deadlocks.

        Expected behavior:
        - Deadlock situations are detected automatically
        - Operations are retried with exponential backoff
        - Eventually one transaction succeeds
        - System maintains data consistency

        This test will fail initially because:
        1. Deadlock detection may not be implemented
        2. Retry mechanisms may not exist
        3. Backoff strategies may not be configured
        """

        async def competing_transaction(
            resource_id: int, session_id: int
        ) -> Dict[str, Any]:
            """Simulate competing transactions that might deadlock."""
            try:
                session = db_test_manager.get_knowledge_session()

                # Start transaction
                session.begin()

                # Lock resource for update
                resource = (
                    session.query(Resource)
                    .filter_by(id=resource_id)
                    .with_for_update()
                    .first()
                )

                if resource:
                    # Simulate some processing time
                    await asyncio.sleep(0.1)

                    # Update resource
                    resource.description = (
                        f"Updated by session {session_id} at {time.time()}"
                    )
                    session.commit()

                    return {"success": True, "session_id": session_id, "updated": True}
                else:
                    session.rollback()
                    return {
                        "success": False,
                        "session_id": session_id,
                        "error": "Resource not found",
                    }

            except Exception as e:
                session.rollback()
                # Check if it's a deadlock error
                if "deadlock" in str(e).lower():
                    # Retry with backoff
                    await asyncio.sleep(0.1 * session_id)  # Simple backoff
                    return await competing_transaction(resource_id, session_id)
                else:
                    return {"success": False, "session_id": session_id, "error": str(e)}
            finally:
                session.close()

        # Create a resource to compete over
        session = db_test_manager.get_knowledge_session()
        resource = Resource(
            title="Deadlock Test Resource",
            url="https://example.com/deadlock-test",
            content_type="article",
            description="Resource for testing deadlock recovery",
            created_by=1,
        )
        session.add(resource)
        session.commit()
        resource_id = resource.id
        session.close()

        # Start competing transactions
        tasks = [competing_transaction(resource_id, i) for i in range(5)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # At least one transaction should succeed
        successful_results = [
            r for r in results if isinstance(r, dict) and r.get("success")
        ]
        assert len(successful_results) >= 1, f"No transactions succeeded: {results}"

        # Clean up
        session = db_test_manager.get_knowledge_session()
        resource = session.query(Resource).filter_by(id=resource_id).first()
        if resource:
            session.delete(resource)
            session.commit()
        session.close()

    @pytest.mark.asyncio
    async def test_connection_timeout_recovery(self, db_test_manager):
        """
        FAILING TEST: System recovers from database connection timeouts.

        Expected behavior:
        - Connection timeouts are detected and handled gracefully
        - New connections are established automatically
        - Operations are retried after connection recovery
        - System maintains operational state

        This test will fail initially because:
        1. Timeout detection may not be implemented
        2. Connection recovery may not be automatic
        3. Retry logic may not exist
        """

        async def operation_with_timeout_risk() -> Dict[str, Any]:
            """Perform operation that might timeout."""
            try:
                session = db_test_manager.get_knowledge_session()

                # Simulate a long-running query that might timeout
                result = session.execute(
                    text("SELECT pg_sleep(0.1), 1 as test_value")
                ).scalar()

                session.close()
                return {"success": True, "result": result}

            except OperationalError as e:
                if "timeout" in str(e).lower():
                    # Retry with new connection
                    await asyncio.sleep(0.1)
                    return await operation_with_timeout_risk()
                else:
                    return {"success": False, "error": str(e)}
            except Exception as e:
                return {"success": False, "error": str(e)}

        # Run multiple operations that might timeout
        tasks = [operation_with_timeout_risk() for _ in range(5)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All operations should eventually succeed
        successful_results = [
            r for r in results if isinstance(r, dict) and r.get("success")
        ]
        failed_results = [
            r for r in results if isinstance(r, dict) and not r.get("success")
        ]

        assert len(successful_results) == 5, f"Some operations failed: {failed_results}"

    @pytest.mark.asyncio
    async def test_transaction_rollback_scenarios(self, db_test_manager):
        """
        FAILING TEST: Transaction rollbacks work correctly in error scenarios.

        Expected behavior:
        - Failed transactions are rolled back completely
        - No partial data is committed
        - Database remains in consistent state
        - Rollback doesn't affect other transactions

        This test will fail initially because:
        1. Rollback mechanisms may not be properly implemented
        2. Transaction isolation may not be configured
        3. Error handling may not trigger rollbacks
        """

        async def transaction_with_intentional_failure() -> Dict[str, Any]:
            """Perform transaction that will fail and should rollback."""
            session = db_test_manager.get_knowledge_session()

            try:
                session.begin()

                # Create a resource
                resource = Resource(
                    title="Rollback Test Resource",
                    url="https://example.com/rollback-test",
                    content_type="article",
                    description="This should be rolled back",
                    created_by=1,
                )
                session.add(resource)
                session.flush()  # Get ID but don't commit yet
                resource_id = resource.id

                # Create a citation
                citation = Citation(
                    resource_id=resource_id,
                    citation_text="This should also be rolled back",
                    page_number=1,
                    created_by=1,
                )
                session.add(citation)

                # Intentionally cause an error (duplicate resource with same URL)
                duplicate_resource = Resource(
                    title="Duplicate Resource",
                    url="https://example.com/rollback-test",  # Same URL - should cause constraint violation
                    content_type="article",
                    description="This will cause an error",
                    created_by=1,
                )
                session.add(duplicate_resource)

                # This should fail due to unique constraint on URL
                session.commit()

                return {"success": False, "error": "Transaction should have failed"}

            except Exception as e:
                session.rollback()

                # Verify rollback worked - resource and citation should not exist
                resource_count = (
                    session.query(Resource)
                    .filter_by(url="https://example.com/rollback-test")
                    .count()
                )
                citation_count = (
                    session.query(Citation)
                    .filter_by(citation_text="This should also be rolled back")
                    .count()
                )

                return {
                    "success": True,
                    "rollback_worked": resource_count == 0 and citation_count == 0,
                    "error": str(e),
                }
            finally:
                session.close()

        # Run the failing transaction
        result = await transaction_with_intentional_failure()

        # Verify rollback worked correctly
        assert result["success"] is True, f"Transaction handling failed: {result}"
        assert result["rollback_worked"] is True, "Rollback did not work correctly"

        # Verify database is still functional after rollback
        session = db_test_manager.get_knowledge_session()
        test_resource = Resource(
            title="Post-Rollback Test",
            url="https://example.com/post-rollback",
            content_type="article",
            description="Verifying database still works",
            created_by=1,
        )
        session.add(test_resource)
        session.commit()

        # Clean up
        session.delete(test_resource)
        session.commit()
        session.close()


class TestDatabaseConstraintValidation:
    """Test database constraint validation (TDD)."""

    @pytest.mark.asyncio
    async def test_unique_constraint_violations(self, db_test_manager):
        """
        FAILING TEST: Unique constraints are properly enforced.

        Expected behavior:
        - Duplicate values in unique fields raise IntegrityError
        - Error messages clearly indicate constraint violation
        - Database maintains data integrity
        - Constraint violations don't corrupt database state

        This test will fail initially because:
        1. Unique constraints may not be properly defined
        2. Error handling may not be implemented
        3. Constraint validation may be missing
        """
        # Import models dynamically to avoid import issues
        try:
            from apps.user_service.src.models.user import User
        except ImportError:
            pytest.skip("User service models not available")

        # Test unique email constraint in User model
        user_session = db_test_manager.get_user_session()

        # Create first user
        user1 = User(
            email="unique.test@example.com",
            password_hash="hashed_password",
            first_name="First",
            last_name="User",
            role_id=1,  # Assuming role exists
        )
        user_session.add(user1)
        user_session.commit()

        # Try to create second user with same email
        user2 = User(
            email="unique.test@example.com",  # Same email
            password_hash="different_hash",
            first_name="Second",
            last_name="User",
            role_id=1,
        )
        user_session.add(user2)

        # This should raise IntegrityError due to unique constraint
        with pytest.raises(IntegrityError) as exc_info:
            user_session.commit()

        # Verify error is about unique constraint
        assert (
            "unique" in str(exc_info.value).lower()
            or "duplicate" in str(exc_info.value).lower()
        )

        # Clean up
        user_session.rollback()
        user_session.delete(user1)
        user_session.commit()
        user_session.close()

    @pytest.mark.asyncio
    async def test_check_constraint_violations(self, db_test_manager):
        """
        FAILING TEST: Check constraints are properly enforced.

        Expected behavior:
        - Invalid values that violate check constraints raise IntegrityError
        - Constraint validation happens at database level
        - Error messages indicate which constraint was violated

        This test will fail initially because:
        1. Check constraints may not be defined in migrations
        2. Constraint validation may not be implemented
        3. Error handling may not be proper
        """
        # Import models dynamically to avoid import issues
        try:
            from apps.project_service.src.models.project import Project
        except ImportError:
            pytest.skip("Project service models not available")

        # Test project status check constraint
        project_session = db_test_manager.get_project_session()

        # Try to create project with invalid status
        project = Project(
            name="Invalid Status Project",
            description="Testing check constraint",
            status="invalid_status",  # Should violate check constraint
            created_by=1,
        )
        project_session.add(project)

        # This should raise IntegrityError due to check constraint
        with pytest.raises(IntegrityError) as exc_info:
            project_session.commit()

        # Verify error is about check constraint
        error_message = str(exc_info.value).lower()
        assert "check" in error_message or "constraint" in error_message

        project_session.close()

    @pytest.mark.asyncio
    async def test_not_null_constraint_violations(self, db_test_manager):
        """
        FAILING TEST: NOT NULL constraints are properly enforced.

        Expected behavior:
        - Required fields cannot be NULL
        - NOT NULL violations raise IntegrityError
        - Error messages indicate which field is required

        This test will fail initially because:
        1. NOT NULL constraints may not be properly defined
        2. Model validation may not enforce required fields
        3. Database constraints may be missing
        """
        # Import models dynamically to avoid import issues
        try:
            from apps.knowledge_service.knowledge_service.models.resource import \
                Resource
        except ImportError:
            pytest.skip("Knowledge service models not available")

        knowledge_session = db_test_manager.get_knowledge_session()

        # Try to create resource without required title
        resource = Resource(
            title=None,  # Should violate NOT NULL constraint
            url="https://example.com/null-test",
            content_type="article",
            created_by=1,
        )
        knowledge_session.add(resource)

        # This should raise IntegrityError due to NOT NULL constraint
        with pytest.raises(IntegrityError) as exc_info:
            knowledge_session.commit()

        # Verify error is about NOT NULL constraint
        error_message = str(exc_info.value).lower()
        assert "null" in error_message or "not null" in error_message

        knowledge_session.close()
