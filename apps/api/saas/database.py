from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .settings import settings

_engine = None
_SessionLocal = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(settings.DATABASE_URL)
    return _engine


def get_session_factory():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())
    return _SessionLocal


def SessionLocal():
    """Create a new DB session."""
    factory = get_session_factory()
    return factory()
