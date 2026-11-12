"""Unit tests for the Comment model."""

import pytest
from sqlalchemy.exc import IntegrityError

from src.models.comment import Comment


def test_create_comment(db_session):
    """Test creating a new comment with valid data."""
    comment = Comment(
        content="Test comment",
        author_id=1,
        project_id=1
    )
    db_session.add(comment)
    db_session.commit()

    assert comment.id is not None
    assert comment.content == "Test comment"
    assert comment.author_id == 1
    assert comment.project_id == 1
    assert comment.parent_id is None


def test_comment_without_content(db_session):
    """Test that comments require content."""
    with pytest.raises(ValueError, match="Comment content is required"):
        Comment(
            content="",
            author_id=1,
            project_id=1
        )


def test_comment_without_author(db_session):
    """Test that comments require an author."""
    with pytest.raises(ValueError, match="Author ID is required"):
        Comment(
            content="Test comment",
            project_id=1
        )


def test_comment_without_project(db_session):
    """Test that comments require a project."""
    with pytest.raises(ValueError, match="Project ID is required"):
        Comment(
            content="Test comment",
            author_id=1
        )


def test_comment_reply(db_session):
    """Test creating a reply to a comment."""
    parent_comment = Comment(
        content="Parent comment",
        author_id=1,
        project_id=1
    )
    db_session.add(parent_comment)
    db_session.commit()

    reply = Comment(
        content="Reply comment",
        author_id=2,
        project_id=1,
        parent_id=parent_comment.id
    )
    db_session.add(reply)
    db_session.commit()

    assert reply.parent_id == parent_comment.id
    assert len(parent_comment.replies) == 1
    assert parent_comment.replies[0].content == "Reply comment"


def test_comment_cascade_delete(db_session):
    """Test that deleting a comment cascades to its replies."""
    parent_comment = Comment(
        content="Parent comment",
        author_id=1,
        project_id=1
    )
    db_session.add(parent_comment)
    db_session.commit()

    reply = Comment(
        content="Reply comment",
        author_id=2,
        project_id=1,
        parent_id=parent_comment.id
    )
    db_session.add(reply)
    db_session.commit()

    # Delete parent comment
    db_session.delete(parent_comment)
    db_session.commit()

    # Check that reply was also deleted
    assert db_session.query(Comment).count() == 0