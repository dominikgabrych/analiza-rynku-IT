"""`radar migrate` on a throwaway database, with a stand-in for the backup."""

from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import inspect

from radar.migrate import migrate

pytestmark = pytest.mark.db

PYPROJECT = Path(__file__).parents[1] / "pyproject.toml"


class FakeBackup:
    def __init__(self, fail: bool = False):
        self.calls = 0
        self.fail = fail

    def __call__(self) -> Path:
        self.calls += 1
        if self.fail:
            raise OSError("disk full")
        return Path("radar-2026-10-29-031500.dump")


def run_migrate(engine, backup) -> Path | None:
    with engine.begin() as connection:
        return migrate(Config(toml_file=PYPROJECT), connection, backup)


def test_backup_comes_before_pending_migrations(engine):
    backup = FakeBackup()

    assert run_migrate(engine, backup) == Path("radar-2026-10-29-031500.dump")

    assert backup.calls == 1
    assert "postings" in inspect(engine).get_table_names()


def test_database_at_head_needs_no_backup(engine):
    run_migrate(engine, FakeBackup())
    backup = FakeBackup()

    assert run_migrate(engine, backup) is None
    assert backup.calls == 0


def test_failed_backup_stops_the_migration(engine):
    with pytest.raises(OSError):
        run_migrate(engine, FakeBackup(fail=True))

    assert inspect(engine).get_table_names() == []
