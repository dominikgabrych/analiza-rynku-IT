# Architecture decision records

Each record explains one decision: its context, the choice, the alternatives considered and the consequences. A changed decision gets a new record that supersedes the old one.

| ADR | Decision | Status |
| --- | --- | --- |
| [0001](0001-python-tooling.md) | Python 3.14 with uv, ruff and pytest | accepted |
| [0002](0002-postgres-with-pgvector.md) | PostgreSQL with pgvector as the single data store | accepted |
| [0003](0003-read-only-database-role.md) | Read-only database role for dashboards and other readers | accepted |
| [0004](0004-ci-with-pinned-actions.md) | CI on GitHub Actions with actions pinned to commit SHAs | accepted |
| [0005](0005-local-llm-with-ollama.md) | Local LLM served by Ollama on the host | accepted |
| [0006](0006-migrations-with-alembic.md) | Schema migrations with Alembic in plain SQL, without an ORM | accepted |
| [0007](0007-posting-presence-history.md) | Posting presence stored as validity periods | accepted |
| [0008](0008-backups-with-pg-dump-and-age.md) | Backups with pg_dump and an age-encrypted off-site copy | accepted |
