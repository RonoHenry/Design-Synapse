"""
Database Cleanup Utilities for Labor Service

This module provides utilities for cleaning up test data and resetting
the database to a clean state.
"""

from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text

from models.service_provider import ServiceProvider, SkillCategory, Skill, ProviderSkill, ServiceArea
from models.service_request import ServiceRequest, SkillRequirement
from models.quote import Quote
from models.booking import Booking, BookingMilestone
from models.review import Review
from core.database import get_db_session


class DatabaseCleaner:
    """Database cleanup utility class."""
    
    def __init__(self, session: Session):
        self.session = session
    
    def clean_all_data(self, confirm: bool = False) -> Dict[str, Any]:
        """
        Clean all data from the database.
        
        Args:
            confirm: Must be True to actually perform the cleanup
            
        Returns:
            Summary of cleanup operation
        """
        if not confirm:
            return {
                "status": "cancelled",
                "message": "Cleanup cancelled - confirmation required"
            }
        
        print("🧹 Starting database cleanup...")
        
        # Order matters due to foreign key constraints
        tables_to_clean = [
            ("reviews", Review),
            ("booking_milestones", BookingMilestone),
            ("bookings", Booking),
            ("quotes", Quote),
            ("skill_requirements", SkillRequirement),
            ("service_requests", ServiceRequest),
            ("provider_skills", ProviderSkill),
            ("service_areas", ServiceArea),
            ("service_providers", ServiceProvider),
            ("skills", Skill),
            ("skill_categories", SkillCategory),
        ]
        
        deleted_counts = {}
        
        for table_name, model_class in tables_to_clean:
            try:
                count = self.session.query(model_class).count()
                if count > 0:
                    self.session.query(model_class).delete()
                    deleted_counts[table_name] = count
                    print(f"🗑️  Deleted {count} records from {table_name}")
                else:
                    deleted_counts[table_name] = 0
            except Exception as e:
                print(f"❌ Error cleaning {table_name}: {e}")
                self.session.rollback()
                return {
                    "status": "error",
                    "message": f"Failed to clean {table_name}: {e}",
                    "deleted_counts": deleted_counts
                }
        
        # Reset auto-increment sequences (SQLite specific)
        try:
            self.session.execute(text("DELETE FROM sqlite_sequence"))
            print("🔄 Reset auto-increment sequences")
        except Exception as e:
            print(f"⚠️  Could not reset sequences: {e}")
        
        self.session.commit()
        
        total_deleted = sum(deleted_counts.values())
        print(f"✅ Cleanup completed! Deleted {total_deleted} total records")
        
        return {
            "status": "completed",
            "total_deleted": total_deleted,
            "deleted_counts": deleted_counts
        }
    
    def clean_test_data(self) -> Dict[str, Any]:
        """
        Clean only test data (identified by specific patterns).
        This is safer than cleaning all data.
        """
        print("🧪 Cleaning test data...")
        
        deleted_counts = {}
        
        # Clean test service providers (user_id >= 1000)
        test_providers = self.session.query(ServiceProvider).filter(
            ServiceProvider.user_id >= 1000
        ).all()
        
        if test_providers:
            # Clean related data first
            provider_ids = [p.id for p in test_providers]
            
            # Clean reviews
            review_count = self.session.query(Review).filter(
                Review.reviewee_id.in_(provider_ids)
            ).count()
            if review_count > 0:
                self.session.query(Review).filter(
                    Review.reviewee_id.in_(provider_ids)
                ).delete(synchronize_session=False)
                deleted_counts["reviews"] = review_count
            
            # Clean bookings
            booking_count = self.session.query(Booking).filter(
                Booking.provider_id.in_(provider_ids)
            ).count()
            if booking_count > 0:
                # Clean milestones first
                milestone_count = self.session.query(BookingMilestone).join(Booking).filter(
                    Booking.provider_id.in_(provider_ids)
                ).count()
                if milestone_count > 0:
                    self.session.query(BookingMilestone).join(Booking).filter(
                        Booking.provider_id.in_(provider_ids)
                    ).delete(synchronize_session=False)
                    deleted_counts["booking_milestones"] = milestone_count
                
                self.session.query(Booking).filter(
                    Booking.provider_id.in_(provider_ids)
                ).delete(synchronize_session=False)
                deleted_counts["bookings"] = booking_count
            
            # Clean quotes
            quote_count = self.session.query(Quote).filter(
                Quote.provider_id.in_(provider_ids)
            ).count()
            if quote_count > 0:
                self.session.query(Quote).filter(
                    Quote.provider_id.in_(provider_ids)
                ).delete(synchronize_session=False)
                deleted_counts["quotes"] = quote_count
            
            # Clean provider skills
            provider_skill_count = self.session.query(ProviderSkill).filter(
                ProviderSkill.provider_id.in_(provider_ids)
            ).count()
            if provider_skill_count > 0:
                self.session.query(ProviderSkill).filter(
                    ProviderSkill.provider_id.in_(provider_ids)
                ).delete(synchronize_session=False)
                deleted_counts["provider_skills"] = provider_skill_count
            
            # Clean service areas
            service_area_count = self.session.query(ServiceArea).filter(
                ServiceArea.provider_id.in_(provider_ids)
            ).count()
            if service_area_count > 0:
                self.session.query(ServiceArea).filter(
                    ServiceArea.provider_id.in_(provider_ids)
                ).delete(synchronize_session=False)
                deleted_counts["service_areas"] = service_area_count
            
            # Finally clean providers
            self.session.query(ServiceProvider).filter(
                ServiceProvider.user_id >= 1000
            ).delete(synchronize_session=False)
            deleted_counts["service_providers"] = len(test_providers)
        
        # Clean test service requests (seeker_id >= 1000)
        test_requests = self.session.query(ServiceRequest).filter(
            ServiceRequest.seeker_id >= 1000
        ).all()
        
        if test_requests:
            request_ids = [r.id for r in test_requests]
            
            # Clean skill requirements
            skill_req_count = self.session.query(SkillRequirement).filter(
                SkillRequirement.service_request_id.in_(request_ids)
            ).count()
            if skill_req_count > 0:
                self.session.query(SkillRequirement).filter(
                    SkillRequirement.service_request_id.in_(request_ids)
                ).delete(synchronize_session=False)
                deleted_counts["skill_requirements"] = skill_req_count
            
            # Clean service requests
            self.session.query(ServiceRequest).filter(
                ServiceRequest.seeker_id >= 1000
            ).delete(synchronize_session=False)
            deleted_counts["service_requests"] = len(test_requests)
        
        self.session.commit()
        
        total_deleted = sum(deleted_counts.values())
        print(f"✅ Test data cleanup completed! Deleted {total_deleted} total records")
        
        return {
            "status": "completed",
            "total_deleted": total_deleted,
            "deleted_counts": deleted_counts
        }
    
    def vacuum_database(self):
        """Vacuum the database to reclaim space (SQLite specific)."""
        try:
            self.session.execute(text("VACUUM"))
            self.session.commit()
            print("🗜️  Database vacuumed successfully")
        except Exception as e:
            print(f"⚠️  Could not vacuum database: {e}")


def clean_all_data(confirm: bool = False):
    """Clean all data from the database."""
    with get_db_session() as session:
        cleaner = DatabaseCleaner(session)
        return cleaner.clean_all_data(confirm=confirm)


def clean_test_data():
    """Clean only test data from the database."""
    with get_db_session() as session:
        cleaner = DatabaseCleaner(session)
        return cleaner.clean_test_data()


def vacuum_database():
    """Vacuum the database to reclaim space."""
    with get_db_session() as session:
        cleaner = DatabaseCleaner(session)
        cleaner.vacuum_database()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "clean-all":
            confirm = len(sys.argv) > 2 and sys.argv[2] == "--confirm"
            clean_all_data(confirm=confirm)
        elif sys.argv[1] == "clean-test":
            clean_test_data()
        elif sys.argv[1] == "vacuum":
            vacuum_database()
        else:
            print("Usage: python database_cleanup.py [clean-all|clean-test|vacuum] [--confirm]")
    else:
        print("Usage: python database_cleanup.py [clean-all|clean-test|vacuum] [--confirm]")