"""Skill repository for managing skills and skill categories."""
from typing import List, Optional

from sqlalchemy.orm import Session
from src.models.service_provider import Skill, SkillCategory
from src.repositories.base_repository import BaseRepository


class SkillRepository(BaseRepository[Skill]):
    """Repository for managing skills."""

    def __init__(self, db: Session):
        super().__init__(Skill, db)

    async def get_by_name(self, name: str) -> Optional[Skill]:
        """Get skill by name."""
        return self.db_session.query(Skill).filter(Skill.name == name).first()

    async def get_by_category(self, category_id: int) -> List[Skill]:
        """Get skills by category."""
        return (
            self.db_session.query(Skill).filter(Skill.category_id == category_id).all()
        )

    async def search_skills(self, query: str) -> List[Skill]:
        """Search skills by name."""
        return self.db_session.query(Skill).filter(Skill.name.ilike(f"%{query}%")).all()


class SkillCategoryRepository(BaseRepository[SkillCategory]):
    """Repository for managing skill categories."""

    def __init__(self, db: Session):
        super().__init__(SkillCategory, db)

    async def get_by_name(self, name: str) -> Optional[SkillCategory]:
        """Get category by name."""
        return (
            self.db_session.query(SkillCategory)
            .filter(SkillCategory.name == name)
            .first()
        )

    async def get_all_ordered(self) -> List[SkillCategory]:
        """Get all categories ordered by sort_order."""
        return (
            self.db_session.query(SkillCategory)
            .order_by(SkillCategory.sort_order)
            .all()
        )
