"""BYOK provider key management endpoints."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ...models.api_keys import UserProviderKey
from ...models.user import User
from ...schemas.common import ErrorDetail, ErrorResponse
from ...utils.encryption import decrypt_value, encrypt_value
from ..deps import get_current_user, get_db

router = APIRouter()

# Supported providers and their verification details
SUPPORTED_PROVIDERS = {
    "anthropic": {
        "display_name": "Anthropic",
        "verify_url": "https://api.anthropic.com/v1/messages",
    },
    "gemini": {
        "display_name": "Google Gemini",
        "verify_url": "https://generativelanguage.googleapis.com/v1beta/models",
    },
    "elevenlabs": {
        "display_name": "ElevenLabs",
        "verify_url": "https://api.elevenlabs.io/v1/user",
    },
    "openai": {
        "display_name": "OpenAI",
        "verify_url": "https://api.openai.com/v1/models",
    },
}


class ProviderKeyResponse(BaseModel):
    provider: str
    is_active: bool
    last_verified_at: datetime | None = None
    key_prefix: str


class SetProviderKeyRequest(BaseModel):
    api_key: str = Field(..., min_length=5, max_length=500)


class VerifyResponse(BaseModel):
    provider: str
    valid: bool
    message: str


@router.get("", response_model=list[ProviderKeyResponse])
async def list_provider_keys(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List connected providers (show key prefix only, never the full key)."""
    keys = (
        db.query(UserProviderKey)
        .filter(UserProviderKey.user_id == user.id)
        .all()
    )

    results = []
    for k in keys:
        # Decrypt to get prefix, then discard
        try:
            plaintext = decrypt_value(k.api_key_enc)
            prefix = plaintext[:8] + "**"
        except Exception:
            prefix = "****"

        results.append(
            ProviderKeyResponse(
                provider=k.provider,
                is_active=k.is_active,
                last_verified_at=k.last_verified_at,
                key_prefix=prefix,
            )
        )

    return results


@router.put("/{provider}", response_model=ProviderKeyResponse)
async def set_provider_key(
    provider: str,
    body: SetProviderKeyRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Set or update an encrypted provider API key."""
    if provider not in SUPPORTED_PROVIDERS:
        raise HTTPException(
            status_code=400,
            detail=ErrorResponse(
                error=ErrorDetail(
                    code="INVALID_INPUT",
                    message=f"Unsupported provider: {provider}. "
                    f"Supported: {', '.join(SUPPORTED_PROVIDERS.keys())}",
                )
            ).model_dump(),
        )

    encrypted = encrypt_value(body.api_key)
    prefix = body.api_key[:8] + "**"

    existing = (
        db.query(UserProviderKey)
        .filter(
            UserProviderKey.user_id == user.id,
            UserProviderKey.provider == provider,
        )
        .first()
    )

    if existing:
        existing.api_key_enc = encrypted
        existing.key_version += 1
        existing.is_active = True
        existing.last_verified_at = None  # Reset verification on key change
    else:
        existing = UserProviderKey(
            user_id=user.id,
            provider=provider,
            api_key_enc=encrypted,
            key_version=1,
            is_active=True,
        )
        db.add(existing)

    db.commit()
    db.refresh(existing)

    return ProviderKeyResponse(
        provider=existing.provider,
        is_active=existing.is_active,
        last_verified_at=existing.last_verified_at,
        key_prefix=prefix,
    )


@router.delete("/{provider}", status_code=204)
async def delete_provider_key(
    provider: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Remove a provider key."""
    key = (
        db.query(UserProviderKey)
        .filter(
            UserProviderKey.user_id == user.id,
            UserProviderKey.provider == provider,
        )
        .first()
    )
    if not key:
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                error=ErrorDetail(
                    code="NOT_FOUND",
                    message=f"No key found for provider: {provider}",
                )
            ).model_dump(),
        )

    db.delete(key)
    db.commit()


@router.post("/{provider}/verify", response_model=VerifyResponse)
async def verify_provider_key(
    provider: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Test that a stored provider key works by making a lightweight API call."""
    if provider not in SUPPORTED_PROVIDERS:
        raise HTTPException(
            status_code=400,
            detail=ErrorResponse(
                error=ErrorDetail(
                    code="INVALID_INPUT",
                    message=f"Unsupported provider: {provider}",
                )
            ).model_dump(),
        )

    key_record = (
        db.query(UserProviderKey)
        .filter(
            UserProviderKey.user_id == user.id,
            UserProviderKey.provider == provider,
        )
        .first()
    )
    if not key_record:
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                error=ErrorDetail(
                    code="NOT_FOUND",
                    message=f"No key found for provider: {provider}",
                )
            ).model_dump(),
        )

    try:
        api_key = decrypt_value(key_record.api_key_enc)
    except Exception:
        return VerifyResponse(
            provider=provider,
            valid=False,
            message="Failed to decrypt stored key. Please re-enter your API key.",
        )

    # Make a lightweight verification call per provider
    import httpx

    valid = False
    message = ""

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            if provider == "anthropic":
                resp = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json={
                        "model": "claude-sonnet-4-20250514",
                        "max_tokens": 1,
                        "messages": [{"role": "user", "content": "hi"}],
                    },
                )
                # 200 = works, 401 = bad key, others might be rate limit (still valid key)
                if resp.status_code == 401:
                    valid = False
                    message = "Invalid API key"
                else:
                    valid = True
                    message = "Key verified successfully"

            elif provider == "gemini":
                resp = await client.get(
                    "https://generativelanguage.googleapis.com/v1beta/models",
                    params={"key": api_key},
                )
                if resp.status_code == 400 or resp.status_code == 403:
                    valid = False
                    message = "Invalid API key"
                else:
                    valid = True
                    message = "Key verified successfully"

            elif provider == "elevenlabs":
                resp = await client.get(
                    "https://api.elevenlabs.io/v1/user",
                    headers={"xi-api-key": api_key},
                )
                if resp.status_code == 401:
                    valid = False
                    message = "Invalid API key"
                else:
                    valid = True
                    message = "Key verified successfully"

            elif provider == "openai":
                resp = await client.get(
                    "https://api.openai.com/v1/models",
                    headers={"Authorization": f"Bearer {api_key}"},
                )
                if resp.status_code == 401:
                    valid = False
                    message = "Invalid API key"
                else:
                    valid = True
                    message = "Key verified successfully"

    except httpx.TimeoutException:
        valid = False
        message = "Verification timed out. The key may still be valid."
    except Exception as e:
        valid = False
        message = f"Verification failed: {str(e)[:100]}"

    # Update verification status
    if valid:
        key_record.last_verified_at = datetime.now(timezone.utc)
        key_record.is_active = True
    else:
        key_record.is_active = False

    db.commit()

    return VerifyResponse(provider=provider, valid=valid, message=message)
