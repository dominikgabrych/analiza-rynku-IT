# ADR 0003: Read-only database role

- Status: accepted
- Date: 2026-10-16 (recorded 2026-10-19)

## Context

Dashboards read the data, and later an LLM agent will query it through read-only SQL tools. Neither should be able to change data or the schema, even through a faulty query or an instruction injected by the untrusted posting texts the agent processes.

## Decision

- **`radar_reader` is a login role that can only read:** `CONNECT` on the database, `USAGE` on schema `public` and `SELECT` on all its tables and views.
- **Default privileges** ([`ALTER DEFAULT PRIVILEGES FOR ROLE postgres`](https://www.postgresql.org/docs/18/sql-alterdefaultprivileges.html)) grant `SELECT` on tables and views that `postgres` creates later, so new migrations need no extra grants.
- **Two role settings add a safety margin:** sessions start with `default_transaction_read_only = on` and `statement_timeout = 30s`. The grants are the real guard.
- **`db/init/10-reader-role.sh` creates the role** when the data volume is empty, with the password from `RADAR_READER_PASSWORD` in `.env`. Later changes to grants go through migrations.

## Alternatives considered

- **Connecting every reader as `postgres`:** simplest, but any faulty query or misled agent could modify or drop data.
- **Relying on `default_transaction_read_only` alone:** a session can switch it off with `SET`, so it only prevents accidents.
- **A separate schema that exposes only views:** tighter, because readers would not see raw tables. No views exist yet, and the extra schema would complicate early migrations. Worth revisiting before the agent gets SQL access.

## Consequences

- Objects must be created by `postgres`, which runs the migrations, for the default privileges to apply.
- Init scripts run only on an empty volume, so changing the role on an existing database needs a migration.
- Tested on 2026-10-16: `SELECT` works on tables and views created after the role. `INSERT`, `CREATE`, `DROP`, `SET ROLE postgres` and granting privileges to itself fail, also after switching off `default_transaction_read_only`.
