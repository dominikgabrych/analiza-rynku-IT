"""Fixtures shared by the database tests."""

import os
import uuid

import pytest
from sqlalchemy import create_engine, text

from radar.db import database_url


@pytest.fixture
def engine():
    if not os.environ.get("POSTGRES_PASSWORD"):
        if os.environ.get("CI"):
            pytest.fail(
                "POSTGRES_PASSWORD must be set in CI, or the database tests never run"
            )
        pytest.skip("no database; run `uv run --env-file .env pytest` with Compose up")
    # Never the real radar database: each test gets its own and drops it afterwards.
    name = f"radar_test_{uuid.uuid4().hex[:12]}"
    admin = create_engine(database_url("postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as connection:
        connection.execute(text(f'CREATE DATABASE "{name}"'))
    engine = create_engine(database_url(name))
    try:
        yield engine
    finally:
        engine.dispose()
        with admin.connect() as connection:
            connection.execute(text(f'DROP DATABASE "{name}" WITH (FORCE)'))
        admin.dispose()
