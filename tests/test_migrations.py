"""Migrations against a real PostgreSQL server, in a throwaway database per test."""

import os
import uuid
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.exc import IntegrityError

from radar.db import database_url

pytestmark = pytest.mark.db

PYPROJECT = Path(__file__).parents[1] / "pyproject.toml"
TABLES = {"runs", "postings", "posting_periods", "posting_details"}


def migrate(engine: Engine, action, revision: str) -> None:
    config = Config(toml_file=PYPROJECT)
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        action(config, revision)


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


@pytest.fixture
def migrated(engine):
    migrate(engine, command.upgrade, "head")
    return engine


@pytest.fixture
def posting(migrated):
    """A run and a posting it found, as committed rows other statements can reference."""
    with migrated.begin() as connection:
        run_id = connection.execute(
            text("INSERT INTO runs (source) VALUES ('test') RETURNING id")
        ).scalar_one()
        posting_id = connection.execute(
            text(
                "INSERT INTO postings (source, source_key, url, first_seen_at, first_run_id) "
                "VALUES ('test', 'job-1', 'https://example.com/job-1', now(), :run_id) "
                "RETURNING id"
            ),
            {"run_id": run_id},
        ).scalar_one()
    return {"run_id": run_id, "posting_id": posting_id}


def tables(engine: Engine) -> set[str]:
    with engine.connect() as connection:
        rows = connection.execute(
            text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
        )
        return set(rows.scalars())


def has_vector(engine: Engine) -> bool:
    with engine.connect() as connection:
        return connection.execute(
            text("SELECT EXISTS (SELECT FROM pg_extension WHERE extname = 'vector')")
        ).scalar_one()


def open_period(connection, posting: dict, **columns) -> None:
    values = {
        "first_seen_at": "now()",
        "last_seen_at": "now()",
        "closed_run_id": "NULL",
        "close_reason": "NULL",
    } | columns
    connection.execute(
        text(
            "INSERT INTO posting_periods (posting_id, opened_run_id, first_seen_at, "
            "last_seen_at, closed_run_id, close_reason, list_data) VALUES (:posting_id, "
            f":run_id, {values['first_seen_at']}, {values['last_seen_at']}, "
            f"{values['closed_run_id']}, {values['close_reason']}, '{{}}')"
        ),
        posting,
    )


def test_upgrade_creates_tables_and_vector_extension(migrated):
    assert TABLES <= tables(migrated)
    assert has_vector(migrated)


def test_jsonb_columns_use_lz4(migrated):
    with migrated.connect() as connection:
        rows = connection.execute(
            text(
                "SELECT attrelid::regclass::text, attname, attcompression FROM pg_attribute "
                "WHERE (attrelid, attname) IN "
                "(('posting_periods'::regclass, 'list_data'), ('posting_details'::regclass, 'data'))"
            )
        )
        assert {(table, column): method for table, column, method in rows} == {
            ("posting_periods", "list_data"): "l",
            ("posting_details", "data"): "l",
        }


def test_posting_has_at_most_one_open_period(migrated, posting):
    with migrated.begin() as connection:
        open_period(connection, posting)
    with pytest.raises(IntegrityError) as error, migrated.begin() as connection:
        open_period(connection, posting)
    assert error.value.orig.diag.constraint_name == "posting_periods_one_open_idx"

    # Closing the period frees the slot, so the posting can reappear.
    with migrated.begin() as connection:
        connection.execute(
            text(
                "UPDATE posting_periods SET closed_run_id = :run_id, close_reason = 'gone'"
            ),
            posting,
        )
        open_period(connection, posting)


@pytest.mark.parametrize(
    ("columns", "constraint"),
    [
        ({"last_seen_at": "now() - interval '1 day'"}, "posting_periods_seen_order"),
        ({"closed_run_id": ":run_id"}, "posting_periods_close_consistent"),
        ({"close_reason": "'gone'"}, "posting_periods_close_consistent"),
        (
            {"closed_run_id": ":run_id", "close_reason": "'deleted'"},
            "posting_periods_close_reason_check",
        ),
    ],
)
def test_inconsistent_period_is_rejected(migrated, posting, columns, constraint):
    with pytest.raises(IntegrityError) as error, migrated.begin() as connection:
        open_period(connection, posting, **columns)
    assert error.value.orig.diag.constraint_name == constraint


@pytest.mark.parametrize(
    ("statement", "constraint"),
    [
        (
            "INSERT INTO runs (source, status) VALUES ('test', 'succeeded')",
            "runs_status_matches_finished_at",
        ),
        (
            "INSERT INTO runs (source, finished_at) VALUES ('test', now())",
            "runs_status_matches_finished_at",
        ),
        (
            "INSERT INTO posting_details (posting_id, first_run_id, first_fetched_at, "
            "last_fetched_at, content_hash, data) "
            "VALUES (:posting_id, :run_id, now(), now(), '\\x00', '{}')",
            "posting_details_content_hash_check",
        ),
    ],
)
def test_inconsistent_run_or_page_is_rejected(migrated, posting, statement, constraint):
    with pytest.raises(IntegrityError) as error, migrated.begin() as connection:
        connection.execute(text(statement), posting)
    assert error.value.orig.diag.constraint_name == constraint


def test_same_page_content_is_stored_once(migrated, posting):
    insert = text(
        "INSERT INTO posting_details (posting_id, first_run_id, first_fetched_at, "
        "last_fetched_at, content_hash, data) "
        "VALUES (:posting_id, :run_id, now(), now(), sha256('{}'), '{}')"
    )
    with migrated.begin() as connection:
        connection.execute(insert, posting)
    with pytest.raises(IntegrityError) as error, migrated.begin() as connection:
        connection.execute(insert, posting)
    assert error.value.orig.diag.constraint_name == "posting_details_content_unique"


def names_with_prefix(engine: Engine, prefix: str) -> set[str]:
    """Tables, indexes, sequences and constraints whose names start with prefix."""
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                "SELECT relname FROM pg_class WHERE relname LIKE :pattern "
                "UNION SELECT conname FROM pg_constraint WHERE conname LIKE :pattern"
            ),
            {"pattern": f"{prefix}%"},
        )
        return set(rows.scalars())


def test_posting_pages_is_renamed_with_all_its_objects(migrated):
    # A constraint or index left with the old name would mislead anyone reading
    # errors or \d output.
    assert names_with_prefix(migrated, "posting_pages") == set()
    renamed = names_with_prefix(migrated, "posting_details")
    assert {
        "posting_details",
        "posting_details_id_seq",
        "posting_details_pkey",
    } <= renamed

    migrate(migrated, command.downgrade, "0001")
    assert names_with_prefix(migrated, "posting_details") == set()
    assert len(names_with_prefix(migrated, "posting_pages")) == len(renamed)


def test_downgrade_removes_everything_and_upgrade_works_again(migrated):
    migrate(migrated, command.downgrade, "base")
    assert tables(migrated) == {"alembic_version"}
    assert not has_vector(migrated)

    migrate(migrated, command.upgrade, "head")
    assert TABLES <= tables(migrated)
