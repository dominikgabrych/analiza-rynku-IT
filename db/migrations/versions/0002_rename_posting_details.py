"""Rename posting_pages to posting_details

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-21
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0002"
down_revision: str | Sequence[str] | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Constraint names start with the table name, so they are renamed with it.
# PostgreSQL 18 names NOT NULL constraints too. Renaming a primary key or
# unique constraint also renames its index.
CONSTRAINT_SUFFIXES = [
    "pkey",
    "posting_id_fkey",
    "first_run_id_fkey",
    "content_unique",
    "content_hash_check",
    "fetch_order",
    "id_not_null",
    "posting_id_not_null",
    "first_run_id_not_null",
    "first_fetched_at_not_null",
    "last_fetched_at_not_null",
    "content_hash_not_null",
    "data_not_null",
]


def rename_table(old: str, new: str) -> None:
    op.execute(f"ALTER TABLE {old} RENAME TO {new}")
    op.execute(f"ALTER SEQUENCE {old}_id_seq RENAME TO {new}_id_seq")
    for suffix in CONSTRAINT_SUFFIXES:
        op.execute(
            f"ALTER TABLE {new} RENAME CONSTRAINT {old}_{suffix} TO {new}_{suffix}"
        )


def upgrade() -> None:
    rename_table("posting_pages", "posting_details")
    op.execute(
        "COMMENT ON TABLE posting_details IS 'Details extracted from a posting''s own "
        "page, such as requirements and description. A new version only when the "
        "extracted content changes.'"
    )


def downgrade() -> None:
    rename_table("posting_details", "posting_pages")
    op.execute(
        "COMMENT ON TABLE posting_pages IS 'Fields extracted from posting pages. "
        "A new row only when the extracted content changes.'"
    )
