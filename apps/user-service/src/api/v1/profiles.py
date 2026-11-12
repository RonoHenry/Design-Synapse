"""API endpoints for managing user profiles."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.api.dependencies import get_current_user
from src.api.v1.schemas.profiles import (
    UserProfilePreferencesUpdate,
    UserProfileResponse,
    UserProfileUpdate,
)
from src.infrastructure.database import get_db
from src.models.user import User
from src.models.user_profile import UserProfile

router = APIRouter(
    prefix="/users/me",
    tags=["profile"],
    responses={401: {"description": "Not authenticated"}},
)


@router.get(
    "/profile",
    response_model=UserProfileResponse,
    summary="Get current user's profile",
    description="Get profile information for the current authenticated user.",
)
def get_user_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserProfileResponse:
    """Get the current user's profile."""
    if not current_user.profile:
        # Create a default profile if one doesn't exist
        profile = UserProfile(user_id=current_user.id)
        db.add(profile)
        db.commit()
        db.refresh(profile)
        current_user.profile = profile

    # Create a dictionary that combines profile data with user email
    profile_data = {
        "id": current_user.profile.id,
        "user_id": current_user.id,
        "email": current_user.email,
        "created_at": current_user.profile.created_at,
        "updated_at": current_user.profile.updated_at,
        "display_name": current_user.profile.display_name,
        "bio": current_user.profile.bio,
        "organization": current_user.profile.organization,
        "phone_number": current_user.profile.phone_number,
        "location": current_user.profile.location,
        "preferences": current_user.profile.preferences,
        "social_links": current_user.profile.social_links,
    }
    return UserProfileResponse(**profile_data)


@router.put(
    "/profile",
    response_model=UserProfileResponse,
    summary="Update user profile",
    description="Update the complete profile for the currently authenticated user.",
)
def update_user_profile(
    profile_update: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserProfileResponse:
    """Update the current user's profile."""
    if not current_user.profile:
        profile = UserProfile(user_id=current_user.id)
        db.add(profile)
    else:
        profile = current_user.profile

    for field, value in profile_update.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)

    db.commit()
    db.refresh(profile)

    # Create a dictionary that combines profile data with user email
    profile_data = {
        "id": profile.id,
        "user_id": current_user.id,
        "email": current_user.email,
        "created_at": profile.created_at,
        "updated_at": profile.updated_at,
        "display_name": profile.display_name,
        "bio": profile.bio,
        "organization": profile.organization,
        "phone_number": profile.phone_number,
        "location": profile.location,
        "preferences": profile.preferences,
        "social_links": profile.social_links,
    }
    return UserProfileResponse(**profile_data)


@router.patch(
    "/profile/preferences",
    response_model=UserProfileResponse,
    summary="Update user preferences",
    description="Update just the preferences section of the user's profile.",
)
def update_user_preferences(
    preferences: UserProfilePreferencesUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserProfileResponse:
    """Update the current user's preferences."""
    if not current_user.profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User profile not found",
        )

    current_user.profile.preferences = preferences.preferences
    db.commit()
    db.refresh(current_user.profile)

    # Create a dictionary that combines profile data with user email
    profile_data = {
        "id": current_user.profile.id,
        "user_id": current_user.id,
        "email": current_user.email,
        "created_at": current_user.profile.created_at,
        "updated_at": current_user.profile.updated_at,
        "display_name": current_user.profile.display_name,
        "bio": current_user.profile.bio,
        "organization": current_user.profile.organization,
        "phone_number": current_user.profile.phone_number,
        "location": current_user.profile.location,
        "preferences": current_user.profile.preferences,
        "social_links": current_user.profile.social_links,
    }
    return UserProfileResponse(**profile_data)
