"""`radar migrate`: back up the database, then apply pending migrations."""

from collections.abc import Callable
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import Connection, create_engine, pool

from radar.backup import backup_before_migration
from radar.db import database_url


def pending(config: Config, connection: Connection) -> bool:
    heads = set(ScriptDirectory.from_config(config).get_heads())
    return set(MigrationContext.configure(connection).get_current_heads()) != heads


def migrate(
    config: Config, connection: Connection, backup: Callable[[], Path]
) -> Path | None:
    """Upgrade to head only after a backup succeeded; do nothing, and make no
    backup, when the database is already at head."""
    if not pending(config, connection):
        return None
    path = backup()
    config.attributes["connection"] = connection
    command.upgrade(config, "head")
    return path


def run() -> int:
    pyproject = Path("pyproject.toml")
    if not pyproject.exists():
        raise RuntimeError("run `radar migrate` from the repository root")
    config = Config(toml_file=pyproject.resolve())
    engine = create_engine(database_url(), poolclass=pool.NullPool)
    with engine.begin() as connection:
        path = migrate(config, connection, backup_before_migration)
    engine.dispose()
    print(f"backed up to {path}, migrated to head" if path else "already at head")
    return 0
