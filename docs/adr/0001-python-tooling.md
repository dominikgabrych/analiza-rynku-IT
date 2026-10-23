# ADR 0001: Python tooling with uv, ruff and pytest

- Status: accepted
- Date: 2026-10-14

## Context

The code has to run the same way on a developer machine, in Docker images and in CI, and the checks should be fast enough to run on every change.

## Decision

- **Python 3.14.** 3.15 was released on 2026-10-09, and libraries with compiled extensions usually need a few weeks to support a new version.
- **uv** installs the pinned interpreter, manages dependencies and writes `uv.lock`, so every environment gets the same versions.
- **ruff** lints and formats; **pytest** runs the tests.

## Alternatives considered

- **pip and venv:** no single tool for the interpreter, the environment and a lockfile.
- **Poetry:** comparable dependency management, but slower and without interpreter management.
- **flake8, isort and Black:** three tools for what ruff does alone.

## Consequences

- `uv sync` sets up the whole environment, and `uv.lock` is the single source of dependency versions, also for Docker and CI.
- Moving to Python 3.15 is a change of `.python-version` once the dependencies support it.
