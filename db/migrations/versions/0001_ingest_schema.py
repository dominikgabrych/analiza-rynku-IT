"""Ingest schema: fetch runs, postings, their presence history and page data

Revision ID: 0001
Revises:
Create Date: 2026-10-19
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.execute(
        """
        CREATE TABLE runs (
            id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            source text NOT NULL,
            started_at timestamptz NOT NULL DEFAULT now(),
            finished_at timestamptz,
            status text NOT NULL DEFAULT 'running'
                CHECK (status IN ('running', 'succeeded', 'failed')),
            list_complete boolean NOT NULL DEFAULT false,
            list_pages integer NOT NULL DEFAULT 0,
            offer_pages integer NOT NULL DEFAULT 0,
            postings_seen integer NOT NULL DEFAULT 0,
            postings_new integer NOT NULL DEFAULT 0,
            postings_gone integer NOT NULL DEFAULT 0,
            http_errors integer NOT NULL DEFAULT 0,
            parse_errors integer NOT NULL DEFAULT 0,
            source_total integer,
            details jsonb NOT NULL DEFAULT '{}',
            CONSTRAINT runs_status_matches_finished_at
                CHECK ((status = 'running') = (finished_at IS NULL)),
            CONSTRAINT runs_finished_after_start CHECK (finished_at >= started_at)
        )
        """
    )
    op.execute(
        "COMMENT ON TABLE runs IS 'One fetch run of one source: timing, counters and errors.'"
    )
    op.execute(
        "COMMENT ON COLUMN runs.list_complete IS 'The whole posting list was read "
        "without errors; only such runs may close presence periods.'"
    )
    op.execute(
        "COMMENT ON COLUMN runs.source_total IS 'Number of postings the source "
        "itself reports, for completeness checks.'"
    )

    op.execute(
        """
        CREATE TABLE postings (
            id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            source text NOT NULL,
            source_key text NOT NULL,
            url text NOT NULL,
            first_seen_at timestamptz NOT NULL,
            first_run_id bigint NOT NULL REFERENCES runs (id),
            CONSTRAINT postings_source_key_unique UNIQUE (source, source_key)
        )
        """
    )
    op.execute(
        "COMMENT ON TABLE postings IS 'One posting address on one source. The same "
        "job under several addresses or sources is several postings.'"
    )
    op.execute(
        "COMMENT ON COLUMN postings.source_key IS 'Stable identifier of the posting "
        "within its source, such as an id or a slug.'"
    )

    # PostgreSQL compresses jsonb only when a row grows past about 2 kB (the TOAST
    # threshold); COMPRESSION lz4 replaces the slower default, pglz.
    op.execute(
        """
        CREATE TABLE posting_periods (
            id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            posting_id bigint NOT NULL REFERENCES postings (id),
            opened_run_id bigint NOT NULL REFERENCES runs (id),
            first_seen_at timestamptz NOT NULL,
            last_seen_at timestamptz NOT NULL,
            closed_run_id bigint REFERENCES runs (id),
            close_reason text CHECK (close_reason IN ('gone', 'changed')),
            list_data jsonb COMPRESSION lz4 NOT NULL,
            CONSTRAINT posting_periods_seen_order CHECK (last_seen_at >= first_seen_at),
            CONSTRAINT posting_periods_close_consistent
                CHECK ((closed_run_id IS NULL) = (close_reason IS NULL))
        )
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX posting_periods_one_open_idx
            ON posting_periods (posting_id)
            WHERE closed_run_id IS NULL
        """
    )
    op.execute(
        "CREATE INDEX posting_periods_posting_id_idx ON posting_periods (posting_id)"
    )
    op.execute(
        "COMMENT ON TABLE posting_periods IS 'Presence history: one row per continuous "
        "period in which a posting was listed with the same list fields.'"
    )
    op.execute(
        "COMMENT ON COLUMN posting_periods.list_data IS 'Posting fields as the "
        "source list showed them during this period.'"
    )
    op.execute(
        "COMMENT ON COLUMN posting_periods.close_reason IS 'gone: a complete run no "
        "longer listed the posting; changed: its list fields changed and a new "
        "period started.'"
    )

    op.execute(
        """
        CREATE TABLE posting_pages (
            id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            posting_id bigint NOT NULL REFERENCES postings (id),
            first_run_id bigint NOT NULL REFERENCES runs (id),
            first_fetched_at timestamptz NOT NULL,
            last_fetched_at timestamptz NOT NULL,
            content_hash bytea NOT NULL CHECK (octet_length(content_hash) = 32),
            data jsonb COMPRESSION lz4 NOT NULL,
            CONSTRAINT posting_pages_fetch_order CHECK (last_fetched_at >= first_fetched_at),
            CONSTRAINT posting_pages_content_unique UNIQUE (posting_id, content_hash)
        )
        """
    )
    op.execute(
        "COMMENT ON TABLE posting_pages IS 'Fields extracted from posting pages. "
        "A new row only when the extracted content changes.'"
    )
    op.execute(
        "COMMENT ON COLUMN posting_pages.content_hash IS 'SHA-256 of the extracted "
        "JSON, so unchanged content is never stored twice.'"
    )


def downgrade() -> None:
    op.execute("DROP TABLE posting_pages")
    op.execute("DROP TABLE posting_periods")
    op.execute("DROP TABLE postings")
    op.execute("DROP TABLE runs")
    op.execute("DROP EXTENSION IF EXISTS vector")
