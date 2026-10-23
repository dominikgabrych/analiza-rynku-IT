# analiza-rynku-IT

[![CI](https://github.com/dominikgabrych/analiza-rynku-IT/actions/workflows/ci.yml/badge.svg)](https://github.com/dominikgabrych/analiza-rynku-IT/actions/workflows/ci.yml)

IT job market analysis (*analiza rynku IT* is Polish for "IT market analysis"). The tool collects job postings, extracts seniority, skills and salary ranges with a local LLM, and uses SQL to show what employers expect at each level, from internship to senior, with AI roles analyzed against the IT market as a whole.

**Status:** early development.

## Principles

- **Every number has context.** Each statistic is reported with its sample size, time window and population. Small samples get an uncertainty interval or "not enough data".
- **Every extracted value has a quote.** The model quotes the posting for each value it extracts, and code verifies the quote. Values without a verified quote never reach the statistics.
- **SQL counts, the model reads.** The LLM only extracts data and describes results. Every metric is defined once, as an SQL view.
- **Local first.** Models run locally through Ollama, so processing thousands of postings costs nothing.

## Planned stack

Python (uv, ruff, pytest) · FastAPI · PostgreSQL with pgvector · Ollama · n8n · Grafana · Arize Phoenix · Docker Compose

## Development

Requires [uv](https://docs.astral.sh/uv/), which installs the Python version from `.python-version` and the locked dependencies.

```sh
uv sync              # create .venv with Python and the dev tools
uv run pytest        # run the tests
uv run ruff check    # lint
uv run ruff format   # format
```

### Database

PostgreSQL with pgvector runs in Docker Compose. Copy `.env.example` to `.env` and set the passwords first; `--env-file .env` passes them to the commands below.

```sh
docker compose up -d                           # start PostgreSQL; wait for (healthy) in `docker compose ps`
uv run --env-file .env radar migrate           # back up, then apply pending schema migrations
uv run --env-file .env pytest                  # run all tests, including the database tests
```

The schema changes only through plain-SQL migrations in `db/migrations/versions/`. Without `--env-file`, `pytest` skips the database tests; each database test creates its own throwaway database and drops it afterwards.

### Backups

`radar backup` dumps the database with `pg_dump` into `BACKUP_DIR`, which belongs outside the Docker volume. It needs [age](https://age-encryption.org/) for the encrypted off-site copy; the settings are in `.env.example`.

```sh
uv run --env-file .env radar backup    # dump to recent/, keep the newest BACKUP_KEEP, refresh offsite/ weekly
uv run --env-file .env radar migrate   # dump to pre-migration/, then apply pending migrations
```

| Folder | Contents |
| --- | --- |
| `recent/` | the newest backups, rotated by count |
| `pre-migration/` | one backup before each migration, never rotated |
| `offsite/` | one age-encrypted copy, replaced when older than 7 days; the only folder to sync to cloud storage |

Apply migrations to a database with data through `radar migrate`, not `alembic upgrade head`, so that a backup always comes first. [ADR 0008](docs/adr/0008-backups-with-pg-dump-and-age.md) explains the design.

Architecture decisions are recorded in [docs/adr](docs/adr/).

## License

[MIT](LICENSE)
