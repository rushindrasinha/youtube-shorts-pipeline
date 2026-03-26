from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ...models.user import User
from ...schemas.auth import UpdateUserRequest, UserResponse
from ..deps import get_current_user, get_db

router = APIRouter()


def _build_user_response(user: User) -> dict:
    """Build a user response dict from a User model."""
    sub_info = None
    if user.subscription and user.subscription.plan:
        sub_info = {
            "plan": user.subscription.plan.name,
            "status": user.subscription.status,
            "videos_used": 0,
            "videos_limit": user.subscription.plan.videos_per_month,
            "current_period_end": user.subscription.current_period_end,
        }
    return {
        "id": user.id,
        "email": user.email,
        "display_name": user.display_name,
        "avatar_url": user.avatar_url,
        "role": user.role,
        "default_lang": user.default_lang,
        "default_voice_id": user.default_voice_id,
        "caption_style": user.caption_style,
        "music_genre": user.music_genre,
        "subscription": sub_info,
        "created_at": user.created_at,
    }


@router.get("/me")
def get_me(user: User = Depends(get_current_user)):
    return _build_user_response(user)


@router.patch("/me")
def update_me(
    body: UpdateUserRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return _build_user_response(user)
