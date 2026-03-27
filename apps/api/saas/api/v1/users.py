import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ...models.subscription import Plan, Subscription, UsageRecord
from ...models.user import User, UserAPIKey
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
    ALLOWED_FIELDS = {"display_name", "default_lang", "caption_style", "music_genre"}
    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field in ALLOWED_FIELDS:
            setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return _build_user_response(user)


@router.get("/me/usage")
def get_usage(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Current billing period usage stats."""
    today = datetime.now(timezone.utc).date()
    period_start = today.replace(day=1)
    period_end = (period_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)

    usage = db.query(UsageRecord).filter(
        UsageRecord.user_id == user.id,
        UsageRecord.period_start == period_start,
    ).first()

    plan = db.query(Plan).join(Subscription).filter(Subscription.user_id == user.id).first()

    return {
        "period_start": str(period_start),
        "period_end": str(period_end),
        "videos_created": usage.videos_created if usage else 0,
        "videos_limit": plan.videos_per_month if plan else 3,
        "overage_count": usage.overage_count if usage else 0,
        "total_api_cost": float(usage.total_api_cost) if usage else 0,
    }


class CreateAPIKeyRequest(BaseModel):
    name: str = "Default"


@router.get("/me/api-keys")
def list_api_keys(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """List user's API keys (prefix only, never full key)."""
    keys = db.query(UserAPIKey).filter(
        UserAPIKey.user_id == user.id, UserAPIKey.is_active == True
    ).all()
    return [
        {
            "id": str(k.id),
            "name": k.name,
            "key_prefix": k.key_prefix,
            "created_at": k.created_at.isoformat() if k.created_at else None,
            "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
        }
        for k in keys
    ]


@router.post("/me/api-keys", status_code=201)
def create_api_key(
    body: CreateAPIKeyRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new API key. The full key is returned ONCE — store it safely."""
    raw_key = f"sf_live_{secrets.token_urlsafe(32)}"
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    record = UserAPIKey(
        user_id=user.id, name=body.name, key_prefix=raw_key[:12], key_hash=key_hash
    )
    db.add(record)
    db.commit()
    return {"id": str(record.id), "key": raw_key, "name": body.name}


@router.delete("/me/api-keys/{key_id}")
def revoke_api_key(
    key_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Revoke an API key."""
    key = db.query(UserAPIKey).filter(
        UserAPIKey.id == UUID(key_id), UserAPIKey.user_id == user.id
    ).first()
    if not key:
        raise HTTPException(404, "API key not found")
    key.is_active = False
    db.commit()
    return {"status": "revoked"}
