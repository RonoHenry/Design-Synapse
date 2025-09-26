"""API endpoints for user authentication and token management."""

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from jose import JWTError
from sqlalchemy.orm import Session
from src.api.v1.schemas.auth import Token, TokenRefresh, TokenResponse
from src.core.exceptions import AuthenticationError
from src.core.security import (create_access_token, create_refresh_token,
                               verify_refresh_token)
from src.infrastructure.database import get_db
from src.models.user import User

router = APIRouter(
    tags=["authentication"],
    responses={401: {"description": "Invalid authentication credentials"}},
)


@router.post(
    "/token",
    response_model=Token,
    summary="Create access token",
    description="""
    Log in with username (email) and password to obtain access and refresh tokens.

    The access token is used to authenticate requests to protected endpoints.
    The refresh token can be used to obtain new access tokens when they expire.
    """,
)
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> Token:
    """
    Create an access token for user authentication.

    Args:
        form_data: OAuth2 form containing username (email) and password
        db: Database session

    Returns:
        Token object containing access token, refresh token, and user roles

    Raises:
        AuthenticationError: If credentials are invalid
    """
    user = db.query(User).filter(User.email == form_data.username).first()

    if not user or not user.verify_password(form_data.password):
        raise AuthenticationError("Incorrect username or password")

    user_roles = [role.name for role in user.roles]
    token_data = {"sub": user.email}
    access_token = create_access_token(data=token_data, roles=user_roles)
    refresh_token = create_refresh_token(data=token_data)

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        roles=user_roles,
    )


@router.post(
    "/token/refresh",
    response_model=TokenResponse,
    summary="Refresh access token",
    description="""
    Use a refresh token to obtain a new access token.

    This endpoint is used when an access token has expired but the refresh token is
    still valid. The new access token will include the user's current roles.
    """,
)
def refresh_access_token(
    token_data: TokenRefresh,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """
    Create a new access token using a refresh token.

    Args:
        token_data: Refresh token data
        db: Database session

    Returns:
        TokenResponse containing new access token and user roles

    Raises:
        AuthenticationError: If refresh token is invalid or user not found
    """
    try:
        payload = verify_refresh_token(token_data.refresh_token)
        sub = payload.get("sub")
        user = db.query(User).filter(User.email == sub).first()
        if not user:
            raise AuthenticationError("Could not find user")

        user_roles = [role.name for role in user.roles]
        token_data = {"sub": sub}
        new_access_token = create_access_token(data=token_data, roles=user_roles)
        return TokenResponse(
            access_token=new_access_token,
            token_type="bearer",
            roles=user_roles,
        )
    except JWTError:
        raise AuthenticationError("Invalid refresh token")
