"""Unit tests for DesignRepository."""
import pytest
from datetime import datetime
from sqlalchemy.orm import Session

from src.models.design import Design
from src.repositories.design_repository import DesignRepository
from tests.factories import DesignFactory


class TestDesignRepository:
    """Test suite for DesignRepository."""

    @pytest.fixture
    def repository(self, db_session: Session):
        """Create a DesignRepository instance."""
        return DesignRepository(db_session)

    def test_create_design(self, repository: DesignRepository, db_session: Session):
        """Test creating a design."""
        design_data = {
            "project_id": 1,
            "name": "Test Design",
            "description": "A test design",
            "specification": {"building_info": {"type": "residential"}},
            "building_type": "residential",
            "created_by": 1,
        }

        design = repository.create_design(**design_data)

        assert design.id is not None
        assert design.name == "Test Design"
        assert design.project_id == 1
        assert design.building_type == "residential"
        assert design.version == 1
        assert design.status == "draft"
        assert design.is_archived is False
        assert design.created_at is not None

        # Verify it's in the database
        db_design = db_session.query(Design).filter_by(id=design.id).first()
        assert db_design is not None
        assert db_design.name == "Test Design"

    def test_create_design_with_optional_fields(
        self, repository: DesignRepository, db_session: Session
    ):
        """Test creating a design with optional fields."""
        design_data = {
            "project_id": 1,
            "name": "Complete Design",
            "description": "A complete design",
            "specification": {"building_info": {"type": "commercial"}},
            "building_type": "commercial",
            "total_area": 500.5,
            "num_floors": 3,
            "materials": ["concrete", "steel"],
            "confidence_score": 85.5,
            "ai_model_version": "gpt-4",
            "created_by": 1,
        }

        design = repository.create_design(**design_data)

        assert design.total_area == 500.5
        assert design.num_floors == 3
        assert design.materials == ["concrete", "steel"]
        assert design.confidence_score == 85.5
        assert design.ai_model_version == "gpt-4"

    def test_get_design_by_id_found(self, repository: DesignRepository, db_session: Session):
        """Test getting a design by ID when it exists."""
        design = DesignFactory.create(db_session=db_session)
        db_session.commit()

        retrieved_design = repository.get_design_by_id(design.id)

        assert retrieved_design is not None
        assert retrieved_design.id == design.id
        assert retrieved_design.name == design.name

    def test_get_design_by_id_not_found(self, repository: DesignRepository):
        """Test getting a design by ID when it doesn't exist."""
        retrieved_design = repository.get_design_by_id(99999)

        assert retrieved_design is None

    def test_get_design_by_id_excludes_archived(
        self, repository: DesignRepository, db_session: Session
    ):
        """Test that archived designs are not returned by default."""
        design = DesignFactory.create(db_session=db_session, is_archived=True)
        db_session.commit()

        retrieved_design = repository.get_design_by_id(design.id)

        assert retrieved_design is None

    def test_get_design_by_id_includes_archived_when_specified(
        self, repository: DesignRepository, db_session: Session
    ):
        """Test that archived designs can be retrieved when explicitly requested."""
        design = DesignFactory.create(db_session=db_session, is_archived=True)
        db_session.commit()

        retrieved_design = repository.get_design_by_id(design.id, include_archived=True)

        assert retrieved_design is not None
        assert retrieved_design.id == design.id
        assert retrieved_design.is_archived is True

    def test_update_design(self, repository: DesignRepository, db_session: Session):
        """Test updating a design."""
        design = DesignFactory.create(db_session=db_session, name="Original Name")
        db_session.commit()

        updates = {
            "name": "Updated Name",
            "description": "Updated description",
            "status": "validated",
        }

        updated_design = repository.update_design(design.id, **updates)

        assert updated_design is not None
        assert updated_design.name == "Updated Name"
        assert updated_design.description == "Updated description"
        assert updated_design.status == "validated"

        # Verify in database
        db_design = db_session.query(Design).filter_by(id=design.id).first()
        assert db_design.name == "Updated Name"

    def test_update_design_not_found(self, repository: DesignRepository):
        """Test updating a non-existent design."""
        updated_design = repository.update_design(99999, name="New Name")

        assert updated_design is None

    def test_update_design_specification(
        self, repository: DesignRepository, db_session: Session
    ):
        """Test updating design specification."""
        design = DesignFactory.create(
            db_session=db_session,
            specification={"building_info": {"type": "residential"}},
        )
        db_session.commit()

        new_spec = {
            "building_info": {"type": "commercial", "floors": 5},
            "materials": ["steel", "glass"],
        }

        updated_design = repository.update_design(design.id, specification=new_spec)

        assert updated_design.specification == new_spec

    def test_delete_design_soft_delete(
        self, repository: DesignRepository, db_session: Session
    ):
        """Test soft deleting a design (sets is_archived=True)."""
        design = DesignFactory.create(db_session=db_session)
        db_session.commit()

        result = repository.delete_design(design.id)

        assert result is True

        # Verify it's marked as archived
        db_design = db_session.query(Design).filter_by(id=design.id).first()
        assert db_design is not None
        assert db_design.is_archived is True

    def test_delete_design_not_found(self, repository: DesignRepository):
        """Test deleting a non-existent design."""
        result = repository.delete_design(99999)

        assert result is False

    def test_list_designs_no_filters(
        self, repository: DesignRepository, db_session: Session
    ):
        """Test listing all designs without filters."""
        DesignFactory.create_batch(3, db_session=db_session)
        db_session.commit()

        designs = repository.list_designs()

        assert len(designs) == 3

    def test_list_designs_filter_by_project_id(
        self, repository: DesignRepository, db_session: Session
    ):
        """Test filtering designs by project_id."""
        DesignFactory.create_batch(2, db_session=db_session, project_id=1)
        DesignFactory.create_batch(3, db_session=db_session, project_id=2)
        db_session.commit()

        designs = repository.list_designs(project_id=1)

        assert len(designs) == 2
        assert all(d.project_id == 1 for d in designs)

    def test_list_designs_filter_by_building_type(
        self, repository: DesignRepository, db_session: Session
    ):
        """Test filtering designs by building_type."""
        DesignFactory.create_batch(2, db_session=db_session, building_type="residential")
        DesignFactory.create_batch(3, db_session=db_session, building_type="commercial")
        db_session.commit()

        designs = repository.list_designs(building_type="residential")

        assert len(designs) == 2
        assert all(d.building_type == "residential" for d in designs)

    def test_list_designs_filter_by_status(
        self, repository: DesignRepository, db_session: Session
    ):
        """Test filtering designs by status."""
        DesignFactory.create_batch(2, db_session=db_session, status="draft")
        DesignFactory.create_batch(3, db_session=db_session, status="validated")
        db_session.commit()

        designs = repository.list_designs(status="validated")

        assert len(designs) == 3
        assert all(d.status == "validated" for d in designs)

    def test_list_designs_multiple_filters(
        self, repository: DesignRepository, db_session: Session
    ):
        """Test filtering designs with multiple criteria."""
        DesignFactory.create(
            db_session=db_session,
            project_id=1,
            building_type="residential",
            status="draft",
        )
        DesignFactory.create(
            db_session=db_session,
            project_id=1,
            building_type="residential",
            status="validated",
        )
        DesignFactory.create(
            db_session=db_session,
            project_id=2,
            building_type="residential",
            status="draft",
        )
        db_session.commit()

        designs = repository.list_designs(
            project_id=1, building_type="residential", status="draft"
        )

        assert len(designs) == 1
        assert designs[0].project_id == 1
        assert designs[0].building_type == "residential"
        assert designs[0].status == "draft"

    def test_list_designs_excludes_archived(
        self, repository: DesignRepository, db_session: Session
    ):
        """Test that archived designs are excluded from list by default."""
        DesignFactory.create_batch(2, db_session=db_session, is_archived=False)
        DesignFactory.create_batch(3, db_session=db_session, is_archived=True)
        db_session.commit()

        designs = repository.list_designs()

        assert len(designs) == 2
        assert all(not d.is_archived for d in designs)

    def test_list_designs_pagination(
        self, repository: DesignRepository, db_session: Session
    ):
        """Test pagination of design list."""
        DesignFactory.create_batch(10, db_session=db_session)
        db_session.commit()

        # First page
        page1 = repository.list_designs(limit=5, offset=0)
        assert len(page1) == 5

        # Second page
        page2 = repository.list_designs(limit=5, offset=5)
        assert len(page2) == 5

        # Ensure different results
        page1_ids = {d.id for d in page1}
        page2_ids = {d.id for d in page2}
        assert page1_ids.isdisjoint(page2_ids)

    def test_list_designs_ordered_by_created_at_desc(
        self, repository: DesignRepository, db_session: Session
    ):
        """Test that designs are ordered by created_at descending (newest first)."""
        design1 = DesignFactory.create(db_session=db_session)
        db_session.commit()
        db_session.refresh(design1)

        design2 = DesignFactory.create(db_session=db_session)
        db_session.commit()
        db_session.refresh(design2)

        designs = repository.list_designs()

        assert len(designs) >= 2
        # Newest should be first
        assert designs[0].id == design2.id
        assert designs[1].id == design1.id

    def test_get_design_versions_single_version(
        self, repository: DesignRepository, db_session: Session
    ):
        """Test getting versions when there's only one version."""
        design = DesignFactory.create(db_session=db_session, version=1)
        db_session.commit()

        versions = repository.get_design_versions(design.id)

        assert len(versions) == 1
        assert versions[0].id == design.id
        assert versions[0].version == 1

    def test_get_design_versions_multiple_versions(
        self, repository: DesignRepository, db_session: Session
    ):
        """Test getting all versions of a design."""
        # Create parent design
        parent = DesignFactory.create(db_session=db_session, version=1)
        db_session.commit()

        # Create version 2
        version2 = DesignFactory.create(
            db_session=db_session, version=2, parent_design_id=parent.id
        )
        db_session.commit()

        # Create version 3
        version3 = DesignFactory.create(
            db_session=db_session, version=3, parent_design_id=version2.id
        )
        db_session.commit()

        # Get all versions starting from version 3
        versions = repository.get_design_versions(version3.id)

        assert len(versions) == 3
        # Should be ordered by version descending (newest first)
        assert versions[0].version == 3
        assert versions[1].version == 2
        assert versions[2].version == 1

    def test_get_design_versions_from_middle_version(
        self, repository: DesignRepository, db_session: Session
    ):
        """Test getting versions when starting from a middle version."""
        # Create version chain: v1 -> v2 -> v3
        v1 = DesignFactory.create(db_session=db_session, version=1)
        db_session.commit()

        v2 = DesignFactory.create(
            db_session=db_session, version=2, parent_design_id=v1.id
        )
        db_session.commit()

        v3 = DesignFactory.create(
            db_session=db_session, version=3, parent_design_id=v2.id
        )
        db_session.commit()

        # Get versions starting from v2
        versions = repository.get_design_versions(v2.id)

        assert len(versions) == 2
        assert versions[0].version == 2
        assert versions[1].version == 1

    def test_get_design_versions_not_found(self, repository: DesignRepository):
        """Test getting versions for non-existent design."""
        versions = repository.get_design_versions(99999)

        assert versions == []

    def test_get_design_versions_excludes_archived(
        self, repository: DesignRepository, db_session: Session
    ):
        """Test that archived versions are excluded."""
        v1 = DesignFactory.create(db_session=db_session, version=1, is_archived=True)
        db_session.commit()

        v2 = DesignFactory.create(
            db_session=db_session, version=2, parent_design_id=v1.id, is_archived=False
        )
        db_session.commit()

        versions = repository.get_design_versions(v2.id)

        # Should only get v2, not the archived v1
        assert len(versions) == 1
        assert versions[0].version == 2
