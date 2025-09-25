"""
Integration tests for CRUD operations on the User model.
"""
import pytest
from sqlalchemy.orm import Session
from src.models.user import User


def test_create_user(db_session: Session):
    """Test creating a new user."""
    user = User(
        email="crud_test@example.com",
        username="crud_test_user",
        password="securepassword",
    )
    db_session.add(user)
    db_session.commit()

    retrieved_user = (
        db_session.query(User).filter_by(email="crud_test@example.com").first()
    )
    assert retrieved_user is not None
    assert retrieved_user.username == "crud_test_user"


def test_read_user(db_session: Session, test_user: User):
    """Test reading a user from the database."""
    retrieved_user = db_session.query(User).filter_by(id=test_user.id).first()
    assert retrieved_user is not None
    assert retrieved_user.email == test_user.email


def test_update_user(db_session: Session, test_user: User):
    """Test updating a user's attributes."""
    test_user.username = "updated_username"
    db_session.commit()

    retrieved_user = db_session.query(User).filter_by(id=test_user.id).first()
    assert retrieved_user.username == "updated_username"


def test_delete_user(db_session: Session, test_user: User):
    """Test deleting a user from the database."""
    user_id = test_user.id
    db_session.delete(test_user)
    db_session.commit()

    retrieved_user = db_session.query(User).filter_by(id=user_id).first()
    assert retrieved_user is None
