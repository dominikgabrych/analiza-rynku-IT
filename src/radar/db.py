"""Database connection settings, read from the same POSTGRES_* variables as Compose."""

import os

from sqlalchemy import URL


def database_url(database: str | None = None) -> URL:
    """Build the URL of the radar database, or of another database on the same server.

    URL.create escapes the password, so special characters cannot break the URL,
    and str() of the result hides it.
    """
    password = os.environ.get("POSTGRES_PASSWORD")
    if not password:
        raise RuntimeError(
            "POSTGRES_PASSWORD is not set; load .env with `uv run --env-file .env ...`"
        )
    return URL.create(
        "postgresql+psycopg",
        username=os.environ.get("POSTGRES_USER", "postgres"),
        password=password,
        host=os.environ.get("POSTGRES_HOST", "127.0.0.1"),
        port=int(os.environ.get("POSTGRES_PORT", "5432")),
        database=database or os.environ.get("POSTGRES_DB", "radar"),
    )
