"""
Database Seeding Utilities for Labor Service

This module provides utilities for seeding the database with initial data
for development and testing purposes.
"""

from typing import Any, Dict, List

from core.database import get_db_session
from models.booking import (Booking, BookingMilestone, BookingStatus,
                            MilestoneStatus)
from models.quote import Quote, QuoteStatus
from models.review import Review, ReviewStatus, ReviewType
from models.service_provider import (ProficiencyLevel, ProviderSkill,
                                     ProviderType, ServiceArea,
                                     ServiceProvider, Skill, SkillCategory,
                                     VerificationStatus)
from models.service_request import (RequestStatus, ServiceRequest,
                                    SkillRequirement, UrgencyLevel)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


class DatabaseSeeder:
    """Database seeding utility class."""

    def __init__(self, session: Session):
        self.session = session

    def seed_skill_categories(self) -> List[SkillCategory]:
        """Seed skill categories."""
        categories_data = [
            {
                "name": "Construction",
                "description": "General construction and building work",
                "sort_order": 1,
            },
            {
                "name": "Electrical",
                "description": "Electrical installation and repair",
                "sort_order": 2,
            },
            {
                "name": "Plumbing",
                "description": "Plumbing installation and repair",
                "sort_order": 3,
            },
            {
                "name": "HVAC",
                "description": "Heating, ventilation, and air conditioning",
                "sort_order": 4,
            },
            {
                "name": "Carpentry",
                "description": "Woodworking and carpentry services",
                "sort_order": 5,
            },
            {
                "name": "Painting",
                "description": "Interior and exterior painting",
                "sort_order": 6,
            },
            {
                "name": "Roofing",
                "description": "Roof installation and repair",
                "sort_order": 7,
            },
            {
                "name": "Landscaping",
                "description": "Outdoor landscaping and maintenance",
                "sort_order": 8,
            },
        ]

        categories = []
        for data in categories_data:
            try:
                category = SkillCategory(**data)
                self.session.add(category)
                self.session.flush()  # Get the ID
                categories.append(category)
            except IntegrityError:
                self.session.rollback()
                # Category already exists, fetch it
                category = (
                    self.session.query(SkillCategory)
                    .filter_by(name=data["name"])
                    .first()
                )
                if category:
                    categories.append(category)

        self.session.commit()
        return categories

    def seed_skills(self, categories: List[SkillCategory]) -> List[Skill]:
        """Seed skills for each category."""
        skills_data = {
            "Construction": [
                {
                    "name": "Framing",
                    "description": "Structural framing work",
                    "requires_certification": False,
                },
                {
                    "name": "Foundation Work",
                    "description": "Foundation and concrete work",
                    "requires_certification": True,
                },
                {
                    "name": "Drywall Installation",
                    "description": "Drywall hanging and finishing",
                    "requires_certification": False,
                },
                {
                    "name": "Flooring Installation",
                    "description": "Various flooring installation",
                    "requires_certification": False,
                },
            ],
            "Electrical": [
                {
                    "name": "Residential Wiring",
                    "description": "Home electrical wiring",
                    "requires_certification": True,
                },
                {
                    "name": "Commercial Electrical",
                    "description": "Commercial electrical systems",
                    "requires_certification": True,
                },
                {
                    "name": "Electrical Repair",
                    "description": "General electrical repairs",
                    "requires_certification": True,
                },
                {
                    "name": "Panel Installation",
                    "description": "Electrical panel installation",
                    "requires_certification": True,
                },
            ],
            "Plumbing": [
                {
                    "name": "Pipe Installation",
                    "description": "Water and sewer pipe installation",
                    "requires_certification": True,
                },
                {
                    "name": "Fixture Installation",
                    "description": "Bathroom and kitchen fixtures",
                    "requires_certification": False,
                },
                {
                    "name": "Drain Cleaning",
                    "description": "Drain and sewer cleaning",
                    "requires_certification": False,
                },
                {
                    "name": "Water Heater Service",
                    "description": "Water heater installation and repair",
                    "requires_certification": True,
                },
            ],
            "HVAC": [
                {
                    "name": "AC Installation",
                    "description": "Air conditioning installation",
                    "requires_certification": True,
                },
                {
                    "name": "Heating System Repair",
                    "description": "Heating system maintenance",
                    "requires_certification": True,
                },
                {
                    "name": "Ductwork",
                    "description": "HVAC ductwork installation",
                    "requires_certification": False,
                },
                {
                    "name": "HVAC Maintenance",
                    "description": "Regular HVAC maintenance",
                    "requires_certification": True,
                },
            ],
            "Carpentry": [
                {
                    "name": "Cabinet Installation",
                    "description": "Kitchen and bathroom cabinets",
                    "requires_certification": False,
                },
                {
                    "name": "Trim Work",
                    "description": "Interior trim and molding",
                    "requires_certification": False,
                },
                {
                    "name": "Custom Furniture",
                    "description": "Custom furniture building",
                    "requires_certification": False,
                },
                {
                    "name": "Deck Building",
                    "description": "Outdoor deck construction",
                    "requires_certification": False,
                },
            ],
            "Painting": [
                {
                    "name": "Interior Painting",
                    "description": "Interior wall and ceiling painting",
                    "requires_certification": False,
                },
                {
                    "name": "Exterior Painting",
                    "description": "Exterior house painting",
                    "requires_certification": False,
                },
                {
                    "name": "Specialty Finishes",
                    "description": "Decorative and specialty finishes",
                    "requires_certification": False,
                },
                {
                    "name": "Commercial Painting",
                    "description": "Large-scale commercial painting",
                    "requires_certification": False,
                },
            ],
            "Roofing": [
                {
                    "name": "Shingle Installation",
                    "description": "Asphalt shingle roofing",
                    "requires_certification": True,
                },
                {
                    "name": "Metal Roofing",
                    "description": "Metal roof installation",
                    "requires_certification": True,
                },
                {
                    "name": "Roof Repair",
                    "description": "General roof repairs",
                    "requires_certification": False,
                },
                {
                    "name": "Gutter Installation",
                    "description": "Gutter and downspout installation",
                    "requires_certification": False,
                },
            ],
            "Landscaping": [
                {
                    "name": "Lawn Maintenance",
                    "description": "Regular lawn care services",
                    "requires_certification": False,
                },
                {
                    "name": "Garden Design",
                    "description": "Landscape design and installation",
                    "requires_certification": False,
                },
                {
                    "name": "Tree Services",
                    "description": "Tree trimming and removal",
                    "requires_certification": True,
                },
                {
                    "name": "Irrigation Systems",
                    "description": "Sprinkler system installation",
                    "requires_certification": False,
                },
            ],
        }

        category_map = {cat.name: cat for cat in categories}
        skills = []

        for category_name, skill_list in skills_data.items():
            category = category_map.get(category_name)
            if not category:
                continue

            for skill_data in skill_list:
                try:
                    skill = Skill(category_id=category.id, **skill_data)
                    self.session.add(skill)
                    self.session.flush()
                    skills.append(skill)
                except IntegrityError:
                    self.session.rollback()
                    # Skill already exists, fetch it
                    skill = (
                        self.session.query(Skill)
                        .filter_by(name=skill_data["name"], category_id=category.id)
                        .first()
                    )
                    if skill:
                        skills.append(skill)

        self.session.commit()
        return skills

    def seed_sample_providers(self, skills: List[Skill]) -> List[ServiceProvider]:
        """Seed sample service providers."""
        providers_data = [
            {
                "user_id": 1001,
                "individual_name": "John Smith",
                "provider_type": ProviderType.INDIVIDUAL,
                "description": "Experienced electrician with 10+ years in residential and commercial work",
                "experience_years": 12,
                "verification_status": VerificationStatus.VERIFIED,
                "rating": 4.8,
                "total_reviews": 45,
                "total_jobs_completed": 120,
                "response_time_avg": 30,
                "is_active": True,
                "is_available": True,
            },
            {
                "user_id": 1002,
                "business_name": "ABC Plumbing Services",
                "individual_name": "Mike Johnson",
                "provider_type": ProviderType.BUSINESS,
                "description": "Full-service plumbing company serving residential and commercial clients",
                "experience_years": 8,
                "verification_status": VerificationStatus.VERIFIED,
                "rating": 4.6,
                "total_reviews": 32,
                "total_jobs_completed": 85,
                "response_time_avg": 45,
                "is_active": True,
                "is_available": True,
            },
            {
                "user_id": 1003,
                "individual_name": "Sarah Wilson",
                "provider_type": ProviderType.INDIVIDUAL,
                "description": "Professional painter specializing in interior and exterior residential work",
                "experience_years": 6,
                "verification_status": VerificationStatus.VERIFIED,
                "rating": 4.9,
                "total_reviews": 28,
                "total_jobs_completed": 65,
                "response_time_avg": 25,
                "is_active": True,
                "is_available": True,
            },
        ]

        providers = []
        for data in providers_data:
            try:
                provider = ServiceProvider(**data)
                self.session.add(provider)
                self.session.flush()
                providers.append(provider)
            except IntegrityError:
                self.session.rollback()
                # Provider already exists, fetch it
                provider = (
                    self.session.query(ServiceProvider)
                    .filter_by(user_id=data["user_id"])
                    .first()
                )
                if provider:
                    providers.append(provider)

        self.session.commit()
        return providers

    def seed_provider_skills(
        self, providers: List[ServiceProvider], skills: List[Skill]
    ):
        """Seed provider-skill relationships."""
        # Map skills by name for easy lookup
        skill_map = {skill.name: skill for skill in skills}

        # Define provider skills
        provider_skills_data = [
            {
                "provider_user_id": 1001,  # John Smith - Electrician
                "skills": [
                    {
                        "name": "Residential Wiring",
                        "proficiency": ProficiencyLevel.EXPERT,
                        "is_primary": True,
                    },
                    {
                        "name": "Commercial Electrical",
                        "proficiency": ProficiencyLevel.ADVANCED,
                        "is_primary": False,
                    },
                    {
                        "name": "Panel Installation",
                        "proficiency": ProficiencyLevel.EXPERT,
                        "is_primary": False,
                    },
                    {
                        "name": "Electrical Repair",
                        "proficiency": ProficiencyLevel.EXPERT,
                        "is_primary": False,
                    },
                ],
            },
            {
                "provider_user_id": 1002,  # Mike Johnson - Plumber
                "skills": [
                    {
                        "name": "Pipe Installation",
                        "proficiency": ProficiencyLevel.EXPERT,
                        "is_primary": True,
                    },
                    {
                        "name": "Fixture Installation",
                        "proficiency": ProficiencyLevel.ADVANCED,
                        "is_primary": False,
                    },
                    {
                        "name": "Water Heater Service",
                        "proficiency": ProficiencyLevel.EXPERT,
                        "is_primary": False,
                    },
                    {
                        "name": "Drain Cleaning",
                        "proficiency": ProficiencyLevel.INTERMEDIATE,
                        "is_primary": False,
                    },
                ],
            },
            {
                "provider_user_id": 1003,  # Sarah Wilson - Painter
                "skills": [
                    {
                        "name": "Interior Painting",
                        "proficiency": ProficiencyLevel.EXPERT,
                        "is_primary": True,
                    },
                    {
                        "name": "Exterior Painting",
                        "proficiency": ProficiencyLevel.ADVANCED,
                        "is_primary": False,
                    },
                    {
                        "name": "Specialty Finishes",
                        "proficiency": ProficiencyLevel.INTERMEDIATE,
                        "is_primary": False,
                    },
                ],
            },
        ]

        provider_map = {p.user_id: p for p in providers}

        for provider_data in provider_skills_data:
            provider = provider_map.get(provider_data["provider_user_id"])
            if not provider:
                continue

            for skill_data in provider_data["skills"]:
                skill = skill_map.get(skill_data["name"])
                if not skill:
                    continue

                try:
                    provider_skill = ProviderSkill(
                        provider_id=provider.id,
                        skill_id=skill.id,
                        proficiency_level=skill_data["proficiency"],
                        is_primary=skill_data["is_primary"],
                        years_experience=provider.experience_years
                        // 2,  # Rough estimate
                        certifications={"certified": skill.requires_certification}
                        if skill.requires_certification
                        else None,
                    )
                    self.session.add(provider_skill)
                except IntegrityError:
                    self.session.rollback()
                    continue

        self.session.commit()

    def seed_all(self) -> Dict[str, Any]:
        """Seed all data and return summary."""
        print("🌱 Starting database seeding...")

        # Seed skill categories
        print("📂 Seeding skill categories...")
        categories = self.seed_skill_categories()
        print(f"✅ Created {len(categories)} skill categories")

        # Seed skills
        print("🔧 Seeding skills...")
        skills = self.seed_skills(categories)
        print(f"✅ Created {len(skills)} skills")

        # Seed sample providers
        print("👷 Seeding sample service providers...")
        providers = self.seed_sample_providers(skills)
        print(f"✅ Created {len(providers)} service providers")

        # Seed provider skills
        print("🤝 Seeding provider-skill relationships...")
        self.seed_provider_skills(providers, skills)
        print("✅ Created provider-skill relationships")

        summary = {
            "categories": len(categories),
            "skills": len(skills),
            "providers": len(providers),
            "status": "completed",
        }

        print("🎉 Database seeding completed successfully!")
        return summary


def seed_database():
    """Main function to seed the database."""
    with get_db_session() as session:
        seeder = DatabaseSeeder(session)
        return seeder.seed_all()


if __name__ == "__main__":
    seed_database()
