"""
Recalculation Service for managing automatic recalculation of dependent calculations.

This service handles dependency tracking and triggers recalculation cascades
when calculation inputs change.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ..core.logging import get_logger
from ..models.calculation_dependency import CalculationDependency
from ..models.calculation_sheet import CalculationSheet
from ..repositories.calculation_dependency_repository import \
    CalculationDependencyRepository
from ..repositories.calculation_sheet_repository import \
    CalculationSheetRepository

logger = get_logger(__name__)


class RecalculationService:
    """
    Service for managing automatic recalculation of dependent calculations.

    Tracks dependencies between calculations and triggers recalculation
    cascades when inputs change.
    """

    def __init__(
        self,
        db_session: AsyncSession,
        calculation_sheet_repo: Optional[CalculationSheetRepository] = None,
        dependency_repo: Optional[CalculationDependencyRepository] = None,
    ):
        """
        Initialize the recalculation service.

        Args:
            db_session: Database session for persistence
            calculation_sheet_repo: Repository for calculation sheets
            dependency_repo: Repository for calculation dependencies
        """
        self.db_session = db_session
        self.calculation_sheet_repo = (
            calculation_sheet_repo or CalculationSheetRepository(db_session)
        )
        self.dependency_repo = dependency_repo or CalculationDependencyRepository(
            db_session
        )

    async def add_dependency(
        self,
        source_calculation_id: int,
        target_calculation_id: int,
        dependency_type: str,
        user_id: str,
        dependent_field: Optional[str] = None,
        source_field: Optional[str] = None,
    ) -> CalculationDependency:
        """
        Add a dependency between two calculations.

        Args:
            source_calculation_id: ID of the calculation that depends
            target_calculation_id: ID of the calculation being depended upon
            dependency_type: Type of dependency (e.g., "load_input", "material_property")
            user_id: User creating the dependency
            dependent_field: Field in source that depends on target
            source_field: Field in target that is depended upon

        Returns:
            Created dependency record

        Raises:
            ValueError: If adding the dependency would create a circular dependency
        """
        # Check for circular dependencies
        has_cycle = await self.dependency_repo.has_circular_dependency(
            source_calculation_id, target_calculation_id
        )

        if has_cycle:
            raise ValueError(
                f"Cannot add dependency: would create circular dependency between "
                f"calculations {source_calculation_id} and {target_calculation_id}"
            )

        # Add the dependency
        dependency = await self.dependency_repo.add_dependency(
            source_calculation_id=source_calculation_id,
            target_calculation_id=target_calculation_id,
            dependency_type=dependency_type,
            user_id=user_id,
            dependent_field=dependent_field,
            source_field=source_field,
        )

        await self.db_session.commit()

        logger.info(
            f"Added dependency: calculation {source_calculation_id} "
            f"depends on {target_calculation_id} ({dependency_type})"
        )

        return dependency

    async def remove_dependency(
        self, source_calculation_id: int, target_calculation_id: int
    ) -> bool:
        """
        Remove a dependency between two calculations.

        Args:
            source_calculation_id: ID of the source calculation
            target_calculation_id: ID of the target calculation

        Returns:
            True if dependency was removed, False if not found
        """
        removed = await self.dependency_repo.remove_dependency(
            source_calculation_id, target_calculation_id
        )

        if removed:
            await self.db_session.commit()
            logger.info(
                f"Removed dependency: calculation {source_calculation_id} "
                f"no longer depends on {target_calculation_id}"
            )

        return removed

    async def get_dependents(self, calculation_id: int) -> List[CalculationSheet]:
        """
        Get all calculations that depend on the given calculation.

        Args:
            calculation_id: ID of the target calculation

        Returns:
            List of calculation sheets that depend on this calculation
        """
        dependencies = await self.dependency_repo.get_dependents(calculation_id)
        dependent_ids = [dep.source_calculation_id for dep in dependencies]

        if not dependent_ids:
            return []

        # Fetch the actual calculation sheets
        dependents = []
        for dep_id in dependent_ids:
            sheet = await self.calculation_sheet_repo.get_by_id(dep_id)
            if sheet:
                dependents.append(sheet)

        return dependents

    async def get_dependencies(self, calculation_id: int) -> List[CalculationSheet]:
        """
        Get all calculations that the given calculation depends on.

        Args:
            calculation_id: ID of the source calculation

        Returns:
            List of calculation sheets that this calculation depends on
        """
        dependencies = await self.dependency_repo.get_dependencies(calculation_id)
        dependency_ids = [dep.target_calculation_id for dep in dependencies]

        if not dependency_ids:
            return []

        # Fetch the actual calculation sheets
        deps = []
        for dep_id in dependency_ids:
            sheet = await self.calculation_sheet_repo.get_by_id(dep_id)
            if sheet:
                deps.append(sheet)

        return deps

    async def trigger_recalculation_cascade(
        self,
        calculation_id: int,
        user_id: str,
        recalculation_callback=None,
    ) -> List[int]:
        """
        Trigger recalculation of all dependent calculations.

        Args:
            calculation_id: ID of the calculation that changed
            user_id: User triggering the recalculation
            recalculation_callback: Optional async callback function to perform
                                   the actual recalculation. Should accept
                                   (calculation_sheet, user_id) and return
                                   updated calculation sheet.

        Returns:
            List of calculation IDs that were recalculated

        Note:
            If no callback is provided, this method only marks calculations
            as needing recalculation by updating their status to 'draft'.
        """
        # Get all calculations in the dependency chain
        dependent_ids = await self.dependency_repo.get_dependency_chain(calculation_id)

        if not dependent_ids:
            logger.info(
                f"No dependent calculations found for calculation {calculation_id}"
            )
            return []

        logger.info(
            f"Triggering recalculation cascade for {len(dependent_ids)} "
            f"dependent calculations"
        )

        recalculated = []

        for dep_id in dependent_ids:
            sheet = await self.calculation_sheet_repo.get_by_id(dep_id)
            if not sheet:
                logger.warning(f"Calculation sheet {dep_id} not found, skipping")
                continue

            if recalculation_callback:
                # Perform actual recalculation using the callback
                try:
                    updated_sheet = await recalculation_callback(sheet, user_id)
                    if updated_sheet:
                        recalculated.append(dep_id)
                        logger.info(f"Recalculated calculation {dep_id}")
                except Exception as e:
                    logger.error(
                        f"Error recalculating calculation {dep_id}: {str(e)}",
                        exc_info=True,
                    )
            else:
                # Mark as needing recalculation
                sheet.status = "draft"
                sheet.updated_by = user_id
                sheet.updated_at = datetime.utcnow()
                await self.calculation_sheet_repo.update(sheet)
                recalculated.append(dep_id)
                logger.info(f"Marked calculation {dep_id} for recalculation")

        await self.db_session.commit()

        logger.info(
            f"Recalculation cascade complete: {len(recalculated)} calculations updated"
        )

        return recalculated

    async def update_calculation_with_cascade(
        self,
        calculation_id: int,
        updates: Dict[str, Any],
        user_id: str,
        recalculation_callback=None,
    ) -> CalculationSheet:
        """
        Update a calculation and trigger recalculation of dependents.

        Args:
            calculation_id: ID of the calculation to update
            updates: Dictionary of fields to update
            user_id: User performing the update
            recalculation_callback: Optional callback for recalculation

        Returns:
            Updated calculation sheet

        Raises:
            ValueError: If calculation not found
        """
        # Get the calculation sheet
        sheet = await self.calculation_sheet_repo.get_by_id(calculation_id)
        if not sheet:
            raise ValueError(f"Calculation sheet {calculation_id} not found")

        # Update the calculation
        for key, value in updates.items():
            if hasattr(sheet, key):
                setattr(sheet, key, value)

        sheet.updated_by = user_id
        sheet.updated_at = datetime.utcnow()

        updated_sheet = await self.calculation_sheet_repo.update(sheet)
        await self.db_session.commit()

        logger.info(f"Updated calculation {calculation_id}")

        # Trigger recalculation cascade
        await self.trigger_recalculation_cascade(
            calculation_id, user_id, recalculation_callback
        )

        return updated_sheet

    async def get_dependency_graph(
        self, calculation_id: int
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get the full dependency graph for a calculation.

        Args:
            calculation_id: ID of the calculation

        Returns:
            Dictionary with 'dependencies' and 'dependents' lists
        """
        dependencies = await self.dependency_repo.get_dependencies(calculation_id)
        dependents = await self.dependency_repo.get_dependents(calculation_id)

        return {
            "dependencies": [
                {
                    "id": dep.target_calculation_id,
                    "type": dep.dependency_type,
                    "field": dep.source_field,
                }
                for dep in dependencies
            ],
            "dependents": [
                {
                    "id": dep.source_calculation_id,
                    "type": dep.dependency_type,
                    "field": dep.dependent_field,
                }
                for dep in dependents
            ],
        }
