import hashlib
from datetime import datetime, timezone
from typing import Generator

import jwt
from fastapi import Cookie, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..models.user import User, UserAPIKey
from ..services.auth_service import verify_token


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_current_user(
    request: Request,
    authorization: str | None = Header(None),
    x_api_key: str | None = Header(None, alias="X-API-Key"),
    access_token: str | None = Cookie(None),
    db: Session = Depends(get_db),
) -> User:
    """Authenticate via JWT (cookie or Bearer header) or API key."""

    # 1. API key authentication
    if x_api_key:
        prefix = x_api_key[:8]
        key_record = (
            db.query(UserAPIKey)
            .filter(
                UserAPIKey.key_prefix == prefix,
                UserAPIKey.is_active == True,  # noqa: E712
            )
            .first()
        )

        # SHA-256 for API keys (not bcrypt -- high-entropy keys don't need slow hashing)
        key_hash = hashlib.sha256(x_api_key.encode()).hexdigest()
        if key_record and key_hash == key_record.key_hash:
            key_record.last_used_at = datetime.now(timezone.utc)
            db.commit()
            return key_record.user
        raise HTTPException(status_code=401, detail="Invalid API key")

    # 2. JWT from Authorization header
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]

    # 3. JWT from httpOnly cookie
    if not token and access_token:
        token = access_token

    if token:
        try:
            payload = verify_token(token)
            if payload.get("type") != "access":
                raise HTTPException(status_code=401, detail="Invalid token type")
            user = db.query(User).filter(User.id == payload["sub"]).first()
            if user and user.is_active:
                return user
            raise HTTPException(status_code=401, detail="User not found or inactive")
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")

    raise HTTPException(status_code=401, detail="Authentication required")
