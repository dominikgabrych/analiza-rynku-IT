# Architecture decision records

Each ADR records one decision: its context, what was decided, the alternatives considered and the consequences. An accepted ADR is not rewritten; a changed decision gets a new ADR that supersedes the old one.

| ADR | Decision | Status |
| --- | --- | --- |
| [0001](0001-python-tooling.md) | Python 3.14 with uv, ruff and pytest | accepted |
| [0002](0002-postgres-with-pgvector.md) | PostgreSQL with pgvector as the single data store | accepted |
| [0003](0003-read-only-database-role.md) | Read-only database role for dashboards and other readers | accepted |
| [0004](0004-ci-with-pinned-actions.md) | CI on GitHub Actions with actions pinned to commit SHAs | accepted |
| [0005](0005-local-llm-with-ollama.md) | Local LLM served by Ollama on the host | accepted |
| [0006](0006-migrations-with-alembic.md) | Schema migrations with Alembic in plain SQL, without an ORM | accepted |
| [0007](0007-posting-presence-history.md) | Posting presence stored as validity periods | accepted |

## When to write one

An ADR goes into the same pull request as the change it explains. Write one when a change:

- adds a dependency, a service or an external tool;
- picks one of several reasonable designs, such as a data model, a storage layout or a protocol;
- sets a rule that later code must follow.

Small choices that are easy to reverse belong in the pull request description instead.

## Template

```markdown
# ADR NNNN: Title

- Status: proposed | accepted | superseded by ADR NNNN
- Date: YYYY-MM-DD

## Context

## Decision

## Alternatives considered

## Consequences
```
