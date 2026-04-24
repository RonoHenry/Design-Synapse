"""Repository for CalculationDependency model."""

from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.calculation_dependency import CalculationDependency
from .base_repository import BaseRepository


class CalculationDependencyRepository(BaseRepository[CalculationDependency]):
    """Repository for managing calculation dependencies.

    Provides operations for tracking and querying dependencies between
    calculation sheets to enable automatic recalculation cascades.
    """

    def __init__(self, db_session: AsyncSession):
        """Initialize repository with session.

        Args:
            db_session: Async database session
        """
        super().__init__(CalculationDependency, db_session)

    async def get_dependents(self, calculation_id: int) -> List[CalculationDependency]:
        """Get all calculations that depend on the given calculation.

        Args:
            calculation_id: ID of the target calculation

        Returns:
            List of dependencies where this calculation is the target
        """
        query = select(CalculationDependency).where(
            CalculationDependency.target_calculation_id == calculation_id
        )

        result = await self.db_session.execute(query)
        return list(result.scalars().all())

    async def get_dependencies(
        self, calculation_id: int
    ) -> List[CalculationDependency]:
        """Get all calculations that the given calculation depends on.

        Args:
            calculation_id: ID of the source calculation

        Returns:
            List of dependencies where this calculation is the source
        """
        query = select(CalculationDependency).where(
            CalculationDependency.source_calculation_id == calculation_id
        )

        result = await self.db_session.execute(query)
        return list(result.scalars().all())

    async def add_dependency(
        self,
        source_calculation_id: int,
        target_calculation_id: int,
        dependency_type: str,
        user_id: str,
        dependent_field: str = None,
        source_field: str = None,
    ) -> CalculationDependency:
        """Add a dependency between two calculations.

        Args:
            source_calculation_id: ID of the calculation that depends
            target_calculation_id: ID of the calculation being depended upon
            dependency_type: Type of dependency
            user_id: User creating the dependency
            dependent_field: Field in source that depends on target
            source_field: Field in target that is depended upon

        Returns:
            Created dependency record
        """
        dependency = CalculationDependency(
            source_calculation_id=source_calculation_id,
            target_calculation_id=target_calculation_id,
            dependency_type=dependency_type,
            dependent_field=dependent_field,
            source_field=source_field,
            created_by=user_id,
        )

        return await self.create(dependency)

    async def remove_dependency(
        self, source_calculation_id: int, target_calculation_id: int
    ) -> bool:
        """Remove a dependency between two calculations.

        Args:
            source_calculation_id: ID of the source calculation
            target_calculation_id: ID of the target calculation

        Returns:
            True if dependency was removed, False if not found
        """
        query = select(CalculationDependency).where(
            CalculationDependency.source_calculation_id == source_calculation_id,
            CalculationDependency.target_calculation_id == target_calculation_id,
        )

        result = await self.db_session.execute(query)
        dependency = result.scalar_one_or_none()

        if dependency:
            await self.delete(dependency.id)
            return True

        return False

    async def get_dependency_chain(
        self, calculation_id: int, visited: set = None
    ) -> List[int]:
        """Get all calculations in the dependency chain (recursive).

        Args:
            calculation_id: Starting calculation ID
            visited: Set of already visited calculation IDs (for cycle detection)

        Returns:
            List of calculation IDs that depend on this calculation (directly or indirectly)
        """
        if visited is None:
            visited = set()

        if calculation_id in visited:
            # Cycle detected, return empty to avoid infinite recursion
            return []

        visited.add(calculation_id)

        # Get direct dependents
        dependents = await self.get_dependents(calculation_id)
        dependent_ids = [dep.source_calculation_id for dep in dependents]

        # Recursively get their dependents
        all_dependents = list(dependent_ids)
        for dep_id in dependent_ids:
            chain = await self.get_dependency_chain(dep_id, visited)
            all_dependents.extend(chain)

        # Remove duplicates while preserving order
        seen = set()
        unique_dependents = []
        for dep_id in all_dependents:
            if dep_id not in seen:
                seen.add(dep_id)
                unique_dependents.append(dep_id)

        return unique_dependents

    async def has_circular_dependency(
        self, source_calculation_id: int, target_calculation_id: int
    ) -> bool:
        """Check if adding a dependency would create a circular dependency.

        Args:
            source_calculation_id: ID of the source calculation
            target_calculation_id: ID of the target calculation

        Returns:
            True if adding this dependency would create a cycle
        """
        # Check if target depends on source (directly or indirectly)
        chain = await self.get_dependency_chain(source_calculation_id)
        return target_calculation_id in chain
