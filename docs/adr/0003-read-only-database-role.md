# ADR 0003: Read-only database role

- Status: accepted
- Date: 2026-10-16 (recorded 2026-10-19)

## Context

Dashboards read the data, and later an LLM agent will query it through SQL tools. Neither should be able to change data or the schema, even through a faulty query or an instruction injected by the untrusted posting texts the agent reads.

## Decision

- **`radar_reader` can only read:** `SELECT` on all tables and views, including those created later (default privileges).
- **Its sessions also start read-only and with a 30 s statement timeout.** This is a safety margin; the grants are the real guard.

## Alternatives considered

- **Connecting every reader as `postgres`:** simplest, but any faulty query or misled agent could modify or drop data.
- **Read-only sessions alone:** a session can switch them off with `SET`.
- **A separate schema that exposes only views:** tighter, but no views exist yet; worth revisiting before the agent gets SQL access.

## Consequences

- Tables and views must be created by `postgres`, which runs the migrations, for the default privileges to apply.
- Changing the role on an existing database needs a migration.
