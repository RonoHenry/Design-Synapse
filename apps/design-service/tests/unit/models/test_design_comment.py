"""Tests for DesignComment model."""

import pytest
from sqlalchemy.exc import IntegrityError

from src.models.design import Design
from src.models.design_comment import DesignComment


class TestDesignCommentModel:
    """Test suite for DesignComment model."""

    def test_create_design_comment_with_required_fields(self, db_session):
        """Test creating a DesignComment with all required fields."""
        # Create a design first
        design = Design(
            project_id=1,
            name="Test Design",
            specification={"building_info": {}},
            building_type="residential",
            created_by=1
        )
        db_session.add(design)
        db_session.commit()

        # Create design comment
        comment = DesignComment(
            design_id=design.id,
            content="This design looks great!",
            created_by=1
        )
        db_session.add(comment)
        db_session.commit()

        # Verify
        assert comment.id is not None
        assert comment.design_id == design.id
        assert comment.content == "This design looks great!"
        assert comment.created_by == 1
        assert comment.created_at is not None
        assert comment.updated_at is not None
        assert comment.is_edited is False

    def test_create_design_comment_with_spatial_positioning(self, db_session):
        """Test creating a DesignComment with optional spatial coordinates."""
        design = Design(
            project_id=1,
            name="Test Design",
            specification={"building_info": {}},
            building_type="residential",
            created_by=1
        )
        db_session.add(design)
        db_session.commit()

        # Create comment with spatial positioning
        comment = DesignComment(
            design_id=design.id,
            content="Issue with this wall",
            created_by=1,
            position_x=10.5,
            position_y=20.3,
            position_z=5.0
        )
        db_session.add(comment)
        db_session.commit()

        assert comment.position_x == 10.5
        assert comment.position_y == 20.3
        assert comment.position_z == 5.0

    def test_create_design_comment_without_spatial_positioning(self, db_session):
        """Test creating a DesignComment without spatial coordinates."""
        design = Design(
            project_id=1,
            name="Test Design",
            specification={"building_info": {}},
            building_type="residential",
            created_by=1
        )
        db_session.add(design)
        db_session.commit()

        comment = DesignComment(
            design_id=design.id,
            content="General comment",
            created_by=1
        )
        db_session.add(comment)
        db_session.commit()

        assert comment.position_x is None
        assert comment.position_y is None
        assert comment.position_z is None

    def test_create_design_comment_with_partial_coordinates(self, db_session):
        """Test creating a DesignComment with only some coordinates."""
        design = Design(
            project_id=1,
            name="Test Design",
            specification={"building_info": {}},
            building_type="residential",
            created_by=1
        )
        db_session.add(design)
        db_session.commit()

        # Only x and y coordinates
        comment = DesignComment(
            design_id=design.id,
            content="2D annotation",
            created_by=1,
            position_x=15.0,
            position_y=25.0
        )
        db_session.add(comment)
        db_session.commit()

        assert comment.position_x == 15.0
        assert comment.position_y == 25.0
        assert comment.position_z is None

    def test_is_edited_flag_default_false(self, db_session):
        """Test that is_edited flag defaults to False."""
        design = Design(
            project_id=1,
            name="Test Design",
            specification={"building_info": {}},
            building_type="residential",
            created_by=1
        )
        db_session.add(design)
        db_session.commit()

        comment = DesignComment(
            design_id=design.id,
            content="Original comment",
            created_by=1
        )
        db_session.add(comment)
        db_session.commit()

        assert comment.is_edited is False

    def test_is_edited_flag_when_comment_updated(self, db_session):
        """Test that is_edited flag is set to True when comment is updated."""
        design = Design(
            project_id=1,
            name="Test Design",
            specification={"building_info": {}},
            building_type="residential",
            created_by=1
        )
        db_session.add(design)
        db_session.commit()

        comment = DesignComment(
            design_id=design.id,
            content="Original comment",
            created_by=1
        )
        db_session.add(comment)
        db_session.commit()

        # Update the comment
        comment.content = "Updated comment"
        comment.is_edited = True
        db_session.commit()

        assert comment.content == "Updated comment"
        assert comment.is_edited is True

    def test_updated_at_changes_on_update(self, db_session):
        """Test that updated_at timestamp changes when comment is updated."""
        design = Design(
            project_id=1,
            name="Test Design",
            specification={"building_info": {}},
            building_type="residential",
            created_by=1
        )
        db_session.add(design)
        db_session.commit()

        comment = DesignComment(
            design_id=design.id,
            content="Original comment",
            created_by=1
        )
        db_session.add(comment)
        db_session.commit()

        original_updated_at = comment.updated_at

        # Update the comment
        import time
        time.sleep(0.01)  # Small delay to ensure timestamp difference
        comment.content = "Updated comment"
        db_session.commit()
        db_session.refresh(comment)

        assert comment.updated_at > original_updated_at

    def test_cascade_delete_with_design(self, db_session):
        """Test that deleting a design cascades to delete its comments."""
        # Create design
        design = Design(
            project_id=1,
            name="Test Design",
            specification={"building_info": {}},
            building_type="residential",
            created_by=1
        )
        db_session.add(design)
        db_session.commit()

        # Create multiple comments
        comment1 = DesignComment(
            design_id=design.id,
            content="First comment",
            created_by=1
        )
        comment2 = DesignComment(
            design_id=design.id,
            content="Second comment",
            created_by=2
        )
        db_session.add_all([comment1, comment2])
        db_session.commit()

        comment1_id = comment1.id
        comment2_id = comment2.id

        # Delete design
        db_session.delete(design)
        db_session.commit()

        # Verify comments are deleted
        assert db_session.get(DesignComment, comment1_id) is None
        assert db_session.get(DesignComment, comment2_id) is None

    def test_design_relationship(self, db_session):
        """Test the relationship between DesignComment and Design."""
        design = Design(
            project_id=1,
            name="Test Design",
            specification={"building_info": {}},
            building_type="residential",
            created_by=1
        )
        db_session.add(design)
        db_session.commit()

        comment = DesignComment(
            design_id=design.id,
            content="Test comment",
            created_by=1
        )
        db_session.add(comment)
        db_session.commit()

        # Test relationship from comment to design
        assert comment.design is not None
        assert comment.design.id == design.id
        assert comment.design.name == "Test Design"

        # Test relationship from design to comments
        assert len(design.comments) == 1
        assert design.comments[0].id == comment.id
        assert design.comments[0].content == "Test comment"

    def test_multiple_comments_per_design(self, db_session):
        """Test that a design can have multiple comments."""
        design = Design(
            project_id=1,
            name="Test Design",
            specification={"building_info": {}},
            building_type="residential",
            created_by=1
        )
        db_session.add(design)
        db_session.commit()

        # Create multiple comments
        comments = [
            DesignComment(
                design_id=design.id,
                content=f"Comment {i}",
                created_by=1
            )
            for i in range(5)
        ]
        db_session.add_all(comments)
        db_session.commit()

        # Verify all comments are associated with the design
        assert len(design.comments) == 5
        assert all(c.design_id == design.id for c in design.comments)

    def test_comments_by_different_users(self, db_session):
        """Test that different users can comment on the same design."""
        design = Design(
            project_id=1,
            name="Test Design",
            specification={"building_info": {}},
            building_type="residential",
            created_by=1
        )
        db_session.add(design)
        db_session.commit()

        comment1 = DesignComment(
            design_id=design.id,
            content="Comment by user 1",
            created_by=1
        )
        comment2 = DesignComment(
            design_id=design.id,
            content="Comment by user 2",
            created_by=2
        )
        comment3 = DesignComment(
            design_id=design.id,
            content="Comment by user 3",
            created_by=3
        )
        db_session.add_all([comment1, comment2, comment3])
        db_session.commit()

        assert comment1.created_by == 1
        assert comment2.created_by == 2
        assert comment3.created_by == 3

    def test_missing_required_field_design_id(self, db_session):
        """Test that missing design_id raises IntegrityError."""
        with pytest.raises(IntegrityError):
            comment = DesignComment(
                content="Comment without design",
                created_by=1
            )
            db_session.add(comment)
            db_session.commit()

        db_session.rollback()

    def test_missing_required_field_content(self, db_session):
        """Test that missing content raises IntegrityError."""
        design = Design(
            project_id=1,
            name="Test Design",
            specification={"building_info": {}},
            building_type="residential",
            created_by=1
        )
        db_session.add(design)
        db_session.commit()

        with pytest.raises(IntegrityError):
            comment = DesignComment(
                design_id=design.id,
                created_by=1
            )
            db_session.add(comment)
            db_session.commit()

        db_session.rollback()

    def test_missing_required_field_created_by(self, db_session):
        """Test that missing created_by raises IntegrityError."""
        design = Design(
            project_id=1,
            name="Test Design",
            specification={"building_info": {}},
            building_type="residential",
            created_by=1
        )
        db_session.add(design)
        db_session.commit()

        with pytest.raises(IntegrityError):
            comment = DesignComment(
                design_id=design.id,
                content="Comment without creator"
            )
            db_session.add(comment)
            db_session.commit()

        db_session.rollback()

    def test_empty_content_validation(self, db_session):
        """Test that empty content raises ValueError."""
        design = Design(
            project_id=1,
            name="Test Design",
            specification={"building_info": {}},
            building_type="residential",
            created_by=1
        )
        db_session.add(design)
        db_session.commit()

        with pytest.raises(ValueError, match="Comment content cannot be empty"):
            DesignComment(
                design_id=design.id,
                content="",
                created_by=1
            )

    def test_whitespace_only_content_validation(self, db_session):
        """Test that whitespace-only content raises ValueError."""
        design = Design(
            project_id=1,
            name="Test Design",
            specification={"building_info": {}},
            building_type="residential",
            created_by=1
        )
        db_session.add(design)
        db_session.commit()

        with pytest.raises(ValueError, match="Comment content cannot be empty"):
            DesignComment(
                design_id=design.id,
                content="   ",
                created_by=1
            )

    def test_repr_method(self, db_session):
        """Test the __repr__ method of DesignComment."""
        design = Design(
            project_id=1,
            name="Test Design",
            specification={"building_info": {}},
            building_type="residential",
            created_by=1
        )
        db_session.add(design)
        db_session.commit()

        comment = DesignComment(
            design_id=design.id,
            content="Test comment",
            created_by=1
        )
        db_session.add(comment)
        db_session.commit()

        repr_str = repr(comment)
        assert "DesignComment" in repr_str
        assert f"id={comment.id}" in repr_str
        assert f"design_id={design.id}" in repr_str
        assert f"created_by=1" in repr_str
