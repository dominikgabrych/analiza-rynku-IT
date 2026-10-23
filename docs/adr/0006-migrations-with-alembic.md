# ADR 0006: Schema migrations with Alembic in plain SQL, without an ORM

- Status: accepted
- Date: 2026-10-19

## Context

The database will hold data that cannot be recreated, and its schema grows with every stage. The same schema has to exist in the development database, in test databases, in CI and in a database restored from a backup. Most queries are set-based and PostgreSQL-specific: batch upserts, `jsonb`, window functions and pgvector operators.

## Decision

- **[Alembic](https://alembic.sqlalchemy.org/) applies numbered migrations written in plain SQL**, each with a downgrade. An applied migration is never edited; a fix is a new migration.
- **No ORM.** Application code sends SQL through psycopg, kept in modules per area.

## Alternatives considered

- **A hand-written migration runner:** no dependency, but transactions, downgrades and history would all be ours to build and test.
- **dbmate:** plain `.sql` files, but a separate binary outside `uv.lock`.
- **SQLAlchemy ORM or SQLModel:** less code for single-record edits, but writes here come in batches, metrics live in SQL views, and the models would duplicate the schema the migrations define.

## Consequences

- Every schema change, views included, goes through a migration in the same pull request as the code that needs it.
- Migrations are written by hand; CI checks upgrade, downgrade and upgrade again on an empty database.
