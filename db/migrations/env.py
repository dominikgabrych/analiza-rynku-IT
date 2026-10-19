"""Alembic environment: applies the plain-SQL migrations in db/migrations/versions."""

import logging

from alembic import context
from sqlalchemy import Connection, create_engine, pool

from radar.db import database_url

config = context.config

# There is no alembic.ini with a logging section, so set up logging here to see
# which migrations run. Does nothing when logging is already configured (pytest).
logging.basicConfig(level=logging.INFO, format="%(levelname)s [%(name)s] %(message)s")


def run_migrations(connection: Connection) -> None:
    context.configure(connection=connection)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Migrate the database from POSTGRES_* variables, or a connection passed in by tests."""
    connection = config.attributes.get("connection")
    if connection is not None:
        run_migrations(connection)
        return
    engine = create_engine(database_url(), poolclass=pool.NullPool)
    with engine.connect() as connection:
        run_migrations(connection)


def run_migrations_offline() -> None:
    """Print the migrations as SQL (`alembic upgrade head --sql`) without connecting."""
    context.configure(url="postgresql+psycopg://", literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
