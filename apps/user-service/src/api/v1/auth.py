"""
API endpoints for authentication.
"""
from fastapi import APIRouter, Depends, status, Body
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from jose import JWTError

from src.core.security import create_access_token, create_refresh_token, verify_refresh_token
from src.core.exceptions import AuthenticationError
from src.models.user import User
from src.infrastructure.database import get_db
from src.api.v1.schemas.auth import Token, TokenRefresh, TokenResponse

router = APIRouter(
    tags=["authentication"],
    responses={401: {"description": "Invalid authentication credentials"}}
)

@router.post(
    "/token",
    response_model=Token,
    summary="Create access token",
    description="""
    Log in with username (email) and password to obtain access and refresh tokens.
    
    The access token is used to authenticate requests to protected endpoints.
    The refresh token can be used to obtain new access tokens when they expire.
    """
)
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
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
    print(f"Attempting to log in user: {form_data.username}")
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user:
        print("User not found in database.")
    else:
        print(f"User found: {user.email}")
        password_verified = user.verify_password(form_data.password)
        print(f"Password verification result: {password_verified}")

    if not user or not user.verify_password(form_data.password):
        raise AuthenticationError("Incorrect username or password")
    
    user_roles = [role.name for role in user.roles]
    access_token = create_access_token(
        data={"sub": user.email},
        roles=user_roles
    )
    refresh_token = create_refresh_token(
        data={"sub": user.email}
    )
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        roles=user_roles
    )


@router.post(
    "/token/refresh",
    response_model=TokenResponse,
    summary="Refresh access token",
    description="""
    Use a refresh token to obtain a new access token.
    
    This endpoint is used when an access token has expired but the refresh token is still valid.
    The new access token will include the user's current roles.
    """
)
def refresh_access_token(
    token_data: TokenRefresh,
    db: Session = Depends(get_db)
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
        user = db.query(User).filter(User.email == payload.get("sub")).first()
        if not user:
            raise AuthenticationError("Could not find user")
        
        user_roles = [role.name for role in user.roles]
        new_access_token = create_access_token(
            data={"sub": payload.get("sub")},
            roles=user_roles
        )
        return TokenResponse(
            access_token=new_access_token,
            token_type="bearer",
            roles=user_roles
        )
    except JWTError:
        raise AuthenticationError("Invalid refresh token")
