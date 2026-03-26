from uuid import UUID

import jwt
from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from ...models.subscription import Plan, Subscription
from ...models.user import OAuthConnection, User
from ...schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from ...services.auth_service import (
    ACCESS_TOKEN_EXPIRE,
    REFRESH_TOKEN_EXPIRE,
    clear_auth_cookies,
    create_access_token,
    create_refresh_token,
    hash_password,
    set_auth_cookies,
    verify_password,
    verify_token,
)
from ...settings import settings as app_settings
from ..deps import get_db

router = APIRouter()

# ---------- OAuth2 Social Login Setup ----------
oauth = OAuth()

oauth.register(
    name="google",
    client_id=app_settings.GOOGLE_CLIENT_ID,
    client_secret=app_settings.GOOGLE_CLIENT_SECRET,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)

oauth.register(
    name="github",
    client_id=app_settings.GITHUB_CLIENT_ID,
    client_secret=app_settings.GITHUB_CLIENT_SECRET,
    authorize_url="https://github.com/login/oauth/authorize",
    access_token_url="https://github.com/login/oauth/access_token",
    api_base_url="https://api.github.com/",
    client_kwargs={"scope": "user:email"},
)


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
    user = db.query(User).filter(User.id == UUID(payload["sub"])).first()
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


# ---------- Social Login: Google ----------


def _find_or_create_oauth_user(
    db: Session,
    provider: str,
    provider_user_id: str,
    email: str,
    display_name: str | None = None,
    avatar_url: str | None = None,
) -> User:
    """Find existing user by OAuth connection or create a new one."""
    # Check for existing OAuth connection
    user = (
        db.query(User)
        .join(OAuthConnection)
        .filter(
            OAuthConnection.provider == provider,
            OAuthConnection.provider_user_id == provider_user_id,
        )
        .first()
    )

    if user:
        return user

    # Check if user exists by email (link accounts)
    user = db.query(User).filter(User.email == email).first()
    if user:
        # Link the OAuth provider to existing account
        oauth_conn = OAuthConnection(
            user_id=user.id,
            provider=provider,
            provider_user_id=provider_user_id,
        )
        db.add(oauth_conn)
        db.commit()
        return user

    # Create new user
    user = User(
        email=email,
        display_name=display_name,
        avatar_url=avatar_url,
        email_verified=True,
    )
    db.add(user)
    db.flush()

    # Create free subscription
    free_plan = db.query(Plan).filter(Plan.name == "free").first()
    if free_plan:
        subscription = Subscription(
            user_id=user.id,
            plan_id=free_plan.id,
            status="active",
        )
        db.add(subscription)

    # Create OAuth connection
    oauth_conn = OAuthConnection(
        user_id=user.id,
        provider=provider,
        provider_user_id=provider_user_id,
    )
    db.add(oauth_conn)

    db.commit()
    db.refresh(user)
    return user


def _set_social_auth_cookies(user: User) -> RedirectResponse:
    """Create redirect response with httpOnly auth cookies. NEVER in URL params."""
    access_token = create_access_token(user)
    refresh_token = create_refresh_token(user)

    response = RedirectResponse(f"{app_settings.FRONTEND_URL}/auth/callback")
    response.set_cookie(
        "access_token",
        access_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=int(ACCESS_TOKEN_EXPIRE.total_seconds()),
    )
    response.set_cookie(
        "refresh_token",
        refresh_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=int(REFRESH_TOKEN_EXPIRE.total_seconds()),
        path="/api/v1/auth/refresh",
    )
    return response


@router.get("/google")
async def google_login(request: Request):
    """Redirect to Google OAuth consent screen."""
    redirect_uri = str(request.url_for("google_callback"))
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/google/callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):
    """Handle Google OAuth callback. Creates/links user, sets httpOnly cookies."""
    try:
        token = await oauth.google.authorize_access_token(request)
    except Exception:
        raise HTTPException(status_code=401, detail="Google authentication failed")

    userinfo = token.get("userinfo")
    if not userinfo:
        raise HTTPException(status_code=401, detail="Could not retrieve user info from Google")

    user = _find_or_create_oauth_user(
        db=db,
        provider="google",
        provider_user_id=userinfo["sub"],
        email=userinfo["email"],
        display_name=userinfo.get("name"),
        avatar_url=userinfo.get("picture"),
    )

    return _set_social_auth_cookies(user)


# ---------- Social Login: GitHub ----------


@router.get("/github")
async def github_login(request: Request):
    """Redirect to GitHub OAuth consent screen."""
    redirect_uri = str(request.url_for("github_callback"))
    return await oauth.github.authorize_redirect(request, redirect_uri)


@router.get("/github/callback")
async def github_callback(request: Request, db: Session = Depends(get_db)):
    """Handle GitHub OAuth callback. Creates/links user, sets httpOnly cookies."""
    try:
        token = await oauth.github.authorize_access_token(request)
    except Exception:
        raise HTTPException(status_code=401, detail="GitHub authentication failed")

    # Get user profile from GitHub API
    resp = await oauth.github.get("user", token=token)
    github_user = resp.json()

    # GitHub may not return email in profile; fetch from emails endpoint
    email = github_user.get("email")
    if not email:
        emails_resp = await oauth.github.get("user/emails", token=token)
        emails = emails_resp.json()
        primary = next(
            (e for e in emails if e.get("primary") and e.get("verified")),
            None,
        )
        if primary:
            email = primary["email"]
        elif emails:
            email = emails[0]["email"]

    if not email:
        raise HTTPException(
            status_code=400,
            detail="Could not retrieve email from GitHub. Please ensure your email is visible.",
        )

    user = _find_or_create_oauth_user(
        db=db,
        provider="github",
        provider_user_id=str(github_user["id"]),
        email=email,
        display_name=github_user.get("name") or github_user.get("login"),
        avatar_url=github_user.get("avatar_url"),
    )

    return _set_social_auth_cookies(user)
