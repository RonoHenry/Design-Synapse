"""
Integration tests for design comment endpoints.

Tests cover:
- Creating comments on designs
- Listing comments for a design
- Updating own comments
- Deleting own comments
- Authorization checks (owner-only operations)

Requirements:
- 7.1: Add comments to designs with timestamp and author
- 7.2: Optional coordinate-based positioning for spatial annotations
- 7.3: Display comments in chronological order
- 7.4: Edit own comments with edited flag
- 7.5: Delete own comments
- 7.6: Project membership required for commenting
"""

import pytest
from fastapi import status
from datetime import datetime, timezone

from src.models.design import Design
from src.models.design_comment import DesignComment
from tests.factories import DesignFactory, DesignCommentFactory


class TestCreateComment:
    """Tests for POST /api/v1/designs/{id}/comments endpoint."""

    def test_create_comment_success(self, client, db_session, mock_auth_user, mock_project_access):
        """Test creating a comment on a design."""
        # Arrange
        DesignFactory._meta.sqlalchemy_session = db_session
        design = DesignFactory.create(project_id=1, created_by=1)
        db_session.commit()

        comment_data = {
            "content": "This is a great design!",
        }

        # Act
        response = client.post(
            f"/api/v1/designs/{design.id}/comments",
            json=comment_data,
            headers={"Authorization": "Bearer fake-token"}
        )

        # Assert
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["content"] == comment_data["content"]
        assert data["design_id"] == design.id
        assert data["created_by"] == 1
        assert data["is_edited"] is False
        assert data["position_x"] is None
        assert data["position_y"] is None
        assert data["position_z"] is None
        assert "created_at" in data
        assert "updated_at" in data

        # Verify in database
        comment = db_session.query(DesignComment).filter_by(id=data["id"]).first()
        assert comment is not None
        assert comment.content == comment_data["content"]

    def test_create_comment_with_spatial_position(self, client, db_session, mock_auth_user, mock_project_access):
        """Test creating a comment with spatial positioning (Requirement 7.2)."""
        # Arrange
        DesignFactory._meta.sqlalchemy_session = db_session
        design = DesignFactory.create(project_id=1, created_by=1)
        db_session.commit()

        comment_data = {
            "content": "Issue with this wall section",
            "position_x": 10.5,
            "position_y": 20.3,
            "position_z": 5.0,
        }

        # Act
        response = client.post(
            f"/api/v1/designs/{design.id}/comments",
            json=comment_data,
            headers={"Authorization": "Bearer fake-token"}
        )

        # Assert
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["content"] == comment_data["content"]
        assert data["position_x"] == 10.5
        assert data["position_y"] == 20.3
        assert data["position_z"] == 5.0

    def test_create_comment_design_not_found(self, client, mock_auth_user, mock_project_access):
        """Test creating a comment on non-existent design returns 404."""
        # Arrange
        comment_data = {
            "content": "This design doesn't exist",
        }

        # Act
        response = client.post(
            "/api/v1/designs/99999/comments",
            json=comment_data,
            headers={"Authorization": "Bearer fake-token"}
        )

        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_create_comment_empty_content(self, client, db_session, mock_auth_user, mock_project_access):
        """Test creating a comment with empty content returns 422."""
        # Arrange
        DesignFactory._meta.sqlalchemy_session = db_session
        design = DesignFactory.create(project_id=1, created_by=1)
        db_session.commit()

        comment_data = {
            "content": "",
        }

        # Act
        response = client.post(
            f"/api/v1/designs/{design.id}/comments",
            json=comment_data,
            headers={"Authorization": "Bearer fake-token"}
        )

        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_comment_without_auth(self, client_no_auth, db_session):
        """Test creating a comment without authentication returns 401."""
        # Arrange
        DesignFactory._meta.sqlalchemy_session = db_session
        design = DesignFactory.create(project_id=1, created_by=1)
        db_session.commit()

        comment_data = {
            "content": "Unauthorized comment",
        }

        # Act
        response = client_no_auth.post(
            f"/api/v1/designs/{design.id}/comments",
            json=comment_data
        )

        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_comment_without_project_access(self, client_no_project_access, db_session):
        """Test creating a comment without project access returns 403 (Requirement 7.6)."""
        # Arrange
        DesignFactory._meta.sqlalchemy_session = db_session
        design = DesignFactory.create(project_id=1, created_by=1)
        db_session.commit()

        comment_data = {
            "content": "I shouldn't be able to comment",
        }

        # Act
        response = client_no_project_access.post(
            f"/api/v1/designs/{design.id}/comments",
            json=comment_data,
            headers={"Authorization": "Bearer fake-token"}
        )

        # Assert
        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestListComments:
    """Tests for GET /api/v1/designs/{id}/comments endpoint."""

    def test_list_comments_success(self, client, db_session, mock_auth_user, mock_project_access):
        """Test listing comments for a design (Requirement 7.3)."""
        # Arrange
        DesignFactory._meta.sqlalchemy_session = db_session
        DesignCommentFactory._meta.sqlalchemy_session = db_session
        
        design = DesignFactory.create(project_id=1, created_by=1)
        db_session.commit()

        # Create comments with different timestamps
        comment1 = DesignCommentFactory.create(
            design=design,
            content="First comment",
            created_by=1
        )
        comment2 = DesignCommentFactory.create(
            design=design,
            content="Second comment",
            created_by=2
        )
        comment3 = DesignCommentFactory.create(
            design=design,
            content="Third comment",
            created_by=1
        )
        db_session.commit()

        # Act
        response = client.get(
            f"/api/v1/designs/{design.id}/comments",
            headers={"Authorization": "Bearer fake-token"}
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 3
        
        # Verify chronological order (oldest first)
        assert data[0]["id"] == comment1.id
        assert data[1]["id"] == comment2.id
        assert data[2]["id"] == comment3.id

    def test_list_comments_empty(self, client, db_session, mock_auth_user, mock_project_access):
        """Test listing comments for a design with no comments."""
        # Arrange
        DesignFactory._meta.sqlalchemy_session = db_session
        design = DesignFactory.create(project_id=1, created_by=1)
        db_session.commit()

        # Act
        response = client.get(
            f"/api/v1/designs/{design.id}/comments",
            headers={"Authorization": "Bearer fake-token"}
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 0

    def test_list_comments_design_not_found(self, client, mock_auth_user, mock_project_access):
        """Test listing comments for non-existent design returns 404."""
        # Act
        response = client.get(
            "/api/v1/designs/99999/comments",
            headers={"Authorization": "Bearer fake-token"}
        )

        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_list_comments_without_auth(self, client_no_auth, db_session):
        """Test listing comments without authentication returns 401."""
        # Arrange
        DesignFactory._meta.sqlalchemy_session = db_session
        design = DesignFactory.create(project_id=1, created_by=1)
        db_session.commit()

        # Act
        response = client_no_auth.get(f"/api/v1/designs/{design.id}/comments")

        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestUpdateComment:
    """Tests for PUT /api/v1/comments/{id} endpoint."""

    def test_update_own_comment_success(self, client, db_session, mock_auth_user, mock_project_access):
        """Test updating own comment (Requirement 7.4)."""
        # Arrange
        DesignFactory._meta.sqlalchemy_session = db_session
        DesignCommentFactory._meta.sqlalchemy_session = db_session
        
        design = DesignFactory.create(project_id=1, created_by=1)
        comment = DesignCommentFactory.create(
            design=design,
            content="Original content",
            created_by=1  # Same as mock_auth_user
        )
        db_session.commit()

        update_data = {
            "content": "Updated content",
        }

        # Act
        response = client.put(
            f"/api/v1/comments/{comment.id}",
            json=update_data,
            headers={"Authorization": "Bearer fake-token"}
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["content"] == "Updated content"
        assert data["is_edited"] is True
        assert data["updated_at"] != data["created_at"]

        # Verify in database
        db_session.refresh(comment)
        assert comment.content == "Updated content"
        assert comment.is_edited is True

    def test_update_comment_with_position(self, client, db_session, mock_auth_user, mock_project_access):
        """Test updating comment with spatial position."""
        # Arrange
        DesignFactory._meta.sqlalchemy_session = db_session
        DesignCommentFactory._meta.sqlalchemy_session = db_session
        
        design = DesignFactory.create(project_id=1, created_by=1)
        comment = DesignCommentFactory.create(
            design=design,
            content="Original content",
            created_by=1,
            position_x=10.0,
            position_y=20.0,
            position_z=5.0
        )
        db_session.commit()

        update_data = {
            "content": "Updated content",
            "position_x": 15.0,
            "position_y": 25.0,
            "position_z": 7.5,
        }

        # Act
        response = client.put(
            f"/api/v1/comments/{comment.id}",
            json=update_data,
            headers={"Authorization": "Bearer fake-token"}
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["position_x"] == 15.0
        assert data["position_y"] == 25.0
        assert data["position_z"] == 7.5

    def test_update_other_user_comment_forbidden(self, client, db_session, mock_auth_user, mock_project_access):
        """Test updating another user's comment returns 403."""
        # Arrange
        DesignFactory._meta.sqlalchemy_session = db_session
        DesignCommentFactory._meta.sqlalchemy_session = db_session
        
        design = DesignFactory.create(project_id=1, created_by=1)
        comment = DesignCommentFactory.create(
            design=design,
            content="Original content",
            created_by=999  # Different user
        )
        db_session.commit()

        update_data = {
            "content": "Trying to update someone else's comment",
        }

        # Act
        response = client.put(
            f"/api/v1/comments/{comment.id}",
            json=update_data,
            headers={"Authorization": "Bearer fake-token"}
        )

        # Assert
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_update_comment_not_found(self, client, mock_auth_user, mock_project_access):
        """Test updating non-existent comment returns 404."""
        # Arrange
        update_data = {
            "content": "Updated content",
        }

        # Act
        response = client.put(
            "/api/v1/comments/99999",
            json=update_data,
            headers={"Authorization": "Bearer fake-token"}
        )

        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_comment_empty_content(self, client, db_session, mock_auth_user, mock_project_access):
        """Test updating comment with empty content returns 422."""
        # Arrange
        DesignFactory._meta.sqlalchemy_session = db_session
        DesignCommentFactory._meta.sqlalchemy_session = db_session
        
        design = DesignFactory.create(project_id=1, created_by=1)
        comment = DesignCommentFactory.create(
            design=design,
            content="Original content",
            created_by=1
        )
        db_session.commit()

        update_data = {
            "content": "",
        }

        # Act
        response = client.put(
            f"/api/v1/comments/{comment.id}",
            json=update_data,
            headers={"Authorization": "Bearer fake-token"}
        )

        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_update_comment_without_auth(self, client_no_auth, db_session):
        """Test updating comment without authentication returns 401."""
        # Arrange
        DesignFactory._meta.sqlalchemy_session = db_session
        DesignCommentFactory._meta.sqlalchemy_session = db_session
        
        design = DesignFactory.create(project_id=1, created_by=1)
        comment = DesignCommentFactory.create(
            design=design,
            content="Original content",
            created_by=1
        )
        db_session.commit()

        update_data = {
            "content": "Updated content",
        }

        # Act
        response = client_no_auth.put(
            f"/api/v1/comments/{comment.id}",
            json=update_data
        )

        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestDeleteComment:
    """Tests for DELETE /api/v1/comments/{id} endpoint."""

    def test_delete_own_comment_success(self, client, db_session, mock_auth_user, mock_project_access):
        """Test deleting own comment (Requirement 7.5)."""
        # Arrange
        DesignFactory._meta.sqlalchemy_session = db_session
        DesignCommentFactory._meta.sqlalchemy_session = db_session
        
        design = DesignFactory.create(project_id=1, created_by=1)
        comment = DesignCommentFactory.create(
            design=design,
            content="Comment to delete",
            created_by=1  # Same as mock_auth_user
        )
        db_session.commit()
        comment_id = comment.id

        # Act
        response = client.delete(
            f"/api/v1/comments/{comment_id}",
            headers={"Authorization": "Bearer fake-token"}
        )

        # Assert
        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify deleted from database
        deleted_comment = db_session.query(DesignComment).filter_by(id=comment_id).first()
        assert deleted_comment is None

    def test_delete_other_user_comment_forbidden(self, client, db_session, mock_auth_user, mock_project_access):
        """Test deleting another user's comment returns 403."""
        # Arrange
        DesignFactory._meta.sqlalchemy_session = db_session
        DesignCommentFactory._meta.sqlalchemy_session = db_session
        
        design = DesignFactory.create(project_id=1, created_by=1)
        comment = DesignCommentFactory.create(
            design=design,
            content="Someone else's comment",
            created_by=999  # Different user
        )
        db_session.commit()

        # Act
        response = client.delete(
            f"/api/v1/comments/{comment.id}",
            headers={"Authorization": "Bearer fake-token"}
        )

        # Assert
        assert response.status_code == status.HTTP_403_FORBIDDEN

        # Verify not deleted from database
        db_session.refresh(comment)
        assert comment is not None

    def test_delete_comment_not_found(self, client, mock_auth_user, mock_project_access):
        """Test deleting non-existent comment returns 404."""
        # Act
        response = client.delete(
            "/api/v1/comments/99999",
            headers={"Authorization": "Bearer fake-token"}
        )

        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_comment_without_auth(self, client_no_auth, db_session):
        """Test deleting comment without authentication returns 401."""
        # Arrange
        DesignFactory._meta.sqlalchemy_session = db_session
        DesignCommentFactory._meta.sqlalchemy_session = db_session
        
        design = DesignFactory.create(project_id=1, created_by=1)
        comment = DesignCommentFactory.create(
            design=design,
            content="Comment to delete",
            created_by=1
        )
        db_session.commit()

        # Act
        response = client_no_auth.delete(f"/api/v1/comments/{comment.id}")

        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
