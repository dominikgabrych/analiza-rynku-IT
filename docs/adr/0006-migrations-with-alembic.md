# ADR 0006: Schema migrations with Alembic in plain SQL, without an ORM

- Status: accepted
- Date: 2026-10-19

## Context

The database will hold data that cannot be recreated, such as the presence history of postings, and its schema grows with every stage. The same schema has to exist in the development database, in throwaway test databases, in CI and in a database restored from a backup. Init scripts run only on an empty data volume, so they cannot change an existing schema.

Most database work is set-based: upserting thousands of postings per run, closing presence periods with one `UPDATE`, and metrics defined as SQL views. Queries rely on PostgreSQL features such as `jsonb`, `ON CONFLICT`, window functions and pgvector operators.

## Decision

- **[Alembic](https://alembic.sqlalchemy.org/) tracks and applies migrations.** Each migration is plain SQL passed to `op.execute`, with a downgrade that reverses it. The configuration lives in `pyproject.toml` (`[tool.alembic]`), and `db/migrations/env.py` builds the database URL from the same `POSTGRES_*` variables as Compose.
- **Migrations are numbered** (`0001`, `0002`, …, created with `alembic revision --rev-id`). An applied migration is never edited; a fix is a new migration.
- **No ORM.** Application code sends SQL through psycopg, kept in modules per area rather than in endpoints. SQLAlchemy is installed only as Alembic's engine; its Core query builder may be used where a query is assembled from optional filters.
- **CI runs the database tests** against an empty PostgreSQL with pgvector. Each test creates its own database, so the tests check upgrade, downgrade and upgrade again, as well as the constraints of the schema.

## Alternatives considered

- **A hand-written runner over psycopg** with a `schema_migrations` table: no extra dependency, but a transaction per step, downgrades, `status` and `history` commands and migrations added on parallel branches would all be ours to build and test.
- **dbmate:** plain `.sql` files and independent of the language, but a separate binary outside `uv.lock`, and the password has to be embedded in `DATABASE_URL`.
- **SQLAlchemy ORM or SQLModel:** less code to create, read, update and delete single records, and migrations generated from models. Here, writes come in batches, metrics live in SQL views, and PostgreSQL-specific SQL would end up in `text()` anyway, while the models would duplicate the schema that the migrations already define. Worth revisiting if a part appears where related records are edited one by one through the API.

## Consequences

- Every schema change, views included, goes through a migration in the same pull request as the code that needs it.
- Migrations cannot be generated automatically without models; they are written as SQL by hand.
- A migration that rewrites existing rows runs on real data only after a fresh backup, because a downgrade cannot bring overwritten values back.
- Database tests need a running server. Locally they are skipped without `POSTGRES_PASSWORD`; in CI a missing password fails the run.
