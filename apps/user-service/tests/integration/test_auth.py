from fastapi.testclient import TestClient
import pytest
from sqlalchemy.orm import Session

from src.main import app
from src.models.user import User
from src.infrastructure.database import get_db, SessionLocal

# Create a test client
client = TestClient(app)

@pytest.fixture(autouse=True)
def override_dependency(db_session: Session):
    """Override the get_db dependency with our test session."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass  # Session cleanup is handled by the db_session fixture
    
    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.clear()


def test_login_for_access_token(db_session: Session, test_user: User):
    # When
    response = client.post(
        "/api/v1/token",
        data={"username": test_user.email, "password": "testpassword"},
    )

    # Then
    assert response.status_code == 200
    json_response = response.json()
    assert "access_token" in json_response
    assert json_response["token_type"] == "bearer"


def test_login_for_access_token_invalid_credentials(db_session: Session, test_user: User):
    # When
    response = client.post(
        "/api/v1/token",
        data={"username": test_user.email, "password": "wrongpassword"},
    )

    # Then
    assert response.status_code == 401
    json_response = response.json()
    assert json_response["detail"] == "Incorrect username or password"


def test_refresh_token(db_session: Session, test_user: User):
    """Test that a refresh token can be used to get a new access token."""
    # First, get an initial access token and refresh token
    response = client.post(
        "/api/v1/token",
        data={"username": test_user.email, "password": "testpassword"},
    )
    assert response.status_code == 200
    
    # Extract the refresh token
    tokens = response.json()
    assert "refresh_token" in tokens
    refresh_token = tokens["refresh_token"]
    
    # Use the refresh token to get a new access token
    response = client.post(
        "/api/v1/token/refresh",
        json={"refresh_token": refresh_token}
    )
    assert response.status_code == 200
    new_tokens = response.json()
    assert "access_token" in new_tokens
    assert "token_type" in new_tokens
    assert new_tokens["token_type"] == "bearer"


def test_refresh_token_invalid(db_session: Session):
    """Test that an invalid refresh token is rejected."""
    response = client.post(
        "/api/v1/token/refresh",
        json={"refresh_token": "invalid_token"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid refresh token"
