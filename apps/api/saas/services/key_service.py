"""API key resolution for pipeline jobs.

Checks for user-provided BYOK keys first, falls back to platform keys.
"""

from uuid import UUID

from sqlalchemy.orm import Session

from ..models.api_keys import UserProviderKey
from ..utils.encryption import decrypt_value


def resolve_api_keys(db: Session, user_id: UUID) -> dict[str, str]:
    """Return API keys for a pipeline job.

    Priority: user BYOK keys > platform-owned keys.
    """
    from ..settings import settings

    # Start with platform defaults
    keys = {
        "anthropic": settings.PLATFORM_ANTHROPIC_API_KEY,
        "gemini": settings.PLATFORM_GEMINI_API_KEY,
        "elevenlabs": settings.PLATFORM_ELEVENLABS_API_KEY,
    }

    # Check for user BYOK keys
    user_keys = (
        db.query(UserProviderKey)
        .filter(
            UserProviderKey.user_id == user_id,
            UserProviderKey.is_active == True,  # noqa: E712
        )
        .all()
    )

    for uk in user_keys:
        if uk.provider in keys:
            try:
                decrypted = decrypt_value(uk.api_key_enc)
                if decrypted:
                    keys[uk.provider] = decrypted
            except Exception:
                # Fall back to platform key if decryption fails
                pass

    return keys


def is_using_byok(db: Session, user_id: UUID) -> bool:
    """Check if user has any active BYOK keys."""
    count = (
        db.query(UserProviderKey)
        .filter(
            UserProviderKey.user_id == user_id,
            UserProviderKey.is_active == True,  # noqa: E712
        )
        .count()
    )
    return count > 0
