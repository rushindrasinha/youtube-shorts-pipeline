import jwt
from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from ...models.subscription import Plan, Subscription
from ...models.user import User
from ...schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from ...services.auth_service import (
    clear_auth_cookies,
    create_access_token,
    create_refresh_token,
    hash_password,
    set_auth_cookies,
    verify_password,
    verify_token,
)
from ..deps import get_db

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


@router.post("/register", status_code=201)
def register(body: RegisterRequest, response: Response, db: Session = Depends(get_db)):
    # Check for duplicate email
    existing = db.query(User).filter(User.email == body.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    # Create user
    user = User(
        email=body.email,
        password_hash=hash_password(body.password),
        display_name=body.display_name,
    )
    db.add(user)
    db.flush()

    # Create free plan subscription
    free_plan = db.query(Plan).filter(Plan.name == "free").first()
    if free_plan:
        subscription = Subscription(
            user_id=user.id,
            plan_id=free_plan.id,
            status="active",
        )
        db.add(subscription)

    db.commit()
    db.refresh(user)

    # Generate tokens
    access_token = create_access_token(user)
    refresh_token = create_refresh_token(user)
    set_auth_cookies(response, access_token, refresh_token)

    return {
        "user": _build_user_response(user),
        "access_token": access_token,
        "expires_in": 900,
    }


@router.post("/login")
def login(body: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not user.password_hash:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not user.is_active:
        raise HTTPException(status_code=401, detail="Account is disabled")

    access_token = create_access_token(user)
    refresh_token = create_refresh_token(user)
    set_auth_cookies(response, access_token, refresh_token)

    return {
        "access_token": access_token,
        "expires_in": 900,
    }


@router.post("/refresh")
def refresh(
    response: Response,
    refresh_token: str | None = Cookie(None),
    db: Session = Depends(get_db),
):
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token required")

    try:
        payload = verify_token(refresh_token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Refresh token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")

    # Look up user
    user = db.query(User).filter(User.id == payload["sub"]).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    # Rotation: issue new tokens (old JTI is implicitly invalidated)
    new_access_token = create_access_token(user)
    new_refresh_token = create_refresh_token(user)
    set_auth_cookies(response, new_access_token, new_refresh_token)

    return {
        "access_token": new_access_token,
        "expires_in": 900,
    }


@router.post("/logout")
def logout(response: Response):
    clear_auth_cookies(response)
    return {"status": "ok"}
