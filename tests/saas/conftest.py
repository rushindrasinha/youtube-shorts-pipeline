import sys
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker

# Add apps/api to path so saas package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "apps", "api"))

from saas.models import Base
from saas.models.subscription import Plan


@pytest.fixture(scope="function")
def engine():
    """Create an in-memory SQLite engine for testing.

    Registers a custom compilation rule so PostgreSQL ARRAY columns
    render as TEXT in SQLite (which lacks native array support).
    """
    import sqlite3
    from uuid import UUID as PyUUID
    from sqlalchemy.dialects.postgresql import ARRAY
    from sqlalchemy.ext.compiler import compiles

    @compiles(ARRAY, "sqlite")
    def _compile_array_sqlite(type_, compiler, **kw):
        return "TEXT"

    # Register sqlite3 adapters so UUID objects are stored/retrieved as strings
    sqlite3.register_adapter(PyUUID, lambda u: str(u))
    sqlite3.register_converter("UUID", lambda b: b.decode())
    sqlite3.register_converter("CHAR", lambda b: b.decode())

    from sqlalchemy.pool import StaticPool

    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Enable foreign key enforcement in SQLite
    @event.listens_for(eng, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    # Create all tables, skipping partial indexes that use postgresql_where
    partial_indexes = []
    for table in Base.metadata.tables.values():
        to_remove = []
        for idx in table.indexes:
            dialect_opts = idx.dialect_options.get("postgresql", {})
            if dialect_opts.get("where") is not None:
                to_remove.append(idx)
        for idx in to_remove:
            table.indexes.discard(idx)
            partial_indexes.append((table, idx))

    Base.metadata.create_all(eng)

    # Restore partial indexes so they don't affect the real metadata
    for table, idx in partial_indexes:
        table.indexes.add(idx)

    yield eng

    # Drop tables with FK checks disabled to avoid circular dependency issues
    with eng.connect() as conn:
        conn.execute(text("PRAGMA foreign_keys=OFF"))
        conn.commit()
    Base.metadata.drop_all(eng)
    eng.dispose()


@pytest.fixture(scope="function")
def session(engine):
    """Create a new database session for a test."""
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture(scope="function")
def db_session(engine):
    """Create a DB session and seed the free plan for auth tests."""
    Session = sessionmaker(bind=engine)
    session = Session()

    # Seed free plan
    free_plan = Plan(
        name="free",
        display_name="Free",
        videos_per_month=3,
        channels_limit=1,
        team_seats=1,
        price_cents=0,
        overage_cents=0,
        features={},
    )
    session.add(free_plan)
    session.commit()

    yield session
    session.close()


@pytest.fixture(scope="function")
def client(db_session):
    """Create a FastAPI TestClient wired to the in-memory SQLite DB."""
    from saas.main import create_app
    from saas.api.deps import get_db

    app = create_app()

    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as tc:
        yield tc


def create_test_user(db_session, email="test@example.com", password="testpassword123"):
    """Helper to create a test user via the register endpoint logic."""
    from saas.models.user import User
    from saas.models.subscription import Subscription
    from saas.services.auth_service import hash_password

    user = User(
        email=email,
        password_hash=hash_password(password),
        display_name="Test User",
    )
    db_session.add(user)
    db_session.flush()

    free_plan = db_session.query(Plan).filter(Plan.name == "free").first()
    if free_plan:
        sub = Subscription(
            user_id=user.id,
            plan_id=free_plan.id,
            status="active",
        )
        db_session.add(sub)

    db_session.commit()
    db_session.refresh(user)
    return user
