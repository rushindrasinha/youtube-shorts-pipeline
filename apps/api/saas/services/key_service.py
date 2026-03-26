"""API key resolution for pipeline jobs.

For now, returns platform keys from settings. BYOK support comes in Phase 2.
"""

from sqlalchemy.orm import Session


def resolve_api_keys(db: Session, user_id) -> dict[str, str]:
    """Return API keys for a pipeline job.

    Currently returns platform-owned keys. Phase 2 will check for
    user-provided BYOK keys first.
    """
    from ..settings import settings

    return {
        "anthropic": settings.PLATFORM_ANTHROPIC_API_KEY,
        "gemini": settings.PLATFORM_GEMINI_API_KEY,
        "elevenlabs": settings.PLATFORM_ELEVENLABS_API_KEY,
    }
