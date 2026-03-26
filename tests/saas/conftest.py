import sys
import os

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker

# Add apps/api to path so saas package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "apps", "api"))

from saas.models import Base


@pytest.fixture(scope="function")
def engine():
    """Create an in-memory SQLite engine for testing.

    Registers a custom compilation rule so PostgreSQL ARRAY columns
    render as TEXT in SQLite (which lacks native array support).
    """
    from sqlalchemy.dialects.postgresql import ARRAY
    from sqlalchemy.ext.compiler import compiles

    @compiles(ARRAY, "sqlite")
    def _compile_array_sqlite(type_, compiler, **kw):
        return "TEXT"

    eng = create_engine("sqlite:///:memory:")

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
